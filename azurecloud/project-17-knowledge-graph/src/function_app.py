"""
Knowledge Graph Builder - Azure Functions
==========================================
Entity/relationship extraction, graph-enhanced RAG, and ontology management
for building and querying enterprise knowledge graphs backed by Cosmos DB Gremlin.
"""

import azure.functions as func
import logging
import json
import os
from datetime import datetime
from typing import Optional
import hashlib

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.cosmos import CosmosClient
from openai import AzureOpenAI
from gremlin_python.driver import client as gremlin_client
from gremlin_python.driver import serializer

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Azure Function App
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# ==============================================================================
# Configuration
# ==============================================================================

class Config:
    """Application configuration from environment variables."""

    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    COSMOS_GREMLIN_ENDPOINT = os.getenv("COSMOS_GREMLIN_ENDPOINT")
    COSMOS_GREMLIN_KEY = os.getenv("COSMOS_GREMLIN_KEY")
    AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
    COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
    KEY_VAULT_URL = os.getenv("KEY_VAULT_URL")

    # Model configurations
    GPT_MODEL = "gpt-4o"
    EMBEDDING_MODEL = "text-embedding-ada-002"
    SEARCH_INDEX = "knowledge-graph-index"

    # Graph parameters
    GREMLIN_DATABASE = "knowledgegraph"
    GREMLIN_CONTAINER = "entities"
    MAX_TRAVERSAL_DEPTH = 3
    MAX_GRAPH_RESULTS = 50

    # RAG parameters
    TOP_K = 5
    SEMANTIC_CONFIG = "default-semantic-config"
    MAX_TOKENS = 4096
    TEMPERATURE = 0.3


# ==============================================================================
# Service Clients (Lazy Initialization)
# ==============================================================================

_credential = None
_openai_client = None
_search_client = None
_cosmos_client = None
_gremlin_client = None


def get_credential():
    """Get Azure credential using Managed Identity."""
    global _credential
    if _credential is None:
        _credential = DefaultAzureCredential()
    return _credential


def get_openai_client() -> AzureOpenAI:
    """Get Azure OpenAI client."""
    global _openai_client
    if _openai_client is None:
        _openai_client = AzureOpenAI(
            azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
            azure_ad_token_provider=lambda: get_credential().get_token(
                "https://cognitiveservices.azure.com/.default"
            ).token,
            api_version="2024-06-01"
        )
    return _openai_client


def get_search_client() -> SearchClient:
    """Get Azure AI Search client."""
    global _search_client
    if _search_client is None:
        _search_client = SearchClient(
            endpoint=Config.AZURE_SEARCH_ENDPOINT,
            index_name=Config.SEARCH_INDEX,
            credential=get_credential()
        )
    return _search_client


def get_cosmos_container(container_name: str):
    """Get Cosmos DB container client."""
    global _cosmos_client
    if _cosmos_client is None:
        _cosmos_client = CosmosClient(
            url=Config.COSMOS_ENDPOINT,
            credential=get_credential()
        )
    database = _cosmos_client.get_database_client(Config.GREMLIN_DATABASE)
    return database.get_container_client(container_name)


def get_gremlin_client():
    """Get Cosmos DB Gremlin client for graph queries."""
    global _gremlin_client
    if _gremlin_client is None:
        _gremlin_client = gremlin_client.Client(
            url=Config.COSMOS_GREMLIN_ENDPOINT,
            traversal_source="g",
            username=f"/dbs/{Config.GREMLIN_DATABASE}/colls/{Config.GREMLIN_CONTAINER}",
            password=Config.COSMOS_GREMLIN_KEY,
            message_serializer=serializer.GraphSONSerializersV2d0()
        )
    return _gremlin_client


# ==============================================================================
# Core Domain Functions
# ==============================================================================

def generate_embedding(text: str) -> list[float]:
    """Generate embedding vector for text using Azure OpenAI."""
    client = get_openai_client()

    response = client.embeddings.create(
        input=text,
        model=Config.EMBEDDING_MODEL
    )

    return response.data[0].embedding


