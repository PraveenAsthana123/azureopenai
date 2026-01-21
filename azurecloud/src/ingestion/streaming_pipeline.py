"""
Streaming Ingestion Pipeline with Durable Functions

Implements:
- Event-driven ingestion (Event Grid → Service Bus → Durable Functions)
- Incremental reprocessing with page-level hashing
- Self-healing loops for tables and captions
- Deterministic chunk IDs for stable citations
- Tombstoning for deleted documents
"""

import azure.functions as func
import azure.durable_functions as df
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient
from azure.search.documents import SearchClient
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.identity import DefaultAzureCredential

from dataclasses import dataclass, field, asdict
from typing import Any
from enum import Enum
import hashlib
import json
import logging
from datetime import datetime, timezone


# Initialize Durable Functions app
app = df.DFApp(http_auth_level=func.AuthLevel.FUNCTION)


class IngestionStatus(Enum):
    """Status of document ingestion."""
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"
    ARCHIVED = "archived"


class ChunkType(Enum):
    """Types of extracted chunks."""
    TEXT = "text"
    TABLE = "table"
    IMAGE_CAPTION = "image_caption"
    CODE = "code"


@dataclass
class DocumentManifest:
    """Manifest tracking document state and versions."""
    doc_id: str
    tenant_id: str
    blob_uri: str
    version: int
    etag: str
    content_hash: str
    status: str
    last_ingested_utc: str | None
    page_count: int | None = None
    page_hashes: dict[str, str] = field(default_factory=dict)
    chunk_count: int = 0
    embedding_model_version: str = "text-embedding-3-large"
    ingestion_version: str = "v1.0"
    error_message: str | None = None
    repair_attempts: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IngestionContext:
    """Context passed through ingestion pipeline."""
    doc_id: str
    tenant_id: str
    blob_uri: str
    source_system: str
    etag: str
    content_hash: str
    force_reprocess: bool = False
    pages_to_process: list[int] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    acl_users: list[str] = field(default_factory=list)
    acl_groups: list[str] = field(default_factory=list)
    sensitivity: str = "internal"


@dataclass
class ExtractedPage:
    """Results from Document Intelligence extraction."""
    page_number: int
    content_hash: str
    text_content: str
    tables: list[dict[str, Any]]
    figures: list[dict[str, Any]]
    sections: list[dict[str, str]]


@dataclass
class ProcessedChunk:
    """A chunk ready for indexing."""
    id: str  # Deterministic: docId_pageStart_pageEnd_blockType_index
    doc_id: str
    chunk_id: str
    chunk_type: str
    content: str
    content_md: str | None
    embedding: list[float] | None
    section_path: list[str]
    heading: str | None
    page_start: int
    page_end: int
    reading_order: int
    table_headers: list[str] | None
    table_row_count: int | None
    table_col_count: int | None
    figure_ref: str | None
    bbox_union: str | None
    content_hash: str
    token_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


# ============================================================================
# HTTP Trigger - Start Ingestion
# ============================================================================

@app.route(route="ingest", methods=["POST"])
@app.durable_client_input(client_name="client")
async def start_ingestion(req: func.HttpRequest, client: df.DurableOrchestrationClient):
    """
    HTTP trigger to start document ingestion.

    Request body:
    {
        "blob_uri": "https://storage.blob.../container/doc.pdf",
        "tenant_id": "T1",
        "source_system": "sharepoint",
        "metadata": {...},
        "acl_users": ["user@company.com"],
        "acl_groups": ["group-id-1"],
        "sensitivity": "internal",
        "force_reprocess": false
    }
    """
    try:
        body = req.get_json()

        context = IngestionContext(
            doc_id=_generate_doc_id(body["blob_uri"]),
            tenant_id=body["tenant_id"],
            blob_uri=body["blob_uri"],
            source_system=body.get("source_system", "blob"),
            etag=body.get("etag", ""),
            content_hash=body.get("content_hash", ""),
            force_reprocess=body.get("force_reprocess", False),
            metadata=body.get("metadata", {}),
            acl_users=body.get("acl_users", []),
            acl_groups=body.get("acl_groups", []),
            sensitivity=body.get("sensitivity", "internal"),
        )

        # Start orchestration
        instance_id = await client.start_new(
            "ingestion_orchestrator",
            client_input=asdict(context),
        )

        return func.HttpResponse(
            json.dumps({
                "instance_id": instance_id,
                "doc_id": context.doc_id,
                "status": "started",
            }),
            status_code=202,
            mimetype="application/json",
        )

    except Exception as e:
        logging.error(f"Failed to start ingestion: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=400,
            mimetype="application/json",
        )


