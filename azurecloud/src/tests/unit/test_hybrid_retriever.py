"""
Unit tests for Hybrid Retriever

Tests:
- Query routing and intent classification
- Query expansion
- ACL filter building
- RRF fusion
- Structure-aware boosting
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.retrieval.hybrid_retriever import (
    QueryRouter,
    QueryExpander,
    ACLFilterBuilder,
    HybridRetriever,
    NeighborStitcher,
    QueryIntent,
    ChunkType,
    UserContext,
    RetrievalConfig,
    RetrievedChunk,
)


class TestQueryRouter:
    """Tests for QueryRouter intent classification."""

    @pytest.fixture
    def router(self):
        return QueryRouter()

    @pytest.mark.parametrize("query,expected_intent", [
        # Table-related queries
        ("show me the cost table", QueryIntent.TABLE_LOOKUP),
        ("what are the pricing values", QueryIntent.TABLE_LOOKUP),
        ("list all the rates", QueryIntent.TABLE_LOOKUP),

        # Comparison queries
        ("compare Azure vs AWS pricing", QueryIntent.COMPARE_VALUES),
        ("what's the difference between v1 and v2", QueryIntent.COMPARE_VALUES),

        # Figure queries
        ("show the architecture diagram", QueryIntent.FIGURE_UNDERSTANDING),
        ("what does figure 3 look like", QueryIntent.FIGURE_UNDERSTANDING),

        # Procedure queries
        ("how to configure key vault", QueryIntent.PROCEDURE_HOWTO),
        ("steps to deploy the application", QueryIntent.PROCEDURE_HOWTO),

        # Definition queries
        ("what is a managed identity", QueryIntent.DEFINITION),
        ("define rotation interval", QueryIntent.DEFINITION),

        # General text queries
        ("tell me about security best practices", QueryIntent.TEXT_EXPLAIN),
        ("explain the authentication flow", QueryIntent.TEXT_EXPLAIN),
    ])
    def test_classify_intent(self, router, query, expected_intent):
        """Test intent classification for various query types."""
        result = router.classify_intent(query)
        assert result == expected_intent

    def test_get_retrieval_config_for_table_intent(self, router):
        """Test config adjustment for table lookups."""
        base_config = RetrievalConfig()
        config = router.get_retrieval_config_for_intent(QueryIntent.TABLE_LOOKUP, base_config)

        assert config.vector_weight == 0.5
        assert config.bm25_weight == 0.5
        assert config.table_boost == 2.0

    def test_get_retrieval_config_for_comparison(self, router):
        """Test config adjustment for comparison queries."""
        base_config = RetrievalConfig()
        config = router.get_retrieval_config_for_intent(QueryIntent.COMPARE_VALUES, base_config)

        assert config.final_top_k == 15  # Need more chunks for comparison


class TestQueryExpander:
    """Tests for QueryExpander."""

    @pytest.fixture
    def expander(self):
        return QueryExpander()

    def test_expand_query_basic(self, expander):
        """Test basic query expansion."""
        queries = expander.expand_query("key vault rotation", QueryIntent.TEXT_EXPLAIN)

        assert len(queries) >= 1
        assert "key vault rotation" in queries

    def test_abbreviation_expansion(self, expander):
        """Test abbreviation expansion."""
        queries = expander.expand_query("kv secrets", QueryIntent.TEXT_EXPLAIN)

        # Should include expanded version
        expanded = [q for q in queries if "key vault" in q.lower()]
        assert len(expanded) > 0

    def test_table_specific_expansion(self, expander):
        """Test table-specific query variants."""
        queries = expander.expand_query("pricing data", QueryIntent.TABLE_LOOKUP)

        # Should include table-specific terms
        table_variants = [q for q in queries if "table" in q.lower() or "matrix" in q.lower()]
        assert len(table_variants) > 0

    def test_deduplication(self, expander):
        """Test that duplicate queries are removed."""
        queries = expander.expand_query("test query", QueryIntent.TEXT_EXPLAIN)

        # All queries should be unique
        assert len(queries) == len(set(q.lower() for q in queries))

    def test_max_queries_limit(self, expander):
        """Test that max 6 queries are returned."""
        queries = expander.expand_query("complex query with many terms", QueryIntent.COMPARE_VALUES)

        assert len(queries) <= 6


class TestACLFilterBuilder:
    """Tests for ACL filter building."""

    @pytest.fixture
    def builder(self):
        return ACLFilterBuilder(max_groups=100)

    @pytest.fixture
    def user_context(self):
        return UserContext(
            user_id="user@company.com",
            tenant_id="tenant-123",
            groups=["group-1", "group-2", "group-3"],
            clearance_level="internal",
        )

    def test_build_basic_filter(self, builder, user_context):
        """Test basic ACL filter construction."""
        filter_str, warnings = builder.build_filter(user_context)

        assert "tenant_id eq 'tenant-123'" in filter_str
        assert "is_active eq true" in filter_str
        assert "sensitivity eq 'public'" in filter_str
        assert "user@company.com" in filter_str
        assert len(warnings) == 0

    def test_group_filter_inclusion(self, builder, user_context):
        """Test that groups are included in filter."""
        filter_str, warnings = builder.build_filter(user_context)

        assert "group-1" in filter_str
        assert "group-2" in filter_str
        assert "group-3" in filter_str

    def test_group_overflow_warning(self, builder):
        """Test warning when groups exceed limit."""
        # Create user with more groups than limit
        many_groups = [f"group-{i}" for i in range(150)]
        user = UserContext(
            user_id="user@company.com",
            tenant_id="tenant-123",
            groups=many_groups,
        )

        filter_str, warnings = builder.build_filter(user)

        assert len(warnings) > 0
        assert "truncated" in warnings[0].lower()

    def test_additional_filters(self, builder, user_context):
        """Test additional filter integration."""
        additional = {
            "doc_type": "policy",
            "department": ["engineering", "security"],
        }

        filter_str, warnings = builder.build_filter(user_context, additional)

        assert "doc_type eq 'policy'" in filter_str


class TestRetrievedChunk:
    """Tests for RetrievedChunk dataclass."""

    def test_chunk_creation(self):
        """Test chunk creation with all fields."""
        chunk = RetrievedChunk(
            id="doc1_c1",
            doc_id="doc1",
            chunk_id="c1",
            chunk_type="text",
            content="Test content",
            content_md=None,
            heading="Test Heading",
            section_path=["Section 1", "Subsection 1.1"],
            page_start=1,
            page_end=2,
            reading_order=0,
            table_headers=None,
            figure_ref=None,
            source_uri="https://storage.blob.core.windows.net/docs/test.pdf",
            doc_title="Test Document",
        )

        assert chunk.id == "doc1_c1"
        assert chunk.chunk_type == "text"
        assert chunk.vector_score == 0.0
        assert chunk.final_score == 0.0


class TestHybridRetriever:
    """Tests for HybridRetriever."""

    @pytest.fixture
    def mock_search_client(self):
        return MagicMock()

    @pytest.fixture
    def mock_embedding_client(self):
        client = AsyncMock()
        client.embeddings.create = AsyncMock(return_value=MagicMock(
            data=[MagicMock(embedding=[0.1] * 3072)]
        ))
        return client

    @pytest.fixture
    def retriever(self, mock_search_client, mock_embedding_client):
        with patch('src.retrieval.hybrid_retriever.SearchClient', return_value=mock_search_client):
            return HybridRetriever(
                search_endpoint="https://search.windows.net",
                index_name="test-index",
                embedding_client=mock_embedding_client,
            )

    def test_rrf_fusion_calculation(self, retriever):
        """Test RRF fusion score calculation."""
        config = RetrievalConfig(rrf_k=60, vector_weight=0.6, bm25_weight=0.4)

        # Create mock results
        results = [
            {
                "chunk1": RetrievedChunk(
                    id="chunk1", doc_id="doc1", chunk_id="c1",
                    chunk_type="text", content="test", content_md=None,
                    heading=None, section_path=[], page_start=1, page_end=1,
                    reading_order=0, table_headers=None, figure_ref=None,
                    source_uri="", doc_title="",
                    vector_score=1/61,  # Rank 1
                    bm25_score=1/62,    # Rank 2
                )
            }
        ]

        fused = retriever._apply_rrf_fusion(results, config)

        assert "chunk1" in fused
        assert fused["chunk1"].rrf_score > 0

    def test_structure_boosting_tables(self, retriever):
        """Test structure boosting for table chunks."""
        config = RetrievalConfig(table_boost=2.0)

        chunks = {
            "chunk1": RetrievedChunk(
                id="chunk1", doc_id="doc1", chunk_id="c1",
                chunk_type="table", content="test table", content_md=None,
                heading=None, section_path=[], page_start=1, page_end=1,
                reading_order=0, table_headers=["Col1", "Col2"], figure_ref=None,
                source_uri="", doc_title="",
                rrf_score=0.5,
            )
        }

        boosted = retriever._apply_structure_boosting(
            chunks, QueryIntent.TABLE_LOOKUP, config
        )

        # Table should be boosted for table lookup intent
        assert boosted["chunk1"].final_score == 0.5 * 2.0


class TestNeighborStitcher:
    """Tests for NeighborStitcher."""

    @pytest.fixture
    def mock_search_client(self):
        return MagicMock()

    @pytest.fixture
    def stitcher(self, mock_search_client):
        return NeighborStitcher(mock_search_client, max_neighbors=1)

    @pytest.mark.asyncio
    async def test_stitch_respects_token_budget(self, stitcher):
        """Test that stitching respects token budget."""
        chunks = [
            RetrievedChunk(
                id="chunk1", doc_id="doc1", chunk_id="c1",
                chunk_type="text", content="test", content_md=None,
                heading=None, section_path=["Section 1"], page_start=1, page_end=1,
                reading_order=0, table_headers=None, figure_ref=None,
                source_uri="", doc_title="",
                token_count=5000,  # Already at budget
            )
        ]

        result = await stitcher.stitch_neighbors(chunks, max_total_tokens=6000)

        # Should not add more chunks when already near budget
        assert len(result) == 1


# Fixtures for integration-style tests

@pytest.fixture
def sample_chunks():
    """Sample chunks for testing."""
    return [
        RetrievedChunk(
            id=f"doc1_c{i}",
            doc_id="doc1",
            chunk_id=f"c{i}",
            chunk_type="text",
            content=f"Content for chunk {i}",
            content_md=None,
            heading=f"Heading {i}",
            section_path=["Section 1"],
            page_start=i,
            page_end=i,
            reading_order=i,
            table_headers=None,
            figure_ref=None,
            source_uri="https://storage/doc1.pdf",
            doc_title="Test Document",
            token_count=100,
        )
        for i in range(5)
    ]


class TestIntegration:
    """Integration-style tests for retrieval pipeline."""

    def test_full_pipeline_data_flow(self, sample_chunks):
        """Test that data flows correctly through pipeline components."""
        router = QueryRouter()
        expander = QueryExpander()

        # Step 1: Route query
        intent = router.classify_intent("what is the rotation policy table")
        assert intent == QueryIntent.TABLE_LOOKUP

        # Step 2: Expand query
        queries = expander.expand_query("rotation policy", intent)
        assert len(queries) >= 1

        # Step 3: Get config for intent
        config = router.get_retrieval_config_for_intent(intent, RetrievalConfig())
        assert config.table_boost == 2.0
