"""
Entity Extraction for Knowledge Graph

Implements:
- Named Entity Recognition (NER)
- Entity normalization and deduplication
- Relationship extraction
- Graph node/edge creation
- Integration with Azure Cosmos DB (Gremlin or SQL)
"""

from dataclasses import dataclass, field
from typing import Any
from enum import Enum
import asyncio
import hashlib
import json
import re
from datetime import datetime

from openai import AsyncAzureOpenAI


class EntityType(Enum):
    """Types of entities to extract."""
    PERSON = "person"
    ORGANIZATION = "organization"
    SYSTEM = "system"
    SERVICE = "service"
    POLICY = "policy"
    CONTROL = "control"
    METRIC = "metric"
    THRESHOLD = "threshold"
    DATE = "date"
    VERSION = "version"
    LOCATION = "location"
    TERM = "term"
    PROCESS = "process"
    DOCUMENT = "document"


class RelationType(Enum):
    """Types of relationships between entities."""
    OWNS = "owns"
    MANAGES = "manages"
    DEPENDS_ON = "depends_on"
    REFERENCES = "references"
    DEFINES = "defines"
    CONTAINS = "contains"
    APPLIES_TO = "applies_to"
    SUPERSEDES = "supersedes"
    CO_OCCURS = "co_occurs"


@dataclass
class Entity:
    """An extracted entity."""
    id: str
    name: str
    normalized_name: str
    entity_type: EntityType
    confidence: float
    source_chunk_ids: list[str]
    source_doc_ids: list[str]
    attributes: dict[str, Any] = field(default_factory=dict)
    aliases: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class Relationship:
    """A relationship between two entities."""
    id: str
    source_entity_id: str
    target_entity_id: str
    relation_type: RelationType
    confidence: float
    source_chunk_ids: list[str]
    attributes: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ExtractionResult:
    """Result of entity extraction."""
    entities: list[Entity]
    relationships: list[Relationship]
    chunk_id: str
    doc_id: str
    extraction_time_ms: float


class EntityNormalizer:
    """Normalizes and deduplicates entities."""

    # Common abbreviations and their expansions
    ABBREVIATIONS = {
        "kv": "azure key vault",
        "vm": "virtual machine",
        "rg": "resource group",
        "nsg": "network security group",
        "vnet": "virtual network",
        "lb": "load balancer",
        "aks": "azure kubernetes service",
        "acr": "azure container registry",
        "aad": "azure active directory",
        "entra": "microsoft entra id",
        "sql": "azure sql",
        "cosmos": "azure cosmos db",
        "apim": "api management",
        "func": "azure functions",
        "aca": "azure container apps",
    }

    # Version patterns
    VERSION_PATTERN = re.compile(r"v?(\d+(?:\.\d+)*)")

    def normalize(self, name: str, entity_type: EntityType) -> str:
        """Normalize an entity name."""
        # Lowercase and strip
        normalized = name.lower().strip()

        # Remove extra whitespace
        normalized = " ".join(normalized.split())

        # Expand abbreviations for systems/services
        if entity_type in [EntityType.SYSTEM, EntityType.SERVICE]:
            words = normalized.split()
            expanded_words = []
            for word in words:
                if word in self.ABBREVIATIONS:
                    expanded_words.append(self.ABBREVIATIONS[word])
                else:
                    expanded_words.append(word)
            normalized = " ".join(expanded_words)

        # Normalize versions
        if entity_type == EntityType.VERSION:
            match = self.VERSION_PATTERN.search(normalized)
            if match:
                normalized = match.group(1)

        # Remove common suffixes
        for suffix in [" policy", " service", " system", " control"]:
            if normalized.endswith(suffix) and entity_type != EntityType.TERM:
                normalized = normalized[:-len(suffix)]

        return normalized

    def generate_id(self, normalized_name: str, entity_type: EntityType) -> str:
        """Generate deterministic entity ID."""
        key = f"{entity_type.value}:{normalized_name}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def are_same_entity(self, entity1: Entity, entity2: Entity) -> bool:
        """Check if two entities are the same."""
        if entity1.entity_type != entity2.entity_type:
            return False

        # Check normalized names
        if entity1.normalized_name == entity2.normalized_name:
            return True

        # Check aliases
        if entity1.normalized_name in entity2.aliases:
            return True
        if entity2.normalized_name in entity1.aliases:
            return True

        return False


