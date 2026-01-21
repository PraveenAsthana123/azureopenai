"""
Domain Memory Layer

Implements:
- Stable enterprise knowledge beyond raw PDFs
- Curated facts with source tracking
- Human approval workflows
- Personalized retrieval by role/team
- Feedback-driven learning loops
"""

from dataclasses import dataclass, field
from typing import Any
from enum import Enum
import asyncio
import hashlib
import json
from datetime import datetime, timedelta

from azure.cosmos import CosmosClient
from azure.search.documents import SearchClient
from azure.identity import DefaultAzureCredential
from openai import AsyncAzureOpenAI


class MemoryStatus(Enum):
    """Status of a memory item."""
    PROPOSED = "proposed"  # Auto-extracted, pending review
    APPROVED = "approved"  # Human-approved
    REJECTED = "rejected"  # Human-rejected
    DEPRECATED = "deprecated"  # Superseded by newer fact
    ACTIVE = "active"  # In production use


class FactType(Enum):
    """Types of facts in memory."""
    THRESHOLD = "threshold"  # Specific limits, values
    POLICY = "policy"  # Policy statements
    DEFINITION = "definition"  # Term definitions
    OWNERSHIP = "ownership"  # Who owns what
    PROCESS = "process"  # How things work
    CONFIGURATION = "configuration"  # System settings
    COMPLIANCE = "compliance"  # Compliance requirements
    METRIC = "metric"  # KPIs, measurements


@dataclass
class MemoryItem:
    """A curated fact in domain memory."""
    id: str
    tenant_id: str
    fact_type: FactType
    fact: str  # The actual statement
    normalized_fact: str  # Canonical form for deduplication
    sources: list[str]  # Source chunk IDs
    source_docs: list[str]  # Source document IDs
    confidence: float
    status: MemoryStatus
    valid_from: str | None = None
    valid_until: str | None = None
    owner_group: str | None = None
    approved_by: str | None = None
    approved_at: str | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    embedding: list[float] | None = None
    tags: list[str] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    conflict_ids: list[str] = field(default_factory=list)  # IDs of conflicting facts


@dataclass
class MemoryCandidate:
    """A proposed memory item from auto-extraction."""
    fact: str
    fact_type: FactType
    confidence: float
    source_chunk_ids: list[str]
    source_doc_ids: list[str]
    reasoning: str
    conflicts_with: list[str] = field(default_factory=list)


@dataclass
class UserPreferences:
    """User/team preferences for personalization."""
    user_id: str
    tenant_id: str
    preferred_sources: list[str] = field(default_factory=list)
    pinned_docs: list[str] = field(default_factory=list)
    role_boosting: dict[str, float] = field(default_factory=dict)
    output_format: str = "detailed"  # "short", "detailed", "bullets"
    preferred_tone: str = "professional"