def extract_entities_and_relations(text: str) -> dict:
    """
    Use OpenAI to extract entities and relationships from text
    with structured JSON output.

    Args:
        text: Source text to extract knowledge from

    Returns:
        Dictionary with 'entities' and 'relations' lists
    """
    client = get_openai_client()

    system_prompt = """You are a knowledge graph extraction engine.
Extract all entities and relationships from the provided text.

Return a JSON object with the following structure:
{
  "entities": [
    {
      "id": "unique_id",
      "label": "entity_type (e.g., Person, Organization, Technology, Concept)",
      "name": "entity_name",
      "properties": {"key": "value"}
    }
  ],
  "relations": [
    {
      "source": "source_entity_id",
      "target": "target_entity_id",
      "type": "relationship_type (e.g., WORKS_FOR, USES, DEPENDS_ON)",
      "properties": {"key": "value"}
    }
  ]
}

Rules:
1. Generate stable IDs by slugifying entity names (lowercase, hyphens)
2. Use consistent entity labels from a standard ontology
3. Extract all meaningful relationships, including implicit ones
4. Include relevant properties for both entities and relationships
5. Return ONLY valid JSON, no markdown formatting"""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract entities and relationships from:\n\n{text}"}
        ],
        max_tokens=Config.MAX_TOKENS,
        temperature=0.1,
        response_format={"type": "json_object"}
    )

    extracted = json.loads(response.choices[0].message.content)

    # Validate structure
    if "entities" not in extracted:
        extracted["entities"] = []
    if "relations" not in extracted:
        extracted["relations"] = []

    logger.info(
        f"Extracted {len(extracted['entities'])} entities and "
        f"{len(extracted['relations'])} relations"
    )

    return extracted


def add_to_graph(entities: list[dict], relations: list[dict]) -> dict:
    """
    Add extracted entities and relations to the Cosmos DB Gremlin graph.

    Args:
        entities: List of entity dictionaries with id, label, name, properties
        relations: List of relation dictionaries with source, target, type, properties

    Returns:
        Summary of added vertices and edges
    """
    graph = get_gremlin_client()
    vertices_added = 0
    edges_added = 0
    errors = []

    # Add vertices (entities)
    for entity in entities:
        try:
            props = entity.get("properties", {})
            prop_steps = ""
            for key, value in props.items():
                safe_value = str(value).replace("'", "\\'")
                prop_steps += f".property('{key}', '{safe_value}')"

            safe_name = entity["name"].replace("'", "\\'")
            query = (
                f"g.V('{entity['id']}').fold()"
                f".coalesce(unfold(), "
                f"addV('{entity['label']}')"
                f".property('id', '{entity['id']}')"
                f".property('name', '{safe_name}')"
                f".property('updatedAt', '{datetime.utcnow().isoformat()}')"
                f"{prop_steps})"
            )

            graph.submitAsync(query).result()
            vertices_added += 1

        except Exception as e:
            logger.error(f"Error adding vertex {entity.get('id')}: {e}")
            errors.append({"type": "vertex", "id": entity.get("id"), "error": str(e)})

    # Add edges (relations)
    for relation in relations:
        try:
            props = relation.get("properties", {})
            prop_steps = ""
            for key, value in props.items():
                safe_value = str(value).replace("'", "\\'")
                prop_steps += f".property('{key}', '{safe_value}')"

            edge_id = hashlib.md5(
                f"{relation['source']}-{relation['type']}-{relation['target']}".encode()
            ).hexdigest()

            query = (
                f"g.V('{relation['source']}')"
                f".coalesce("
                f"outE('{relation['type']}').where(inV().has('id', '{relation['target']}')),"
                f"addE('{relation['type']}').to(g.V('{relation['target']}'))"
                f".property('id', '{edge_id}')"
                f".property('createdAt', '{datetime.utcnow().isoformat()}')"
                f"{prop_steps})"
            )

            graph.submitAsync(query).result()
            edges_added += 1

        except Exception as e:
            logger.error(f"Error adding edge {relation.get('type')}: {e}")
            errors.append({"type": "edge", "relation": relation.get("type"), "error": str(e)})

    return {
        "vertices_added": vertices_added,
        "edges_added": edges_added,
        "errors": errors
    }


def query_graph(gremlin_query: str) -> list[dict]:
    """
    Execute a Gremlin query against the knowledge graph.

    Args:
        gremlin_query: Valid Gremlin traversal query string

    Returns:
        List of query results
    """
    graph = get_gremlin_client()

    logger.info(f"Executing Gremlin query: {gremlin_query[:100]}...")

    callback = graph.submitAsync(gremlin_query)
    results = callback.result().all().result()

    formatted = []
    for result in results:
        if isinstance(result, dict):
            formatted.append(result)
        else:
            formatted.append({"value": str(result)})

    logger.info(f"Graph query returned {len(formatted)} results")
    return formatted