# ============================================================================
# Event Grid Trigger - Auto-ingest on blob changes
# ============================================================================

@app.event_grid_trigger(arg_name="event")
@app.durable_client_input(client_name="client")
async def blob_created_trigger(event: func.EventGridEvent, client: df.DurableOrchestrationClient):
    """
    Event Grid trigger for automatic ingestion on blob creation/update.

    Subscribes to:
    - Microsoft.Storage.BlobCreated
    - Microsoft.Storage.BlobDeleted
    """
    event_type = event.event_type
    data = event.get_json()

    blob_uri = data.get("url", "")
    etag = data.get("eTag", "")

    # Extract tenant from container name (convention: {tenant}-documents)
    container = _extract_container_from_uri(blob_uri)
    tenant_id = container.split("-")[0] if "-" in container else "default"

    if event_type == "Microsoft.Storage.BlobDeleted":
        # Handle deletion - tombstone the document
        instance_id = await client.start_new(
            "tombstone_orchestrator",
            client_input={
                "doc_id": _generate_doc_id(blob_uri),
                "tenant_id": tenant_id,
                "blob_uri": blob_uri,
            },
        )
        logging.info(f"Started tombstone for {blob_uri}: {instance_id}")

    elif event_type == "Microsoft.Storage.BlobCreated":
        # Handle creation/update
        context = IngestionContext(
            doc_id=_generate_doc_id(blob_uri),
            tenant_id=tenant_id,
            blob_uri=blob_uri,
            source_system="blob",
            etag=etag,
            content_hash="",  # Will be computed
        )

        instance_id = await client.start_new(
            "ingestion_orchestrator",
            client_input=asdict(context),
        )
        logging.info(f"Started ingestion for {blob_uri}: {instance_id}")


# ============================================================================
# Orchestrator - Main Ingestion Pipeline
# ============================================================================