@dataclass
class FeedbackItem:
    """User feedback on RAG responses."""
    id: str
    tenant_id: str
    user_id: str
    query: str
    response_id: str
    feedback_type: str  # "helpful", "not_helpful", "wrong_citation", "outdated", "missing"
    comment: str | None = None
    chunk_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class MemoryExtractor:
    """
    Extracts candidate memory items from chunks.

    Uses LLM to identify stable facts that should be memorized.
    """

    EXTRACTION_PROMPT = """You are an expert at identifying stable, reusable facts from documents.

Analyze the following text and extract facts that should be "memorized" for quick retrieval.

Good candidates for memory:
- Specific thresholds, limits, or values (e.g., "rotation interval is 90 days")
- Policy statements (e.g., "all secrets must be stored in Key Vault")
- Ownership/responsibility (e.g., "SecOps team owns Key Vault policies")
- Definitions of domain terms
- Compliance requirements
- Configuration standards

NOT good candidates:
- Temporary information
- Opinions or recommendations without authority
- Vague or ambiguous statements
- Information that changes frequently

Text to analyze:
{text}

Extract facts as JSON:
{{
  "facts": [
    {{
      "fact": "exact statement of the fact",
      "fact_type": "threshold|policy|definition|ownership|process|configuration|compliance|metric",
      "confidence": 0.0-1.0,
      "reasoning": "why this should be memorized"
    }}
  ]
}}

If no suitable facts are found, return {{"facts": []}}"""

    def __init__(
        self,
        openai_client: AsyncAzureOpenAI,
        model: str = "gpt-4o-mini",
    ):
        self.client = openai_client
        self.model = model

    async def extract_candidates(
        self,
        text: str,
        chunk_id: str,
        doc_id: str,
        tenant_id: str,
    ) -> list[MemoryCandidate]:
        """Extract memory candidates from text."""
        if len(text) > 8000:
            text = text[:8000] + "..."

        prompt = self.EXTRACTION_PROMPT.format(text=text)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            candidates = []

            for fact_data in result.get("facts", []):
                try:
                    fact_type = FactType(fact_data["fact_type"])
                except ValueError:
                    fact_type = FactType.POLICY

                candidates.append(MemoryCandidate(
                    fact=fact_data["fact"],
                    fact_type=fact_type,
                    confidence=fact_data.get("confidence", 0.7),
                    source_chunk_ids=[chunk_id],
                    source_doc_ids=[doc_id],
                    reasoning=fact_data.get("reasoning", ""),
                ))

            return candidates

        except Exception:
            return []

    async def extract_batch(
        self,
        chunks: list[dict],
        tenant_id: str,
        max_concurrency: int = 5,
    ) -> list[MemoryCandidate]:
        """Extract candidates from multiple chunks."""
        semaphore = asyncio.Semaphore(max_concurrency)

        async def extract_single(chunk: dict) -> list[MemoryCandidate]:
            async with semaphore:
                return await self.extract_candidates(
                    text=chunk["content"],
                    chunk_id=chunk["chunk_id"],
                    doc_id=chunk["doc_id"],
                    tenant_id=tenant_id,
                )

        tasks = [extract_single(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks)

        # Flatten
        all_candidates = []
        for batch in results:
            all_candidates.extend(batch)

        return all_candidates


class MemoryStore:
    """
    Stores and manages domain memory.

    Uses Cosmos DB for persistence and Azure AI Search for retrieval.
    """

    def __init__(
        self,
        cosmos_client: CosmosClient,
        search_client: SearchClient,
        database_name: str = "rag-platform",
        container_name: str = "domain-memory",
    ):
        database = cosmos_client.get_database_client(database_name)
        self.container = database.get_container_client(container_name)
        self.search_client = search_client

    async def add_candidate(
        self,
        candidate: MemoryCandidate,
        tenant_id: str,
    ) -> MemoryItem:
        """Add a memory candidate for review."""
        # Generate normalized form
        normalized = self._normalize_fact(candidate.fact)

        # Check for existing similar facts
        existing = await self._find_similar_facts(normalized, tenant_id)
        conflict_ids = [e.id for e in existing if e.fact != candidate.fact]

        # Generate ID
        memory_id = hashlib.sha256(
            f"{tenant_id}:{normalized}".encode()
        ).hexdigest()[:16]

        memory_item = MemoryItem(
            id=memory_id,
            tenant_id=tenant_id,
            fact_type=candidate.fact_type,
            fact=candidate.fact,
            normalized_fact=normalized,
            sources=candidate.source_chunk_ids,
            source_docs=candidate.source_doc_ids,
            confidence=candidate.confidence,
            status=MemoryStatus.PROPOSED,
            conflict_ids=conflict_ids,
        )

        # Store in Cosmos
        self.container.upsert_item(
            body=self._memory_to_dict(memory_item),
            partition_key=tenant_id,
        )

        return memory_item

    async def approve(
        self,
        memory_id: str,
        tenant_id: str,
        approved_by: str,
        valid_from: str | None = None,
        valid_until: str | None = None,
        owner_group: str | None = None,
    ) -> MemoryItem | None:
        """Approve a memory item."""
        try:
            item = self.container.read_item(item=memory_id, partition_key=tenant_id)
        except Exception:
            return None

        item["status"] = MemoryStatus.APPROVED.value
        item["approved_by"] = approved_by
        item["approved_at"] = datetime.utcnow().isoformat()
        item["updated_at"] = datetime.utcnow().isoformat()

        if valid_from:
            item["valid_from"] = valid_from
        if valid_until:
            item["valid_until"] = valid_until
        if owner_group:
            item["owner_group"] = owner_group

        self.container.upsert_item(body=item, partition_key=tenant_id)

        # Index in search for retrieval
        await self._index_memory(item)

        return self._dict_to_memory(item)

    async def reject(
        self,
        memory_id: str,
        tenant_id: str,
        rejected_by: str,
        reason: str | None = None,
    ) -> bool:
        """Reject a memory candidate."""
        try:
            item = self.container.read_item(item=memory_id, partition_key=tenant_id)
            item["status"] = MemoryStatus.REJECTED.value
            item["attributes"]["rejected_by"] = rejected_by
            item["attributes"]["rejection_reason"] = reason
            item["updated_at"] = datetime.utcnow().isoformat()

            self.container.upsert_item(body=item, partition_key=tenant_id)
            return True
        except Exception:
            return False

    async def deprecate(
        self,
        memory_id: str,
        tenant_id: str,
        superseded_by: str | None = None,
    ) -> bool:
        """Deprecate a memory item."""
        try:
            item = self.container.read_item(item=memory_id, partition_key=tenant_id)
            item["status"] = MemoryStatus.DEPRECATED.value
            item["attributes"]["superseded_by"] = superseded_by
            item["updated_at"] = datetime.utcnow().isoformat()

            self.container.upsert_item(body=item, partition_key=tenant_id)

            # Remove from search index
            self.search_client.delete_documents([{"id": memory_id}])
            return True
        except Exception:
            return False

    async def get_pending_approvals(
        self,
        tenant_id: str,
        owner_group: str | None = None,
        limit: int = 50,
    ) -> list[MemoryItem]:
        """Get memory items pending approval."""
        query = f"""
        SELECT * FROM c
        WHERE c.tenant_id = '{tenant_id}'
        AND c.status = '{MemoryStatus.PROPOSED.value}'
        """

        if owner_group:
            query += f" AND (c.owner_group = '{owner_group}' OR NOT IS_DEFINED(c.owner_group))"

        query += f" ORDER BY c.created_at DESC OFFSET 0 LIMIT {limit}"

        items = list(self.container.query_items(query=query, partition_key=tenant_id))
        return [self._dict_to_memory(item) for item in items]

    async def search_memory(
        self,
        query: str,
        tenant_id: str,
        fact_types: list[FactType] | None = None,
        top_k: int = 10,
    ) -> list[MemoryItem]:
        """Search approved memory items."""
        filter_str = f"tenant_id eq '{tenant_id}' and status eq '{MemoryStatus.APPROVED.value}'"

        if fact_types:
            types_filter = " or ".join(f"fact_type eq '{ft.value}'" for ft in fact_types)
            filter_str += f" and ({types_filter})"

        results = self.search_client.search(
            search_text=query,
            filter=filter_str,
            top=top_k,
            select=["id", "fact", "fact_type", "confidence", "sources", "valid_from", "valid_until"],
        )

        memories = []
        for result in results:
            memories.append(MemoryItem(
                id=result["id"],
                tenant_id=tenant_id,
                fact_type=FactType(result["fact_type"]),
                fact=result["fact"],
                normalized_fact="",
                sources=result.get("sources", []),
                source_docs=[],
                confidence=result.get("confidence", 0.0),
                status=MemoryStatus.APPROVED,
                valid_from=result.get("valid_from"),
                valid_until=result.get("valid_until"),
            ))

        return memories

    async def _find_similar_facts(
        self,
        normalized_fact: str,
        tenant_id: str,
    ) -> list[MemoryItem]:
        """Find existing facts similar to the normalized form."""
        # Use search to find similar
        results = self.search_client.search(
            search_text=normalized_fact,
            filter=f"tenant_id eq '{tenant_id}'",
            top=5,
        )

        similar = []
        for result in results:
            if result.get("@search.score", 0) > 0.8:
                similar.append(self._dict_to_memory(result))

        return similar

    async def _index_memory(self, item: dict):
        """Index a memory item for search."""
        doc = {
            "id": item["id"],
            "tenant_id": item["tenant_id"],
            "fact": item["fact"],
            "fact_type": item["fact_type"],
            "confidence": item.get("confidence", 0.0),
            "sources": item.get("sources", []),
            "valid_from": item.get("valid_from"),
            "valid_until": item.get("valid_until"),
            "status": item["status"],
        }

        if item.get("embedding"):
            doc["embedding"] = item["embedding"]

        self.search_client.upload_documents([doc])

    def _normalize_fact(self, fact: str) -> str:
        """Normalize a fact for comparison."""
        return " ".join(fact.lower().split())

    def _memory_to_dict(self, memory: MemoryItem) -> dict:
        """Convert MemoryItem to dict for storage."""
        return {
            "id": memory.id,
            "tenant_id": memory.tenant_id,
            "fact_type": memory.fact_type.value,
            "fact": memory.fact,
            "normalized_fact": memory.normalized_fact,
            "sources": memory.sources,
            "source_docs": memory.source_docs,
            "confidence": memory.confidence,
            "status": memory.status.value,
            "valid_from": memory.valid_from,
            "valid_until": memory.valid_until,
            "owner_group": memory.owner_group,
            "approved_by": memory.approved_by,
            "approved_at": memory.approved_at,
            "created_at": memory.created_at,
            "updated_at": memory.updated_at,
            "embedding": memory.embedding,
            "tags": memory.tags,
            "attributes": memory.attributes,
            "conflict_ids": memory.conflict_ids,
        }

    def _dict_to_memory(self, d: dict) -> MemoryItem:
        """Convert dict to MemoryItem."""
        return MemoryItem(
            id=d["id"],
            tenant_id=d["tenant_id"],
            fact_type=FactType(d["fact_type"]) if isinstance(d["fact_type"], str) else d["fact_type"],
            fact=d["fact"],
            normalized_fact=d.get("normalized_fact", ""),
            sources=d.get("sources", []),
            source_docs=d.get("source_docs", []),
            confidence=d.get("confidence", 0.0),
            status=MemoryStatus(d["status"]) if isinstance(d["status"], str) else d["status"],
            valid_from=d.get("valid_from"),
            valid_until=d.get("valid_until"),
            owner_group=d.get("owner_group"),
            approved_by=d.get("approved_by"),
            approved_at=d.get("approved_at"),
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
            embedding=d.get("embedding"),
            tags=d.get("tags", []),
            attributes=d.get("attributes", {}),
            conflict_ids=d.get("conflict_ids", []),
        )


class PersonalizationService:
    """
    Manages user preferences and personalized retrieval boosting.
    """

    # Role-to-source-type boosting
    ROLE_BOOSTS = {
        "engineer": {"runbooks": 1.5, "design_docs": 1.3, "code": 1.4},
        "compliance": {"policies": 1.5, "audits": 1.4, "controls": 1.3},
        "security": {"security": 1.5, "policies": 1.3, "incidents": 1.4},
        "manager": {"reports": 1.4, "summaries": 1.3, "metrics": 1.3},
        "support": {"troubleshooting": 1.5, "faqs": 1.4, "runbooks": 1.3},
    }

    def __init__(
        self,
        cosmos_client: CosmosClient,
        database_name: str = "rag-platform",
    ):
        database = cosmos_client.get_database_client(database_name)
        self.prefs_container = database.get_container_client("user-preferences")
        self.feedback_container = database.get_container_client("user-feedback")

    async def get_preferences(
        self,
        user_id: str,
        tenant_id: str,
    ) -> UserPreferences:
        """Get user preferences, creating defaults if needed."""
        try:
            item = self.prefs_container.read_item(item=user_id, partition_key=tenant_id)
            return UserPreferences(
                user_id=item["user_id"],
                tenant_id=item["tenant_id"],
                preferred_sources=item.get("preferred_sources", []),
                pinned_docs=item.get("pinned_docs", []),
                role_boosting=item.get("role_boosting", {}),
                output_format=item.get("output_format", "detailed"),
                preferred_tone=item.get("preferred_tone", "professional"),
            )
        except Exception:
            # Return defaults
            return UserPreferences(user_id=user_id, tenant_id=tenant_id)

    async def update_preferences(
        self,
        preferences: UserPreferences,
    ) -> bool:
        """Update user preferences."""
        try:
            self.prefs_container.upsert_item(
                body={
                    "id": preferences.user_id,
                    "user_id": preferences.user_id,
                    "tenant_id": preferences.tenant_id,
                    "preferred_sources": preferences.preferred_sources,
                    "pinned_docs": preferences.pinned_docs,
                    "role_boosting": preferences.role_boosting,
                    "output_format": preferences.output_format,
                    "preferred_tone": preferences.preferred_tone,
                    "updated_at": datetime.utcnow().isoformat(),
                },
                partition_key=preferences.tenant_id,
            )
            return True
        except Exception:
            return False

    def get_role_boosts(self, user_role: str) -> dict[str, float]:
        """Get source type boosts for a user role."""
        return self.ROLE_BOOSTS.get(user_role.lower(), {})

    async def record_feedback(
        self,
        feedback: FeedbackItem,
    ) -> str:
        """Record user feedback."""
        feedback_id = hashlib.sha256(
            f"{feedback.user_id}:{feedback.response_id}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]

        self.feedback_container.upsert_item(
            body={
                "id": feedback_id,
                "tenant_id": feedback.tenant_id,
                "user_id": feedback.user_id,
                "query": feedback.query,
                "response_id": feedback.response_id,
                "feedback_type": feedback.feedback_type,
                "comment": feedback.comment,
                "chunk_ids": feedback.chunk_ids,
                "created_at": feedback.created_at,
            },
            partition_key=feedback.tenant_id,
        )

        return feedback_id

    async def get_feedback_summary(
        self,
        tenant_id: str,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get feedback summary for analysis."""
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        query = f"""
        SELECT c.feedback_type, COUNT(1) as count
        FROM c
        WHERE c.tenant_id = '{tenant_id}'
        AND c.created_at >= '{cutoff}'
        GROUP BY c.feedback_type
        """

        results = list(self.feedback_container.query_items(
            query=query,
            partition_key=tenant_id,
        ))

        summary = {"total": 0, "by_type": {}}
        for r in results:
            summary["by_type"][r["feedback_type"]] = r["count"]
            summary["total"] += r["count"]

        return summary


class MemoryFirstRetriever:
    """
    Retrieves from memory first, then falls back to raw chunks.

    Implements the memory-first answering pattern:
    1. Search memory for relevant facts
    2. Search raw index for supporting details
    3. Compare and flag conflicts
    """

    def __init__(
        self,
        memory_store: MemoryStore,
        raw_retriever: Any,  # HybridRetriever
        personalization: PersonalizationService,
    ):
        self.memory = memory_store
        self.raw_retriever = raw_retriever
        self.personalization = personalization

    async def retrieve(
        self,
        query: str,
        user_id: str,
        tenant_id: str,
        user_role: str | None = None,
    ) -> dict[str, Any]:
        """
        Retrieve from memory and raw index.

        Returns combined results with conflict detection.
        """
        # Get user preferences
        prefs = await self.personalization.get_preferences(user_id, tenant_id)

        # Search memory first
        memory_results = await self.memory.search_memory(
            query=query,
            tenant_id=tenant_id,
            top_k=5,
        )

        # Search raw index
        from src.retrieval.hybrid_retriever import UserContext
        user_context = UserContext(
            user_id=user_id,
            tenant_id=tenant_id,
        )

        raw_results = await self.raw_retriever.retrieve(query, user_context)

        # Apply personalization boosting
        if user_role:
            boosts = self.personalization.get_role_boosts(user_role)
            for chunk in raw_results.chunks:
                doc_type = chunk.metadata.get("doc_type", "")
                if doc_type in boosts:
                    chunk.final_score *= boosts[doc_type]

            # Re-sort after boosting
            raw_results.chunks.sort(key=lambda c: c.final_score, reverse=True)

        # Boost pinned docs
        pinned_set = set(prefs.pinned_docs)
        for chunk in raw_results.chunks:
            if chunk.doc_id in pinned_set:
                chunk.final_score *= 1.2

        # Detect conflicts between memory and raw
        conflicts = self._detect_conflicts(memory_results, raw_results.chunks)

        return {
            "memory_facts": memory_results,
            "raw_chunks": raw_results.chunks,
            "conflicts": conflicts,
            "query": query,
            "personalization_applied": bool(user_role or prefs.pinned_docs),
        }

    def _detect_conflicts(
        self,
        memory_facts: list[MemoryItem],
        raw_chunks: list[Any],
    ) -> list[dict[str, Any]]:
        """Detect conflicts between memory facts and raw chunks."""
        conflicts = []

        # Simple heuristic: look for contradictory numbers/values
        for fact in memory_facts:
            fact_lower = fact.fact.lower()

            for chunk in raw_chunks:
                chunk_lower = chunk.content.lower()

                # Check for potential value conflicts
                # This is a simplified check - production would use more sophisticated NLI
                if self._might_conflict(fact_lower, chunk_lower):
                    conflicts.append({
                        "memory_fact_id": fact.id,
                        "memory_fact": fact.fact,
                        "chunk_id": chunk.id,
                        "chunk_content": chunk.content[:200],
                        "confidence": 0.5,  # Would be computed by conflict detector
                    })

        return conflicts

    def _might_conflict(self, fact: str, chunk: str) -> bool:
        """Simple heuristic to detect potential conflicts."""
        import re

        # Extract numbers from both
        fact_numbers = set(re.findall(r'\d+', fact))
        chunk_numbers = set(re.findall(r'\d+', chunk))

        # If they share context words but have different numbers, might conflict
        context_words = {"days", "hours", "minutes", "percent", "%", "limit", "max", "min"}
        fact_words = set(fact.split())
        chunk_words = set(chunk.split())

        shared_context = (fact_words & context_words) & (chunk_words & context_words)

        if shared_context and fact_numbers and chunk_numbers:
            if fact_numbers != chunk_numbers:
                return True

        return False
