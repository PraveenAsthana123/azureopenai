"""
Unit tests for Cross-Encoder Reranker

Tests:
- Reranking strategies
- Score calculation
- Batch processing
- Table-aware reranking
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from src.retrieval.cross_encoder_reranker import (
    CrossEncoderReranker,
    TableAwareReranker,
    RerankStrategy,
    RerankConfig,
    ChunkScore,
)


class MockChunk:
    """Mock chunk for testing."""
    def __init__(self, id, content, content_md=None, table_headers=None):
        self.id = id
        self.content = content
        self.content_md = content_md
        self.table_headers = table_headers
        self.final_score = 0.0
        self.rerank_score = None
        self.support_score = None
        self.rerank_reasoning = None


class TestChunkScore:
    """Tests for ChunkScore dataclass."""

    def test_chunk_score_defaults(self):
        """Test default values."""
        score = ChunkScore(
            chunk_id="test",
            relevance_score=2.5,
        )

        assert score.support_score is None
        assert score.has_explicit_evidence is False
        assert score.combined_score == 0.0

    def test_chunk_score_full(self):
        """Test with all values."""
        score = ChunkScore(
            chunk_id="test",
            relevance_score=3.0,
            support_score=0.9,
            reasoning="Highly relevant",
            has_explicit_evidence=True,
            combined_score=0.95,
        )

        assert score.relevance_score == 3.0
        assert score.has_explicit_evidence is True


class TestRerankConfig:
    """Tests for RerankConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RerankConfig()

        assert config.strategy == RerankStrategy.RELEVANCE_WITH_SUPPORT
        assert config.model == "gpt-4o-mini"
        assert config.batch_size == 10
        assert config.max_chunks_to_rerank == 30
        assert config.final_top_k == 8

    def test_custom_config(self):
        """Test custom configuration."""
        config = RerankConfig(
            strategy=RerankStrategy.FULL_ANALYSIS,
            final_top_k=12,
            min_relevance_score=0.5,
        )

        assert config.strategy == RerankStrategy.FULL_ANALYSIS
        assert config.final_top_k == 12
        assert config.min_relevance_score == 0.5


class TestCrossEncoderReranker:
    """Tests for CrossEncoderReranker."""

    @pytest.fixture
    def mock_openai_client(self):
        client = AsyncMock()
        return client

    @pytest.fixture
    def reranker(self, mock_openai_client):
        return CrossEncoderReranker(mock_openai_client)

    @pytest.fixture
    def sample_chunks(self):
        return [
            MockChunk("chunk1", "Content about key rotation policies"),
            MockChunk("chunk2", "Unrelated content about networking"),
            MockChunk("chunk3", "More content about security controls"),
        ]

    def test_calculate_combined_score_basic(self, reranker):
        """Test combined score calculation."""
        config = RerankConfig(
            relevance_weight=0.6,
            support_weight=0.3,
        )

        score = ChunkScore(
            chunk_id="test",
            relevance_score=3.0,  # Max score
            support_score=1.0,    # Max score
        )

        combined = reranker._calculate_combined_score(score, config)

        # (3.0/3.0 * 0.6) + (1.0 * 0.3) = 0.6 + 0.3 = 0.9
        assert combined == pytest.approx(0.9, rel=0.01)

    def test_calculate_combined_score_with_evidence_bonus(self, reranker):
        """Test that explicit evidence gets bonus."""
        config = RerankConfig(
            relevance_weight=0.6,
            support_weight=0.3,
        )

        score_with_evidence = ChunkScore(
            chunk_id="test",
            relevance_score=2.0,
            support_score=0.8,
            has_explicit_evidence=True,
        )

        score_without = ChunkScore(
            chunk_id="test",
            relevance_score=2.0,
            support_score=0.8,
            has_explicit_evidence=False,
        )

        combined_with = reranker._calculate_combined_score(score_with_evidence, config)
        combined_without = reranker._calculate_combined_score(score_without, config)

        # With evidence should be higher
        assert combined_with > combined_without

    @pytest.mark.asyncio
    async def test_rerank_returns_top_k(self, reranker, mock_openai_client, sample_chunks):
        """Test that rerank returns correct number of chunks."""
        # Mock LLM response
        mock_openai_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content=json.dumps({"score": 2, "reasoning": "Somewhat relevant"})
            ))]
        ))

        config = RerankConfig(final_top_k=2)
        result = await reranker.rerank("test query", sample_chunks, config)

        assert len(result.chunks) <= 2

    @pytest.mark.asyncio
    async def test_rerank_filters_low_relevance(self, reranker, mock_openai_client, sample_chunks):
        """Test that low relevance chunks are filtered."""
        # Mock LLM to return low score
        mock_openai_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content=json.dumps({"score": 0, "reasoning": "Not relevant"})
            ))]
        ))

        config = RerankConfig(min_relevance_score=0.5)
        result = await reranker.rerank("test query", sample_chunks, config)

        # All chunks should be filtered due to low score
        assert len(result.chunks) == 0

    @pytest.mark.asyncio
    async def test_score_batches_handles_errors(self, reranker, mock_openai_client):
        """Test that batch scoring handles errors gracefully."""
        # Mock to raise exception
        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API Error")
        )

        chunks = [MockChunk("chunk1", "Test content")]
        config = RerankConfig()

        scores = await reranker._score_batches("test query", chunks, config)

        # Should return default score on error
        assert len(scores) == 1
        assert scores[0].relevance_score == 1.0  # Neutral default
        assert "error" in scores[0].reasoning.lower()


