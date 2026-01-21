"""
Chunking Service - Implements LLD Chunking Strategy
Supports semantic, paragraph, table-aware, and hybrid chunking
"""
import re
import hashlib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import tiktoken


class DocType(Enum):
    POLICY = "policy"
    CONTRACT = "contract"
    MANUAL = "manual"
    SCANNED_PDF = "scanned_pdf"
    TABLE = "table"
    GENERAL = "general"


@dataclass
class ChunkConfig:
    """Configuration for chunking based on document type"""
    doc_type: DocType
    target_size: int  # tokens
    min_size: int
    max_size: int
    overlap_pct: float
    preserve_boundaries: List[str]  # e.g., ["heading", "paragraph", "clause"]


# LLD-specified chunking configurations
CHUNK_CONFIGS = {
    DocType.POLICY: ChunkConfig(
        doc_type=DocType.POLICY,
        target_size=950,  # 700-1200 range
        min_size=700,
        max_size=1200,
        overlap_pct=0.12,  # 10-15%
        preserve_boundaries=["heading", "bullet", "section"]
    ),
    DocType.CONTRACT: ChunkConfig(
        doc_type=DocType.CONTRACT,
        target_size=600,  # 400-800 range
        min_size=400,
        max_size=800,
        overlap_pct=0.17,  # 15-20%
        preserve_boundaries=["clause", "paragraph", "section"]
    ),
    DocType.MANUAL: ChunkConfig(
        doc_type=DocType.MANUAL,
        target_size=1150,  # 800-1500 range
        min_size=800,
        max_size=1500,
        overlap_pct=0.10,
        preserve_boundaries=["heading", "code_block", "step"]
    ),
    DocType.SCANNED_PDF: ChunkConfig(
        doc_type=DocType.SCANNED_PDF,
        target_size=700,  # 500-900 range
        min_size=500,
        max_size=900,
        overlap_pct=0.15,
        preserve_boundaries=["page", "paragraph"]
    ),
    DocType.TABLE: ChunkConfig(
        doc_type=DocType.TABLE,
        target_size=500,
        min_size=100,
        max_size=1000,
        overlap_pct=0.0,  # No overlap for tables
        preserve_boundaries=["table"]
    ),
    DocType.GENERAL: ChunkConfig(
        doc_type=DocType.GENERAL,
        target_size=800,
        min_size=500,
        max_size=1200,
        overlap_pct=0.10,
        preserve_boundaries=["paragraph", "sentence"]
    )
}


@dataclass
class Chunk:
    """Represents a document chunk as per LLD schema"""
    id: str
    doc_id: str
    chunk_text: str
    chunk_index: int
    page: Optional[int]
    metadata: Dict[str, Any]
    token_count: int
    char_count: int
    checksum: str