@app.orchestration_trigger(context_name="context")
def ingestion_orchestrator(context: df.DurableOrchestrationContext):
    """
    Main ingestion orchestrator.

    Pipeline:
    1. Load/create manifest
    2. Download and hash document
    3. Diff against previous version
    4. Extract with Document Intelligence
    5. Chunk and embed
    6. Index to Azure AI Search
    7. Update manifest
    """
    input_data = context.get_input()
    ctx = IngestionContext(**input_data)

    try:
        # Step 1: Load or create manifest
        manifest = yield context.call_activity("load_manifest", asdict(ctx))

        # Step 2: Download and compute content hash
        download_result = yield context.call_activity("download_and_hash", asdict(ctx))

        # Check if we need to process
        if not ctx.force_reprocess and manifest and manifest.get("content_hash") == download_result["content_hash"]:
            # No changes, skip processing
            return {
                "status": "skipped",
                "doc_id": ctx.doc_id,
                "reason": "content unchanged",
            }

        ctx.content_hash = download_result["content_hash"]

        # Step 3: Extract with Document Intelligence
        extraction_result = yield context.call_activity("extract_document", {
            **asdict(ctx),
            "blob_content_path": download_result["temp_path"],
        })

        # Step 4: Diff pages against previous version
        pages_to_process = yield context.call_activity("diff_pages", {
            "doc_id": ctx.doc_id,
            "new_page_hashes": extraction_result["page_hashes"],
            "old_page_hashes": manifest.get("page_hashes", {}) if manifest else {},
            "force_reprocess": ctx.force_reprocess,
        })

        if not pages_to_process:
            return {
                "status": "skipped",
                "doc_id": ctx.doc_id,
                "reason": "no page changes",
            }

        # Step 5: Chunk changed pages
        chunks = yield context.call_activity("chunk_pages", {
            "doc_id": ctx.doc_id,
            "tenant_id": ctx.tenant_id,
            "pages": [p for p in extraction_result["pages"] if p["page_number"] in pages_to_process],
            "metadata": ctx.metadata,
            "acl_users": ctx.acl_users,
            "acl_groups": ctx.acl_groups,
            "sensitivity": ctx.sensitivity,
        })

        # Step 6: Generate embeddings (fan-out for parallelism)
        embedding_tasks = []
        batch_size = 20
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            embedding_tasks.append(
                context.call_activity("embed_chunks", {"chunks": batch})
            )

        embedded_batches = yield context.task_all(embedding_tasks)
        embedded_chunks = [chunk for batch in embedded_batches for chunk in batch]

        # Step 7: Index to Azure AI Search
        index_result = yield context.call_activity("index_chunks", {
            "chunks": embedded_chunks,
            "doc_id": ctx.doc_id,
            "pages_processed": pages_to_process,
        })

        # Step 8: Update manifest
        yield context.call_activity("update_manifest", {
            "doc_id": ctx.doc_id,
            "tenant_id": ctx.tenant_id,
            "blob_uri": ctx.blob_uri,
            "etag": ctx.etag,
            "content_hash": ctx.content_hash,
            "page_hashes": extraction_result["page_hashes"],
            "page_count": len(extraction_result["pages"]),
            "chunk_count": len(embedded_chunks),
            "status": IngestionStatus.INDEXED.value,
        })

        # Step 9: Trigger repair if needed
        if extraction_result.get("low_confidence_tables"):
            yield context.call_activity("queue_table_repair", {
                "doc_id": ctx.doc_id,
                "tables": extraction_result["low_confidence_tables"],
            })

        return {
            "status": "completed",
            "doc_id": ctx.doc_id,
            "chunks_indexed": len(embedded_chunks),
            "pages_processed": len(pages_to_process),
        }

    except Exception as e:
        logging.error(f"Ingestion failed for {ctx.doc_id}: {e}")

        # Update manifest with failure
        yield context.call_activity("update_manifest", {
            "doc_id": ctx.doc_id,
            "tenant_id": ctx.tenant_id,
            "blob_uri": ctx.blob_uri,
            "status": IngestionStatus.FAILED.value,
            "error_message": str(e),
        })

        raise


# ============================================================================
# Orchestrator - Tombstone (Soft Delete)
# ============================================================================

@app.orchestration_trigger(context_name="context")
def tombstone_orchestrator(context: df.DurableOrchestrationContext):
    """
    Tombstone orchestrator for deleted documents.

    Marks chunks as inactive rather than deleting immediately.
    """
    input_data = context.get_input()
    doc_id = input_data["doc_id"]
    tenant_id = input_data["tenant_id"]

    # Mark all chunks as inactive
    yield context.call_activity("tombstone_chunks", {"doc_id": doc_id})

    # Update manifest
    yield context.call_activity("update_manifest", {
        "doc_id": doc_id,
        "tenant_id": tenant_id,
        "status": IngestionStatus.ARCHIVED.value,
    })

    return {"status": "tombstoned", "doc_id": doc_id}


# ============================================================================
# Orchestrator - Self-Healing Table Repair
# ============================================================================