def graph_enhanced_rag(query: str) -> dict:
    """
    RAG pipeline that combines vector search with graph traversal
    for richer context retrieval.

    Args:
        query: User's natural language question

    Returns:
        Answer enriched with graph context, sources, and related entities
    """
    client = get_openai_client()
    search = get_search_client()

    # Step 1: Vector search for relevant document chunks
    query_vector = generate_embedding(query)

    vector_query = VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=Config.TOP_K,
        fields="contentVector"
    )

    search_results = search.search(
        search_text=query,
        vector_queries=[vector_query],
        query_type="semantic",
        semantic_configuration_name=Config.SEMANTIC_CONFIG,
        top=Config.TOP_K,
        select=["id", "content", "title", "source", "entities"]
    )

    documents = []
    mentioned_entities = set()
    for result in search_results:
        documents.append({
            "id": result["id"],
            "content": result["content"],
            "title": result.get("title", "Unknown"),
            "source": result.get("source", "Unknown"),
            "score": result["@search.score"]
        })
        # Collect entity IDs mentioned in retrieved documents
        for entity_id in result.get("entities", []):
            mentioned_entities.add(entity_id)

    # Step 2: Graph traversal for related entities
    graph_context = []
    for entity_id in list(mentioned_entities)[:10]:
        try:
            neighbors_query = (
                f"g.V('{entity_id}')"
                f".bothE().otherV()"
                f".path()"
                f".by(valueMap(true))"
                f".limit({Config.MAX_GRAPH_RESULTS})"
            )
            neighbors = query_graph(neighbors_query)
            graph_context.extend(neighbors)
        except Exception as e:
            logger.warning(f"Graph traversal failed for entity {entity_id}: {e}")

    # Step 3: Build enriched prompt
    context_parts = []
    for i, doc in enumerate(documents, 1):
        context_parts.append(
            f"[Document {i}] {doc['title']}\n{doc['content']}"
        )

    if graph_context:
        context_parts.append(
            f"\n[Graph Context]\nRelated entities and relationships:\n"
            + json.dumps(graph_context[:20], indent=2, default=str)
        )

    system_prompt = """You are a knowledge graph-enhanced AI assistant.
Answer questions using BOTH the retrieved documents AND the graph context.

INSTRUCTIONS:
1. Synthesize information from documents and graph relationships
2. Highlight connections between entities when relevant
3. Cite sources using [Source: title] format
4. If graph relationships add insight, explain the connections
5. Be precise and factual based on the provided context

CONTEXT:
""" + "\n---\n".join(context_parts)

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ],
        max_tokens=Config.MAX_TOKENS,
        temperature=Config.TEMPERATURE
    )

    sources = [
        {"title": doc["title"], "source": doc["source"], "score": doc["score"]}
        for doc in documents
    ]

    return {
        "answer": response.choices[0].message.content,
        "sources": sources,
        "graph_entities": list(mentioned_entities),
        "graph_context_count": len(graph_context),
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
    }


