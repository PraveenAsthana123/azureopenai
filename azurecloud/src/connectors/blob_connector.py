"""
Azure Blob Storage Connector
Extracts documents from Azure Blob Storage containers.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterator

from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient, ContainerClient

logger = logging.getLogger(__name__)


@dataclass
class BlobDocument:
    """Represents a document from Azure Blob Storage."""
    id: str
    name: str
    container: str
    storage_account: str
    url: str
    content_type: str
    size: int
    created_at: datetime
    modified_at: datetime
    etag: str
    content_hash: str
    metadata: dict
    content: bytes | None = None


class BlobStorageConnector:
    """
    Connector for Azure Blob Storage.
    Uses managed identity authentication.
    """

    SUPPORTED_EXTENSIONS = {
        ".pdf", ".docx", ".doc", ".pptx", ".ppt",
        ".xlsx", ".xls", ".txt", ".md", ".html",
        ".htm", ".json", ".xml", ".csv"
    }

    def __init__(
        self,
        storage_account_name: str,
        container_name: str | None = None,
        max_file_size_mb: int = 100,
    ):
        self.storage_account_name = storage_account_name
        self.container_name = container_name
        self.max_file_size = max_file_size_mb * 1024 * 1024
        self.account_url = f"https://{storage_account_name}.blob.core.windows.net"
        self.credential = None
        self.service_client = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self):
        """Initialize connection with managed identity."""
        self.credential = DefaultAzureCredential()
        self.service_client = BlobServiceClient(
            account_url=self.account_url,
            credential=self.credential,
        )
        logger.info(f"Blob Storage connector initialized: {self.storage_account_name}")

    async def close(self):
        """Close connections."""
        if self.service_client:
            await self.service_client.close()
        if self.credential:
            await self.credential.close()

    async def list_containers(self) -> list[str]:
        """List all containers in the storage account."""
        containers = []
        async for container in self.service_client.list_containers():
            containers.append(container["name"])
        return containers

    async def list_documents(
        self,
        container_name: str | None = None,
        prefix: str = "",
        modified_since: datetime | None = None,
    ) -> AsyncIterator[BlobDocument]:
        """
        List documents in a container.
        Supports filtering by prefix and modification date.
        """
        container = container_name or self.container_name
        if not container:
            raise ValueError("Container name must be specified")

        container_client = self.service_client.get_container_client(container)

        async for blob in container_client.list_blobs(name_starts_with=prefix):
            # Check file extension
            name = blob["name"]
            ext = "." + name.split(".")[-1].lower() if "." in name else ""

            if ext not in self.SUPPORTED_EXTENSIONS:
                continue

            # Check file size
            if blob["size"] > self.max_file_size:
                logger.warning(f"Skipping large file: {name} ({blob['size']} bytes)")
                continue

            # Check modification date
            modified_at = blob["last_modified"]
            if modified_since and modified_at < modified_since:
                continue

            yield BlobDocument(
                id=f"{self.storage_account_name}/{container}/{name}",
                name=name,
                container=container,
                storage_account=self.storage_account_name,
                url=f"{self.account_url}/{container}/{name}",
                content_type=blob.get("content_settings", {}).get("content_type", ""),
                size=blob["size"],
                created_at=blob.get("creation_time", modified_at),
                modified_at=modified_at,
                etag=blob["etag"],
                content_hash=blob.get("content_settings", {}).get("content_md5", ""),
                metadata=blob.get("metadata", {}),
            )

    async def download_document(self, doc: BlobDocument) -> BlobDocument:
        """Download document content."""
        container_client = self.service_client.get_container_client(doc.container)
        blob_client = container_client.get_blob_client(doc.name)

        download = await blob_client.download_blob()
        doc.content = await download.readall()

        return doc

    async def download_by_path(self, container: str, blob_path: str) -> bytes:
        """Download blob by path."""
        container_client = self.service_client.get_container_client(container)
        blob_client = container_client.get_blob_client(blob_path)

        download = await blob_client.download_blob()
        return await download.readall()

    async def upload_document(
        self,
        container: str,
        blob_path: str,
        content: bytes,
        content_type: str = "application/octet-stream",
        metadata: dict | None = None,
    ) -> str:
        """Upload a document to blob storage."""
        container_client = self.service_client.get_container_client(container)
        blob_client = container_client.get_blob_client(blob_path)

        await blob_client.upload_blob(
            content,
            overwrite=True,
            content_settings={"content_type": content_type},
            metadata=metadata,
        )

        return blob_client.url

    async def sync_container(
        self,
        container_name: str | None = None,
        prefix: str = "",
        last_sync: datetime | None = None,
        include_content: bool = True,
    ) -> AsyncIterator[BlobDocument]:
        """
        Sync documents from a container.
        Yields documents modified since last_sync.
        """
        async for doc in self.list_documents(
            container_name=container_name,
            prefix=prefix,
            modified_since=last_sync,
        ):
            if include_content:
                doc = await self.download_document(doc)
            yield doc

    async def get_blob_metadata(self, container: str, blob_path: str) -> dict:
        """Get metadata for a specific blob."""
        container_client = self.service_client.get_container_client(container)
        blob_client = container_client.get_blob_client(blob_path)

        properties = await blob_client.get_blob_properties()
        return {
            "name": blob_path,
            "size": properties["size"],
            "content_type": properties["content_settings"]["content_type"],
            "created": properties.get("creation_time"),
            "modified": properties["last_modified"],
            "etag": properties["etag"],
            "metadata": properties.get("metadata", {}),
        }

    async def set_blob_metadata(self, container: str, blob_path: str, metadata: dict):
        """Set metadata for a specific blob."""
        container_client = self.service_client.get_container_client(container)
        blob_client = container_client.get_blob_client(blob_path)

        await blob_client.set_blob_metadata(metadata)

    async def delete_blob(self, container: str, blob_path: str):
        """Delete a blob."""
        container_client = self.service_client.get_container_client(container)
        blob_client = container_client.get_blob_client(blob_path)

        await blob_client.delete_blob()