class EntityExtractor:
    """
    Extracts entities and relationships from text chunks.

    Uses GPT-4o-mini for extraction with structured output.
    """

    EXTRACTION_PROMPT = """You are an expert at extracting entities and relationships from technical documents.

Extract all relevant entities and their relationships from the following text.

Entity types to look for:
- person: People mentioned (names, roles)
- organization: Companies, teams, departments
- system: Software systems, platforms, applications
- service: Cloud services, APIs, tools
- policy: Policies, standards, guidelines
- control: Security controls, compliance requirements
- metric: Measurements, KPIs, thresholds
- threshold: Specific limits, values, timeframes
- date: Dates, time periods
- version: Software versions, document versions
- location: Geographic locations, regions
- term: Domain-specific terminology, definitions
- process: Procedures, workflows, operations
- document: Referenced documents, specifications

Relationship types:
- owns: Entity A owns/is responsible for Entity B
- manages: Entity A manages Entity B
- depends_on: Entity A depends on Entity B
- references: Entity A references Entity B
- defines: Entity A defines Entity B
- contains: Entity A contains Entity B
- applies_to: Entity A applies to Entity B
- supersedes: Entity A supersedes Entity B

Text to analyze:
{text}

Respond with ONLY a JSON object in this exact format:
{{
  "entities": [
    {{
      "name": "exact name as it appears",
      "type": "entity_type",
      "confidence": 0.0-1.0,
      "aliases": ["other names for this entity"],
      "attributes": {{"key": "value"}}
    }}
  ],
  "relationships": [
    {{
      "source": "source entity name",
      "target": "target entity name",
      "type": "relationship_type",
      "confidence": 0.0-1.0
    }}
  ]
}}"""

    def __init__(
        self,
        openai_client: AsyncAzureOpenAI,
        normalizer: EntityNormalizer | None = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.0,
    ):
        self.client = openai_client
        self.normalizer = normalizer or EntityNormalizer()
        self.model = model
        self.temperature = temperature

    async def extract(
        self,
        text: str,
        chunk_id: str,
        doc_id: str,
    ) -> ExtractionResult:
        """
        Extract entities and relationships from text.

        Args:
            text: Text to analyze
            chunk_id: ID of the source chunk
            doc_id: ID of the source document

        Returns:
            ExtractionResult with entities and relationships
        """
        start_time = datetime.utcnow()

        # Truncate very long text
        if len(text) > 8000:
            text = text[:8000] + "..."

        # Call LLM
        prompt = self.EXTRACTION_PROMPT.format(text=text)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)

        except Exception as e:
            # Return empty result on error
            return ExtractionResult(
                entities=[],
                relationships=[],
                chunk_id=chunk_id,
                doc_id=doc_id,
                extraction_time_ms=0,
            )

        # Process entities
        entities = []
        entity_name_to_id = {}

        for raw_entity in result.get("entities", []):
            try:
                entity_type = EntityType(raw_entity["type"])
            except ValueError:
                continue

            normalized_name = self.normalizer.normalize(
                raw_entity["name"],
                entity_type,
            )

            entity_id = self.normalizer.generate_id(normalized_name, entity_type)

            entity = Entity(
                id=entity_id,
                name=raw_entity["name"],
                normalized_name=normalized_name,
                entity_type=entity_type,
                confidence=raw_entity.get("confidence", 0.8),
                source_chunk_ids=[chunk_id],
                source_doc_ids=[doc_id],
                attributes=raw_entity.get("attributes", {}),
                aliases=raw_entity.get("aliases", []),
            )

            entities.append(entity)
            entity_name_to_id[raw_entity["name"].lower()] = entity_id

        # Process relationships
        relationships = []

        for raw_rel in result.get("relationships", []):
            source_name = raw_rel.get("source", "").lower()
            target_name = raw_rel.get("target", "").lower()

            source_id = entity_name_to_id.get(source_name)
            target_id = entity_name_to_id.get(target_name)

            if not source_id or not target_id:
                continue

            try:
                rel_type = RelationType(raw_rel["type"])
            except ValueError:
                continue

            rel_id = hashlib.sha256(
                f"{source_id}:{rel_type.value}:{target_id}".encode()
            ).hexdigest()[:16]

            relationship = Relationship(
                id=rel_id,
                source_entity_id=source_id,
                target_entity_id=target_id,
                relation_type=rel_type,
                confidence=raw_rel.get("confidence", 0.7),
                source_chunk_ids=[chunk_id],
            )

            relationships.append(relationship)

        end_time = datetime.utcnow()
        extraction_time_ms = (end_time - start_time).total_seconds() * 1000

        return ExtractionResult(
            entities=entities,
            relationships=relationships,
            chunk_id=chunk_id,
            doc_id=doc_id,
            extraction_time_ms=extraction_time_ms,
        )

    async def extract_batch(
        self,
        chunks: list[dict[str, str]],  # [{"text": ..., "chunk_id": ..., "doc_id": ...}]
        max_concurrency: int = 5,
    ) -> list[ExtractionResult]:
        """Extract entities from multiple chunks concurrently."""
        semaphore = asyncio.Semaphore(max_concurrency)

        async def extract_with_semaphore(chunk: dict) -> ExtractionResult:
            async with semaphore:
                return await self.extract(
                    text=chunk["text"],
                    chunk_id=chunk["chunk_id"],
                    doc_id=chunk["doc_id"],
                )

        tasks = [extract_with_semaphore(chunk) for chunk in chunks]
        return await asyncio.gather(*tasks)