@app.orchestration_trigger(context_name="context")
def table_repair_orchestrator(context: df.DurableOrchestrationContext):
    """
    Self-healing orchestrator for low-confidence tables.

    Attempts:
    1. Re-extract with higher resolution
    2. Use GPT-4V for structure reconstruction
    3. Update index with improved version
    """
    input_data = context.get_input()
    doc_id = input_data["doc_id"]
    table_chunks = input_data["table_chunks"]

    repaired_chunks = []

    for table in table_chunks:
        # Try vision-based repair
        repair_result = yield context.call_activity("repair_table_with_vision", {
            "doc_id": doc_id,
            "chunk_id": table["chunk_id"],
            "page_number": table["page_number"],
            "bbox": table["bbox"],
        })

        if repair_result["success"]:
            repaired_chunks.append(repair_result["chunk"])

    if repaired_chunks:
        # Re-embed and index repaired chunks
        embedded = yield context.call_activity("embed_chunks", {"chunks": repaired_chunks})
        yield context.call_activity("index_chunks", {
            "chunks": embedded,
            "doc_id": doc_id,
            "is_repair": True,
        })

    return {
        "status": "completed",
        "doc_id": doc_id,
        "repaired_count": len(repaired_chunks),
    }


# ============================================================================
# Activity Functions
# ============================================================================

@app.activity_trigger(input_name="input")
async def load_manifest(input: dict) -> dict | None:
    """Load document manifest from Cosmos DB."""
    cosmos_client = CosmosClient.from_connection_string(
        _get_env("COSMOS_CONNECTION_STRING")
    )
    database = cosmos_client.get_database_client(_get_env("COSMOS_DATABASE"))
    container = database.get_container_client("document-manifests")

    doc_id = input["doc_id"]
    tenant_id = input["tenant_id"]

    try:
        manifest = container.read_item(item=doc_id, partition_key=tenant_id)
        return manifest
    except Exception:
        return None


@app.activity_trigger(input_name="input")
async def download_and_hash(input: dict) -> dict:
    """Download blob and compute content hash."""
    blob_uri = input["blob_uri"]

    credential = DefaultAzureCredential()
    blob_client = BlobServiceClient(
        account_url=_extract_account_url(blob_uri),
        credential=credential,
    ).get_blob_client(
        container=_extract_container_from_uri(blob_uri),
        blob=_extract_blob_name(blob_uri),
    )

    # Download content
    download_stream = blob_client.download_blob()
    content = download_stream.readall()

    # Compute hash
    content_hash = hashlib.sha256(content).hexdigest()

    # Save to temp location for processing
    temp_path = f"/tmp/{input['doc_id']}.pdf"
    with open(temp_path, "wb") as f:
        f.write(content)

    return {
        "content_hash": content_hash,
        "temp_path": temp_path,
        "size_bytes": len(content),
    }


@app.activity_trigger(input_name="input")
async def extract_document(input: dict) -> dict:
    """Extract document using Azure Document Intelligence."""
    credential = DefaultAzureCredential()
    client = DocumentAnalysisClient(
        endpoint=_get_env("DOC_INTELLIGENCE_ENDPOINT"),
        credential=credential,
    )

    with open(input["blob_content_path"], "rb") as f:
        poller = client.begin_analyze_document(
            model_id="prebuilt-layout",
            document=f,
        )
        result = poller.result()

    pages = []
    page_hashes = {}
    low_confidence_tables = []

    for page in result.pages:
        page_num = page.page_number

        # Extract page content
        page_content = _extract_page_content(result, page_num)
        page_hash = hashlib.sha256(page_content.encode()).hexdigest()
        page_hashes[str(page_num)] = page_hash

        # Extract tables for this page
        tables = _extract_tables_for_page(result, page_num)

        # Check table confidence
        for table in tables:
            if table.get("confidence", 1.0) < 0.8:
                low_confidence_tables.append({
                    "page_number": page_num,
                    "bbox": table.get("bbox"),
                    "confidence": table.get("confidence"),
                })

        # Extract figures for this page
        figures = _extract_figures_for_page(result, page_num)

        pages.append({
            "page_number": page_num,
            "content_hash": page_hash,
            "text_content": page_content,
            "tables": tables,
            "figures": figures,
            "sections": _extract_sections(result, page_num),
        })

    return {
        "pages": pages,
        "page_hashes": page_hashes,
        "low_confidence_tables": low_confidence_tables,
    }


