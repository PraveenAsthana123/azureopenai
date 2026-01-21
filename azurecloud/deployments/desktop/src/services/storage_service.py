"""
Storage Service - Unified interface for document storage.

Supports:
- Local filesystem (offline)
- Azure Blob Storage (cloud)
- S3-compatible storage (hybrid)

Handles document uploads, downloads, and management.
"""

import hashlib
import logging
import mimetypes
import os
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Optional, BinaryIO

logger = logging.getLogger(__name__)


@dataclass
class StoredFile:
    """Stored file metadata."""
    id: str
    filename: str
    content_type: str
    size: int
    path: str
    created_at: datetime
    metadata: dict


class BaseStorageService(ABC):
    """Abstract base class for storage services."""

    @abstractmethod
    async def upload(
        self,
        file: BinaryIO,
        filename: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> StoredFile:
        """Upload a file."""
        pass

    @abstractmethod
    async def download(self, file_id: str) -> bytes:
        """Download a file by ID."""
        pass

    @abstractmethod
    async def stream(self, file_id: str) -> AsyncGenerator[bytes, None]:
        """Stream a file by ID."""
        pass

    @abstractmethod
    async def delete(self, file_id: str) -> bool:
        """Delete a file."""
        pass

    @abstractmethod
    async def list_files(
        self,
        prefix: Optional[str] = None,
        limit: int = 100
    ) -> list[StoredFile]:
        """List files."""
        pass

    @abstractmethod
    async def get_metadata(self, file_id: str) -> Optional[StoredFile]:
        """Get file metadata."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if storage is available."""
        pass


class LocalStorageService(BaseStorageService):
    """
    Local filesystem storage.

    Stores files on the local disk for offline/development use.
    """

    def __init__(
        self,
        base_path: str = "./data/documents",
        processed_path: str = "./data/processed",
        max_file_size_mb: int = 100
    ):
        self.base_path = Path(base_path)
        self.processed_path = Path(processed_path)
        self.max_file_size_mb = max_file_size_mb
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure storage directories exist."""
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.processed_path.mkdir(parents=True, exist_ok=True)

    def _generate_file_id(self, content: bytes) -> str:
        """Generate unique file ID from content hash."""
        return hashlib.sha256(content).hexdigest()[:16]

    def _get_file_path(self, file_id: str, filename: str) -> Path:
        """Get full file path."""
        # Create subdirectory from first 2 chars of ID for better distribution
        subdir = file_id[:2]
        directory = self.base_path / subdir
        directory.mkdir(exist_ok=True)
        return directory / f"{file_id}_{filename}"

    async def upload(
        self,
        file: BinaryIO,
        filename: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> StoredFile:
        """Upload a file to local storage."""
        content = file.read()
        size = len(content)

        # Check file size
        if size > self.max_file_size_mb * 1024 * 1024:
            raise ValueError(f"File exceeds maximum size of {self.max_file_size_mb}MB")

        # Generate ID and determine content type
        file_id = self._generate_file_id(content)
        if not content_type:
            content_type, _ = mimetypes.guess_type(filename)
            content_type = content_type or "application/octet-stream"

        # Save file
        file_path = self._get_file_path(file_id, filename)
        with open(file_path, "wb") as f:
            f.write(content)

        # Save metadata
        meta_path = file_path.with_suffix(file_path.suffix + ".meta")
        import json
        meta = {
            "id": file_id,
            "filename": filename,
            "content_type": content_type,
            "size": size,
            "path": str(file_path),
            "created_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        with open(meta_path, "w") as f:
            json.dump(meta, f)

        logger.info(f"Uploaded file {filename} as {file_id}")

        return StoredFile(
            id=file_id,
            filename=filename,
            content_type=content_type,
            size=size,
            path=str(file_path),
            created_at=datetime.utcnow(),
            metadata=metadata or {}
        )

    async def download(self, file_id: str) -> bytes:
        """Download a file by ID."""
        # Find file by ID prefix
        for subdir in self.base_path.iterdir():
            if subdir.is_dir():
                for file_path in subdir.iterdir():
                    if file_path.name.startswith(file_id) and not file_path.suffix == ".meta":
                        with open(file_path, "rb") as f:
                            return f.read()

        raise FileNotFoundError(f"File {file_id} not found")

    async def stream(self, file_id: str) -> AsyncGenerator[bytes, None]:
        """Stream a file by ID."""
        # Find file by ID prefix
        for subdir in self.base_path.iterdir():
            if subdir.is_dir():
                for file_path in subdir.iterdir():
                    if file_path.name.startswith(file_id) and not file_path.suffix == ".meta":
                        with open(file_path, "rb") as f:
                            while chunk := f.read(8192):
                                yield chunk
                        return

        raise FileNotFoundError(f"File {file_id} not found")

    async def delete(self, file_id: str) -> bool:
        """Delete a file."""
        deleted = False
        for subdir in self.base_path.iterdir():
            if subdir.is_dir():
                for file_path in subdir.iterdir():
                    if file_path.name.startswith(file_id):
                        file_path.unlink()
                        deleted = True

        return deleted

    async def list_files(
        self,
        prefix: Optional[str] = None,
        limit: int = 100
    ) -> list[StoredFile]:
        """List files in storage."""
        import json

        files = []
        count = 0

        for subdir in sorted(self.base_path.iterdir()):
            if not subdir.is_dir():
                continue

            for file_path in sorted(subdir.iterdir()):
                if file_path.suffix == ".meta":
                    continue

                # Check prefix filter
                if prefix and not file_path.name.startswith(prefix):
                    continue

                # Read metadata
                meta_path = file_path.with_suffix(file_path.suffix + ".meta")
                if meta_path.exists():
                    with open(meta_path) as f:
                        meta = json.load(f)
                    files.append(StoredFile(
                        id=meta["id"],
                        filename=meta["filename"],
                        content_type=meta["content_type"],
                        size=meta["size"],
                        path=meta["path"],
                        created_at=datetime.fromisoformat(meta["created_at"]),
                        metadata=meta.get("metadata", {})
                    ))
                else:
                    # Basic info without metadata
                    stat = file_path.stat()
                    files.append(StoredFile(
                        id=file_path.name.split("_")[0],
                        filename="_".join(file_path.name.split("_")[1:]),
                        content_type="application/octet-stream",
                        size=stat.st_size,
                        path=str(file_path),
                        created_at=datetime.fromtimestamp(stat.st_ctime),
                        metadata={}
                    ))

                count += 1
                if count >= limit:
                    return files

        return files

    async def get_metadata(self, file_id: str) -> Optional[StoredFile]:
        """Get file metadata."""
        import json

        for subdir in self.base_path.iterdir():
            if subdir.is_dir():
                for file_path in subdir.iterdir():
                    if file_path.name.startswith(file_id) and file_path.suffix == ".meta":
                        actual_file = file_path.with_suffix("")
                        meta_path = file_path

                        if meta_path.exists():
                            with open(meta_path) as f:
                                meta = json.load(f)
                            return StoredFile(
                                id=meta["id"],
                                filename=meta["filename"],
                                content_type=meta["content_type"],
                                size=meta["size"],
                                path=meta["path"],
                                created_at=datetime.fromisoformat(meta["created_at"]),
                                metadata=meta.get("metadata", {})
                            )

        return None

    async def health_check(self) -> bool:
        """Check if storage is accessible."""
        try:
            # Try to create and delete a test file
            test_path = self.base_path / ".health_check"
            test_path.write_text("ok")
            test_path.unlink()
            return True
        except Exception as e:
            logger.warning(f"Local storage health check failed: {e}")
            return False


class AzureBlobService(BaseStorageService):
    """
    Azure Blob Storage service.

    Enterprise-grade cloud storage with global replication.
    """

    def __init__(
        self,
        account_url: str,
        container_name: str = "documents",
        connection_string: Optional[str] = None,
        use_managed_identity: bool = False
    ):
        self.account_url = account_url
        self.container_name = container_name
        self.connection_string = connection_string
        self.use_managed_identity = use_managed_identity
        self._client = None
        self._container_client = None

    async def _get_container_client(self):
        """Get Azure Blob container client."""
        if self._container_client is not None:
            return self._container_client

        from azure.storage.blob.aio import BlobServiceClient

        if self.connection_string:
            self._client = BlobServiceClient.from_connection_string(
                self.connection_string
            )
        elif self.use_managed_identity:
            from azure.identity.aio import DefaultAzureCredential
            credential = DefaultAzureCredential()
            self._client = BlobServiceClient(
                account_url=self.account_url,
                credential=credential
            )
        else:
            raise ValueError("No authentication method provided")

        self._container_client = self._client.get_container_client(self.container_name)

        # Create container if not exists
        try:
            await self._container_client.create_container()
        except Exception:
            pass  # Container already exists

        return self._container_client

    def _generate_blob_name(self, file_id: str, filename: str) -> str:
        """Generate blob name."""
        return f"{file_id[:2]}/{file_id}/{filename}"

    async def upload(
        self,
        file: BinaryIO,
        filename: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> StoredFile:
        """Upload a file to Azure Blob."""
        container = await self._get_container_client()

        content = file.read()
        file_id = hashlib.sha256(content).hexdigest()[:16]

        if not content_type:
            content_type, _ = mimetypes.guess_type(filename)
            content_type = content_type or "application/octet-stream"

        blob_name = self._generate_blob_name(file_id, filename)
        blob_client = container.get_blob_client(blob_name)

        # Upload with metadata
        await blob_client.upload_blob(
            content,
            content_settings={"content_type": content_type},
            metadata={
                "file_id": file_id,
                "original_filename": filename,
                **(metadata or {})
            },
            overwrite=True
        )

        logger.info(f"Uploaded file {filename} to Azure Blob as {blob_name}")

        return StoredFile(
            id=file_id,
            filename=filename,
            content_type=content_type,
            size=len(content),
            path=blob_name,
            created_at=datetime.utcnow(),
            metadata=metadata or {}
        )

    async def download(self, file_id: str) -> bytes:
        """Download a file by ID."""
        container = await self._get_container_client()

        # List blobs with prefix to find the file
        prefix = f"{file_id[:2]}/{file_id}/"
        async for blob in container.list_blobs(name_starts_with=prefix):
            blob_client = container.get_blob_client(blob.name)
            download = await blob_client.download_blob()
            return await download.readall()

        raise FileNotFoundError(f"File {file_id} not found")

    async def stream(self, file_id: str) -> AsyncGenerator[bytes, None]:
        """Stream a file by ID."""
        container = await self._get_container_client()

        prefix = f"{file_id[:2]}/{file_id}/"
        async for blob in container.list_blobs(name_starts_with=prefix):
            blob_client = container.get_blob_client(blob.name)
            download = await blob_client.download_blob()

            async for chunk in download.chunks():
                yield chunk
            return

        raise FileNotFoundError(f"File {file_id} not found")

    async def delete(self, file_id: str) -> bool:
        """Delete a file."""
        container = await self._get_container_client()

        prefix = f"{file_id[:2]}/{file_id}/"
        deleted = False

        async for blob in container.list_blobs(name_starts_with=prefix):
            blob_client = container.get_blob_client(blob.name)
            await blob_client.delete_blob()
            deleted = True

        return deleted

    async def list_files(
        self,
        prefix: Optional[str] = None,
        limit: int = 100
    ) -> list[StoredFile]:
        """List files in storage."""
        container = await self._get_container_client()

        files = []
        count = 0

        async for blob in container.list_blobs(name_starts_with=prefix):
            blob_client = container.get_blob_client(blob.name)
            properties = await blob_client.get_blob_properties()

            # Extract file info from blob name
            parts = blob.name.split("/")
            file_id = parts[1] if len(parts) > 1 else parts[0]
            filename = parts[-1]

            files.append(StoredFile(
                id=file_id,
                filename=filename,
                content_type=properties.content_settings.content_type or "application/octet-stream",
                size=properties.size,
                path=blob.name,
                created_at=properties.creation_time,
                metadata=properties.metadata or {}
            ))

            count += 1
            if count >= limit:
                break

        return files

    async def get_metadata(self, file_id: str) -> Optional[StoredFile]:
        """Get file metadata."""
        container = await self._get_container_client()

        prefix = f"{file_id[:2]}/{file_id}/"
        async for blob in container.list_blobs(name_starts_with=prefix):
            blob_client = container.get_blob_client(blob.name)
            properties = await blob_client.get_blob_properties()

            parts = blob.name.split("/")
            filename = parts[-1]

            return StoredFile(
                id=file_id,
                filename=filename,
                content_type=properties.content_settings.content_type or "application/octet-stream",
                size=properties.size,
                path=blob.name,
                created_at=properties.creation_time,
                metadata=properties.metadata or {}
            )

        return None

    async def health_check(self) -> bool:
        """Check if Azure Blob is accessible."""
        try:
            container = await self._get_container_client()
            await container.get_container_properties()
            return True
        except Exception as e:
            logger.warning(f"Azure Blob health check failed: {e}")
            return False

    async def get_sas_url(
        self,
        file_id: str,
        expiry_hours: int = 1
    ) -> Optional[str]:
        """Generate SAS URL for direct access."""
        from azure.storage.blob import generate_blob_sas, BlobSasPermissions
        from datetime import timedelta

        container = await self._get_container_client()

        prefix = f"{file_id[:2]}/{file_id}/"
        async for blob in container.list_blobs(name_starts_with=prefix):
            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=self._client.account_name,
                container_name=self.container_name,
                blob_name=blob.name,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=expiry_hours)
            )

            return f"{self.account_url}/{self.container_name}/{blob.name}?{sas_token}"

        return None


# =============================================================================
# Factory Function
# =============================================================================

def create_storage_service(settings) -> BaseStorageService:
    """
    Create storage service based on settings.

    Args:
        settings: Configuration settings object

    Returns:
        Storage service instance
    """
    from config.settings import StorageProvider

    if settings.storage_provider == StorageProvider.LOCAL:
        return LocalStorageService(
            base_path=settings.local_storage.base_path,
            processed_path=settings.local_storage.processed_path,
            max_file_size_mb=settings.local_storage.max_file_size_mb
        )

    elif settings.storage_provider == StorageProvider.AZURE_BLOB:
        return AzureBlobService(
            account_url=settings.azure_blob.account_url,
            container_name=settings.azure_blob.container_name,
            connection_string=settings.azure_blob.connection_string,
            use_managed_identity=settings.azure_blob.use_managed_identity
        )

    raise ValueError(f"Unknown storage provider: {settings.storage_provider}")
