"""
Knowledge Operating System (KOS) for Enterprise RAG Platform (Phase 12).

Implements the unified knowledge layer that ties together all components:
- Knowledge abstraction layer
- Unified API for all knowledge operations
- Cross-domain reasoning
- Knowledge federation
- Semantic caching
- Knowledge lifecycle management
"""

import asyncio
import hashlib
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from collections import defaultdict

from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential
from openai import AsyncAzureOpenAI

logger = logging.getLogger(__name__)


class KnowledgeType(str, Enum):
    """Types of knowledge in the system."""
    DOCUMENT = "document"
    ENTITY = "entity"
    RELATIONSHIP = "relationship"
    FACT = "fact"
    INSIGHT = "insight"
    RULE = "rule"
    MEMORY = "memory"


class KnowledgeSource(str, Enum):
    """Sources of knowledge."""
    INGESTION = "ingestion"
    EXTRACTION = "extraction"
    USER_INPUT = "user_input"
    INFERENCE = "inference"
    CURATED = "curated"
    EXTERNAL = "external"


class KnowledgeStatus(str, Enum):
    """Status of knowledge items."""
    ACTIVE = "active"
    PENDING_REVIEW = "pending_review"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    CONFLICTED = "conflicted"


@dataclass
class KnowledgeItem:
    """Base class for all knowledge items in the system."""
    id: str
    knowledge_type: KnowledgeType
    content: dict
    source: KnowledgeSource
    status: KnowledgeStatus
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    confidence: float = 1.0
    version: int = 1
    metadata: dict = field(default_factory=dict)
    embeddings: list[float] = field(default_factory=list)
    relationships: list[str] = field(default_factory=list)
    provenance: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "knowledge_type": self.knowledge_type.value,
            "content": self.content,
            "source": self.source.value,
            "status": self.status.value,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "confidence": self.confidence,
            "version": self.version,
            "metadata": self.metadata,
            "embeddings": self.embeddings[:10] if self.embeddings else [],
            "relationships": self.relationships,
            "provenance": self.provenance
        }


@dataclass
class KnowledgeQuery:
    """Query specification for knowledge retrieval."""
    query_text: str
    tenant_id: str
    knowledge_types: list[KnowledgeType] = field(default_factory=list)
    sources: list[KnowledgeSource] = field(default_factory=list)
    min_confidence: float = 0.0
    include_relationships: bool = True
    include_provenance: bool = False
    top_k: int = 10
    filters: dict = field(default_factory=dict)
    reasoning_depth: int = 1


@dataclass
class KnowledgeResult:
    """Result from knowledge queries."""
    items: list[KnowledgeItem]
    reasoning_chain: list[dict] = field(default_factory=list)
    aggregations: dict = field(default_factory=dict)
    confidence: float = 1.0
    latency_ms: float = 0.0
    cache_hit: bool = False


class KnowledgeStore(ABC):
    """Abstract base for knowledge storage backends."""

    @abstractmethod
    async def store(self, item: KnowledgeItem) -> None:
        pass

    @abstractmethod
    async def retrieve(self, item_id: str, tenant_id: str) -> Optional[KnowledgeItem]:
        pass

    @abstractmethod
    async def search(self, query: KnowledgeQuery) -> list[KnowledgeItem]:
        pass

    @abstractmethod
    async def update(self, item: KnowledgeItem) -> None:
        pass

    @abstractmethod
    async def delete(self, item_id: str, tenant_id: str) -> bool:
        pass