def manage_ontology(action: str, ontology_data: Optional[dict] = None) -> dict:
    """
    CRUD operations on ontology definitions stored in Cosmos DB.

    Args:
        action: One of 'create', 'read', 'update', 'delete', 'list'
        ontology_data: Ontology definition (required for create/update)

    Returns:
        Operation result
    """
    container = get_cosmos_container("ontologies")

    if action == "create":
        if not ontology_data:
            raise ValueError("ontology_data is required for create action")

        ontology_doc = {
            "id": ontology_data.get("id", hashlib.md5(
                ontology_data["name"].encode()
            ).hexdigest()),
            "name": ontology_data["name"],
            "version": ontology_data.get("version", "1.0.0"),
            "entityTypes": ontology_data.get("entityTypes", []),
            "relationTypes": ontology_data.get("relationTypes", []),
            "constraints": ontology_data.get("constraints", []),
            "createdAt": datetime.utcnow().isoformat(),
            "updatedAt": datetime.utcnow().isoformat(),
            "partitionKey": "ontology"
        }

        container.create_item(body=ontology_doc)
        logger.info(f"Created ontology: {ontology_doc['name']}")
        return {"status": "created", "ontology": ontology_doc}

    elif action == "read":
        ontology_id = ontology_data.get("id") if ontology_data else None
        if not ontology_id:
            raise ValueError("ontology_data.id is required for read action")

        item = container.read_item(item=ontology_id, partition_key="ontology")
        return {"status": "ok", "ontology": item}

    elif action == "update":
        if not ontology_data or "id" not in ontology_data:
            raise ValueError("ontology_data with id is required for update action")

        existing = container.read_item(
            item=ontology_data["id"], partition_key="ontology"
        )
        existing.update(ontology_data)
        existing["updatedAt"] = datetime.utcnow().isoformat()

        container.replace_item(item=existing["id"], body=existing)
        logger.info(f"Updated ontology: {existing['name']}")
        return {"status": "updated", "ontology": existing}

    elif action == "delete":
        ontology_id = ontology_data.get("id") if ontology_data else None
        if not ontology_id:
            raise ValueError("ontology_data.id is required for delete action")

        container.delete_item(item=ontology_id, partition_key="ontology")
        logger.info(f"Deleted ontology: {ontology_id}")
        return {"status": "deleted", "id": ontology_id}

    elif action == "list":
        items = list(container.query_items(
            query="SELECT * FROM c WHERE c.partitionKey = 'ontology'",
            enable_cross_partition_query=False
        ))
        return {"status": "ok", "ontologies": items, "count": len(items)}

    else:
        raise ValueError(f"Unknown action: {action}. Use create, read, update, delete, or list.")


# ==============================================================================
# HTTP Endpoints
# ==============================================================================