class GraphBuilder:
    """
    Builds and maintains the knowledge graph.

    Supports both Cosmos DB Gremlin and SQL-based graph storage.
    """

    def __init__(
        self,
        cosmos_client: Any,  # CosmosClient
        database_name: str,
        use_gremlin: bool = False,
    ):
        self.cosmos_client = cosmos_client
        self.database_name = database_name
        self.use_gremlin = use_gremlin

        if use_gremlin:
            self._init_gremlin()
        else:
            self._init_sql_graph()

    def _init_gremlin(self):
        """Initialize Gremlin-based graph."""
        # Would use Gremlin client
        raise NotImplementedError("Gremlin support not yet implemented")

    def _init_sql_graph(self):
        """Initialize SQL-based graph tables."""
        database = self.cosmos_client.get_database_client(self.database_name)

        # Create containers for nodes and edges
        self.nodes_container = database.get_container_client("graph-nodes")
        self.edges_container = database.get_container_client("graph-edges")

    async def upsert_entity(self, entity: Entity, tenant_id: str) -> str:
        """Insert or update an entity node."""
        node = {
            "id": entity.id,
            "tenant_id": tenant_id,
            "name": entity.name,
            "normalized_name": entity.normalized_name,
            "entity_type": entity.entity_type.value,
            "confidence": entity.confidence,
            "source_chunk_ids": entity.source_chunk_ids,
            "source_doc_ids": entity.source_doc_ids,
            "attributes": entity.attributes,
            "aliases": entity.aliases,
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Check if exists
        try:
            existing = self.nodes_container.read_item(
                item=entity.id,
                partition_key=tenant_id,
            )

            # Merge source references
            node["source_chunk_ids"] = list(set(
                existing.get("source_chunk_ids", []) + entity.source_chunk_ids
            ))
            node["source_doc_ids"] = list(set(
                existing.get("source_doc_ids", []) + entity.source_doc_ids
            ))
            node["aliases"] = list(set(
                existing.get("aliases", []) + entity.aliases
            ))

            # Keep higher confidence
            node["confidence"] = max(
                existing.get("confidence", 0),
                entity.confidence,
            )

        except Exception:
            # New entity
            node["created_at"] = datetime.utcnow().isoformat()

        self.nodes_container.upsert_item(body=node, partition_key=tenant_id)
        return entity.id

    async def upsert_relationship(
        self,
        relationship: Relationship,
        tenant_id: str,
    ) -> str:
        """Insert or update a relationship edge."""
        edge = {
            "id": relationship.id,
            "tenant_id": tenant_id,
            "source_entity_id": relationship.source_entity_id,
            "target_entity_id": relationship.target_entity_id,
            "relation_type": relationship.relation_type.value,
            "confidence": relationship.confidence,
            "source_chunk_ids": relationship.source_chunk_ids,
            "attributes": relationship.attributes,
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Check if exists
        try:
            existing = self.edges_container.read_item(
                item=relationship.id,
                partition_key=tenant_id,
            )

            # Merge source references
            edge["source_chunk_ids"] = list(set(
                existing.get("source_chunk_ids", []) + relationship.source_chunk_ids
            ))

            # Keep higher confidence
            edge["confidence"] = max(
                existing.get("confidence", 0),
                relationship.confidence,
            )

        except Exception:
            # New edge
            edge["created_at"] = datetime.utcnow().isoformat()

        self.edges_container.upsert_item(body=edge, partition_key=tenant_id)
        return relationship.id

    async def get_related_entities(
        self,
        entity_id: str,
        tenant_id: str,
        relation_types: list[RelationType] | None = None,
        max_depth: int = 1,
    ) -> list[tuple[Entity, Relationship]]:
        """
        Get entities related to the given entity.

        Args:
            entity_id: Starting entity ID
            tenant_id: Tenant for isolation
            relation_types: Filter by relationship types
            max_depth: Maximum traversal depth (default 1)

        Returns:
            List of (Entity, Relationship) tuples
        """
        results = []
        visited = {entity_id}

        current_level = [entity_id]

        for depth in range(max_depth):
            next_level = []

            for current_id in current_level:
                # Get outgoing edges
                query = f"""
                SELECT * FROM c
                WHERE c.tenant_id = '{tenant_id}'
                AND c.source_entity_id = '{current_id}'
                """

                if relation_types:
                    types_filter = ", ".join(f"'{rt.value}'" for rt in relation_types)
                    query += f" AND c.relation_type IN ({types_filter})"

                edges = list(self.edges_container.query_items(
                    query=query,
                    partition_key=tenant_id,
                ))

                for edge in edges:
                    target_id = edge["target_entity_id"]

                    if target_id in visited:
                        continue

                    visited.add(target_id)
                    next_level.append(target_id)

                    # Get target entity
                    try:
                        entity_data = self.nodes_container.read_item(
                            item=target_id,
                            partition_key=tenant_id,
                        )

                        entity = Entity(
                            id=entity_data["id"],
                            name=entity_data["name"],
                            normalized_name=entity_data["normalized_name"],
                            entity_type=EntityType(entity_data["entity_type"]),
                            confidence=entity_data["confidence"],
                            source_chunk_ids=entity_data.get("source_chunk_ids", []),
                            source_doc_ids=entity_data.get("source_doc_ids", []),
                            attributes=entity_data.get("attributes", {}),
                            aliases=entity_data.get("aliases", []),
                        )

                        relationship = Relationship(
                            id=edge["id"],
                            source_entity_id=edge["source_entity_id"],
                            target_entity_id=edge["target_entity_id"],
                            relation_type=RelationType(edge["relation_type"]),
                            confidence=edge["confidence"],
                            source_chunk_ids=edge.get("source_chunk_ids", []),
                        )

                        results.append((entity, relationship))

                    except Exception:
                        continue

            current_level = next_level

        return results

    async def find_entities_by_name(
        self,
        name_query: str,
        tenant_id: str,
        entity_types: list[EntityType] | None = None,
        limit: int = 10,
    ) -> list[Entity]:
        """Find entities by name (partial match)."""
        query = f"""
        SELECT * FROM c
        WHERE c.tenant_id = '{tenant_id}'
        AND (
            CONTAINS(LOWER(c.name), '{name_query.lower()}')
            OR CONTAINS(LOWER(c.normalized_name), '{name_query.lower()}')
        )
        """

        if entity_types:
            types_filter = ", ".join(f"'{et.value}'" for et in entity_types)
            query += f" AND c.entity_type IN ({types_filter})"

        query += f" ORDER BY c.confidence DESC OFFSET 0 LIMIT {limit}"

        entities = []
        for item in self.nodes_container.query_items(
            query=query,
            partition_key=tenant_id,
        ):
            entities.append(Entity(
                id=item["id"],
                name=item["name"],
                normalized_name=item["normalized_name"],
                entity_type=EntityType(item["entity_type"]),
                confidence=item["confidence"],
                source_chunk_ids=item.get("source_chunk_ids", []),
                source_doc_ids=item.get("source_doc_ids", []),
                attributes=item.get("attributes", {}),
                aliases=item.get("aliases", []),
            ))

        return entities

    async def get_chunks_for_entities(
        self,
        entity_ids: list[str],
        tenant_id: str,
    ) -> list[str]:
        """Get chunk IDs that mention the given entities."""
        all_chunk_ids = set()

        for entity_id in entity_ids:
            try:
                entity_data = self.nodes_container.read_item(
                    item=entity_id,
                    partition_key=tenant_id,
                )
                all_chunk_ids.update(entity_data.get("source_chunk_ids", []))
            except Exception:
                continue

        return list(all_chunk_ids)


class GraphExpander:
    """
    Expands retrieval using the knowledge graph.

    Used for multi-hop retrieval and cross-document reasoning.
    """

    def __init__(
        self,
        graph_builder: GraphBuilder,
        entity_extractor: EntityExtractor,
    ):
        self.graph = graph_builder
        self.extractor = entity_extractor

    async def expand_with_graph(
        self,
        query: str,
        initial_chunk_ids: list[str],
        tenant_id: str,
        max_expansion: int = 30,
        expansion_depth: int = 1,
    ) -> list[str]:
        """
        Expand initial retrieval results using graph relationships.

        Args:
            query: Original user query
            initial_chunk_ids: Chunk IDs from initial retrieval
            tenant_id: Tenant for isolation
            max_expansion: Maximum additional chunks to add
            expansion_depth: How many hops in the graph

        Returns:
            List of additional chunk IDs to include
        """
        # Step 1: Extract entities from query
        query_extraction = await self.extractor.extract(
            text=query,
            chunk_id="query",
            doc_id="query",
        )

        query_entity_names = [e.normalized_name for e in query_extraction.entities]

        # Step 2: Find matching entities in graph
        matched_entities = []
        for name in query_entity_names:
            entities = await self.graph.find_entities_by_name(
                name_query=name,
                tenant_id=tenant_id,
                limit=5,
            )
            matched_entities.extend(entities)

        # Step 3: Expand to related entities
        expanded_entity_ids = set(e.id for e in matched_entities)

        for entity in matched_entities:
            related = await self.graph.get_related_entities(
                entity_id=entity.id,
                tenant_id=tenant_id,
                max_depth=expansion_depth,
            )

            for related_entity, _ in related:
                expanded_entity_ids.add(related_entity.id)

        # Step 4: Get chunks for expanded entities
        expansion_chunks = await self.graph.get_chunks_for_entities(
            entity_ids=list(expanded_entity_ids),
            tenant_id=tenant_id,
        )

        # Step 5: Filter out already-retrieved chunks
        initial_set = set(initial_chunk_ids)
        new_chunks = [c for c in expansion_chunks if c not in initial_set]

        # Limit expansion
        return new_chunks[:max_expansion]