class CosmosKnowledgeStore(KnowledgeStore):
    """Cosmos DB implementation of knowledge store."""

    def __init__(self, cosmos_client: CosmosClient, database_name: str):
        self.cosmos_client = cosmos_client
        self.database_name = database_name

    async def store(self, item: KnowledgeItem) -> None:
        try:
            database = self.cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client("knowledge_items")
            await container.upsert_item({
                **item.to_dict(),
                "partitionKey": item.tenant_id
            })
        except Exception as e:
            logger.error(f"Failed to store knowledge item: {e}")
            raise

    async def retrieve(self, item_id: str, tenant_id: str) -> Optional[KnowledgeItem]:
        try:
            database = self.cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client("knowledge_items")
            item = await container.read_item(item=item_id, partition_key=tenant_id)
            return self._dict_to_item(item)
        except Exception:
            return None

    async def search(self, query: KnowledgeQuery) -> list[KnowledgeItem]:
        try:
            database = self.cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client("knowledge_items")

            sql_query = """
                SELECT * FROM c
                WHERE c.tenant_id = @tenant_id
                AND c.confidence >= @min_confidence
                AND c.status = 'active'
            """
            params = [
                {"name": "@tenant_id", "value": query.tenant_id},
                {"name": "@min_confidence", "value": query.min_confidence}
            ]

            if query.knowledge_types:
                sql_query += " AND ARRAY_CONTAINS(@types, c.knowledge_type)"
                params.append({"name": "@types", "value": [t.value for t in query.knowledge_types]})

            if query.sources:
                sql_query += " AND ARRAY_CONTAINS(@sources, c.source)"
                params.append({"name": "@sources", "value": [s.value for s in query.sources]})

            items = []
            async for item in container.query_items(query=sql_query, parameters=params):
                items.append(self._dict_to_item(item))
                if len(items) >= query.top_k:
                    break

            return items
        except Exception as e:
            logger.error(f"Failed to search knowledge items: {e}")
            return []

    async def update(self, item: KnowledgeItem) -> None:
        item.updated_at = datetime.utcnow()
        item.version += 1
        await self.store(item)

    async def delete(self, item_id: str, tenant_id: str) -> bool:
        item = await self.retrieve(item_id, tenant_id)
        if item:
            item.status = KnowledgeStatus.ARCHIVED
            await self.update(item)
            return True
        return False

    def _dict_to_item(self, d: dict) -> KnowledgeItem:
        return KnowledgeItem(
            id=d["id"],
            knowledge_type=KnowledgeType(d["knowledge_type"]),
            content=d["content"],
            source=KnowledgeSource(d["source"]),
            status=KnowledgeStatus(d["status"]),
            tenant_id=d["tenant_id"],
            created_at=datetime.fromisoformat(d["created_at"]),
            updated_at=datetime.fromisoformat(d["updated_at"]),
            confidence=d.get("confidence", 1.0),
            version=d.get("version", 1),
            metadata=d.get("metadata", {}),
            embeddings=d.get("embeddings", []),
            relationships=d.get("relationships", []),
            provenance=d.get("provenance", [])
        )


class SemanticCache:
    """Semantic caching layer for knowledge queries."""

    def __init__(
        self,
        openai_client: AsyncAzureOpenAI,
        embedding_model: str = "text-embedding-3-large",
        similarity_threshold: float = 0.95,
        ttl_seconds: int = 3600
    ):
        self.openai_client = openai_client
        self.embedding_model = embedding_model
        self.similarity_threshold = similarity_threshold
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, dict] = {}
        self._embeddings: dict[str, list[float]] = {}

    async def get(self, query: str, tenant_id: str) -> Optional[dict]:
        query_embedding = await self._get_embedding(query)
        cache_key_prefix = f"{tenant_id}:"
        best_match = None
        best_similarity = 0.0

        for key, cached in self._cache.items():
            if not key.startswith(cache_key_prefix):
                continue
            if datetime.utcnow() > cached["expires_at"]:
                continue

            cached_embedding = self._embeddings.get(key, [])
            if cached_embedding:
                similarity = self._cosine_similarity(query_embedding, cached_embedding)
                if similarity > self.similarity_threshold and similarity > best_similarity:
                    best_match = cached
                    best_similarity = similarity

        if best_match:
            return best_match["result"]
        return None

    async def set(self, query: str, tenant_id: str, result: dict) -> None:
        cache_key = f"{tenant_id}:{hashlib.sha256(query.encode()).hexdigest()[:16]}"
        query_embedding = await self._get_embedding(query)

        self._cache[cache_key] = {
            "query": query,
            "result": result,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(seconds=self.ttl_seconds)
        }
        self._embeddings[cache_key] = query_embedding

    async def invalidate(self, tenant_id: str, pattern: str = None) -> int:
        prefix = f"{tenant_id}:"
        keys_to_delete = [
            k for k in self._cache.keys()
            if k.startswith(prefix) and (pattern is None or pattern in self._cache[k].get("query", ""))
        ]

        for key in keys_to_delete:
            del self._cache[key]
            if key in self._embeddings:
                del self._embeddings[key]

        return len(keys_to_delete)

    async def _get_embedding(self, text: str) -> list[float]:
        try:
            response = await self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return []

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)