@app.route(route="extract", methods=["POST"])
async def extract_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Entity and relationship extraction endpoint.

    Request Body:
    {
        "text": "The text to extract entities from...",
        "persist": true
    }

    Response:
    {
        "entities": [...],
        "relations": [...],
        "graph_result": {...}
    }
    """
    try:
        req_body = req.get_json()
        text = req_body.get("text")
        persist = req_body.get("persist", True)

        if not text:
            return func.HttpResponse(
                json.dumps({"error": "text field is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Extracting entities from text ({len(text)} chars)")

        # Extract entities and relations using OpenAI
        extraction = extract_entities_and_relations(text)

        response_data = {
            "entities": extraction["entities"],
            "relations": extraction["relations"]
        }

        # Optionally persist to graph
        if persist:
            graph_result = add_to_graph(
                extraction["entities"],
                extraction["relations"]
            )
            response_data["graph_result"] = graph_result

        return func.HttpResponse(
            json.dumps(response_data, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in extraction endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="query", methods=["POST"])
async def query_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Graph-enhanced RAG query endpoint.

    Request Body:
    {
        "query": "What technologies does the platform use?"
    }

    Response:
    {
        "answer": "Based on the knowledge graph...",
        "sources": [...],
        "graph_entities": [...],
        "usage": {...}
    }
    """
    try:
        req_body = req.get_json()
        query = req_body.get("query")

        if not query:
            return func.HttpResponse(
                json.dumps({"error": "query field is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Processing graph-enhanced RAG query: {query[:80]}...")

        result = graph_enhanced_rag(query)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in query endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="graph-query", methods=["POST"])
async def graph_query_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Direct Gremlin query endpoint for graph exploration.

    Request Body:
    {
        "gremlin": "g.V().hasLabel('Person').limit(10).valueMap(true)"
    }

    Response:
    {
        "results": [...],
        "count": 10
    }
    """
    try:
        req_body = req.get_json()
        gremlin_query = req_body.get("gremlin")

        if not gremlin_query:
            return func.HttpResponse(
                json.dumps({"error": "gremlin field is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Basic injection protection
        forbidden = ["drop()", "addV(", "addE(", "property("]
        if any(cmd in gremlin_query for cmd in forbidden):
            return func.HttpResponse(
                json.dumps({"error": "Write operations not allowed via this endpoint"}),
                status_code=403,
                mimetype="application/json"
            )

        logger.info(f"Executing direct Gremlin query: {gremlin_query[:100]}...")

        results = query_graph(gremlin_query)

        return func.HttpResponse(
            json.dumps({"results": results, "count": len(results)}, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in graph query endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="ontology", methods=["POST"])
async def ontology_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Ontology management endpoint.

    Request Body:
    {
        "action": "create|read|update|delete|list",
        "data": {
            "id": "optional-for-read/delete",
            "name": "MyOntology",
            "entityTypes": ["Person", "Organization"],
            "relationTypes": ["WORKS_FOR", "PARTNERS_WITH"],
            "constraints": []
        }
    }

    Response:
    {
        "status": "created|ok|updated|deleted",
        "ontology": {...}
    }
    """
    try:
        req_body = req.get_json()
        action = req_body.get("action")
        data = req_body.get("data")

        if not action:
            return func.HttpResponse(
                json.dumps({"error": "action field is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Ontology management action: {action}")

        result = manage_ontology(action, data)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except ValueError as ve:
        return func.HttpResponse(
            json.dumps({"error": str(ve)}),
            status_code=400,
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"Error in ontology endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="health", methods=["GET"])
async def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint."""
    health = {
        "status": "healthy",
        "service": "knowledge-graph-builder",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "components": {
            "openai": Config.AZURE_OPENAI_ENDPOINT is not None,
            "cosmos_gremlin": Config.COSMOS_GREMLIN_ENDPOINT is not None,
            "search": Config.AZURE_SEARCH_ENDPOINT is not None,
            "cosmos": Config.COSMOS_ENDPOINT is not None
        }
    }

    return func.HttpResponse(
        json.dumps(health),
        mimetype="application/json"
    )


# ==============================================================================
# Event Grid Trigger for Document Ingestion into Graph
# ==============================================================================

@app.function_name(name="DocumentGraphIngestionTrigger")
@app.event_grid_trigger(arg_name="event")
async def document_graph_ingestion_trigger(event: func.EventGridEvent):
    """
    Triggered when a new document is uploaded to blob storage.
    Extracts entities and relationships and ingests them into the knowledge graph.
    """
    try:
        event_data = event.get_json()
        blob_url = event_data.get("url")
        blob_name = blob_url.split("/")[-1] if blob_url else "unknown"
        content_type = event_data.get("contentType", "")

        logger.info(f"Graph ingestion triggered for document: {blob_name}")

        # Extract document text from the event payload
        document_text = event_data.get("text", "")

        if not document_text:
            logger.warning(f"No text content in event for {blob_name}, skipping extraction")
            return

        # Step 1: Extract entities and relationships
        extraction = extract_entities_and_relations(document_text)

        # Step 2: Add source document as a node
        doc_entity = {
            "id": hashlib.md5(blob_url.encode()).hexdigest(),
            "label": "Document",
            "name": blob_name,
            "properties": {
                "url": blob_url,
                "contentType": content_type,
                "ingestedAt": datetime.utcnow().isoformat()
            }
        }
        extraction["entities"].append(doc_entity)

        # Add MENTIONED_IN relations from entities to document
        for entity in extraction["entities"]:
            if entity["id"] != doc_entity["id"]:
                extraction["relations"].append({
                    "source": entity["id"],
                    "target": doc_entity["id"],
                    "type": "MENTIONED_IN",
                    "properties": {"extractedAt": datetime.utcnow().isoformat()}
                })

        # Step 3: Persist to graph
        result = add_to_graph(extraction["entities"], extraction["relations"])

        # Step 4: Generate embeddings and index for vector search
        for entity in extraction["entities"]:
            try:
                entity_text = f"{entity['label']}: {entity['name']}"
                embedding = generate_embedding(entity_text)

                # Store embedding reference in Cosmos DB for hybrid retrieval
                container = get_cosmos_container("entity-embeddings")
                container.upsert_item({
                    "id": entity["id"],
                    "entityName": entity["name"],
                    "entityLabel": entity["label"],
                    "embedding": embedding,
                    "sourceDocument": blob_name,
                    "updatedAt": datetime.utcnow().isoformat(),
                    "partitionKey": entity["label"]
                })
            except Exception as emb_err:
                logger.warning(f"Failed to embed entity {entity['name']}: {emb_err}")

        logger.info(
            f"Graph ingestion complete for {blob_name}: "
            f"{result['vertices_added']} vertices, {result['edges_added']} edges"
        )

    except Exception as e:
        logger.error(f"Error in graph ingestion trigger: {e}", exc_info=True)
        raise
