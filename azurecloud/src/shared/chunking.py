"""
Enterprise Document Chunking Utilities
Supports: Semantic, Heading-Aware, Fixed-Size, Sentence-Based chunking
With token budget management and overlap handling.
"""

import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator

import tiktoken


class ChunkingStrategy(str, Enum):
    """Available chunking strategies."""
    FIXED_SIZE = "fixed_size"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    SEMANTIC = "semantic"
    HEADING_AWARE = "heading_aware"
    HYBRID = "hybrid"


@dataclass
class Chunk:
    """Represents a document chunk."""
    chunk_id: str
    document_id: str
    text: str
    token_count: int
    chunk_order: int
    heading_path: str = ""
    section_name: str = ""
    page_number: int | None = None
    start_char: int = 0
    end_char: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class ChunkingConfig:
    """Configuration for chunking operations."""
    strategy: ChunkingStrategy = ChunkingStrategy.HEADING_AWARE
    max_tokens: int = 512
    min_tokens: int = 50
    overlap_tokens: int = 64
    encoding_name: str = "cl100k_base"  # GPT-4/text-embedding-3 encoding
    respect_sentence_boundaries: bool = True
    preserve_markdown_structure: bool = True
    include_heading_in_chunk: bool = True


class TokenCounter:
    """Efficient token counting with caching."""

    _encodings: dict[str, tiktoken.Encoding] = {}

    @classmethod
    def get_encoding(cls, encoding_name: str = "cl100k_base") -> tiktoken.Encoding:
        """Get or create encoding instance."""
        if encoding_name not in cls._encodings:
            cls._encodings[encoding_name] = tiktoken.get_encoding(encoding_name)
        return cls._encodings[encoding_name]

    @classmethod
    def count_tokens(cls, text: str, encoding_name: str = "cl100k_base") -> int:
        """Count tokens in text."""
        encoding = cls.get_encoding(encoding_name)
        return len(encoding.encode(text))

    @classmethod
    def truncate_to_tokens(
        cls,
        text: str,
        max_tokens: int,
        encoding_name: str = "cl100k_base",
    ) -> str:
        """Truncate text to maximum token count."""
        encoding = cls.get_encoding(encoding_name)
        tokens = encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text
        return encoding.decode(tokens[:max_tokens])

    @classmethod
    def split_by_tokens(
        cls,
        text: str,
        chunk_size: int,
        overlap: int = 0,
        encoding_name: str = "cl100k_base",
    ) -> list[str]:
        """Split text into chunks by token count with overlap."""
        encoding = cls.get_encoding(encoding_name)
        tokens = encoding.encode(text)

        if len(tokens) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunks.append(encoding.decode(chunk_tokens))
            start = end - overlap if overlap > 0 else end

        return chunks