class ChunkingService:
    """
    Document chunking service implementing LLD specifications
    - Semantic section chunking for policies/SOPs
    - Paragraph + clause chunking for contracts
    - Hybrid chunking for manuals
    - Layout-aware chunking for scanned PDFs
    - Table-to-text conversion for tables
    """

    def __init__(self, model: str = "cl100k_base"):
        self.tokenizer = tiktoken.get_encoding(model)

    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.tokenizer.encode(text))

    def detect_doc_type(self, text: str, filename: str, metadata: Dict) -> DocType:
        """Detect document type based on content and metadata"""
        filename_lower = filename.lower()

        # Check filename patterns
        if any(kw in filename_lower for kw in ["policy", "sop", "procedure", "guideline"]):
            return DocType.POLICY
        if any(kw in filename_lower for kw in ["contract", "agreement", "legal", "terms"]):
            return DocType.CONTRACT
        if any(kw in filename_lower for kw in ["manual", "guide", "documentation", "handbook"]):
            return DocType.MANUAL

        # Check content patterns
        if re.search(r'(Article|Section|Clause)\s+\d+', text):
            return DocType.CONTRACT
        if re.search(r'(Step\s+\d+|```|<code>)', text):
            return DocType.MANUAL
        if re.search(r'(Policy|Procedure|Compliance|Regulation)', text, re.IGNORECASE):
            return DocType.POLICY

        # Check metadata
        if metadata.get("has_tables"):
            return DocType.TABLE
        if metadata.get("is_scanned"):
            return DocType.SCANNED_PDF

        return DocType.GENERAL

    def chunk_document(
        self,
        text: str,
        doc_id: str,
        filename: str,
        metadata: Dict[str, Any],
        doc_type: Optional[DocType] = None,
        page_boundaries: Optional[List[int]] = None
    ) -> List[Chunk]:
        """
        Main chunking method - routes to appropriate strategy
        """
        if doc_type is None:
            doc_type = self.detect_doc_type(text, filename, metadata)

        config = CHUNK_CONFIGS[doc_type]

        # Route to appropriate chunking strategy
        if doc_type == DocType.POLICY:
            chunks = self._chunk_semantic_sections(text, config)
        elif doc_type == DocType.CONTRACT:
            chunks = self._chunk_clauses(text, config)
        elif doc_type == DocType.MANUAL:
            chunks = self._chunk_hybrid(text, config)
        elif doc_type == DocType.SCANNED_PDF:
            chunks = self._chunk_layout_aware(text, config, page_boundaries)
        elif doc_type == DocType.TABLE:
            chunks = self._chunk_tables(text, config)
        else:
            chunks = self._chunk_sliding_window(text, config)

        # Convert to Chunk objects with metadata
        return self._create_chunk_objects(chunks, doc_id, metadata, page_boundaries)

    def _chunk_semantic_sections(self, text: str, config: ChunkConfig) -> List[str]:
        """
        Semantic section chunking for policies/SOPs
        Splits on headings, bullets, sections
        """
        chunks = []

        # Split on section headers (##, ###, numbered sections)
        section_pattern = r'(?=(?:^|\n)(?:#{1,3}\s|(?:\d+\.)+\s|\*\s|•\s|-\s))'
        sections = re.split(section_pattern, text)

        current_chunk = ""
        for section in sections:
            section = section.strip()
            if not section:
                continue

            section_tokens = self.count_tokens(section)

            # If section alone exceeds max, split it further
            if section_tokens > config.max_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                # Split large section by paragraphs
                sub_chunks = self._split_by_paragraphs(section, config)
                chunks.extend(sub_chunks)
                continue

            # Check if adding section exceeds target
            combined = current_chunk + "\n\n" + section if current_chunk else section
            combined_tokens = self.count_tokens(combined)

            if combined_tokens <= config.max_size:
                current_chunk = combined
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = section

        if current_chunk:
            chunks.append(current_chunk)

        # Add overlap
        return self._add_overlap(chunks, config)

    def _chunk_clauses(self, text: str, config: ChunkConfig) -> List[str]:
        """
        Clause-based chunking for contracts/legal documents
        Preserves clause boundaries
        """
        chunks = []

        # Split on clause patterns
        clause_pattern = r'(?=(?:^|\n)(?:(?:Article|Section|Clause|ARTICLE|SECTION|CLAUSE)\s+(?:\d+|[IVXLCDM]+)|(?:\d+\.)+\d*\s))'
        clauses = re.split(clause_pattern, text)

        current_chunk = ""
        for clause in clauses:
            clause = clause.strip()
            if not clause:
                continue

            clause_tokens = self.count_tokens(clause)

            if clause_tokens > config.max_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                sub_chunks = self._split_by_sentences(clause, config)
                chunks.extend(sub_chunks)
                continue

            combined = current_chunk + "\n\n" + clause if current_chunk else clause
            combined_tokens = self.count_tokens(combined)

            if combined_tokens <= config.max_size:
                current_chunk = combined
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = clause

        if current_chunk:
            chunks.append(current_chunk)

        return self._add_overlap(chunks, config)

    def _chunk_hybrid(self, text: str, config: ChunkConfig) -> List[str]:
        """
        Hybrid chunking for manuals/technical docs
        Combines semantic + fixed size, preserves code blocks
        """
        chunks = []

        # First, extract and protect code blocks
        code_blocks = []
        code_pattern = r'```[\s\S]*?```|<code>[\s\S]*?</code>'

        def replace_code(match):
            code_blocks.append(match.group())
            return f"__CODE_BLOCK_{len(code_blocks) - 1}__"

        protected_text = re.sub(code_pattern, replace_code, text)

        # Split on headers
        section_pattern = r'(?=(?:^|\n)(?:#{1,4}\s))'
        sections = re.split(section_pattern, protected_text)

        current_chunk = ""
        for section in sections:
            section = section.strip()
            if not section:
                continue

            # Restore code blocks in this section
            for i, code in enumerate(code_blocks):
                section = section.replace(f"__CODE_BLOCK_{i}__", code)

            section_tokens = self.count_tokens(section)

            if section_tokens > config.max_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                sub_chunks = self._split_by_paragraphs(section, config)
                chunks.extend(sub_chunks)
                continue

            combined = current_chunk + "\n\n" + section if current_chunk else section
            combined_tokens = self.count_tokens(combined)

            if combined_tokens <= config.max_size:
                current_chunk = combined
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = section

        if current_chunk:
            chunks.append(current_chunk)

        return self._add_overlap(chunks, config)

    def _chunk_layout_aware(
        self,
        text: str,
        config: ChunkConfig,
        page_boundaries: Optional[List[int]] = None
    ) -> List[str]:
        """
        Layout-aware chunking for scanned PDFs
        Uses page boundaries from Document Intelligence
        """
        if not page_boundaries:
            return self._chunk_sliding_window(text, config)

        chunks = []
        current_chunk = ""
        current_page_content = ""

        lines = text.split("\n")
        line_idx = 0

        for page_end in page_boundaries:
            # Collect content for this page
            page_lines = []
            while line_idx < len(lines) and line_idx < page_end:
                page_lines.append(lines[line_idx])
                line_idx += 1

            page_content = "\n".join(page_lines)
            page_tokens = self.count_tokens(page_content)

            if page_tokens > config.max_size:
                # Split page by paragraphs
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                sub_chunks = self._split_by_paragraphs(page_content, config)
                chunks.extend(sub_chunks)
            else:
                combined = current_chunk + "\n\n" + page_content if current_chunk else page_content
                combined_tokens = self.count_tokens(combined)

                if combined_tokens <= config.max_size:
                    current_chunk = combined
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = page_content

        if current_chunk:
            chunks.append(current_chunk)

        return self._add_overlap(chunks, config)

    def _chunk_tables(self, text: str, config: ChunkConfig) -> List[str]:
        """
        Table chunking - converts tables to markdown/CSV text
        Each table becomes its own chunk
        """
        chunks = []

        # Pattern to match markdown tables
        table_pattern = r'(\|[^\n]+\|\n(?:\|[-:| ]+\|\n)?(?:\|[^\n]+\|\n)*)'

        # Split text into table and non-table parts
        parts = re.split(table_pattern, text)

        for part in parts:
            part = part.strip()
            if not part:
                continue

            if part.startswith("|"):
                # This is a table - keep as single chunk
                chunks.append(f"[TABLE]\n{part}")
            else:
                # Non-table content - use standard chunking
                sub_chunks = self._chunk_sliding_window(part, config)
                chunks.extend(sub_chunks)

        return chunks

    def _chunk_sliding_window(self, text: str, config: ChunkConfig) -> List[str]:
        """
        Sliding window chunking with sentence boundary respect
        """
        chunks = []
        sentences = self._split_sentences(text)

        current_chunk = ""
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)

            if current_tokens + sentence_tokens <= config.max_size:
                current_chunk += " " + sentence if current_chunk else sentence
                current_tokens += sentence_tokens
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
                current_tokens = sentence_tokens

        if current_chunk:
            chunks.append(current_chunk.strip())

        return self._add_overlap(chunks, config)

    def _split_by_paragraphs(self, text: str, config: ChunkConfig) -> List[str]:
        """Split text by paragraphs"""
        paragraphs = re.split(r'\n\s*\n', text)
        return self._merge_small_chunks(paragraphs, config)

    def _split_by_sentences(self, text: str, config: ChunkConfig) -> List[str]:
        """Split text by sentences"""
        sentences = self._split_sentences(text)
        return self._merge_small_chunks(sentences, config)

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])'
        return re.split(sentence_pattern, text)

    def _merge_small_chunks(self, parts: List[str], config: ChunkConfig) -> List[str]:
        """Merge small chunks until they reach target size"""
        chunks = []
        current_chunk = ""

        for part in parts:
            part = part.strip()
            if not part:
                continue

            combined = current_chunk + "\n\n" + part if current_chunk else part
            combined_tokens = self.count_tokens(combined)

            if combined_tokens <= config.max_size:
                current_chunk = combined
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = part

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _add_overlap(self, chunks: List[str], config: ChunkConfig) -> List[str]:
        """Add overlap between chunks"""
        if config.overlap_pct == 0 or len(chunks) <= 1:
            return chunks

        overlapped = []
        for i, chunk in enumerate(chunks):
            if i == 0:
                overlapped.append(chunk)
                continue

            # Get overlap from previous chunk
            prev_chunk = chunks[i - 1]
            prev_tokens = self.count_tokens(prev_chunk)
            overlap_tokens = int(prev_tokens * config.overlap_pct)

            # Get last N tokens worth of text from previous chunk
            prev_sentences = self._split_sentences(prev_chunk)
            overlap_text = ""
            current_overlap_tokens = 0

            for sentence in reversed(prev_sentences):
                sentence_tokens = self.count_tokens(sentence)
                if current_overlap_tokens + sentence_tokens <= overlap_tokens:
                    overlap_text = sentence + " " + overlap_text
                    current_overlap_tokens += sentence_tokens
                else:
                    break

            # Prepend overlap to current chunk
            overlapped.append(overlap_text.strip() + "\n\n" + chunk)

        return overlapped

    def _create_chunk_objects(
        self,
        chunk_texts: List[str],
        doc_id: str,
        metadata: Dict[str, Any],
        page_boundaries: Optional[List[int]] = None
    ) -> List[Chunk]:
        """Convert chunk texts to Chunk objects with full metadata"""
        chunks = []

        for idx, text in enumerate(chunk_texts):
            chunk_id = f"{doc_id}_chunk_{idx:03d}"
            checksum = hashlib.sha256(text.encode()).hexdigest()[:16]

            # Determine page number if available
            page = None
            if page_boundaries:
                # Estimate page based on position
                text_position = sum(len(t) for t in chunk_texts[:idx])
                total_length = sum(len(t) for t in chunk_texts)
                relative_position = text_position / total_length if total_length > 0 else 0
                page = int(relative_position * len(page_boundaries)) + 1

            chunk = Chunk(
                id=chunk_id,
                doc_id=doc_id,
                chunk_text=text,
                chunk_index=idx,
                page=page,
                metadata=metadata,
                token_count=self.count_tokens(text),
                char_count=len(text),
                checksum=checksum
            )
            chunks.append(chunk)

        return chunks