class KnowledgeReasoner:
    """Performs multi-hop reasoning across knowledge items."""

    def __init__(self, openai_client: AsyncAzureOpenAI, knowledge_store: KnowledgeStore):
        self.openai_client = openai_client
        self.knowledge_store = knowledge_store
        self.model = "gpt-4o"

    async def reason(
        self,
        query: str,
        initial_items: list[KnowledgeItem],
        depth: int = 2,
        tenant_id: str = None
    ) -> dict:
        reasoning_chain = []
        current_context = initial_items

        for hop in range(depth):
            step_result = await self._reasoning_step(query, current_context, hop, reasoning_chain)
            reasoning_chain.append(step_result)

            if step_result.get("is_final", False):
                break

            if step_result.get("follow_up_queries"):
                for follow_up in step_result["follow_up_queries"]:
                    additional_items = await self._fetch_related(follow_up, tenant_id)
                    current_context.extend(additional_items)

        final_answer = await self._synthesize(query, reasoning_chain)

        return {
            "answer": final_answer,
            "reasoning_chain": reasoning_chain,
            "hops": len(reasoning_chain),
            "items_used": len(set(item.id for item in current_context))
        }

    async def _reasoning_step(
        self,
        query: str,
        context: list[KnowledgeItem],
        hop: int,
        prior_reasoning: list[dict]
    ) -> dict:
        context_text = "\n".join([
            f"[{item.knowledge_type.value}] {json.dumps(item.content)}"
            for item in context[:20]
        ])

        prior_text = "\n".join([
            f"Step {i+1}: {step.get('reasoning', '')}"
            for i, step in enumerate(prior_reasoning)
        ])

        prompt = f"""Perform reasoning step {hop + 1} to answer this query.

Query: {query}

Available Knowledge:
{context_text}

Prior Reasoning:
{prior_text if prior_text else "None"}

Return JSON:
{{
    "reasoning": "explanation of this step's logic",
    "conclusions": ["conclusions drawn"],
    "gaps": ["information gaps identified"],
    "follow_up_queries": ["queries to find more info"],
    "is_final": true/false,
    "confidence": 0.0-1.0
}}"""

        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        result["hop"] = hop
        return result

    async def _fetch_related(self, query_text: str, tenant_id: str) -> list[KnowledgeItem]:
        query = KnowledgeQuery(query_text=query_text, tenant_id=tenant_id, top_k=5)
        return await self.knowledge_store.search(query)

    async def _synthesize(self, query: str, reasoning_chain: list[dict]) -> str:
        chain_text = "\n".join([
            f"Step {step['hop'] + 1}:\n- Reasoning: {step['reasoning']}\n- Conclusions: {step['conclusions']}"
            for step in reasoning_chain
        ])

        prompt = f"""Synthesize a final answer based on the reasoning chain.

Query: {query}

Reasoning Chain:
{chain_text}

Provide a comprehensive answer."""

        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        return response.choices[0].message.content


