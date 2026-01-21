"""
SharePoint/OneDrive Connector
Uses Microsoft Graph API for document extraction from SharePoint sites and OneDrive.
"""

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterator

import aiohttp
from azure.identity.aio import DefaultAzureCredential

logger = logging.getLogger(__name__)


@dataclass
class SharePointDocument:
    """Represents a document from SharePoint."""
    id: str
    name: str
    web_url: str
    drive_id: str
    site_id: str
    content_type: str
    size: int
    created_at: datetime
    modified_at: datetime
    created_by: str
    modified_by: str
    etag: str
    parent_path: str
    content: bytes | None = None
    metadata: dict | None = None


class SharePointConnector:
    """
    Connector for SharePoint Online and OneDrive for Business.
    Uses Microsoft Graph API with managed identity authentication.
    """

    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".txt", ".md", ".html"}

    def __init__(
        self,
        tenant_id: str | None = None,
        client_id: str | None = None,
        batch_size: int = 100,
        max_file_size_mb: int = 50,
    ):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.batch_size = batch_size
        self.max_file_size = max_file_size_mb * 1024 * 1024
        self.credential = None
        self.session = None
        self._token = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self):
        """Initialize connection and get access token."""
        self.credential = DefaultAzureCredential()
        self._token = await self.credential.get_token("https://graph.microsoft.com/.default")
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self._token.token}",
                "Content-Type": "application/json",
            }
        )
        logger.info("SharePoint connector initialized")

    async def close(self):
        """Close connections."""
        if self.session:
            await self.session.close()
        if self.credential:
            await self.credential.close()

    async def _make_request(self, url: str, method: str = "GET") -> dict:
        """Make authenticated request to Graph API."""
        async with self.session.request(method, url) as response:
            if response.status == 429:
                # Rate limited - wait and retry
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Rate limited, waiting {retry_after}s")
                await asyncio.sleep(retry_after)
                return await self._make_request(url, method)

            response.raise_for_status()
            return await response.json()

    async def _download_file(self, download_url: str) -> bytes:
        """Download file content."""
        async with self.session.get(download_url) as response:
            response.raise_for_status()
            return await response.read()

    async def list_sites(self) -> list[dict]:
        """List all SharePoint sites the app has access to."""
        sites = []
        url = f"{self.GRAPH_BASE_URL}/sites?search=*"

        while url:
            data = await self._make_request(url)
            sites.extend(data.get("value", []))
            url = data.get("@odata.nextLink")

        logger.info(f"Found {len(sites)} SharePoint sites")
        return sites

    async def list_drives(self, site_id: str) -> list[dict]:
        """List document libraries (drives) in a site."""
        url = f"{self.GRAPH_BASE_URL}/sites/{site_id}/drives"
        data = await self._make_request(url)
        return data.get("value", [])

    async def list_documents(
        self,
        site_id: str,
        drive_id: str,
        folder_path: str = "root",
        modified_since: datetime | None = None,
    ) -> AsyncIterator[SharePointDocument]:
        """
        List all documents in a drive/folder.
        Supports incremental sync via modified_since.
        """
        url = f"{self.GRAPH_BASE_URL}/sites/{site_id}/drives/{drive_id}/items/{folder_path}/children"

        if modified_since:
            filter_date = modified_since.isoformat() + "Z"
            url += f"?$filter=lastModifiedDateTime ge {filter_date}"

        while url:
            data = await self._make_request(url)

            for item in data.get("value", []):
                # Recurse into folders
                if "folder" in item:
                    async for doc in self.list_documents(
                        site_id, drive_id, item["id"], modified_since
                    ):
                        yield doc

                # Process files
                elif "file" in item:
                    # Check file extension
                    name = item.get("name", "")
                    ext = "." + name.split(".")[-1].lower() if "." in name else ""

                    if ext not in self.SUPPORTED_EXTENSIONS:
                        continue

                    # Check file size
                    if item.get("size", 0) > self.max_file_size:
                        logger.warning(f"Skipping large file: {name} ({item['size']} bytes)")
                        continue

                    yield SharePointDocument(
                        id=item["id"],
                        name=name,
                        web_url=item.get("webUrl", ""),
                        drive_id=drive_id,
                        site_id=site_id,
                        content_type=item.get("file", {}).get("mimeType", ""),
                        size=item.get("size", 0),
                        created_at=datetime.fromisoformat(item["createdDateTime"].replace("Z", "+00:00")),
                        modified_at=datetime.fromisoformat(item["lastModifiedDateTime"].replace("Z", "+00:00")),
                        created_by=item.get("createdBy", {}).get("user", {}).get("email", ""),
                        modified_by=item.get("lastModifiedBy", {}).get("user", {}).get("email", ""),
                        etag=item.get("eTag", ""),
                        parent_path=item.get("parentReference", {}).get("path", ""),
                    )

            url = data.get("@odata.nextLink")

    async def download_document(self, doc: SharePointDocument) -> SharePointDocument:
        """Download document content."""
        url = f"{self.GRAPH_BASE_URL}/sites/{doc.site_id}/drives/{doc.drive_id}/items/{doc.id}/content"

        async with self.session.get(url, allow_redirects=True) as response:
            response.raise_for_status()
            doc.content = await response.read()

        return doc

    async def get_document_permissions(self, doc: SharePointDocument) -> list[str]:
        """Get document permissions (for RBAC)."""
        url = f"{self.GRAPH_BASE_URL}/sites/{doc.site_id}/drives/{doc.drive_id}/items/{doc.id}/permissions"

        try:
            data = await self._make_request(url)
            permissions = []

            for perm in data.get("value", []):
                if "grantedToV2" in perm:
                    granted = perm["grantedToV2"]
                    if "group" in granted:
                        permissions.append(granted["group"].get("id", ""))
                    if "user" in granted:
                        permissions.append(granted["user"].get("id", ""))

            return permissions
        except Exception as e:
            logger.warning(f"Could not get permissions for {doc.name}: {e}")
            return []

    async def get_delta(self, site_id: str, drive_id: str, delta_token: str | None = None) -> tuple[list[dict], str]:
        """
        Get changes since last sync using delta query.
        Returns (changes, new_delta_token).
        """
        if delta_token:
            url = f"{self.GRAPH_BASE_URL}/sites/{site_id}/drives/{drive_id}/root/delta?token={delta_token}"
        else:
            url = f"{self.GRAPH_BASE_URL}/sites/{site_id}/drives/{drive_id}/root/delta"

        changes = []
        new_token = None

        while url:
            data = await self._make_request(url)
            changes.extend(data.get("value", []))

            # Get next page or delta link
            url = data.get("@odata.nextLink")
            if "@odata.deltaLink" in data:
                # Extract token from delta link
                delta_link = data["@odata.deltaLink"]
                new_token = delta_link.split("token=")[-1] if "token=" in delta_link else None

        return changes, new_token

    async def sync_site(
        self,
        site_id: str,
        delta_token: str | None = None,
        include_content: bool = True,
    ) -> AsyncIterator[tuple[SharePointDocument, str]]:
        """
        Sync all documents from a site.
        Yields (document, action) where action is 'upsert' or 'delete'.
        """
        drives = await self.list_drives(site_id)

        for drive in drives:
            drive_id = drive["id"]
            changes, new_token = await self.get_delta(site_id, drive_id, delta_token)

            for item in changes:
                # Check if deleted
                if "deleted" in item:
                    yield SharePointDocument(
                        id=item["id"],
                        name=item.get("name", ""),
                        web_url="",
                        drive_id=drive_id,
                        site_id=site_id,
                        content_type="",
                        size=0,
                        created_at=datetime.now(),
                        modified_at=datetime.now(),
                        created_by="",
                        modified_by="",
                        etag="",
                        parent_path="",
                    ), "delete"
                    continue

                # Skip folders
                if "folder" in item:
                    continue

                # Check file extension
                name = item.get("name", "")
                ext = "." + name.split(".")[-1].lower() if "." in name else ""

                if ext not in self.SUPPORTED_EXTENSIONS:
                    continue

                doc = SharePointDocument(
                    id=item["id"],
                    name=name,
                    web_url=item.get("webUrl", ""),
                    drive_id=drive_id,
                    site_id=site_id,
                    content_type=item.get("file", {}).get("mimeType", ""),
                    size=item.get("size", 0),
                    created_at=datetime.fromisoformat(item["createdDateTime"].replace("Z", "+00:00")),
                    modified_at=datetime.fromisoformat(item["lastModifiedDateTime"].replace("Z", "+00:00")),
                    created_by=item.get("createdBy", {}).get("user", {}).get("email", ""),
                    modified_by=item.get("lastModifiedBy", {}).get("user", {}).get("email", ""),
                    etag=item.get("eTag", ""),
                    parent_path=item.get("parentReference", {}).get("path", ""),
                )

                if include_content:
                    doc = await self.download_document(doc)

                yield doc, "upsert"


def compute_document_hash(content: bytes) -> str:
    """Compute SHA256 hash of document content."""
    return hashlib.sha256(content).hexdigest()
