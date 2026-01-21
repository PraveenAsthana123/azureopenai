"""
Vector Database Service - Unified interface for vector stores.

Supports:
- ChromaDB (local, offline)
- Azure AI Search (cloud)
- Qdrant (local/cloud)

Connects to Azure Search from desktop when configured.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Search result from vector store."""
    id: str
    content: str
    metadata: dict
    score: float


class BaseVectorService(ABC):
    """Abstract base class for vector database services."""

    @abstractmethod
    async def add_documents(
        self,
        documents: list[dict],
        embeddings: list[list[float]]
    ) -> list[str]:
        """Add documents with embeddings to the store."""
        pass

    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter: Optional[dict] = None
    ) -> list[SearchResult]:
        """Search for similar documents."""
        pass

    @abstractmethod
    async def delete(self, ids: list[str]) -> bool:
        """Delete documents by ID."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if service is available."""
        pass


class ChromaDBService(BaseVectorService):
    """
    ChromaDB local vector store.

    Lightweight, runs entirely locally without external dependencies.
    """

    def __init__(
        self,
        persist_directory: str = "./data/chromadb",
        collection_name: str = "rag_documents"
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self._client = None
        self._collection = None

    def _get_collection(self):
        """Get or create ChromaDB collection."""
        if self._collection is not None:
            return self._collection

        import chromadb
        from chromadb.config import Settings

        self._client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=self.persist_directory,
            anonymized_telemetry=False
        ))

        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

        return self._collection

    async def add_documents(
        self,
        documents: list[dict],
        embeddings: list[list[float]]
    ) -> list[str]:
        """Add documents with embeddings to ChromaDB."""
        collection = self._get_collection()

        ids = []
        contents = []
        metadatas = []

        for i, doc in enumerate(documents):
            doc_id = doc.get("id") or f"doc_{i}_{hash(doc['content'])}"
            ids.append(doc_id)
            contents.append(doc["content"])
            metadatas.append(doc.get("metadata", {}))

        collection.add(
            ids=ids,
            documents=contents,
            embeddings=embeddings,
            metadatas=metadatas
        )

        # Persist to disk
        self._client.persist()

        logger.info(f"Added {len(ids)} documents to ChromaDB")
        return ids

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter: Optional[dict] = None
    ) -> list[SearchResult]:
        """Search ChromaDB for similar documents."""
        collection = self._get_collection()

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter
        )

        search_results = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                search_results.append(SearchResult(
                    id=doc_id,
                    content=results["documents"][0][i] if results["documents"] else "",
                    metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                    score=1 - results["distances"][0][i] if results["distances"] else 0
                ))

        return search_results

    async def delete(self, ids: list[str]) -> bool:
        """Delete documents from ChromaDB."""
        collection = self._get_collection()
        collection.delete(ids=ids)
        self._client.persist()
        return True

    async def health_check(self) -> bool:
        """Check if ChromaDB is accessible."""
        try:
            self._get_collection()
            return True
        except Exception as e:
            logger.warning(f"ChromaDB health check failed: {e}")
            return False

    async def get_stats(self) -> dict:
        """Get collection statistics."""
        collection = self._get_collection()
        return {
            "name": self.collection_name,
            "count": collection.count(),
            "persist_directory": self.persist_directory
        }


class AzureSearchService(BaseVectorService):
    """
    Azure AI Search vector store.

    Connects to Azure Search from desktop for enterprise vector search.
    """

    def __init__(
        self,
        endpoint: str,
        index_name: str = "rag-multimodal-index",
        api_key: Optional[str] = None,
        use_managed_identity: bool = False
    ):
        self.endpoint = endpoint.rstrip("/")
        self.index_name = index_name
        self.api_key = api_key
        self.use_managed_identity = use_managed_identity
        self._client = None

    async def _get_client(self):
        """Get Azure Search client."""
        if self._client is not None:
            return self._client

        from azure.search.documents.aio import SearchClient

        if self.api_key:
            from azure.core.credentials import AzureKeyCredential
            credential = AzureKeyCredential(self.api_key)
        else:
            from azure.identity.aio import DefaultAzureCredential
            credential = DefaultAzureCredential()

        self._client = SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=credential
        )

        return self._client

    async def add_documents(
        self,
        documents: list[dict],
        embeddings: list[list[float]]
    ) -> list[str]:
        """Add documents to Azure Search."""
        client = await self._get_client()

        actions = []
        ids = []

        for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
            doc_id = doc.get("id") or f"doc_{i}"
            ids.append(doc_id)

            actions.append({
                "@search.action": "mergeOrUpload",
                "id": doc_id,
                "content_text": doc["content"],
                "content_vector": embedding,
                "metadata": doc.get("metadata", {}),
                **doc.get("metadata", {})  # Flatten metadata
            })

        result = await client.upload_documents(documents=actions)
        logger.info(f"Added {len(ids)} documents to Azure Search")
        return ids

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter: Optional[dict] = None
    ) -> list[SearchResult]:
        """Search Azure Search for similar documents."""
        client = await self._get_client()

        from azure.search.documents.models import VectorizedQuery

        vector_query = VectorizedQuery(
            vector=query_embedding,
            fields="content_vector",
            k_nearest_neighbors=top_k
        )

        # Build filter string from dict
        filter_str = None
        if filter:
            filter_parts = []
            for key, value in filter.items():
                if isinstance(value, str):
                    filter_parts.append(f"{key} eq '{value}'")
                else:
                    filter_parts.append(f"{key} eq {value}")
            filter_str = " and ".join(filter_parts)

        results = client.search(
            search_text=None,
            vector_queries=[vector_query],
            top=top_k,
            filter=filter_str,
            select=["id", "content_text", "metadata"]
        )

        search_results = []
        async for result in results:
            search_results.append(SearchResult(
                id=result.get("id", ""),
                content=result.get("content_text", ""),
                metadata=result.get("metadata", {}),
                score=result.get("@search.score", 0)
            ))

        return search_results

    async def delete(self, ids: list[str]) -> bool:
        """Delete documents from Azure Search."""
        client = await self._get_client()

        actions = [{"@search.action": "delete", "id": doc_id} for doc_id in ids]
        await client.delete_documents(documents=actions)
        return True

    async def health_check(self) -> bool:
        """Check if Azure Search is accessible."""
        try:
            client = await self._get_client()
            # Try to get document count
            async for _ in client.search(search_text="*", top=1):
                pass
            return True
        except Exception as e:
            logger.warning(f"Azure Search health check failed: {e}")
            return False

    async def hybrid_search(
        self,
        query_text: str,
        query_embedding: list[float],
        top_k: int = 5,
        filter: Optional[dict] = None
    ) -> list[SearchResult]:
        """Hybrid search combining text and vector search."""
        client = await self._get_client()

        from azure.search.documents.models import VectorizedQuery

        vector_query = VectorizedQuery(
            vector=query_embedding,
            fields="content_vector",
            k_nearest_neighbors=top_k
        )

        results = client.search(
            search_text=query_text,
            vector_queries=[vector_query],
            top=top_k,
            query_type="semantic",
            semantic_configuration_name="default"
        )

        search_results = []
        async for result in results:
            search_results.append(SearchResult(
                id=result.get("id", ""),
                content=result.get("content_text", ""),
                metadata=result.get("metadata", {}),
                score=result.get("@search.score", 0)
            ))

        return search_results


