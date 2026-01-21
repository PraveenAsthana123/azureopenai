"""
Retrieval Service - Implements LLD RAG Architecture
Pre-retrieval, Hybrid Search, Reranking, Post-retrieval processing
"""
import hashlib
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import re


class IntentType(Enum):
    """Query intent types"""
    FACTUAL = "factual"
    PROCEDURAL = "procedural"
    COMPARATIVE = "comparative"
    SUMMARIZATION = "summarization"
    DEFINITION = "definition"
    TROUBLESHOOTING = "troubleshooting"
    UNKNOWN = "unknown"


@dataclass
class PreRetrievalResult:
    """Output of pre-retrieval processing"""
    original_query: str
    normalized_query: str
    intent: IntentType
    filters: Dict[str, Any]
    metadata_extracted: Dict[str, Any]
    top_k: int
    security_groups: List[str]


@dataclass
class RetrievedChunk:
    """A retrieved document chunk"""
    id: str
    doc_id: str
    content: str
    score: float
    metadata: Dict[str, Any]
    page: Optional[int]
    highlights: List[str]


@dataclass
class PostRetrievalResult:
    """Output of post-retrieval processing"""
    context: List[Dict[str, Any]]
    grounding_score: float
    sources_used: int
    conflicts_resolved: int
    duplicates_removed: int


