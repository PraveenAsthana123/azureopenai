"""
Unit Tests for Chunking Module
"""

import pytest
from src.shared.chunking import (
    DocumentChunker,
    ChunkingConfig,
    ChunkingStrategy,
    TokenCounter,
    TokenBudgetManager,
    Chunk,
)


class TestTokenCounter:
    """Tests for TokenCounter class."""

    def test_count_tokens_basic(self):
        """Test basic token counting."""
        text = "Hello, world!"
        count = TokenCounter.count_tokens(text)
        assert count > 0
        assert count < 10

    def test_count_tokens_empty(self):
        """Test token counting for empty string."""
        assert TokenCounter.count_tokens("") == 0

    def test_count_tokens_unicode(self):
        """Test token counting for unicode text."""
        text = "こんにちは世界"  # Hello world in Japanese
        count = TokenCounter.count_tokens(text)
        assert count > 0

    def test_truncate_to_tokens(self):
        """Test text truncation to token limit."""
        text = "This is a longer text that should be truncated to fit within the token limit."
        truncated = TokenCounter.truncate_to_tokens(text, 5)
        assert TokenCounter.count_tokens(truncated) <= 5

    def test_split_by_tokens(self):
        """Test splitting text by token count."""
        text = "This is a test. " * 50  # Long text
        chunks = TokenCounter.split_by_tokens(text, 20)

        assert len(chunks) > 1
        for chunk in chunks:
            assert TokenCounter.count_tokens(chunk) <= 25  # Allow some flexibility


class TestDocumentChunker:
    """Tests for DocumentChunker class."""

    @pytest.fixture
    def chunker(self):
        """Create a chunker with default config."""
        config = ChunkingConfig(
            strategy=ChunkingStrategy.HEADING_AWARE,
            max_tokens=100,
            min_tokens=10,
            overlap_tokens=20,
        )
        return DocumentChunker(config)

    def test_chunk_simple_text(self, chunker):
        """Test chunking simple text."""
        text = "This is a simple test document. " * 20
        chunks = chunker.chunk_document("doc1", text, "Test Document")

        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.document_id == "doc1"
            assert chunk.token_count > 0
            assert chunk.text

    def test_chunk_with_headings(self, chunker):
        """Test chunking text with markdown headings."""
        text = """# Introduction
This is the introduction section with some content.

## Section One
Content for section one goes here with more details.

## Section Two
Content for section two goes here with additional information.

### Subsection
A nested subsection with its own content.
"""
        chunks = chunker.chunk_document("doc1", text, "Test Document")

        assert len(chunks) > 0
        # Check that headings are preserved
        heading_paths = [c.heading_path for c in chunks]
        assert any("Introduction" in h for h in heading_paths)

    def test_chunk_ordering(self, chunker):
        """Test that chunks maintain document order."""
        text = "Section A content. " * 20 + "Section B content. " * 20
        chunks = chunker.chunk_document("doc1", text)

        for i, chunk in enumerate(chunks):
            assert chunk.chunk_order == i

    def test_chunk_ids_unique(self, chunker):
        """Test that chunk IDs are unique."""
        text = "Test content. " * 50
        chunks = chunker.chunk_document("doc1", text)

        chunk_ids = [c.chunk_id for c in chunks]
        assert len(chunk_ids) == len(set(chunk_ids))

    def test_fixed_size_chunking(self):
        """Test fixed-size chunking strategy."""
        config = ChunkingConfig(
            strategy=ChunkingStrategy.FIXED_SIZE,
            max_tokens=50,
            overlap_tokens=10,
        )
        chunker = DocumentChunker(config)

        text = "Word " * 200  # Long text
        chunks = chunker.chunk_document("doc1", text)

        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.token_count <= 60  # Allow some flexibility

    def test_sentence_chunking(self):
        """Test sentence-based chunking strategy."""
        config = ChunkingConfig(
            strategy=ChunkingStrategy.SENTENCE,
            max_tokens=50,
        )
        chunker = DocumentChunker(config)

        text = "This is sentence one. This is sentence two. This is sentence three. " * 10
        chunks = chunker.chunk_document("doc1", text)

        assert len(chunks) > 0

    def test_paragraph_chunking(self):
        """Test paragraph-based chunking strategy."""
        config = ChunkingConfig(
            strategy=ChunkingStrategy.PARAGRAPH,
            max_tokens=100,
        )
        chunker = DocumentChunker(config)

        text = """First paragraph with some content.

Second paragraph with different content.

Third paragraph with more information."""

        chunks = chunker.chunk_document("doc1", text)
        assert len(chunks) > 0

    def test_empty_document(self, chunker):
        """Test chunking empty document."""
        chunks = chunker.chunk_document("doc1", "")
        assert len(chunks) == 0

    def test_chunk_metadata(self, chunker):
        """Test that chunks include proper metadata."""
        text = "# Test Heading\n\nContent goes here. " * 20
        chunks = chunker.chunk_document("doc1", text, "My Document")

        for chunk in chunks:
            assert chunk.document_id == "doc1"
            assert chunk.chunk_id
            assert isinstance(chunk.token_count, int)