@app.activity_trigger(input_name="input")
async def diff_pages(input: dict) -> list[int]:
    """Determine which pages need reprocessing."""
    new_hashes = input["new_page_hashes"]
    old_hashes = input["old_page_hashes"]
    force = input.get("force_reprocess", False)

    if force:
        return list(range(1, len(new_hashes) + 1))

    changed_pages = []
    for page_num, new_hash in new_hashes.items():
        old_hash = old_hashes.get(page_num)
        if old_hash != new_hash:
            changed_pages.append(int(page_num))

    # Also include pages that were deleted
    for page_num in old_hashes:
        if page_num not in new_hashes:
            changed_pages.append(int(page_num))

    return sorted(changed_pages)


@app.activity_trigger(input_name="input")
async def chunk_pages(input: dict) -> list[dict]:
    """Chunk pages into indexable units."""
    doc_id = input["doc_id"]
    tenant_id = input["tenant_id"]
    pages = input["pages"]
    metadata = input.get("metadata", {})
    acl_users = input.get("acl_users", [])
    acl_groups = input.get("acl_groups", [])
    sensitivity = input.get("sensitivity", "internal")

    chunks = []
    reading_order = 0

    for page in pages:
        page_num = page["page_number"]
        sections = page.get("sections", [])
        current_section_path = []

        # Process text content
        text_chunks = _chunk_text(
            page["text_content"],
            max_tokens=512,
            overlap_tokens=64,
        )

        for idx, text in enumerate(text_chunks):
            chunk_id = f"{doc_id}_p{page_num}_text_{idx}"
            chunks.append({
                "id": chunk_id,
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "chunk_type": ChunkType.TEXT.value,
                "content": text,
                "content_md": None,
                "section_path": current_section_path.copy(),
                "heading": sections[-1]["text"] if sections else None,
                "page_start": page_num,
                "page_end": page_num,
                "reading_order": reading_order,
                "table_headers": None,
                "table_row_count": None,
                "table_col_count": None,
                "figure_ref": None,
                "bbox_union": None,
                "content_hash": hashlib.sha256(text.encode()).hexdigest(),
                "token_count": _count_tokens(text),
                "tenant_id": tenant_id,
                "acl_users": acl_users,
                "acl_groups": acl_groups,
                "sensitivity": sensitivity,
                "metadata": metadata,
            })
            reading_order += 1

        # Process tables (atomic, no splitting)
        for idx, table in enumerate(page.get("tables", [])):
            chunk_id = f"{doc_id}_p{page_num}_table_{idx}"
            table_md = _table_to_markdown(table)

            chunks.append({
                "id": chunk_id,
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "chunk_type": ChunkType.TABLE.value,
                "content": _table_to_text(table),
                "content_md": table_md,
                "section_path": current_section_path.copy(),
                "heading": sections[-1]["text"] if sections else None,
                "page_start": page_num,
                "page_end": page_num,
                "reading_order": reading_order,
                "table_headers": table.get("headers", []),
                "table_row_count": table.get("row_count"),
                "table_col_count": table.get("col_count"),
                "figure_ref": None,
                "bbox_union": json.dumps(table.get("bbox")),
                "content_hash": hashlib.sha256(table_md.encode()).hexdigest(),
                "token_count": _count_tokens(table_md),
                "tenant_id": tenant_id,
                "acl_users": acl_users,
                "acl_groups": acl_groups,
                "sensitivity": sensitivity,
                "metadata": metadata,
            })
            reading_order += 1

        # Process figures
        for idx, figure in enumerate(page.get("figures", [])):
            chunk_id = f"{doc_id}_p{page_num}_figure_{idx}"
            caption = figure.get("caption", "")

            chunks.append({
                "id": chunk_id,
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "chunk_type": ChunkType.IMAGE_CAPTION.value,
                "content": caption,
                "content_md": None,
                "section_path": current_section_path.copy(),
                "heading": sections[-1]["text"] if sections else None,
                "page_start": page_num,
                "page_end": page_num,
                "reading_order": reading_order,
                "table_headers": None,
                "table_row_count": None,
                "table_col_count": None,
                "figure_ref": figure.get("blob_uri"),
                "bbox_union": json.dumps(figure.get("bbox")),
                "content_hash": hashlib.sha256(caption.encode()).hexdigest(),
                "token_count": _count_tokens(caption),
                "tenant_id": tenant_id,
                "acl_users": acl_users,
                "acl_groups": acl_groups,
                "sensitivity": sensitivity,
                "metadata": metadata,
            })
            reading_order += 1

    return chunks


