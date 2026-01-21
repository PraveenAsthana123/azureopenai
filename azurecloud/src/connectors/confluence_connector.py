"""
Confluence Wiki Connector
Supports both Confluence Cloud and Confluence Server/Data Center.
"""

import asyncio
import base64
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterator
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class ConfluencePage:
    """Represents a Confluence page."""
    id: str
    title: str
    space_key: str
    space_name: str
    web_url: str
    content_html: str
    content_text: str
    version: int
    created_at: datetime
    modified_at: datetime
    created_by: str
    modified_by: str
    parent_id: str | None
    ancestors: list[str]
    labels: list[str]
    attachments: list[dict]
    restrictions: list[str]


class ConfluenceConnector:
    """
    Connector for Atlassian Confluence.
    Supports both Cloud (API token) and Server (personal access token).
    """

    def __init__(
        self,
        base_url: str,
        username: str | None = None,
        api_token: str | None = None,
        personal_access_token: str | None = None,
        batch_size: int = 50,
        is_cloud: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.api_token = api_token
        self.personal_access_token = personal_access_token
        self.batch_size = batch_size
        self.is_cloud = is_cloud
        self.session = None

        # API paths differ between Cloud and Server
        if is_cloud:
            self.api_base = f"{self.base_url}/wiki/rest/api"
        else:
            self.api_base = f"{self.base_url}/rest/api"

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self):
        """Initialize HTTP session with authentication."""
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        if self.personal_access_token:
            # Server/Data Center with PAT
            headers["Authorization"] = f"Bearer {self.personal_access_token}"
        elif self.username and self.api_token:
            # Cloud with API token
            auth_str = base64.b64encode(f"{self.username}:{self.api_token}".encode()).decode()
            headers["Authorization"] = f"Basic {auth_str}"

        self.session = aiohttp.ClientSession(headers=headers)
        logger.info(f"Confluence connector initialized: {self.base_url}")

    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()

    async def _make_request(self, endpoint: str, params: dict | None = None) -> dict:
        """Make authenticated request to Confluence API."""
        url = urljoin(self.api_base + "/", endpoint.lstrip("/"))

        async with self.session.get(url, params=params) as response:
            if response.status == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Rate limited, waiting {retry_after}s")
                await asyncio.sleep(retry_after)
                return await self._make_request(endpoint, params)

            response.raise_for_status()
            return await response.json()

    def _html_to_text(self, html: str) -> str:
        """Convert HTML content to plain text."""
        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer"]):
            element.decompose()

        # Get text with some structure preserved
        text = soup.get_text(separator="\n", strip=True)

        # Clean up multiple newlines
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        return "\n".join(lines)

    async def list_spaces(self) -> list[dict]:
        """List all accessible Confluence spaces."""
        spaces = []
        start = 0

        while True:
            data = await self._make_request(
                "/space",
                params={"start": start, "limit": self.batch_size, "expand": "description.plain"}
            )

            spaces.extend(data.get("results", []))

            if data.get("size", 0) < self.batch_size:
                break
            start += self.batch_size

        logger.info(f"Found {len(spaces)} Confluence spaces")
        return spaces

    async def list_pages(
        self,
        space_key: str,
        modified_since: datetime | None = None,
    ) -> AsyncIterator[ConfluencePage]:
        """List all pages in a space."""
        start = 0
        expand = "body.storage,version,ancestors,metadata.labels,restrictions.read.restrictions.group"

        while True:
            params = {
                "spaceKey": space_key,
                "start": start,
                "limit": self.batch_size,
                "expand": expand,
            }

            data = await self._make_request("/content", params=params)

            for page_data in data.get("results", []):
                page = await self._parse_page(page_data, space_key)

                # Filter by modified date if specified
                if modified_since and page.modified_at < modified_since:
                    continue

                yield page

            if data.get("size", 0) < self.batch_size:
                break
            start += self.batch_size

    async def _parse_page(self, data: dict, space_key: str) -> ConfluencePage:
        """Parse API response into ConfluencePage object."""
        # Extract content
        body = data.get("body", {}).get("storage", {}).get("value", "")

        # Extract version info
        version = data.get("version", {})

        # Extract ancestors (parent pages)
        ancestors = [a.get("title", "") for a in data.get("ancestors", [])]

        # Extract labels
        labels = [
            label.get("name", "")
            for label in data.get("metadata", {}).get("labels", {}).get("results", [])
        ]

        # Extract read restrictions (for RBAC)
        restrictions = []
        read_restrictions = data.get("restrictions", {}).get("read", {}).get("restrictions", {})
        for group in read_restrictions.get("group", {}).get("results", []):
            restrictions.append(group.get("name", ""))

        # Get space name
        space_name = data.get("space", {}).get("name", space_key)

        return ConfluencePage(
            id=data["id"],
            title=data.get("title", ""),
            space_key=space_key,
            space_name=space_name,
            web_url=urljoin(self.base_url, data.get("_links", {}).get("webui", "")),
            content_html=body,
            content_text=self._html_to_text(body),
            version=version.get("number", 1),
            created_at=datetime.fromisoformat(data.get("history", {}).get("createdDate", "").replace("Z", "+00:00")) if data.get("history", {}).get("createdDate") else datetime.now(),
            modified_at=datetime.fromisoformat(version.get("when", "").replace("Z", "+00:00")) if version.get("when") else datetime.now(),
            created_by=data.get("history", {}).get("createdBy", {}).get("email", ""),
            modified_by=version.get("by", {}).get("email", ""),
            parent_id=data.get("ancestors", [{}])[-1].get("id") if data.get("ancestors") else None,
            ancestors=ancestors,
            labels=labels,
            attachments=[],
            restrictions=restrictions,
        )

    async def get_page(self, page_id: str) -> ConfluencePage:
        """Get a single page by ID."""
        expand = "body.storage,version,ancestors,metadata.labels,restrictions.read.restrictions.group,space"

        data = await self._make_request(f"/content/{page_id}", params={"expand": expand})
        return await self._parse_page(data, data.get("space", {}).get("key", ""))

    async def get_page_attachments(self, page_id: str) -> list[dict]:
        """Get attachments for a page."""
        attachments = []
        start = 0

        while True:
            data = await self._make_request(
                f"/content/{page_id}/child/attachment",
                params={"start": start, "limit": self.batch_size}
            )

            for att in data.get("results", []):
                attachments.append({
                    "id": att["id"],
                    "title": att.get("title", ""),
                    "filename": att.get("title", ""),
                    "media_type": att.get("metadata", {}).get("mediaType", ""),
                    "size": att.get("extensions", {}).get("fileSize", 0),
                    "download_url": urljoin(
                        self.base_url,
                        att.get("_links", {}).get("download", "")
                    ),
                })

            if data.get("size", 0) < self.batch_size:
                break
            start += self.batch_size

        return attachments

    async def download_attachment(self, download_url: str) -> bytes:
        """Download attachment content."""
        async with self.session.get(download_url) as response:
            response.raise_for_status()
            return await response.read()

    async def search(
        self,
        cql: str,
        limit: int = 100,
    ) -> AsyncIterator[ConfluencePage]:
        """
        Search Confluence using CQL (Confluence Query Language).
        Example CQL: "space = DEV and type = page and lastModified > now('-7d')"
        """
        start = 0
        expand = "body.storage,version,ancestors,metadata.labels"

        while True:
            params = {
                "cql": cql,
                "start": start,
                "limit": min(self.batch_size, limit - start),
                "expand": expand,
            }

            data = await self._make_request("/content/search", params=params)

            for result in data.get("results", []):
                page = await self._parse_page(result, result.get("space", {}).get("key", ""))
                yield page

            if data.get("size", 0) < self.batch_size or start + data.get("size", 0) >= limit:
                break
            start += self.batch_size

    async def get_recently_modified(
        self,
        space_key: str | None = None,
        days: int = 7,
    ) -> AsyncIterator[ConfluencePage]:
        """Get pages modified in the last N days."""
        cql = f"type = page and lastModified > now('-{days}d')"
        if space_key:
            cql = f"space = {space_key} and {cql}"

        async for page in self.search(cql):
            yield page

    async def sync_space(
        self,
        space_key: str,
        last_sync: datetime | None = None,
        include_attachments: bool = False,
    ) -> AsyncIterator[ConfluencePage]:
        """
        Sync all pages from a space.
        If last_sync is provided, only returns pages modified since then.
        """
        async for page in self.list_pages(space_key, modified_since=last_sync):
            if include_attachments:
                page.attachments = await self.get_page_attachments(page.id)

            yield page