class TestTokenBudgetManager:
    """Tests for TokenBudgetManager class."""

    @pytest.fixture
    def budget_manager(self):
        """Create a budget manager."""
        return TokenBudgetManager(
            max_context_tokens=4000,
            max_response_tokens=1000,
            system_prompt_tokens=500,
        )

    def test_calculate_available_tokens(self, budget_manager):
        """Test available token calculation."""
        available = budget_manager.calculate_available_tokens(query_tokens=50)

        # 4000 - 500 - 1000 - 50 = 2450
        assert available == 2450

    def test_calculate_with_conversation(self, budget_manager):
        """Test available tokens with conversation history."""
        available = budget_manager.calculate_available_tokens(
            query_tokens=50,
            conversation_tokens=200,
        )

        # 4000 - 500 - 1000 - 50 - 200 = 2250
        assert available == 2250

    def test_select_chunks_for_budget(self, budget_manager):
        """Test chunk selection within budget."""
        chunks = [
            Chunk(chunk_id="1", document_id="doc1", text="A" * 100, token_count=100, chunk_order=0),
            Chunk(chunk_id="2", document_id="doc1", text="B" * 100, token_count=100, chunk_order=1),
            Chunk(chunk_id="3", document_id="doc1", text="C" * 100, token_count=100, chunk_order=2),
        ]

        selected = budget_manager.select_chunks_for_budget(chunks, available_tokens=250)

        total_tokens = sum(c.token_count for c in selected)
        assert total_tokens <= 250

    def test_format_context(self, budget_manager):
        """Test context formatting."""
        chunks = [
            Chunk(
                chunk_id="1",
                document_id="doc1",
                text="First chunk content",
                token_count=10,
                chunk_order=0,
                heading_path="Doc > Section 1",
            ),
            Chunk(
                chunk_id="2",
                document_id="doc1",
                text="Second chunk content",
                token_count=10,
                chunk_order=1,
                heading_path="Doc > Section 2",
            ),
        ]

        context = budget_manager.format_context(chunks)

        assert "Source 1" in context
        assert "Source 2" in context
        assert "First chunk content" in context
        assert "Second chunk content" in context


class TestChunkingEdgeCases:
    """Tests for edge cases in chunking."""

    def test_very_long_sentence(self):
        """Test handling of very long sentences."""
        config = ChunkingConfig(max_tokens=50)
        chunker = DocumentChunker(config)

        # Create a single very long sentence
        long_sentence = "word " * 500
        chunks = chunker.chunk_document("doc1", long_sentence)

        assert len(chunks) > 1

    def test_special_characters(self):
        """Test handling of special characters."""
        config = ChunkingConfig(max_tokens=100)
        chunker = DocumentChunker(config)

        text = "Special chars: @#$%^&*(){}[]|\\<>? and unicode: 你好世界"
        chunks = chunker.chunk_document("doc1", text)

        assert len(chunks) > 0

    def test_code_blocks(self):
        """Test handling of code blocks."""
        config = ChunkingConfig(max_tokens=200)
        chunker = DocumentChunker(config)

        text = """# Code Example

```python
def hello():
    print("Hello, World!")
```

More text after the code block.
"""
        chunks = chunker.chunk_document("doc1", text)

        assert len(chunks) > 0

    def test_tables_markdown(self):
        """Test handling of markdown tables."""
        config = ChunkingConfig(max_tokens=200)
        chunker = DocumentChunker(config)

        text = """# Table Section

| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |
| Value 3  | Value 4  |

Text after table.
"""
        chunks = chunker.chunk_document("doc1", text)

        assert len(chunks) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