@app.activity_trigger(input_name="input")
async def embed_chunks(input: dict) -> list[dict]:
    """Generate embeddings for chunks."""
    from openai import AzureOpenAI

    chunks = input["chunks"]

    client = AzureOpenAI(
        azure_endpoint=_get_env("AZURE_OPENAI_ENDPOINT"),
        api_version="2024-02-15-preview",
        azure_ad_token_provider=_get_token_provider(),
    )

    # Batch embed
    texts = [c["content"] for c in chunks]

    response = client.embeddings.create(
        input=texts,
        model="text-embedding-3-large",
    )

    for i, chunk in enumerate(chunks):
        chunk["embedding"] = response.data[i].embedding

    return chunks


@app.activity_trigger(input_name="input")
async def index_chunks(input: dict) -> dict:
    """Index chunks to Azure AI Search."""
    chunks = input["chunks"]
    doc_id = input["doc_id"]
    is_repair = input.get("is_repair", False)

    credential = DefaultAzureCredential()
    search_client = SearchClient(
        endpoint=_get_env("AZURE_SEARCH_ENDPOINT"),
        index_name=_get_env("AZURE_SEARCH_INDEX"),
        credential=credential,
    )

    # Prepare documents for indexing
    documents = []
    for chunk in chunks:
        doc = {
            "id": chunk["id"],
            "doc_id": chunk["doc_id"],
            "chunk_id": chunk["chunk_id"],
            "chunk_type": chunk["chunk_type"],
            "content": chunk["content"],
            "content_md": chunk.get("content_md"),
            "embedding": chunk.get("embedding"),
            "section_path": chunk.get("section_path", []),
            "heading": chunk.get("heading"),
            "page_start": chunk.get("page_start"),
            "page_end": chunk.get("page_end"),
            "reading_order": chunk.get("reading_order"),
            "table_headers": chunk.get("table_headers"),
            "table_row_count": chunk.get("table_row_count"),
            "table_col_count": chunk.get("table_col_count"),
            "figure_ref": chunk.get("figure_ref"),
            "bbox_union": chunk.get("bbox_union"),
            "content_hash": chunk.get("content_hash"),
            "chunk_token_count": chunk.get("token_count"),
            "tenant_id": chunk.get("tenant_id"),
            "acl_users": chunk.get("acl_users", []),
            "acl_groups": chunk.get("acl_groups", []),
            "sensitivity": chunk.get("sensitivity", "internal"),
            "is_active": True,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
            "embedding_model_version": "text-embedding-3-large",
            "ingestion_version": "v1.0",
        }
        documents.append(doc)

    # Upsert in batches
    batch_size = 100
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        search_client.upload_documents(documents=batch)

    return {
        "indexed_count": len(documents),
        "doc_id": doc_id,
        "is_repair": is_repair,
    }


@app.activity_trigger(input_name="input")
async def tombstone_chunks(input: dict) -> dict:
    """Mark all chunks for a document as inactive."""
    doc_id = input["doc_id"]

    credential = DefaultAzureCredential()
    search_client = SearchClient(
        endpoint=_get_env("AZURE_SEARCH_ENDPOINT"),
        index_name=_get_env("AZURE_SEARCH_INDEX"),
        credential=credential,
    )

    # Find all chunks for this document
    results = search_client.search(
        search_text="*",
        filter=f"doc_id eq '{doc_id}'",
        select=["id"],
    )

    # Update each to inactive
    updates = []
    for result in results:
        updates.append({
            "id": result["id"],
            "is_active": False,
        })

    if updates:
        search_client.merge_documents(documents=updates)

    return {"tombstoned_count": len(updates)}


