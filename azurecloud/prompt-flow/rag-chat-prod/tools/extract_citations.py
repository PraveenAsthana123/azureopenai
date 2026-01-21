"""
Citation Extraction Tool for Prompt Flow.

Parses citations from LLM responses and links them to source documents.
Provides bounding box information for UI highlighting.
"""

import re
from typing import TypedDict


class Citation(TypedDict):
    source_pdf: str
    page_number: int
    bounding_box: list | None
    excerpt: str | None


class CitationOutput(TypedDict):
    citations: list[Citation]
    citation_count: int
    has_valid_citations: bool


def extract_citations(
    answer: str,
    chunks: list[dict]
) -> CitationOutput:
    """
    Extract and validate citations from an LLM answer.

    Args:
        answer: Generated answer text
        chunks: Retrieved chunks with metadata

    Returns:
        CitationOutput with validated citations
    """
    # Pattern to match citations: [Source: file.pdf, Page N]
    citation_patterns = [
        r"\[Source:\s*([^,\]]+\.pdf),\s*Page\s*(\d+)\]",
        r"\[See Figure\s*\d+\s*on Page\s*(\d+)\]",
        r"\[([^\]]+\.pdf)\]",
    ]

    # Build lookup from chunks
    chunk_lookup = {}
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        source = metadata.get("source_pdf", "")
        page = metadata.get("page_number", 0)
        key = f"{source.lower()}:{page}"
        chunk_lookup[key] = {
            "bounding_box": metadata.get("bounding_box"),
            "content": chunk.get("content", "")[:200]  # First 200 chars as excerpt
        }

    citations = []
    seen = set()

    # Extract citations from answer
    for pattern in citation_patterns:
        matches = re.finditer(pattern, answer, re.IGNORECASE)
        for match in matches:
            groups = match.groups()

            if len(groups) >= 2:
                # Full citation: file.pdf, Page N
                source_pdf = groups[0].strip()
                page_number = int(groups[1])
            elif len(groups) == 1:
                # Partial: just file.pdf or just page number
                if groups[0].endswith('.pdf'):
                    source_pdf = groups[0].strip()
                    page_number = 0
                else:
                    # Figure reference - need to find source
                    page_number = int(groups[0])
                    source_pdf = _find_source_for_page(chunks, page_number)
            else:
                continue

            # Deduplicate
            key = f"{source_pdf.lower()}:{page_number}"
            if key in seen:
                continue
            seen.add(key)

            # Look up metadata from chunks
            chunk_info = chunk_lookup.get(key, {})

            citations.append({
                "source_pdf": source_pdf,
                "page_number": page_number,
                "bounding_box": chunk_info.get("bounding_box"),
                "excerpt": chunk_info.get("content")
            })

    # Check if citations are valid (exist in retrieved chunks)
    retrieved_sources = set()
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        source = metadata.get("source_pdf", "").lower()
        if source:
            retrieved_sources.add(source)

    has_valid = all(
        c["source_pdf"].lower() in retrieved_sources
        for c in citations
    ) if citations else False

    return {
        "citations": citations,
        "citation_count": len(citations),
        "has_valid_citations": has_valid
    }


def _find_source_for_page(chunks: list[dict], page_number: int) -> str:
    """Find the source PDF for a given page number."""
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        if metadata.get("page_number") == page_number:
            return metadata.get("source_pdf", "unknown.pdf")
    return "unknown.pdf"


def format_citations_for_display(citations: list[Citation]) -> str:
    """Format citations for display in UI."""
    if not citations:
        return ""

    formatted = []
    for i, citation in enumerate(citations, 1):
        formatted.append(f"{i}. {citation['source_pdf']}, Page {citation['page_number']}")

    return "\n".join(formatted)


# Prompt Flow entry point
def main(answer: str, chunks: list[dict]) -> CitationOutput:
    """Entry point for Prompt Flow."""
    return extract_citations(answer, chunks)


if __name__ == "__main__":
    # Test
    test_answer = """
    Based on the security policy, logs must be retained for 365 days [Source: policy.pdf, Page 4].
    The incident response procedure is outlined in [Source: procedures.pdf, Page 12].
    See Figure 3 on Page 8 for the data flow diagram.
    """

    test_chunks = [
        {
            "content": "Logs are retained for 365 days per compliance.",
            "metadata": {
                "source_pdf": "policy.pdf",
                "page_number": 4,
                "bounding_box": [100, 200, 500, 250]
            }
        },
        {
            "content": "Incident response procedure steps...",
            "metadata": {
                "source_pdf": "procedures.pdf",
                "page_number": 12
            }
        }
    ]

    result = extract_citations(test_answer, test_chunks)
    print(f"Found {result['citation_count']} citations:")
    for citation in result["citations"]:
        print(f"  - {citation['source_pdf']}, Page {citation['page_number']}")
    print(f"All valid: {result['has_valid_citations']}")