class KnowledgeFederator:
    """Federates knowledge across multiple domains and sources."""

    def __init__(self):
        self._domain_stores: dict[str, KnowledgeStore] = {}
        self._domain_mappings: dict[str, list[str]] = {}

    def register_domain(
        self,
        domain_name: str,
        store: KnowledgeStore,
        mapped_concepts: list[str] = None
    ) -> None:
        self._domain_stores[domain_name] = store
        self._domain_mappings[domain_name] = mapped_concepts or []

    async def federated_search(
        self,
        query: KnowledgeQuery,
        domains: list[str] = None
    ) -> dict[str, list[KnowledgeItem]]:
        target_domains = domains or list(self._domain_stores.keys())
        results = {}

        search_tasks = [
            self._search_domain(domain, query)
            for domain in target_domains
            if domain in self._domain_stores
        ]

        domain_results = await asyncio.gather(*search_tasks, return_exceptions=True)

        for domain, result in zip(target_domains, domain_results):
            if isinstance(result, Exception):
                logger.error(f"Search failed for domain {domain}: {result}")
                results[domain] = []
            else:
                results[domain] = result

        return results

    async def _search_domain(self, domain: str, query: KnowledgeQuery) -> list[KnowledgeItem]:
        store = self._domain_stores.get(domain)
        if store:
            return await store.search(query)
        return []


class KnowledgeLifecycleManager:
    """Manages the lifecycle of knowledge items."""

    def __init__(self, knowledge_store: KnowledgeStore):
        self.knowledge_store = knowledge_store

    async def promote(self, item_id: str, tenant_id: str) -> bool:
        item = await self.knowledge_store.retrieve(item_id, tenant_id)
        if item and item.status == KnowledgeStatus.PENDING_REVIEW:
            item.status = KnowledgeStatus.ACTIVE
            item.provenance.append({
                "action": "promoted",
                "timestamp": datetime.utcnow().isoformat(),
                "from_status": "pending_review"
            })
            await self.knowledge_store.update(item)
            return True
        return False

    async def deprecate(
        self,
        item_id: str,
        tenant_id: str,
        reason: str,
        replacement_id: str = None
    ) -> bool:
        item = await self.knowledge_store.retrieve(item_id, tenant_id)
        if item:
            item.status = KnowledgeStatus.DEPRECATED
            item.metadata["deprecation"] = {
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat(),
                "replacement_id": replacement_id
            }
            await self.knowledge_store.update(item)
            return True
        return False

    async def merge(
        self,
        item_ids: list[str],
        tenant_id: str,
        merge_strategy: str = "union"
    ) -> Optional[KnowledgeItem]:
        items = []
        for item_id in item_ids:
            item = await self.knowledge_store.retrieve(item_id, tenant_id)
            if item:
                items.append(item)

        if len(items) < 2:
            return None

        merged_content = self._merge_contents([i.content for i in items], merge_strategy)
        merged_relationships = list(set(r for i in items for r in i.relationships))

        merged = KnowledgeItem(
            id=hashlib.sha256(":".join(item_ids).encode()).hexdigest()[:16],
            knowledge_type=items[0].knowledge_type,
            content=merged_content,
            source=KnowledgeSource.CURATED,
            status=KnowledgeStatus.PENDING_REVIEW,
            tenant_id=tenant_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            confidence=min(i.confidence for i in items),
            metadata={"merged_from": item_ids},
            relationships=merged_relationships,
            provenance=[{
                "action": "merged",
                "timestamp": datetime.utcnow().isoformat(),
                "source_items": item_ids,
                "strategy": merge_strategy
            }]
        )

        await self.knowledge_store.store(merged)

        for item in items:
            await self.deprecate(item.id, tenant_id, "merged", merged.id)

        return merged

    def _merge_contents(self, contents: list[dict], strategy: str) -> dict:
        if strategy == "union":
            merged = {}
            for content in contents:
                for key, value in content.items():
                    if key not in merged:
                        merged[key] = value
                    elif isinstance(value, list) and isinstance(merged[key], list):
                        merged[key] = list(set(merged[key] + value))
            return merged
        elif strategy == "latest":
            return contents[-1] if contents else {}
        else:
            return contents[0] if contents else {}