@app.activity_trigger(input_name="input")
async def update_manifest(input: dict) -> dict:
    """Update document manifest in Cosmos DB."""
    cosmos_client = CosmosClient.from_connection_string(
        _get_env("COSMOS_CONNECTION_STRING")
    )
    database = cosmos_client.get_database_client(_get_env("COSMOS_DATABASE"))
    container = database.get_container_client("document-manifests")

    manifest = {
        "id": input["doc_id"],
        "doc_id": input["doc_id"],
        "tenant_id": input["tenant_id"],
        "blob_uri": input.get("blob_uri"),
        "etag": input.get("etag"),
        "content_hash": input.get("content_hash"),
        "status": input.get("status", IngestionStatus.INDEXED.value),
        "page_hashes": input.get("page_hashes", {}),
        "page_count": input.get("page_count"),
        "chunk_count": input.get("chunk_count"),
        "error_message": input.get("error_message"),
        "last_ingested_utc": datetime.now(timezone.utc).isoformat(),
        "embedding_model_version": "text-embedding-3-large",
        "ingestion_version": "v1.0",
    }

    container.upsert_item(body=manifest, partition_key=input["tenant_id"])

    return {"status": "updated"}


@app.activity_trigger(input_name="input")
async def queue_table_repair(input: dict) -> dict:
    """Queue low-confidence tables for repair."""
    # In production, this would send to a Service Bus queue
    # For now, just log
    logging.warning(
        f"Queued {len(input['tables'])} tables for repair in doc {input['doc_id']}"
    )
    return {"queued": len(input["tables"])}


@app.activity_trigger(input_name="input")
async def repair_table_with_vision(input: dict) -> dict:
    """Attempt to repair a table using GPT-4V."""
    from openai import AzureOpenAI

    doc_id = input["doc_id"]
    chunk_id = input["chunk_id"]
    page_number = input["page_number"]
    bbox = input["bbox"]

    # In production:
    # 1. Extract the table region as an image from the PDF
    # 2. Send to GPT-4V for structure reconstruction
    # 3. Return improved markdown representation

    # Placeholder implementation
    client = AzureOpenAI(
        azure_endpoint=_get_env("AZURE_OPENAI_ENDPOINT"),
        api_version="2024-02-15-preview",
        azure_ad_token_provider=_get_token_provider(),
    )

    # This would actually send the image to vision model
    # For now, return failure to indicate repair not attempted
    return {
        "success": False,
        "chunk_id": chunk_id,
        "reason": "Vision repair not implemented",
    }


# ============================================================================
# Helper Functions
# ============================================================================

def _generate_doc_id(blob_uri: str) -> str:
    """Generate deterministic document ID from URI."""
    return hashlib.sha256(blob_uri.encode()).hexdigest()[:16]


def _extract_account_url(blob_uri: str) -> str:
    """Extract storage account URL from blob URI."""
    # https://storageaccount.blob.core.windows.net/container/blob.pdf
    parts = blob_uri.split("/")
    return f"{parts[0]}//{parts[2]}"


def _extract_container_from_uri(blob_uri: str) -> str:
    """Extract container name from blob URI."""
    parts = blob_uri.split("/")
    return parts[3]


def _extract_blob_name(blob_uri: str) -> str:
    """Extract blob name from URI."""
    parts = blob_uri.split("/")
    return "/".join(parts[4:])


def _get_env(name: str) -> str:
    """Get environment variable."""
    import os
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"Missing environment variable: {name}")
    return value


def _get_token_provider():
    """Get Azure AD token provider."""
    from azure.identity import get_bearer_token_provider
    credential = DefaultAzureCredential()
    return get_bearer_token_provider(
        credential,
        "https://cognitiveservices.azure.com/.default"
    )