class PreRetrievalProcessor:
    """
    Pre-retrieval processing as per LLD:
    - Intent detection
    - Query rewriting/normalization
    - Metadata extraction
    - Access filter building
    - Hybrid query construction
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    async def process(
        self,
        query: str,
        user_id: str,
        user_groups: List[str],
        conversation_history: List[Dict] = None
    ) -> PreRetrievalResult:
        """
        Main pre-retrieval processing pipeline
        """
        # Step 1: Detect intent
        intent = await self._detect_intent(query)

        # Step 2: Normalize/rewrite query
        normalized_query = await self._normalize_query(query, conversation_history)

        # Step 3: Extract metadata filters
        metadata = self._extract_metadata(query)

        # Step 4: Build security filters (ACL trimming)
        security_filters = self._build_security_filters(user_groups)

        # Step 5: Combine all filters
        filters = {**metadata, **security_filters}

        # Step 6: Determine top_k based on intent
        top_k = self._determine_top_k(intent)

        return PreRetrievalResult(
            original_query=query,
            normalized_query=normalized_query,
            intent=intent,
            filters=filters,
            metadata_extracted=metadata,
            top_k=top_k,
            security_groups=user_groups
        )

    async def _detect_intent(self, query: str) -> IntentType:
        """
        Classify query intent
        Uses lightweight rules or LLM
        """
        query_lower = query.lower()

        # Rule-based intent detection
        if any(kw in query_lower for kw in ["what is", "define", "meaning of", "explain"]):
            return IntentType.DEFINITION

        if any(kw in query_lower for kw in ["how to", "steps to", "process for", "procedure"]):
            return IntentType.PROCEDURAL

        if any(kw in query_lower for kw in ["compare", "difference", "vs", "versus", "better"]):
            return IntentType.COMPARATIVE

        if any(kw in query_lower for kw in ["summarize", "summary", "overview", "brief"]):
            return IntentType.SUMMARIZATION

        if any(kw in query_lower for kw in ["error", "issue", "problem", "fix", "troubleshoot", "not working"]):
            return IntentType.TROUBLESHOOTING

        if any(kw in query_lower for kw in ["what", "when", "where", "who", "which", "how many", "how much"]):
            return IntentType.FACTUAL

        return IntentType.UNKNOWN

    async def _normalize_query(
        self,
        query: str,
        conversation_history: List[Dict] = None
    ) -> str:
        """
        Normalize and clarify query
        - Resolve pronouns using conversation context
        - Expand abbreviations
        - Fix spelling
        """
        normalized = query.strip()

        # Basic normalization
        normalized = re.sub(r'\s+', ' ', normalized)

        # Expand common abbreviations
        abbreviations = {
            "aml": "anti-money laundering",
            "kyc": "know your customer",
            "sop": "standard operating procedure",
            "hr": "human resources",
            "it": "information technology",
            "faq": "frequently asked questions",
        }

        for abbr, expansion in abbreviations.items():
            pattern = rf'\b{abbr}\b'
            normalized = re.sub(pattern, f"{abbr} ({expansion})", normalized, flags=re.IGNORECASE)

        # Resolve pronouns using conversation history
        if conversation_history and len(conversation_history) > 0:
            # Simple pronoun resolution
            if normalized.lower().startswith(("it", "that", "this", "they")):
                last_topic = self._extract_last_topic(conversation_history)
                if last_topic:
                    normalized = f"{normalized} (referring to {last_topic})"

        return normalized

    def _extract_metadata(self, query: str) -> Dict[str, Any]:
        """
        Extract metadata filters from query
        - Region
        - Department/BU
        - Date ranges
        - Document types
        """
        filters = {}

        # Region extraction
        regions = {
            "canada": "CA", "ca": "CA",
            "us": "US", "usa": "US", "united states": "US",
            "uk": "UK", "united kingdom": "UK",
            "emea": "EMEA", "europe": "EMEA",
            "apac": "APAC", "asia": "APAC"
        }

        query_lower = query.lower()
        for region_name, region_code in regions.items():
            if region_name in query_lower:
                filters["region"] = region_code
                break

        # Department extraction
        departments = {
            "compliance": "Compliance",
            "finance": "Finance",
            "hr": "HR", "human resources": "HR",
            "legal": "Legal",
            "engineering": "Engineering",
            "sales": "Sales",
            "marketing": "Marketing"
        }

        for dept_name, dept_code in departments.items():
            if dept_name in query_lower:
                filters["department"] = dept_code
                break

        # Date extraction
        if "latest" in query_lower or "recent" in query_lower or "current" in query_lower:
            # Filter to last 90 days
            filters["effectiveDate"] = {
                "gte": (datetime.utcnow() - timedelta(days=90)).isoformat()
            }

        # Year extraction
        year_match = re.search(r'\b(202[0-9])\b', query)
        if year_match:
            year = int(year_match.group(1))
            filters["effectiveDate"] = {
                "gte": f"{year}-01-01",
                "lte": f"{year}-12-31"
            }

        return filters

    def _build_security_filters(self, user_groups: List[str]) -> Dict[str, Any]:
        """
        Build security trimming filters based on user groups
        Maps Entra ID groups to ACL filters
        """
        if not user_groups:
            return {}

        # Convert group IDs to ACL filter
        return {
            "aclGroups": {
                "any": user_groups
            }
        }

    def _determine_top_k(self, intent: IntentType) -> int:
        """
        Determine optimal top_k based on intent
        """
        intent_top_k = {
            IntentType.FACTUAL: 8,
            IntentType.PROCEDURAL: 10,
            IntentType.COMPARATIVE: 12,
            IntentType.SUMMARIZATION: 15,
            IntentType.DEFINITION: 5,
            IntentType.TROUBLESHOOTING: 10,
            IntentType.UNKNOWN: 8
        }
        return intent_top_k.get(intent, 8)

    def _extract_last_topic(self, conversation_history: List[Dict]) -> Optional[str]:
        """Extract the main topic from the last exchange"""
        if not conversation_history:
            return None

        # Get last assistant message
        for msg in reversed(conversation_history):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                # Extract first noun phrase (simplified)
                match = re.search(r'\b([A-Z][a-z]+ (?:[A-Z][a-z]+ )*[A-Z][a-z]+)\b', content)
                if match:
                    return match.group(1)

        return None


class HybridSearchBuilder:
    """
    Builds hybrid search queries for Azure AI Search
    Combines vector, keyword (BM25), and metadata filters
    """

    def build_query(
        self,
        pre_retrieval: PreRetrievalResult,
        query_vector: List[float]
    ) -> Dict[str, Any]:
        """
        Build Azure AI Search hybrid query as per LLD
        """
        # Build filter string
        filter_parts = []

        for key, value in pre_retrieval.filters.items():
            if key == "aclGroups":
                # Handle ACL filter
                if isinstance(value, dict) and "any" in value:
                    groups = value["any"]
                    group_filters = " or ".join([f"aclGroups/any(g: g eq '{g}')" for g in groups])
                    filter_parts.append(f"({group_filters})")
            elif isinstance(value, dict):
                # Range filter
                if "gte" in value:
                    filter_parts.append(f"{key} ge {value['gte']}")
                if "lte" in value:
                    filter_parts.append(f"{key} le {value['lte']}")
            else:
                # Equality filter
                filter_parts.append(f"{key} eq '{value}'")

        filter_string = " and ".join(filter_parts) if filter_parts else None

        # Build the hybrid query
        search_query = {
            "search": pre_retrieval.normalized_query,
            "searchMode": "any",
            "queryType": "semantic",
            "semanticConfiguration": "enterprise-semantic",
            "top": pre_retrieval.top_k,
            "select": "id,docId,chunkText,metadata,page,score",
            "highlightFields": "chunkText",
            "highlightPreTag": "<em>",
            "highlightPostTag": "</em>",
            "vectors": [
                {
                    "value": query_vector,
                    "fields": "chunkVector",
                    "k": pre_retrieval.top_k
                }
            ]
        }

        if filter_string:
            search_query["filter"] = filter_string

        return search_query


class PostRetrievalProcessor:
    """
    Post-retrieval processing as per LLD:
    - Deduplication
    - Temporal filtering (prioritize latest)
    - Conflict resolution
    - Context compression
    - Grounding score calculation
    """

    def __init__(self, max_context_tokens: int = 4000):
        self.max_context_tokens = max_context_tokens

    def process(
        self,
        chunks: List[RetrievedChunk],
        query: str
    ) -> PostRetrievalResult:
        """
        Main post-retrieval processing pipeline
        """
        # Step 1: Deduplicate
        deduped_chunks, duplicates_removed = self._deduplicate(chunks)

        # Step 2: Temporal filter (prioritize recent)
        temporally_sorted = self._temporal_sort(deduped_chunks)

        # Step 3: Resolve conflicts
        resolved_chunks, conflicts_resolved = self._resolve_conflicts(temporally_sorted)

        # Step 4: Compress context
        compressed = self._compress_context(resolved_chunks)

        # Step 5: Calculate grounding score
        grounding_score = self._calculate_grounding_score(compressed, query)

        # Build context
        context = [
            {
                "id": chunk.id,
                "text": chunk.content,
                "score": chunk.score,
                "docId": chunk.doc_id,
                "page": chunk.page,
                "metadata": chunk.metadata
            }
            for chunk in compressed
        ]

        return PostRetrievalResult(
            context=context,
            grounding_score=grounding_score,
            sources_used=len(compressed),
            conflicts_resolved=conflicts_resolved,
            duplicates_removed=duplicates_removed
        )

    def _deduplicate(
        self,
        chunks: List[RetrievedChunk],
        similarity_threshold: float = 0.85
    ) -> Tuple[List[RetrievedChunk], int]:
        """
        Remove near-duplicate chunks based on content similarity
        """
        if len(chunks) <= 1:
            return chunks, 0

        seen_hashes = set()
        deduped = []
        duplicates = 0

        for chunk in chunks:
            # Create content hash
            content_hash = hashlib.md5(chunk.content.lower().encode()).hexdigest()

            # Check for exact duplicates
            if content_hash in seen_hashes:
                duplicates += 1
                continue

            # Check for near-duplicates using simple word overlap
            is_duplicate = False
            chunk_words = set(chunk.content.lower().split())

            for existing in deduped:
                existing_words = set(existing.content.lower().split())
                if chunk_words and existing_words:
                    overlap = len(chunk_words & existing_words) / len(chunk_words | existing_words)
                    if overlap > similarity_threshold:
                        is_duplicate = True
                        duplicates += 1
                        break

            if not is_duplicate:
                seen_hashes.add(content_hash)
                deduped.append(chunk)

        return deduped, duplicates

    def _temporal_sort(self, chunks: List[RetrievedChunk]) -> List[RetrievedChunk]:
        """
        Sort chunks prioritizing latest versions
        """
        def get_effective_date(chunk: RetrievedChunk) -> datetime:
            effective_date = chunk.metadata.get("effectiveDate")
            if effective_date:
                try:
                    return datetime.fromisoformat(effective_date.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass
            return datetime.min

        # Sort by score first, then by date (newer first)
        return sorted(
            chunks,
            key=lambda c: (c.score, get_effective_date(c)),
            reverse=True
        )

    def _resolve_conflicts(
        self,
        chunks: List[RetrievedChunk]
    ) -> Tuple[List[RetrievedChunk], int]:
        """
        Resolve conflicting information:
        - Keep higher version
        - Keep newer effective date
        - Flag contradictions
        """
        conflicts_resolved = 0

        # Group by document
        doc_groups: Dict[str, List[RetrievedChunk]] = {}
        for chunk in chunks:
            doc_id = chunk.doc_id
            if doc_id not in doc_groups:
                doc_groups[doc_id] = []
            doc_groups[doc_id].append(chunk)

        resolved = []
        for doc_id, doc_chunks in doc_groups.items():
            if len(doc_chunks) == 1:
                resolved.extend(doc_chunks)
                continue

            # Check for version conflicts
            versions = {}
            for chunk in doc_chunks:
                version = chunk.metadata.get("version", "v1")
                if version not in versions:
                    versions[version] = []
                versions[version].append(chunk)

            if len(versions) > 1:
                # Keep only latest version
                latest_version = max(versions.keys(), key=lambda v: v.replace("v", ""))
                resolved.extend(versions[latest_version])
                conflicts_resolved += len(doc_chunks) - len(versions[latest_version])
            else:
                resolved.extend(doc_chunks)

        return resolved, conflicts_resolved

    def _compress_context(self, chunks: List[RetrievedChunk]) -> List[RetrievedChunk]:
        """
        Compress context to fit within token limit
        """
        compressed = []
        total_tokens = 0

        for chunk in chunks:
            # Estimate tokens (rough: 4 chars per token)
            chunk_tokens = len(chunk.content) // 4

            if total_tokens + chunk_tokens <= self.max_context_tokens:
                compressed.append(chunk)
                total_tokens += chunk_tokens
            else:
                # Try to add truncated version
                remaining_tokens = self.max_context_tokens - total_tokens
                if remaining_tokens > 100:
                    truncated_content = chunk.content[:remaining_tokens * 4]
                    truncated_chunk = RetrievedChunk(
                        id=chunk.id,
                        doc_id=chunk.doc_id,
                        content=truncated_content + "...",
                        score=chunk.score,
                        metadata=chunk.metadata,
                        page=chunk.page,
                        highlights=chunk.highlights
                    )
                    compressed.append(truncated_chunk)
                break

        return compressed

    def _calculate_grounding_score(
        self,
        chunks: List[RetrievedChunk],
        query: str
    ) -> float:
        """
        Calculate grounding score based on:
        - Number of sources
        - Score distribution
        - Query term coverage
        """
        if not chunks:
            return 0.0

        # Factor 1: Average retrieval score (0-1)
        avg_score = sum(c.score for c in chunks) / len(chunks)

        # Factor 2: Number of unique sources (normalized)
        unique_docs = len(set(c.doc_id for c in chunks))
        source_factor = min(unique_docs / 3, 1.0)  # 3+ sources = max

        # Factor 3: Query term coverage
        query_terms = set(query.lower().split())
        all_content = " ".join(c.content.lower() for c in chunks)
        covered_terms = sum(1 for term in query_terms if term in all_content)
        coverage_factor = covered_terms / len(query_terms) if query_terms else 0

        # Weighted combination
        grounding_score = (
            0.5 * avg_score +
            0.2 * source_factor +
            0.3 * coverage_factor
        )

        return round(min(max(grounding_score, 0), 1), 2)