class KnowledgeOperatingSystem:
    """Main Knowledge Operating System - unified API for all knowledge operations."""

    def __init__(
        self,
        cosmos_endpoint: str,
        openai_endpoint: str,
        openai_api_key: str,
        openai_api_version: str = "2024-02-15-preview"
    ):
        self.cosmos_endpoint = cosmos_endpoint
        self.openai_endpoint = openai_endpoint
        self.openai_api_key = openai_api_key
        self.openai_api_version = openai_api_version

        self._cosmos_client: Optional[CosmosClient] = None
        self._openai_client: Optional[AsyncAzureOpenAI] = None

        self.store: Optional[KnowledgeStore] = None
        self.cache: Optional[SemanticCache] = None
        self.reasoner: Optional[KnowledgeReasoner] = None
        self.federator: Optional[KnowledgeFederator] = None
        self.lifecycle: Optional[KnowledgeLifecycleManager] = None

        self._initialized = False

    async def initialize(self) -> None:
        if self._initialized:
            return

        credential = DefaultAzureCredential()
        self._cosmos_client = CosmosClient(self.cosmos_endpoint, credential=credential)
        self._openai_client = AsyncAzureOpenAI(
            azure_endpoint=self.openai_endpoint,
            api_key=self.openai_api_key,
            api_version=self.openai_api_version
        )

        database_name = "rag_platform"
        self.store = CosmosKnowledgeStore(self._cosmos_client, database_name)
        self.cache = SemanticCache(self._openai_client)
        self.reasoner = KnowledgeReasoner(self._openai_client, self.store)
        self.federator = KnowledgeFederator()
        self.lifecycle = KnowledgeLifecycleManager(self.store)
        self.federator.register_domain("main", self.store)

        self._initialized = True
        logger.info("Knowledge Operating System initialized")

    async def query(
        self,
        query_text: str,
        tenant_id: str,
        options: dict = None
    ) -> KnowledgeResult:
        if not self._initialized:
            await self.initialize()

        start_time = datetime.utcnow()
        options = options or {}

        if options.get("use_cache", True):
            cached = await self.cache.get(query_text, tenant_id)
            if cached:
                return KnowledgeResult(
                    items=cached.get("items", []),
                    reasoning_chain=cached.get("reasoning_chain", []),
                    confidence=cached.get("confidence", 1.0),
                    cache_hit=True,
                    latency_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
                )

        query = KnowledgeQuery(
            query_text=query_text,
            tenant_id=tenant_id,
            knowledge_types=[KnowledgeType(t) for t in options.get("types", [])],
            min_confidence=options.get("min_confidence", 0.5),
            include_relationships=options.get("include_relationships", True),
            top_k=options.get("top_k", 20),
            reasoning_depth=options.get("reasoning_depth", 1)
        )

        items = await self.store.search(query)

        reasoning_chain = []
        if query.reasoning_depth > 1 and items:
            reasoning_result = await self.reasoner.reason(
                query_text, items, depth=query.reasoning_depth, tenant_id=tenant_id
            )
            reasoning_chain = reasoning_result.get("reasoning_chain", [])

        avg_confidence = sum(i.confidence for i in items) / len(items) if items else 0.0

        result = KnowledgeResult(
            items=items,
            reasoning_chain=reasoning_chain,
            confidence=avg_confidence,
            cache_hit=False,
            latency_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
        )

        if options.get("use_cache", True) and items:
            await self.cache.set(query_text, tenant_id, {
                "items": [i.to_dict() for i in items],
                "reasoning_chain": reasoning_chain,
                "confidence": avg_confidence
            })

        return result

    async def ingest(
        self,
        content: dict,
        knowledge_type: KnowledgeType,
        tenant_id: str,
        source: KnowledgeSource = KnowledgeSource.INGESTION,
        metadata: dict = None
    ) -> KnowledgeItem:
        if not self._initialized:
            await self.initialize()

        item_id = hashlib.sha256(
            f"{tenant_id}:{json.dumps(content, sort_keys=True)}".encode()
        ).hexdigest()[:16]

        item = KnowledgeItem(
            id=item_id,
            knowledge_type=knowledge_type,
            content=content,
            source=source,
            status=KnowledgeStatus.ACTIVE if source == KnowledgeSource.CURATED else KnowledgeStatus.PENDING_REVIEW,
            tenant_id=tenant_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata=metadata or {},
            provenance=[{
                "action": "ingested",
                "timestamp": datetime.utcnow().isoformat(),
                "source": source.value
            }]
        )

        if "text" in content:
            embedding_response = await self._openai_client.embeddings.create(
                model="text-embedding-3-large",
                input=content["text"][:8000]
            )
            item.embeddings = embedding_response.data[0].embedding

        await self.store.store(item)
        await self.cache.invalidate(tenant_id)

        return item

    async def extract_entities(
        self,
        text: str,
        tenant_id: str,
        entity_types: list[str] = None
    ) -> list[KnowledgeItem]:
        if not self._initialized:
            await self.initialize()

        types_hint = f"Focus on: {', '.join(entity_types)}" if entity_types else ""

        prompt = f"""Extract entities from this text.
{types_hint}

Text:
{text[:4000]}

Return JSON:
{{
    "entities": [
        {{
            "name": "entity name",
            "type": "person|organization|location|concept|product|event",
            "description": "brief description",
            "attributes": {{}},
            "relationships": ["related entity names"]
        }}
    ]
}}"""

        response = await self._openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )

        extraction = json.loads(response.choices[0].message.content)
        items = []

        for entity in extraction.get("entities", []):
            item = await self.ingest(
                content={
                    "name": entity["name"],
                    "type": entity["type"],
                    "description": entity.get("description", ""),
                    "attributes": entity.get("attributes", {})
                },
                knowledge_type=KnowledgeType.ENTITY,
                tenant_id=tenant_id,
                source=KnowledgeSource.EXTRACTION,
                metadata={"source_text_preview": text[:200]}
            )
            items.append(item)

        return items

    async def get_knowledge_graph(
        self,
        tenant_id: str,
        center_id: str = None,
        depth: int = 2
    ) -> dict:
        if not self._initialized:
            await self.initialize()

        nodes = []
        edges = []
        visited = set()

        async def traverse(item_id: str, current_depth: int):
            if item_id in visited or current_depth > depth:
                return

            visited.add(item_id)
            item = await self.store.retrieve(item_id, tenant_id)

            if not item:
                return

            nodes.append({
                "id": item.id,
                "type": item.knowledge_type.value,
                "label": item.content.get("name", item.content.get("text", item.id)[:50]),
                "properties": item.content
            })

            for rel_id in item.relationships:
                rel = await self.store.retrieve(rel_id, tenant_id)
                if rel and rel.knowledge_type == KnowledgeType.RELATIONSHIP:
                    edges.append({
                        "id": rel.id,
                        "source": rel.content.get("source_id"),
                        "target": rel.content.get("target_id"),
                        "type": rel.content.get("relationship_type"),
                        "properties": rel.content.get("properties", {})
                    })

                    next_id = (
                        rel.content.get("target_id")
                        if rel.content.get("source_id") == item_id
                        else rel.content.get("source_id")
                    )
                    if next_id:
                        await traverse(next_id, current_depth + 1)

        if center_id:
            await traverse(center_id, 0)
        else:
            query = KnowledgeQuery(
                query_text="",
                tenant_id=tenant_id,
                knowledge_types=[KnowledgeType.ENTITY],
                top_k=100
            )
            items = await self.store.search(query)
            for item in items[:20]:
                await traverse(item.id, 0)

        return {
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges)
        }

    async def close(self) -> None:
        if self._cosmos_client:
            await self._cosmos_client.close()
        if self._openai_client:
            await self._openai_client.close()


async def main():
    """Example usage of Knowledge Operating System."""
    kos = KnowledgeOperatingSystem(
        cosmos_endpoint="https://your-cosmos.documents.azure.com:443/",
        openai_endpoint="https://your-openai.openai.azure.com/",
        openai_api_key="your-api-key"
    )

    await kos.initialize()

    doc = await kos.ingest(
        content={"text": "Contoso reported Q4 revenue of $5.2 billion.", "title": "Q4 Results"},
        knowledge_type=KnowledgeType.DOCUMENT,
        tenant_id="tenant-123"
    )
    print(f"Ingested document: {doc.id}")

    result = await kos.query(
        query_text="What were Contoso's Q4 results?",
        tenant_id="tenant-123",
        options={"reasoning_depth": 2}
    )
    print(f"Found {len(result.items)} items")

    await kos.close()


if __name__ == "__main__":
    asyncio.run(main())
