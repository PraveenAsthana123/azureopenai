"""
Hybrid Retrieval Service with RRF Fusion

Implements:
- Multi-query expansion
- BM25 + Vector hybrid search
- Reciprocal Rank Fusion (RRF)
- Structure-aware boosting
- ACL-aware filtering with overflow handling
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import asyncio
import hashlib
import json
from datetime import datetime

from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import (
    VectorizedQuery,
    QueryType,
    QueryCaptionType,
    QueryAnswerType,
)


class QueryIntent(Enum):
    """Query intent classification for routing."""
    TEXT_EXPLAIN = "text_explain"
    TABLE_LOOKUP = "table_lookup"
    COMPARE_VALUES = "compare_values"
    FIGURE_UNDERSTANDING = "figure_understanding"
    PROCEDURE_HOWTO = "procedure_howto"
    DEFINITION = "definition"
    GENERAL = "general"


class ChunkType(Enum):
    """Types of chunks in the index."""
    TEXT = "text"
    TABLE = "table"
    IMAGE_CAPTION = "image_caption"
    CODE = "code"


@dataclass
class UserContext:
    """Security context for the current user."""
    user_id: str
    tenant_id: str
    groups: list[str] = field(default_factory=list)
    clearance_level: str = "public"
    department: str | None = None


@dataclass
class RetrievalConfig:
    """Configuration for retrieval operations."""
    # Search parameters
    vector_k: int = 40
    bm25_top: int = 40
    final_top_k: int = 12

    # Fusion weights (vector_weight + bm25_weight should = 1.0)
    vector_weight: float = 0.6
    bm25_weight: float = 0.4

    # RRF parameters
    rrf_k: int = 60  # Smoothing constant

    # Boosting
    table_boost: float = 1.5
    image_boost: float = 1.3
    recency_boost: float = 1.2

    # ACL handling
    max_acl_groups: int = 100  # Azure Search search.in() limit workaround

    # Semantic search
    use_semantic_ranker: bool = True
    semantic_config: str = "semantic-config"


@dataclass
class RetrievedChunk:
    """A retrieved chunk with all metadata."""
    id: str
    doc_id: str
    chunk_id: str
    chunk_type: str
    content: str
    content_md: str | None
    heading: str | None
    section_path: list[str]
    page_start: int | None
    page_end: int | None
    reading_order: int
    table_headers: list[str] | None
    figure_ref: str | None
    source_uri: str
    doc_title: str | None

    # Scores
    vector_score: float = 0.0
    bm25_score: float = 0.0
    rrf_score: float = 0.0
    final_score: float = 0.0
    semantic_score: float | None = None

    # Metadata
    entities: list[str] = field(default_factory=list)
    token_count: int = 0


@dataclass
class RetrievalResult:
    """Result of a retrieval operation."""
    chunks: list[RetrievedChunk]
    query: str
    rewritten_queries: list[str]
    intent: QueryIntent
    total_candidates: int
    retrieval_time_ms: float
    filters_applied: dict[str, Any]
    warnings: list[str] = field(default_factory=list)


class QueryRouter:
    """Routes queries based on intent classification."""

    # Keywords that indicate specific intents
    TABLE_KEYWORDS = {
        "table", "matrix", "schedule", "rate", "cost", "price",
        "compare", "versus", "vs", "difference", "percentage",
        "count", "total", "sum", "average", "max", "min",
        "list", "values", "numbers", "data"
    }

    FIGURE_KEYWORDS = {
        "figure", "diagram", "chart", "graph", "image", "picture",
        "show", "look like", "visual", "illustration", "screenshot"
    }

    PROCEDURE_KEYWORDS = {
        "how to", "how do", "steps", "procedure", "process",
        "instructions", "guide", "tutorial", "setup", "configure"
    }

    DEFINITION_KEYWORDS = {
        "what is", "what are", "define", "definition", "meaning",
        "explain", "describe"
    }

    def classify_intent(self, query: str) -> QueryIntent:
        """Classify query intent using rule-based approach."""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        # Check for table-related queries
        if query_words & self.TABLE_KEYWORDS:
            if any(kw in query_lower for kw in ["compare", "versus", "vs", "difference"]):
                return QueryIntent.COMPARE_VALUES
            return QueryIntent.TABLE_LOOKUP

        # Check for figure-related queries
        if query_words & self.FIGURE_KEYWORDS:
            return QueryIntent.FIGURE_UNDERSTANDING

        # Check for procedural queries
        if any(kw in query_lower for kw in self.PROCEDURE_KEYWORDS):
            return QueryIntent.PROCEDURE_HOWTO

        # Check for definition queries
        if any(kw in query_lower for kw in self.DEFINITION_KEYWORDS):
            return QueryIntent.DEFINITION

        return QueryIntent.TEXT_EXPLAIN

    def get_retrieval_config_for_intent(
        self,
        intent: QueryIntent,
        base_config: RetrievalConfig
    ) -> RetrievalConfig:
        """Adjust retrieval config based on intent."""
        config = RetrievalConfig(
            vector_k=base_config.vector_k,
            bm25_top=base_config.bm25_top,
            final_top_k=base_config.final_top_k,
            vector_weight=base_config.vector_weight,
            bm25_weight=base_config.bm25_weight,
            rrf_k=base_config.rrf_k,
            table_boost=base_config.table_boost,
            image_boost=base_config.image_boost,
            recency_boost=base_config.recency_boost,
            max_acl_groups=base_config.max_acl_groups,
            use_semantic_ranker=base_config.use_semantic_ranker,
            semantic_config=base_config.semantic_config,
        )

        if intent == QueryIntent.TABLE_LOOKUP:
            config.vector_weight = 0.5
            config.bm25_weight = 0.5
            config.table_boost = 2.0

        elif intent == QueryIntent.COMPARE_VALUES:
            config.vector_weight = 0.5
            config.bm25_weight = 0.5
            config.table_boost = 2.0
            config.final_top_k = 15  # Need more chunks for comparison

        elif intent == QueryIntent.FIGURE_UNDERSTANDING:
            config.image_boost = 2.0
            config.vector_weight = 0.7  # Captions benefit from semantic

        elif intent == QueryIntent.PROCEDURE_HOWTO:
            config.final_top_k = 10
            config.recency_boost = 1.5  # Prefer recent procedures

        elif intent == QueryIntent.DEFINITION:
            config.vector_weight = 0.7
            config.bm25_weight = 0.3

        return config


class QueryExpander:
    """Expands queries into multiple search variants."""

    # Common abbreviation expansions
    ABBREVIATIONS = {
        "kv": "key vault",
        "vm": "virtual machine",
        "rg": "resource group",
        "nsg": "network security group",
        "vnet": "virtual network",
        "lb": "load balancer",
        "aks": "azure kubernetes service",
        "acr": "azure container registry",
        "sql": "structured query language",
        "api": "application programming interface",
        "auth": "authentication",
        "config": "configuration",
        "env": "environment",
    }

    def expand_query(self, query: str, intent: QueryIntent) -> list[str]:
        """Generate multiple query variants for better recall."""
        queries = [query]  # Original query first
        query_lower = query.lower()

        # Abbreviation expansion
        expanded = query_lower
        for abbr, full in self.ABBREVIATIONS.items():
            if abbr in query_lower.split():
                expanded = expanded.replace(abbr, full)
        if expanded != query_lower:
            queries.append(expanded)

        # Intent-specific rewrites
        if intent == QueryIntent.TABLE_LOOKUP:
            queries.append(f"{query} table data values")
            queries.append(f"{query} schedule matrix")

        elif intent == QueryIntent.COMPARE_VALUES:
            queries.append(f"{query} comparison differences")
            queries.append(f"{query} versus change")

        elif intent == QueryIntent.FIGURE_UNDERSTANDING:
            queries.append(f"{query} diagram figure illustration")
            queries.append(f"{query} visual chart")

        elif intent == QueryIntent.PROCEDURE_HOWTO:
            queries.append(f"steps to {query}")
            queries.append(f"how to {query} guide")

        elif intent == QueryIntent.DEFINITION:
            queries.append(f"definition of {query}")
            queries.append(f"what is {query} meaning")

        # Deduplicate while preserving order
        seen = set()
        unique_queries = []
        for q in queries:
            q_normalized = q.strip().lower()
            if q_normalized not in seen:
                seen.add(q_normalized)
                unique_queries.append(q.strip())

        return unique_queries[:6]  # Max 6 variants


class ACLFilterBuilder:
    """Builds ACL filters with overflow handling."""

    def __init__(self, max_groups: int = 100):
        self.max_groups = max_groups

    def build_filter(
        self,
        user_context: UserContext,
        additional_filters: dict[str, Any] | None = None
    ) -> tuple[str, list[str]]:
        """
        Build OData filter string for ACL enforcement.

        Returns:
            Tuple of (filter_string, warnings)
        """
        warnings = []
        filter_parts = []

        # Tenant isolation (always required)
        filter_parts.append(f"tenant_id eq '{user_context.tenant_id}'")

        # Active chunks only
        filter_parts.append("is_active eq true")

        # ACL filtering
        acl_conditions = []

        # Public documents
        acl_conditions.append("sensitivity eq 'public'")

        # User-specific access
        acl_conditions.append(f"acl_users/any(u: u eq '{user_context.user_id}')")

        # Group-based access with overflow handling
        if user_context.groups:
            if len(user_context.groups) > self.max_groups:
                # Truncate and warn
                warnings.append(
                    f"User has {len(user_context.groups)} groups, "
                    f"truncated to {self.max_groups} for search filter. "
                    "Some documents may not be visible."
                )
                groups_to_use = user_context.groups[:self.max_groups]
            else:
                groups_to_use = user_context.groups

            # Build search.in() clause
            groups_csv = ",".join(groups_to_use)
            acl_conditions.append(f"acl_groups/any(g: search.in(g, '{groups_csv}'))")

        # Combine ACL conditions with OR
        acl_filter = f"({' or '.join(acl_conditions)})"
        filter_parts.append(acl_filter)

        # Add any additional filters
        if additional_filters:
            for field, value in additional_filters.items():
                if isinstance(value, list):
                    # Collection filter
                    values_csv = ",".join(str(v) for v in value)
                    filter_parts.append(f"{field}/any(x: search.in(x, '{values_csv}'))")
                elif isinstance(value, str):
                    filter_parts.append(f"{field} eq '{value}'")
                elif isinstance(value, bool):
                    filter_parts.append(f"{field} eq {str(value).lower()}")
                elif isinstance(value, (int, float)):
                    filter_parts.append(f"{field} eq {value}")

        return " and ".join(filter_parts), warnings


class HybridRetriever:
    """
    Main hybrid retrieval service.

    Combines:
    - Vector search (semantic similarity)
    - BM25 (keyword matching)
    - Reciprocal Rank Fusion
    - Structure-aware boosting
    - ACL filtering
    """

    def __init__(
        self,
        search_endpoint: str,
        index_name: str,
        embedding_client: Any,  # Azure OpenAI client for embeddings
        config: RetrievalConfig | None = None,
        credential: DefaultAzureCredential | None = None,
    ):
        self.search_endpoint = search_endpoint
        self.index_name = index_name
        self.embedding_client = embedding_client
        self.config = config or RetrievalConfig()
        self.credential = credential or DefaultAzureCredential()

        self.search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=index_name,
            credential=self.credential,
        )

        self.query_router = QueryRouter()
        self.query_expander = QueryExpander()
        self.acl_builder = ACLFilterBuilder(max_groups=self.config.max_acl_groups)

    async def retrieve(
        self,
        query: str,
        user_context: UserContext,
        additional_filters: dict[str, Any] | None = None,
        override_config: RetrievalConfig | None = None,
    ) -> RetrievalResult:
        """
        Execute hybrid retrieval with full pipeline.

        Args:
            query: User's search query
            user_context: Security context
            additional_filters: Extra OData filters
            override_config: Override default config

        Returns:
            RetrievalResult with ranked chunks
        """
        start_time = datetime.utcnow()
        warnings = []

        # Step 1: Classify intent
        intent = self.query_router.classify_intent(query)

        # Step 2: Get intent-specific config
        config = override_config or self.query_router.get_retrieval_config_for_intent(
            intent, self.config
        )

        # Step 3: Expand query
        rewritten_queries = self.query_expander.expand_query(query, intent)

        # Step 4: Build ACL filter
        filter_string, acl_warnings = self.acl_builder.build_filter(
            user_context, additional_filters
        )
        warnings.extend(acl_warnings)

        # Step 5: Execute searches in parallel
        all_results = await self._execute_parallel_searches(
            queries=rewritten_queries,
            filter_string=filter_string,
            config=config,
        )

        # Step 6: Apply RRF fusion
        fused_results = self._apply_rrf_fusion(all_results, config)

        # Step 7: Apply structure-aware boosting
        boosted_results = self._apply_structure_boosting(fused_results, intent, config)

        # Step 8: Select top-k
        final_chunks = sorted(
            boosted_results.values(),
            key=lambda x: x.final_score,
            reverse=True
        )[:config.final_top_k]

        # Calculate timing
        end_time = datetime.utcnow()
        retrieval_time_ms = (end_time - start_time).total_seconds() * 1000

        return RetrievalResult(
            chunks=final_chunks,
            query=query,
            rewritten_queries=rewritten_queries,
            intent=intent,
            total_candidates=len(fused_results),
            retrieval_time_ms=retrieval_time_ms,
            filters_applied={"filter": filter_string},
            warnings=warnings,
        )

    async def _execute_parallel_searches(
        self,
        queries: list[str],
        filter_string: str,
        config: RetrievalConfig,
    ) -> list[dict[str, RetrievedChunk]]:
        """Execute vector and BM25 searches for all query variants."""

        async def search_single_query(q: str) -> dict[str, RetrievedChunk]:
            """Execute both vector and BM25 for one query."""
            results = {}

            # Get embedding for vector search
            embedding = await self._get_embedding(q)

            # Vector search
            vector_query = VectorizedQuery(
                vector=embedding,
                k_nearest_neighbors=config.vector_k,
                fields="embedding",
            )

            vector_results = self.search_client.search(
                search_text=None,
                vector_queries=[vector_query],
                filter=filter_string,
                select=[
                    "id", "doc_id", "chunk_id", "chunk_type", "content",
                    "content_md", "heading", "section_path", "page_start",
                    "page_end", "reading_order", "table_headers", "figure_ref",
                    "source_uri", "doc_title", "entities", "chunk_token_count"
                ],
                top=config.vector_k,
            )

            for rank, result in enumerate(vector_results, 1):
                chunk_id = result["id"]
                if chunk_id not in results:
                    results[chunk_id] = self._result_to_chunk(result)
                # Store vector rank for RRF
                results[chunk_id].vector_score = 1 / (config.rrf_k + rank)

            # BM25 search
            bm25_results = self.search_client.search(
                search_text=q,
                query_type=QueryType.FULL,
                filter=filter_string,
                select=[
                    "id", "doc_id", "chunk_id", "chunk_type", "content",
                    "content_md", "heading", "section_path", "page_start",
                    "page_end", "reading_order", "table_headers", "figure_ref",
                    "source_uri", "doc_title", "entities", "chunk_token_count"
                ],
                top=config.bm25_top,
                semantic_configuration_name=(
                    config.semantic_config if config.use_semantic_ranker else None
                ),
                query_caption=QueryCaptionType.EXTRACTIVE if config.use_semantic_ranker else None,
                query_answer=QueryAnswerType.EXTRACTIVE if config.use_semantic_ranker else None,
            )

            for rank, result in enumerate(bm25_results, 1):
                chunk_id = result["id"]
                if chunk_id not in results:
                    results[chunk_id] = self._result_to_chunk(result)
                # Store BM25 rank for RRF
                results[chunk_id].bm25_score = 1 / (config.rrf_k + rank)

                # Capture semantic score if available
                if hasattr(result, "@search.reranker_score"):
                    results[chunk_id].semantic_score = result["@search.reranker_score"]

            return results

        # Execute all queries in parallel
        tasks = [search_single_query(q) for q in queries]
        all_results = await asyncio.gather(*tasks)

        return all_results

    def _apply_rrf_fusion(
        self,
        all_results: list[dict[str, RetrievedChunk]],
        config: RetrievalConfig,
    ) -> dict[str, RetrievedChunk]:
        """Apply Reciprocal Rank Fusion across all query results."""
        fused = {}

        for result_dict in all_results:
            for chunk_id, chunk in result_dict.items():
                if chunk_id not in fused:
                    fused[chunk_id] = chunk
                    fused[chunk_id].rrf_score = 0

                # Accumulate RRF scores
                weighted_vector = chunk.vector_score * config.vector_weight
                weighted_bm25 = chunk.bm25_score * config.bm25_weight
                fused[chunk_id].rrf_score += weighted_vector + weighted_bm25

        # Normalize RRF scores
        if fused:
            max_score = max(c.rrf_score for c in fused.values())
            if max_score > 0:
                for chunk in fused.values():
                    chunk.rrf_score /= max_score

        return fused

    def _apply_structure_boosting(
        self,
        chunks: dict[str, RetrievedChunk],
        intent: QueryIntent,
        config: RetrievalConfig,
    ) -> dict[str, RetrievedChunk]:
        """Apply structure-aware boosting based on chunk type."""
        for chunk in chunks.values():
            boost = 1.0

            # Type-based boosting
            if chunk.chunk_type == ChunkType.TABLE.value:
                if intent in [QueryIntent.TABLE_LOOKUP, QueryIntent.COMPARE_VALUES]:
                    boost *= config.table_boost

            elif chunk.chunk_type == ChunkType.IMAGE_CAPTION.value:
                if intent == QueryIntent.FIGURE_UNDERSTANDING:
                    boost *= config.image_boost

            # Semantic score boost (if available)
            if chunk.semantic_score is not None:
                boost *= (1 + chunk.semantic_score * 0.2)

            # Calculate final score
            chunk.final_score = chunk.rrf_score * boost

        return chunks

    async def _get_embedding(self, text: str) -> list[float]:
        """Get embedding for text using Azure OpenAI."""
        response = await self.embedding_client.embeddings.create(
            input=text,
            model="text-embedding-3-large",
        )
        return response.data[0].embedding

    def _result_to_chunk(self, result: dict) -> RetrievedChunk:
        """Convert search result to RetrievedChunk."""
        return RetrievedChunk(
            id=result.get("id", ""),
            doc_id=result.get("doc_id", ""),
            chunk_id=result.get("chunk_id", ""),
            chunk_type=result.get("chunk_type", "text"),
            content=result.get("content", ""),
            content_md=result.get("content_md"),
            heading=result.get("heading"),
            section_path=result.get("section_path", []),
            page_start=result.get("page_start"),
            page_end=result.get("page_end"),
            reading_order=result.get("reading_order", 0),
            table_headers=result.get("table_headers"),
            figure_ref=result.get("figure_ref"),
            source_uri=result.get("source_uri", ""),
            doc_title=result.get("doc_title"),
            entities=result.get("entities", []),
            token_count=result.get("chunk_token_count", 0),
        )


class NeighborStitcher:
    """Stitches neighboring chunks for context coherence."""

    def __init__(self, search_client: SearchClient, max_neighbors: int = 1):
        self.search_client = search_client
        self.max_neighbors = max_neighbors

    async def stitch_neighbors(
        self,
        chunks: list[RetrievedChunk],
        max_total_tokens: int = 6000,
    ) -> list[RetrievedChunk]:
        """
        Add neighboring chunks for coherence.

        Rules:
        - Only stitch if same section_path
        - Don't cross table/figure boundaries
        - Respect token budget
        """
        result = []
        current_tokens = sum(c.token_count for c in chunks)
        seen_ids = {c.id for c in chunks}

        for chunk in chunks:
            result.append(chunk)

            if current_tokens >= max_total_tokens:
                break

            # Try to get neighbors
            neighbors = await self._get_neighbors(
                chunk.doc_id,
                chunk.reading_order,
                chunk.section_path,
            )

            for neighbor in neighbors:
                if neighbor["id"] in seen_ids:
                    continue

                # Check if we can add this neighbor
                neighbor_tokens = neighbor.get("chunk_token_count", 0)
                if current_tokens + neighbor_tokens > max_total_tokens:
                    continue

                # Don't stitch across different chunk types
                if neighbor.get("chunk_type") != chunk.chunk_type:
                    continue

                # Add neighbor
                neighbor_chunk = RetrievedChunk(
                    id=neighbor["id"],
                    doc_id=neighbor["doc_id"],
                    chunk_id=neighbor["chunk_id"],
                    chunk_type=neighbor["chunk_type"],
                    content=neighbor["content"],
                    content_md=neighbor.get("content_md"),
                    heading=neighbor.get("heading"),
                    section_path=neighbor.get("section_path", []),
                    page_start=neighbor.get("page_start"),
                    page_end=neighbor.get("page_end"),
                    reading_order=neighbor["reading_order"],
                    table_headers=neighbor.get("table_headers"),
                    figure_ref=neighbor.get("figure_ref"),
                    source_uri=neighbor["source_uri"],
                    doc_title=neighbor.get("doc_title"),
                    token_count=neighbor_tokens,
                    final_score=chunk.final_score * 0.8,  # Slightly lower score
                )

                result.append(neighbor_chunk)
                seen_ids.add(neighbor["id"])
                current_tokens += neighbor_tokens

        # Sort by document and reading order for coherent presentation
        result.sort(key=lambda c: (c.doc_id, c.reading_order))

        return result

    async def _get_neighbors(
        self,
        doc_id: str,
        reading_order: int,
        section_path: list[str],
    ) -> list[dict]:
        """Fetch neighboring chunks by reading order."""
        # Get chunks with reading_order ± max_neighbors
        filter_str = (
            f"doc_id eq '{doc_id}' and "
            f"reading_order ge {reading_order - self.max_neighbors} and "
            f"reading_order le {reading_order + self.max_neighbors} and "
            f"reading_order ne {reading_order}"
        )

        results = self.search_client.search(
            search_text="*",
            filter=filter_str,
            select=[
                "id", "doc_id", "chunk_id", "chunk_type", "content",
                "content_md", "heading", "section_path", "page_start",
                "page_end", "reading_order", "table_headers", "figure_ref",
                "source_uri", "doc_title", "chunk_token_count"
            ],
            top=self.max_neighbors * 2,
        )

        neighbors = []
        for result in results:
            # Only include if same section (for coherence)
            if result.get("section_path") == section_path:
                neighbors.append(result)

        return neighbors