class DocumentChunker:
    """Enterprise document chunking with multiple strategies."""

    # Heading patterns for markdown
    HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    # Sentence boundary pattern
    SENTENCE_PATTERN = re.compile(
        r"(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])\s*\n",
        re.MULTILINE
    )

    # Paragraph boundary pattern
    PARAGRAPH_PATTERN = re.compile(r"\n\s*\n")

    def __init__(self, config: ChunkingConfig | None = None):
        self.config = config or ChunkingConfig()
        self.encoding = TokenCounter.get_encoding(self.config.encoding_name)

    def chunk_document(
        self,
        document_id: str,
        text: str,
        title: str = "",
        strategy: ChunkingStrategy | None = None,
    ) -> list[Chunk]:
        """Chunk a document using the specified strategy."""
        strategy = strategy or self.config.strategy

        if strategy == ChunkingStrategy.FIXED_SIZE:
            return self._chunk_fixed_size(document_id, text, title)
        elif strategy == ChunkingStrategy.SENTENCE:
            return self._chunk_by_sentences(document_id, text, title)
        elif strategy == ChunkingStrategy.PARAGRAPH:
            return self._chunk_by_paragraphs(document_id, text, title)
        elif strategy == ChunkingStrategy.HEADING_AWARE:
            return self._chunk_heading_aware(document_id, text, title)
        elif strategy == ChunkingStrategy.SEMANTIC:
            return self._chunk_semantic(document_id, text, title)
        elif strategy == ChunkingStrategy.HYBRID:
            return self._chunk_hybrid(document_id, text, title)
        else:
            raise ValueError(f"Unknown chunking strategy: {strategy}")

    def _generate_chunk_id(self, document_id: str, chunk_order: int, text: str) -> str:
        """Generate unique chunk ID."""
        content_hash = hashlib.sha256(text.encode()).hexdigest()[:8]
        return f"{document_id}_chunk_{chunk_order:04d}_{content_hash}"

    def _create_chunk(
        self,
        document_id: str,
        text: str,
        chunk_order: int,
        heading_path: str = "",
        section_name: str = "",
        start_char: int = 0,
        end_char: int = 0,
        metadata: dict | None = None,
    ) -> Chunk:
        """Create a Chunk object with token count."""
        token_count = TokenCounter.count_tokens(text, self.config.encoding_name)

        return Chunk(
            chunk_id=self._generate_chunk_id(document_id, chunk_order, text),
            document_id=document_id,
            text=text.strip(),
            token_count=token_count,
            chunk_order=chunk_order,
            heading_path=heading_path,
            section_name=section_name,
            start_char=start_char,
            end_char=end_char,
            metadata=metadata or {},
        )

    def _chunk_fixed_size(
        self,
        document_id: str,
        text: str,
        title: str,
    ) -> list[Chunk]:
        """Simple fixed-size chunking with overlap."""
        text_chunks = TokenCounter.split_by_tokens(
            text,
            self.config.max_tokens,
            self.config.overlap_tokens,
            self.config.encoding_name,
        )

        chunks = []
        char_offset = 0

        for i, chunk_text in enumerate(text_chunks):
            end_char = char_offset + len(chunk_text)
            chunks.append(
                self._create_chunk(
                    document_id=document_id,
                    text=chunk_text,
                    chunk_order=i,
                    heading_path=title,
                    start_char=char_offset,
                    end_char=end_char,
                )
            )
            # Account for overlap when calculating next offset
            if i < len(text_chunks) - 1:
                overlap_text = TokenCounter.truncate_to_tokens(
                    chunk_text,
                    self.config.overlap_tokens,
                    self.config.encoding_name,
                )
                char_offset = end_char - len(overlap_text)
            else:
                char_offset = end_char

        return chunks

    def _chunk_by_sentences(
        self,
        document_id: str,
        text: str,
        title: str,
    ) -> list[Chunk]:
        """Chunk by sentences, respecting token limits."""
        sentences = self.SENTENCE_PATTERN.split(text)
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks = []
        current_text = ""
        current_tokens = 0
        chunk_order = 0
        char_offset = 0

        for sentence in sentences:
            sentence_tokens = TokenCounter.count_tokens(sentence, self.config.encoding_name)

            # If single sentence exceeds max, split it
            if sentence_tokens > self.config.max_tokens:
                # Flush current buffer
                if current_text:
                    chunks.append(
                        self._create_chunk(
                            document_id=document_id,
                            text=current_text,
                            chunk_order=chunk_order,
                            heading_path=title,
                            start_char=char_offset,
                            end_char=char_offset + len(current_text),
                        )
                    )
                    chunk_order += 1
                    char_offset += len(current_text)
                    current_text = ""
                    current_tokens = 0

                # Split the large sentence
                sub_chunks = TokenCounter.split_by_tokens(
                    sentence,
                    self.config.max_tokens,
                    self.config.overlap_tokens,
                    self.config.encoding_name,
                )
                for sub_chunk in sub_chunks:
                    chunks.append(
                        self._create_chunk(
                            document_id=document_id,
                            text=sub_chunk,
                            chunk_order=chunk_order,
                            heading_path=title,
                            start_char=char_offset,
                            end_char=char_offset + len(sub_chunk),
                        )
                    )
                    chunk_order += 1
                    char_offset += len(sub_chunk)
                continue

            # Check if adding this sentence exceeds limit
            if current_tokens + sentence_tokens > self.config.max_tokens:
                # Flush current buffer
                if current_text:
                    chunks.append(
                        self._create_chunk(
                            document_id=document_id,
                            text=current_text,
                            chunk_order=chunk_order,
                            heading_path=title,
                            start_char=char_offset,
                            end_char=char_offset + len(current_text),
                        )
                    )
                    chunk_order += 1
                    char_offset += len(current_text)

                # Start new buffer with overlap
                if self.config.overlap_tokens > 0 and current_text:
                    overlap = TokenCounter.truncate_to_tokens(
                        current_text,
                        self.config.overlap_tokens,
                        self.config.encoding_name,
                    )
                    current_text = overlap + " " + sentence
                    current_tokens = TokenCounter.count_tokens(
                        current_text, self.config.encoding_name
                    )
                else:
                    current_text = sentence
                    current_tokens = sentence_tokens
            else:
                # Add sentence to buffer
                if current_text:
                    current_text += " " + sentence
                else:
                    current_text = sentence
                current_tokens += sentence_tokens

        # Flush remaining buffer
        if current_text and TokenCounter.count_tokens(current_text, self.config.encoding_name) >= self.config.min_tokens:
            chunks.append(
                self._create_chunk(
                    document_id=document_id,
                    text=current_text,
                    chunk_order=chunk_order,
                    heading_path=title,
                    start_char=char_offset,
                    end_char=char_offset + len(current_text),
                )
            )

        return chunks

    def _chunk_by_paragraphs(
        self,
        document_id: str,
        text: str,
        title: str,
    ) -> list[Chunk]:
        """Chunk by paragraphs, merging small ones."""
        paragraphs = self.PARAGRAPH_PATTERN.split(text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        chunks = []
        current_text = ""
        current_tokens = 0
        chunk_order = 0

        for para in paragraphs:
            para_tokens = TokenCounter.count_tokens(para, self.config.encoding_name)

            if para_tokens > self.config.max_tokens:
                # Flush buffer and split large paragraph
                if current_text:
                    chunks.append(
                        self._create_chunk(
                            document_id=document_id,
                            text=current_text,
                            chunk_order=chunk_order,
                            heading_path=title,
                        )
                    )
                    chunk_order += 1
                    current_text = ""
                    current_tokens = 0

                # Use sentence chunking for large paragraphs
                sub_chunks = self._chunk_by_sentences(document_id, para, title)
                for sub in sub_chunks:
                    sub.chunk_order = chunk_order
                    sub.chunk_id = self._generate_chunk_id(document_id, chunk_order, sub.text)
                    chunks.append(sub)
                    chunk_order += 1
                continue

            if current_tokens + para_tokens > self.config.max_tokens:
                if current_text:
                    chunks.append(
                        self._create_chunk(
                            document_id=document_id,
                            text=current_text,
                            chunk_order=chunk_order,
                            heading_path=title,
                        )
                    )
                    chunk_order += 1
                current_text = para
                current_tokens = para_tokens
            else:
                if current_text:
                    current_text += "\n\n" + para
                else:
                    current_text = para
                current_tokens += para_tokens

        if current_text and TokenCounter.count_tokens(current_text, self.config.encoding_name) >= self.config.min_tokens:
            chunks.append(
                self._create_chunk(
                    document_id=document_id,
                    text=current_text,
                    chunk_order=chunk_order,
                    heading_path=title,
                )
            )

        return chunks

    def _chunk_heading_aware(
        self,
        document_id: str,
        text: str,
        title: str,
    ) -> list[Chunk]:
        """Chunk respecting document structure (headings)."""
        sections = self._extract_sections(text)

        if not sections:
            return self._chunk_by_paragraphs(document_id, text, title)

        chunks = []
        chunk_order = 0
        heading_stack: list[str] = []

        for section in sections:
            level = section["level"]
            heading = section["heading"]
            content = section["content"]

            # Update heading stack
            while len(heading_stack) >= level:
                heading_stack.pop()
            heading_stack.append(heading)

            heading_path = " > ".join([title] + heading_stack) if title else " > ".join(heading_stack)
            section_name = heading

            if not content.strip():
                continue

            # Check if content fits in one chunk
            content_tokens = TokenCounter.count_tokens(content, self.config.encoding_name)

            # Add heading to chunk if configured
            if self.config.include_heading_in_chunk:
                prefix = f"{'#' * level} {heading}\n\n"
                prefix_tokens = TokenCounter.count_tokens(prefix, self.config.encoding_name)
            else:
                prefix = ""
                prefix_tokens = 0

            if content_tokens + prefix_tokens <= self.config.max_tokens:
                chunks.append(
                    self._create_chunk(
                        document_id=document_id,
                        text=prefix + content,
                        chunk_order=chunk_order,
                        heading_path=heading_path,
                        section_name=section_name,
                    )
                )
                chunk_order += 1
            else:
                # Split section by paragraphs/sentences
                sub_chunks = self._chunk_by_sentences(document_id, content, heading_path)
                for sub in sub_chunks:
                    # Add heading prefix to first chunk of section
                    if sub.chunk_order == 0 and self.config.include_heading_in_chunk:
                        sub.text = prefix + sub.text
                        sub.token_count = TokenCounter.count_tokens(
                            sub.text, self.config.encoding_name
                        )

                    sub.chunk_order = chunk_order
                    sub.heading_path = heading_path
                    sub.section_name = section_name
                    sub.chunk_id = self._generate_chunk_id(document_id, chunk_order, sub.text)
                    chunks.append(sub)
                    chunk_order += 1

        return chunks

    def _extract_sections(self, text: str) -> list[dict]:
        """Extract sections based on markdown headings."""
        sections = []
        lines = text.split("\n")
        current_section = None

        for line in lines:
            heading_match = self.HEADING_PATTERN.match(line)

            if heading_match:
                # Save previous section
                if current_section:
                    sections.append(current_section)

                level = len(heading_match.group(1))
                heading = heading_match.group(2).strip()
                current_section = {
                    "level": level,
                    "heading": heading,
                    "content": "",
                }
            elif current_section:
                current_section["content"] += line + "\n"

        # Save last section
        if current_section:
            sections.append(current_section)

        return sections

    def _chunk_semantic(
        self,
        document_id: str,
        text: str,
        title: str,
    ) -> list[Chunk]:
        """
        Semantic chunking using sentence embeddings similarity.
        Note: This requires an embedding model. Falls back to paragraph chunking.
        """
        # For now, fall back to heading-aware chunking
        # Full semantic chunking would require embedding model integration
        return self._chunk_heading_aware(document_id, text, title)

    def _chunk_hybrid(
        self,
        document_id: str,
        text: str,
        title: str,
    ) -> list[Chunk]:
        """Hybrid approach: heading-aware with sentence boundary respect."""
        return self._chunk_heading_aware(document_id, text, title)


class TokenBudgetManager:
    """Manage token budgets for RAG context window."""

    def __init__(
        self,
        max_context_tokens: int = 8000,
        max_response_tokens: int = 2000,
        system_prompt_tokens: int = 500,
        encoding_name: str = "cl100k_base",
    ):
        self.max_context_tokens = max_context_tokens
        self.max_response_tokens = max_response_tokens
        self.system_prompt_tokens = system_prompt_tokens
        self.encoding_name = encoding_name

        self.available_for_context = (
            max_context_tokens - system_prompt_tokens - max_response_tokens
        )

    def calculate_available_tokens(
        self,
        query_tokens: int,
        conversation_tokens: int = 0,
    ) -> int:
        """Calculate tokens available for retrieved context."""
        used = query_tokens + conversation_tokens
        return max(0, self.available_for_context - used)

    def select_chunks_for_budget(
        self,
        chunks: list[Chunk],
        available_tokens: int,
        prioritize_by: str = "score",  # "score" or "order"
    ) -> list[Chunk]:
        """Select chunks that fit within token budget."""
        if prioritize_by == "order":
            # Maintain document order
            sorted_chunks = sorted(chunks, key=lambda c: c.chunk_order)
        else:
            # Sort by score (assumed to be in metadata)
            sorted_chunks = sorted(
                chunks,
                key=lambda c: c.metadata.get("score", 0),
                reverse=True,
            )

        selected = []
        total_tokens = 0

        for chunk in sorted_chunks:
            if total_tokens + chunk.token_count <= available_tokens:
                selected.append(chunk)
                total_tokens += chunk.token_count
            elif total_tokens == 0:
                # At least include one chunk (truncated if necessary)
                truncated_text = TokenCounter.truncate_to_tokens(
                    chunk.text,
                    available_tokens,
                    self.encoding_name,
                )
                truncated_chunk = Chunk(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    text=truncated_text,
                    token_count=available_tokens,
                    chunk_order=chunk.chunk_order,
                    heading_path=chunk.heading_path,
                    section_name=chunk.section_name,
                    metadata={**chunk.metadata, "truncated": True},
                )
                selected.append(truncated_chunk)
                break

        # Re-sort by document order for coherent context
        return sorted(selected, key=lambda c: (c.document_id, c.chunk_order))

    def format_context(
        self,
        chunks: list[Chunk],
        include_metadata: bool = True,
    ) -> str:
        """Format selected chunks into context string."""
        context_parts = []

        for i, chunk in enumerate(chunks, 1):
            if include_metadata and chunk.heading_path:
                header = f"[Source {i}: {chunk.heading_path}]"
            else:
                header = f"[Source {i}]"

            context_parts.append(f"{header}\n{chunk.text}")

        return "\n\n---\n\n".join(context_parts)


# Convenience functions
def chunk_document(
    document_id: str,
    text: str,
    title: str = "",
    strategy: ChunkingStrategy = ChunkingStrategy.HEADING_AWARE,
    max_tokens: int = 512,
    overlap_tokens: int = 64,
) -> list[Chunk]:
    """Convenience function to chunk a document."""
    config = ChunkingConfig(
        strategy=strategy,
        max_tokens=max_tokens,
        overlap_tokens=overlap_tokens,
    )
    chunker = DocumentChunker(config)
    return chunker.chunk_document(document_id, text, title)


def count_tokens(text: str) -> int:
    """Convenience function to count tokens."""
    return TokenCounter.count_tokens(text)


def truncate_text(text: str, max_tokens: int) -> str:
    """Convenience function to truncate text to token limit."""
    return TokenCounter.truncate_to_tokens(text, max_tokens)
