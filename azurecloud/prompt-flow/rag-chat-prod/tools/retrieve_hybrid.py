"""
Secure Hybrid Retrieval Tool for Prompt Flow.

Performs hybrid search (vector + keyword) with:
- Azure AI Search integration
- RBAC security trimming
- Multi-modal chunk support (text, tables, images)
"""

import os
import time
import logging
from typing import TypedDict

from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.identity.aio import DefaultAzureCredential
from openai import AsyncAzureOpenAI

logger = logging.getLogger(__name__)


class ChunkMetadata(TypedDict):
    source_pdf: str
    page_number: int
    chunk_type: str
    bounding_box: list | None


class Chunk(TypedDict):
    chunk_id: str
    content: str
    content_type: str
    metadata: ChunkMetadata
    score: float


class RetrievalOutput(TypedDict):
    chunks: list[Chunk]
    query_used: str
    latency_ms: float
    total_results: int


# Configuration from environment
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX", "rag-multimodal-index")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_EMB_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT", "text-embedding-3-large")

# Clients (lazy initialization)
_search_client = None
_openai_client = None
_credential = None


async def get_clients():
    """Lazy initialize clients with managed identity."""
    global _search_client, _openai_client, _credential

    if _search_client and _openai_client:
        return _search_client, _openai_client

    _credential = DefaultAzureCredential()

    _search_client = SearchClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        index_name=AZURE_SEARCH_INDEX,
        credential=_credential
    )

    _openai_client = AsyncAzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        azure_ad_token_provider=lambda: _credential.get_token(
            "https://cognitiveservices.azure.com/.default"
        ).token,
        api_version="2024-02-15-preview"
    )

    return _search_client, _openai_client


async def embed_query(openai_client: AsyncAzureOpenAI, text: str) -> list[float]:
    """Generate embedding for query text."""
    response = await openai_client.embeddings.create(
        model=AZURE_OPENAI_EMB_DEPLOYMENT,
        input=text
    )
    return response.data[0].embedding


async def retrieve_hybrid(
    query: str,
    user_id: str,
    tenant_id: str = "default",
    top_k: int = 5,
    min_score: float = 0.5
) -> RetrievalOutput:
    """
    Perform secure hybrid retrieval.

    Args:
        query: Search query (may be rewritten)
        user_id: User ID for RBAC filtering
        tenant_id: Tenant ID for multi-tenancy
        top_k: Number of results to return
        min_score: Minimum relevance score threshold

    Returns:
        RetrievalOutput with chunks and metadata
    """
    start_time = time.time()

    search_client, openai_client = await get_clients()

    # Generate query embedding
    query_embedding = await embed_query(openai_client, query)

    # Build vector query
    vector_query = VectorizedQuery(
        vector=query_embedding,
        fields="content_vector",
        k_nearest_neighbors=top_k,
        exhaustive=False
    )

    # Build security filter (RBAC)
    # Users can only see documents they have access to
    security_filter = f"tenant_id eq '{tenant_id}' and (acl_users/any(u: u eq '{user_id}') or acl_users/any(u: u eq 'all'))"

    # Execute hybrid search
    results = search_client.search(
        search_text=query,
        vector_queries=[vector_query],
        filter=security_filter,
        top=top_k,
        select=[
            "chunk_id",
            "content_text",
            "content_type",
            "table_markdown",
            "image_description",
            "metadata",
            "source_pdf",
            "page_number"
        ],
        query_type="semantic",
        semantic_configuration_name="default"
    )

    # Process results
    chunks = []
    async for result in results:
        score = result.get("@search.score", 0)

        if score < min_score:
            continue

        # Determine content based on type
        content_type = result.get("content_type", "text")
        if content_type == "table":
            content = result.get("table_markdown", result.get("content_text", ""))
        elif content_type == "image":
            content = result.get("image_description", "")
        else:
            content = result.get("content_text", "")

        chunks.append({
            "chunk_id": result.get("chunk_id", "unknown"),
            "content": content,
            "content_type": content_type,
            "metadata": {
                "source_pdf": result.get("source_pdf", ""),
                "page_number": result.get("page_number", 0),
                "chunk_type": content_type,
                "bounding_box": result.get("metadata", {}).get("bounding_box")
            },
            "score": round(score, 4)
        })

    latency_ms = (time.time() - start_time) * 1000

    return {
        "chunks": chunks,
        "query_used": query,
        "latency_ms": round(latency_ms, 2),
        "total_results": len(chunks)
    }


# Prompt Flow entry point
async def main(
    query: str,
    user_id: str,
    tenant_id: str = "default"
) -> RetrievalOutput:
    """Entry point for Prompt Flow."""
    return await retrieve_hybrid(query, user_id, tenant_id)


if __name__ == "__main__":
    import asyncio

    async def test():
        result = await retrieve_hybrid(
            query="What is the retention policy?",
            user_id="test@company.com",
            tenant_id="default"
        )
        print(f"Found {result['total_results']} chunks in {result['latency_ms']}ms")
        for chunk in result["chunks"]:
            print(f"  - {chunk['chunk_id']}: {chunk['content'][:100]}...")

    asyncio.run(test())