class QdrantService(BaseVectorService):
    """
    Qdrant vector store (local or cloud).

    Alternative to ChromaDB with better performance for large datasets.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        collection_name: str = "rag_documents",
        api_key: Optional[str] = None
    ):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.api_key = api_key
        self._client = None

    async def _get_client(self):
        """Get Qdrant client."""
        if self._client is not None:
            return self._client

        from qdrant_client import QdrantClient

        self._client = QdrantClient(
            host=self.host,
            port=self.port,
            api_key=self.api_key
        )

        return self._client

    async def add_documents(
        self,
        documents: list[dict],
        embeddings: list[list[float]]
    ) -> list[str]:
        """Add documents to Qdrant."""
        from qdrant_client.models import PointStruct

        client = await self._get_client()

        points = []
        ids = []

        for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
            doc_id = doc.get("id") or str(i)
            ids.append(doc_id)

            points.append(PointStruct(
                id=hash(doc_id) % (2**63),  # Qdrant needs int IDs
                vector=embedding,
                payload={
                    "content": doc["content"],
                    "metadata": doc.get("metadata", {}),
                    "doc_id": doc_id
                }
            ))

        client.upsert(
            collection_name=self.collection_name,
            points=points
        )

        return ids

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter: Optional[dict] = None
    ) -> list[SearchResult]:
        """Search Qdrant for similar documents."""
        client = await self._get_client()

        results = client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k
        )

        return [
            SearchResult(
                id=str(r.payload.get("doc_id", r.id)),
                content=r.payload.get("content", ""),
                metadata=r.payload.get("metadata", {}),
                score=r.score
            )
            for r in results
        ]

    async def delete(self, ids: list[str]) -> bool:
        """Delete documents from Qdrant."""
        client = await self._get_client()
        from qdrant_client.models import PointIdsList

        int_ids = [hash(doc_id) % (2**63) for doc_id in ids]
        client.delete(
            collection_name=self.collection_name,
            points_selector=PointIdsList(points=int_ids)
        )
        return True

    async def health_check(self) -> bool:
        """Check if Qdrant is accessible."""
        try:
            client = await self._get_client()
            client.get_collections()
            return True
        except Exception as e:
            logger.warning(f"Qdrant health check failed: {e}")
            return False


# =============================================================================
# Factory Function
# =============================================================================

def create_vector_service(settings) -> BaseVectorService:
    """
    Create vector service based on settings.

    Args:
        settings: Configuration settings object

    Returns:
        Vector service instance
    """
    from config.settings import VectorDBProvider

    if settings.vector_db_provider == VectorDBProvider.CHROMADB:
        return ChromaDBService(
            persist_directory=settings.chromadb.persist_directory,
            collection_name=settings.chromadb.collection_name
        )

    elif settings.vector_db_provider == VectorDBProvider.AZURE_SEARCH:
        return AzureSearchService(
            endpoint=settings.azure_search.endpoint,
            index_name=settings.azure_search.index_name,
            api_key=settings.azure_search.api_key,
            use_managed_identity=settings.azure_search.use_managed_identity
        )

    elif settings.vector_db_provider == VectorDBProvider.QDRANT:
        return QdrantService(
            collection_name="rag_documents"
        )

    raise ValueError(f"Unknown vector DB provider: {settings.vector_db_provider}")