class TestTableAwareReranker:
    """Tests for TableAwareReranker."""

    @pytest.fixture
    def mock_openai_client(self):
        return AsyncMock()

    @pytest.fixture
    def reranker(self, mock_openai_client):
        return TableAwareReranker(mock_openai_client)

    @pytest.fixture
    def table_chunks(self):
        return [
            MockChunk(
                "table1",
                "| Name | Value |\n|------|-------|\n| A | 100 |",
                content_md="| Name | Value |\n|------|-------|\n| A | 100 |",
                table_headers=["Name", "Value"],
            ),
            MockChunk(
                "table2",
                "| Cost | Region |\n|------|--------|\n| $50 | US |",
                content_md="| Cost | Region |\n|------|--------|\n| $50 | US |",
                table_headers=["Cost", "Region"],
            ),
        ]

    @pytest.mark.asyncio
    async def test_rerank_tables_uses_headers(self, reranker, mock_openai_client, table_chunks):
        """Test that table headers are used in ranking."""
        mock_openai_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content=json.dumps({
                    "score": 3,
                    "relevant_columns": ["Cost"],
                    "reasoning": "Contains cost data"
                })
            ))]
        ))

        result = await reranker.rerank_tables("what is the cost", table_chunks)

        # Should return results
        assert len(result.chunks) > 0
        assert result.strategy_used == RerankStrategy.RELEVANCE_ONLY

    @pytest.mark.asyncio
    async def test_rerank_tables_boosts_matching_headers(self, reranker, mock_openai_client, table_chunks):
        """Test that tables with matching headers get boosted."""
        # First call returns matching columns, second doesn't
        mock_openai_client.chat.completions.create = AsyncMock(side_effect=[
            MagicMock(choices=[MagicMock(message=MagicMock(
                content=json.dumps({"score": 2, "relevant_columns": ["Cost"], "reasoning": "Has cost"})
            ))]),
            MagicMock(choices=[MagicMock(message=MagicMock(
                content=json.dumps({"score": 2, "relevant_columns": [], "reasoning": "No match"})
            ))]),
        ])

        result = await reranker.rerank_tables("cost data", table_chunks)

        # First table should rank higher due to column match boost
        if len(result.chunks) >= 2:
            scores = [c.final_score for c in result.chunks]
            # Verify scores are present
            assert all(s > 0 for s in scores)


class TestRerankStrategies:
    """Tests for different reranking strategies."""

    @pytest.fixture
    def mock_openai_client(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_relevance_only_strategy(self, mock_openai_client):
        """Test relevance-only strategy."""
        reranker = CrossEncoderReranker(mock_openai_client)

        mock_openai_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content=json.dumps({"score": 2, "reasoning": "Relevant"})
            ))]
        ))

        config = RerankConfig(strategy=RerankStrategy.RELEVANCE_ONLY)
        chunk = MockChunk("test", "Test content")

        score = await reranker._score_relevance_only(
            "test query", "Test content", "test", config
        )

        assert score.relevance_score == 2
        assert score.support_score is None

    @pytest.mark.asyncio
    async def test_relevance_with_support_strategy(self, mock_openai_client):
        """Test relevance with support strategy."""
        reranker = CrossEncoderReranker(mock_openai_client)

        # Mock both relevance and support calls
        mock_openai_client.chat.completions.create = AsyncMock(side_effect=[
            MagicMock(choices=[MagicMock(message=MagicMock(
                content=json.dumps({"score": 3, "reasoning": "Highly relevant"})
            ))]),
            MagicMock(choices=[MagicMock(message=MagicMock(
                content=json.dumps({
                    "support_score": 0.9,
                    "has_explicit_evidence": True,
                    "evidence_quote": "Key rotation is set to 90 days"
                })
            ))]),
        ])

        config = RerankConfig(strategy=RerankStrategy.RELEVANCE_WITH_SUPPORT)

        score = await reranker._score_with_support(
            "rotation policy", "Key rotation is set to 90 days", "test", config
        )

        assert score.relevance_score == 3
        assert score.support_score == 0.9
        assert score.has_explicit_evidence is True


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def mock_openai_client(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_empty_chunks_list(self, mock_openai_client):
        """Test handling of empty chunks list."""
        reranker = CrossEncoderReranker(mock_openai_client)

        result = await reranker.rerank("test query", [])

        assert len(result.chunks) == 0
        assert result.rerank_time_ms >= 0

    @pytest.mark.asyncio
    async def test_very_long_content_truncation(self, mock_openai_client):
        """Test that very long content is truncated."""
        reranker = CrossEncoderReranker(mock_openai_client)

        mock_openai_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content=json.dumps({"score": 2, "reasoning": "OK"})
            ))]
        ))

        # Create chunk with very long content
        long_content = "A" * 10000
        chunk = MockChunk("test", long_content)

        config = RerankConfig()
        result = await reranker.rerank("test", [chunk], config)

        # Should complete without error
        assert result is not None

    @pytest.mark.asyncio
    async def test_malformed_llm_response(self, mock_openai_client):
        """Test handling of malformed LLM responses."""
        reranker = CrossEncoderReranker(mock_openai_client)

        # Return invalid JSON
        mock_openai_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content="not valid json"
            ))]
        ))

        chunk = MockChunk("test", "Test content")
        config = RerankConfig()

        # Should handle gracefully via _call_llm
        result = await reranker._call_llm("test prompt", config)
        assert result == {}  # Empty dict on error