def _extract_page_content(result: Any, page_num: int) -> str:
    """Extract text content for a specific page."""
    content_parts = []
    for paragraph in result.paragraphs or []:
        if any(region.page_number == page_num for region in paragraph.bounding_regions or []):
            content_parts.append(paragraph.content)
    return "\n".join(content_parts)


def _extract_tables_for_page(result: Any, page_num: int) -> list[dict]:
    """Extract tables for a specific page."""
    tables = []
    for table in result.tables or []:
        if any(region.page_number == page_num for region in table.bounding_regions or []):
            tables.append({
                "headers": [cell.content for cell in table.cells if cell.kind == "columnHeader"],
                "cells": [[cell.content for cell in row] for row in _group_cells_by_row(table.cells)],
                "row_count": table.row_count,
                "col_count": table.column_count,
                "confidence": getattr(table, "confidence", 1.0),
                "bbox": _get_table_bbox(table),
            })
    return tables


def _extract_figures_for_page(result: Any, page_num: int) -> list[dict]:
    """Extract figures for a specific page."""
    figures = []
    for figure in getattr(result, "figures", []) or []:
        if any(region.page_number == page_num for region in figure.bounding_regions or []):
            figures.append({
                "caption": getattr(figure, "caption", {}).get("content", ""),
                "bbox": _get_figure_bbox(figure),
            })
    return figures


def _extract_sections(result: Any, page_num: int) -> list[dict]:
    """Extract section headings for a page."""
    sections = []
    for paragraph in result.paragraphs or []:
        if any(region.page_number == page_num for region in paragraph.bounding_regions or []):
            role = getattr(paragraph, "role", None)
            if role and "heading" in role.lower():
                sections.append({
                    "text": paragraph.content,
                    "role": role,
                })
    return sections


def _group_cells_by_row(cells: list) -> list[list]:
    """Group table cells by row."""
    rows = {}
    for cell in cells:
        row_idx = cell.row_index
        if row_idx not in rows:
            rows[row_idx] = []
        rows[row_idx].append(cell)

    return [rows[i] for i in sorted(rows.keys())]


def _get_table_bbox(table: Any) -> dict | None:
    """Get bounding box for a table."""
    if table.bounding_regions:
        region = table.bounding_regions[0]
        if hasattr(region, "polygon"):
            return {"polygon": region.polygon}
    return None


def _get_figure_bbox(figure: Any) -> dict | None:
    """Get bounding box for a figure."""
    if figure.bounding_regions:
        region = figure.bounding_regions[0]
        if hasattr(region, "polygon"):
            return {"polygon": region.polygon}
    return None


def _table_to_markdown(table: dict) -> str:
    """Convert table dict to markdown."""
    headers = table.get("headers", [])
    cells = table.get("cells", [])

    if not headers and cells:
        headers = cells[0] if cells else []
        cells = cells[1:] if len(cells) > 1 else []

    lines = []
    if headers:
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    for row in cells:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")

    return "\n".join(lines)


def _table_to_text(table: dict) -> str:
    """Convert table to plain text for BM25."""
    parts = []
    if table.get("headers"):
        parts.append(" ".join(table["headers"]))
    for row in table.get("cells", []):
        parts.append(" ".join(str(c) for c in row))
    return " ".join(parts)


def _chunk_text(text: str, max_tokens: int = 512, overlap_tokens: int = 64) -> list[str]:
    """Chunk text into segments."""
    import tiktoken
    encoder = tiktoken.get_encoding("cl100k_base")

    tokens = encoder.encode(text)
    chunks = []

    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunks.append(encoder.decode(chunk_tokens))
        start = end - overlap_tokens if end < len(tokens) else len(tokens)

    return chunks


def _count_tokens(text: str) -> int:
    """Count tokens in text."""
    import tiktoken
    encoder = tiktoken.get_encoding("cl100k_base")
    return len(encoder.encode(text))
