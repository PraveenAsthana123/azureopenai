"""
Enterprise AI Platform - Ingestion Pipeline
Durable Functions for document ingestion: OCR → Chunk → Embed → Index
"""

import azure.functions as func
import azure.durable_functions as df
import logging
import json
import hashlib
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, asdict

app = df.DFApp(http_auth_level=func.AuthLevel.FUNCTION)

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class IngestionContext:
    """Context passed through ingestion pipeline"""
    run_id: str
    document_id: Optional[str]
    source_uri: str
    source_system: str
    blob_path: Optional[str] = None
    ocr_path: Optional[str] = None
    doc_metadata: Optional[dict] = None
    chunks: Optional[list] = None
    embeddings: Optional[list] = None
    hash_sha256: Optional[str] = None
    stage: str = "init"
    error: Optional[str] = None


# =============================================================================
# HTTP TRIGGER - Start Ingestion
# =============================================================================

@app.route(route="ingest", methods=["POST"])
@app.durable_client_input(client_name="client")
async def http_start_ingestion(req: func.HttpRequest, client) -> func.HttpResponse:
    """
    HTTP trigger to start document ingestion.

    Request body:
    {
        "source_uri": "https://...",
        "source_system": "sharepoint|blob|api",
        "metadata": { ... }
    }
    """
    try:
        body = req.get_json()
        source_uri = body.get("source_uri")
        source_system = body.get("source_system", "blob")
        metadata = body.get("metadata", {})

        if not source_uri:
            return func.HttpResponse(
                json.dumps({"error": "source_uri is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Create ingestion context
        import uuid
        context = IngestionContext(
            run_id=str(uuid.uuid4()),
            document_id=metadata.get("document_id"),
            source_uri=source_uri,
            source_system=source_system,
            doc_metadata=metadata
        )

        # Start orchestration
        instance_id = await client.start_new(
            "ingestion_orchestrator",
            client_input=asdict(context)
        )

        logging.info(f"Started ingestion orchestration: {instance_id}")

        return client.create_check_status_response(req, instance_id)

    except Exception as e:
        logging.error(f"Failed to start ingestion: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


# =============================================================================
# EVENT GRID TRIGGER - Auto-ingest on blob creation
# =============================================================================

@app.event_grid_trigger(arg_name="event")
@app.durable_client_input(client_name="client")
async def eventgrid_blob_created(event: func.EventGridEvent, client):
    """
    Event Grid trigger for automatic ingestion when blob is created/updated.
    """
    try:
        event_data = event.get_json()
        blob_url = event_data.get("url", "")

        # Filter for supported file types
        supported_extensions = [".pdf", ".docx", ".doc", ".pptx", ".xlsx", ".txt", ".md", ".html"]
        if not any(blob_url.lower().endswith(ext) for ext in supported_extensions):
            logging.info(f"Skipping unsupported file type: {blob_url}")
            return

        import uuid
        context = IngestionContext(
            run_id=str(uuid.uuid4()),
            document_id=None,
            source_uri=blob_url,
            source_system="blob",
            doc_metadata={
                "triggered_by": "event_grid",
                "event_type": event.event_type,
                "event_time": event.event_time.isoformat() if event.event_time else None
            }
        )

        instance_id = await client.start_new(
            "ingestion_orchestrator",
            client_input=asdict(context)
        )

        logging.info(f"Auto-ingestion started for {blob_url}: {instance_id}")

    except Exception as e:
        logging.error(f"Event Grid trigger failed: {e}")


# =============================================================================
# ORCHESTRATOR - Main Ingestion Pipeline
# =============================================================================

@app.orchestration_trigger(context_name="context")
def ingestion_orchestrator(context: df.DurableOrchestrationContext):
    """
    Main orchestrator for document ingestion pipeline.

    Pipeline stages:
    1. Download/validate document
    2. OCR/extract text
    3. Chunk document
    4. Generate embeddings (parallel)
    5. Index to AI Search
    6. Update metadata DB
    7. Validate & telemetry
    """
    ctx_dict = context.get_input()
    ctx = IngestionContext(**ctx_dict)

    try:
        # Stage 1: Download & Validate
        ctx.stage = "download"
        ctx = yield context.call_activity("activity_download_document", asdict(ctx))
        ctx = IngestionContext(**ctx) if isinstance(ctx, dict) else ctx

        if ctx.error:
            return {"status": "failed", "stage": "download", "error": ctx.error, "run_id": ctx.run_id}

        # Stage 2: OCR/Extract
        ctx.stage = "ocr"
        ctx = yield context.call_activity("activity_extract_text", asdict(ctx))
        ctx = IngestionContext(**ctx) if isinstance(ctx, dict) else ctx

        if ctx.error:
            return {"status": "failed", "stage": "ocr", "error": ctx.error, "run_id": ctx.run_id}

        # Stage 3: Chunking
        ctx.stage = "chunk"
        ctx = yield context.call_activity("activity_chunk_document", asdict(ctx))
        ctx = IngestionContext(**ctx) if isinstance(ctx, dict) else ctx

        if ctx.error:
            return {"status": "failed", "stage": "chunk", "error": ctx.error, "run_id": ctx.run_id}

        # Stage 4: Embedding (parallel fan-out)
        ctx.stage = "embed"
        if ctx.chunks and len(ctx.chunks) > 0:
            # Fan-out: process chunks in batches
            batch_size = 10
            embedding_tasks = []

            for i in range(0, len(ctx.chunks), batch_size):
                batch = ctx.chunks[i:i + batch_size]
                task = context.call_activity("activity_generate_embeddings", {
                    "chunks": batch,
                    "run_id": ctx.run_id,
                    "batch_index": i // batch_size
                })
                embedding_tasks.append(task)

            # Fan-in: collect all embeddings
            embedding_results = yield context.task_all(embedding_tasks)

            # Merge embeddings back to chunks
            all_embeddings = []
            for result in embedding_results:
                if isinstance(result, dict) and "embeddings" in result:
                    all_embeddings.extend(result["embeddings"])

            ctx.embeddings = all_embeddings

        if ctx.error:
            return {"status": "failed", "stage": "embed", "error": ctx.error, "run_id": ctx.run_id}

        # Stage 5: Index to AI Search
        ctx.stage = "index"
        ctx = yield context.call_activity("activity_index_chunks", asdict(ctx))
        ctx = IngestionContext(**ctx) if isinstance(ctx, dict) else ctx

        if ctx.error:
            return {"status": "failed", "stage": "index", "error": ctx.error, "run_id": ctx.run_id}

        # Stage 6: Update SQL metadata
        ctx.stage = "metadata"
        ctx = yield context.call_activity("activity_update_metadata", asdict(ctx))
        ctx = IngestionContext(**ctx) if isinstance(ctx, dict) else ctx

        # Stage 7: Validation & Telemetry
        ctx.stage = "validate"
        result = yield context.call_activity("activity_validate_ingestion", asdict(ctx))

        return {
            "status": "success",
            "run_id": ctx.run_id,
            "document_id": ctx.document_id,
            "chunks_count": len(ctx.chunks) if ctx.chunks else 0,
            "indexed_at": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logging.error(f"Orchestrator failed at stage {ctx.stage}: {e}")
        return {
            "status": "failed",
            "stage": ctx.stage,
            "error": str(e),
            "run_id": ctx.run_id
        }


# =============================================================================
# ACTIVITY: Download Document
# =============================================================================

@app.activity_trigger(input_name="ctx_dict")
async def activity_download_document(ctx_dict: dict) -> dict:
    """Download document from source to ADLS staging."""
    from azure.storage.blob.aio import BlobServiceClient
    from azure.identity.aio import DefaultAzureCredential
    import os
    import uuid

    ctx = IngestionContext(**ctx_dict)

    try:
        logging.info(f"[{ctx.run_id}] Downloading from {ctx.source_uri}")

        # Initialize blob client
        credential = DefaultAzureCredential()
        storage_url = os.environ.get("ADLS_ACCOUNT_URL")
        blob_service = BlobServiceClient(storage_url, credential=credential)

        # Download source document
        # (In production, handle different source systems)
        source_blob_client = blob_service.get_blob_client(
            container="raw",
            blob=ctx.source_uri.split("/")[-1]
        )

        # Download and compute hash
        download_stream = await source_blob_client.download_blob()
        content = await download_stream.readall()
        ctx.hash_sha256 = hashlib.sha256(content).hexdigest()

        # Upload to staging
        staging_path = f"staging/{ctx.run_id}/{ctx.source_uri.split('/')[-1]}"
        staging_blob = blob_service.get_blob_client(container="processed", blob=staging_path)
        await staging_blob.upload_blob(content, overwrite=True)

        ctx.blob_path = staging_path
        logging.info(f"[{ctx.run_id}] Downloaded to {staging_path}, hash={ctx.hash_sha256[:16]}...")

        await credential.close()
        return asdict(ctx)

    except Exception as e:
        ctx.error = f"Download failed: {str(e)}"
        logging.error(f"[{ctx.run_id}] {ctx.error}")
        return asdict(ctx)


# =============================================================================
# ACTIVITY: Extract Text (OCR)
# =============================================================================

@app.activity_trigger(input_name="ctx_dict")
async def activity_extract_text(ctx_dict: dict) -> dict:
    """Extract text using Document Intelligence."""
    from azure.ai.documentintelligence.aio import DocumentIntelligenceClient
    from azure.identity.aio import DefaultAzureCredential
    import os

    ctx = IngestionContext(**ctx_dict)

    try:
        logging.info(f"[{ctx.run_id}] Extracting text from {ctx.blob_path}")

        credential = DefaultAzureCredential()
        doc_intel_endpoint = os.environ.get("DOC_INTELLIGENCE_ENDPOINT")

        async with DocumentIntelligenceClient(
            endpoint=doc_intel_endpoint,
            credential=credential
        ) as client:
            # Get blob URL
            storage_url = os.environ.get("ADLS_ACCOUNT_URL")
            blob_url = f"{storage_url}/processed/{ctx.blob_path}"

            # Analyze document
            poller = await client.begin_analyze_document(
                model_id="prebuilt-layout",
                analyze_request={"urlSource": blob_url}
            )
            result = await poller.result()

            # Extract text with structure
            extracted_content = {
                "full_text": result.content if result.content else "",
                "pages": [],
                "tables": [],
                "paragraphs": []
            }

            # Process pages
            if result.pages:
                for page in result.pages:
                    page_info = {
                        "page_number": page.page_number,
                        "width": page.width,
                        "height": page.height,
                        "lines": []
                    }
                    if page.lines:
                        for line in page.lines:
                            page_info["lines"].append(line.content)
                    extracted_content["pages"].append(page_info)

            # Process tables
            if result.tables:
                for table in result.tables:
                    table_data = {
                        "row_count": table.row_count,
                        "column_count": table.column_count,
                        "cells": []
                    }
                    if table.cells:
                        for cell in table.cells:
                            table_data["cells"].append({
                                "row": cell.row_index,
                                "col": cell.column_index,
                                "content": cell.content
                            })
                    extracted_content["tables"].append(table_data)

            # Store OCR result
            from azure.storage.blob.aio import BlobServiceClient
            blob_service = BlobServiceClient(storage_url, credential=credential)

            ocr_path = f"ocr/{ctx.run_id}/extracted.json"
            ocr_blob = blob_service.get_blob_client(container="processed", blob=ocr_path)
            await ocr_blob.upload_blob(
                json.dumps(extracted_content, indent=2),
                overwrite=True
            )

            ctx.ocr_path = ocr_path
            ctx.doc_metadata = ctx.doc_metadata or {}
            ctx.doc_metadata["page_count"] = len(extracted_content["pages"])
            ctx.doc_metadata["has_tables"] = len(extracted_content["tables"]) > 0
            ctx.doc_metadata["word_count"] = len(extracted_content["full_text"].split())

            logging.info(f"[{ctx.run_id}] Extracted {ctx.doc_metadata['word_count']} words, {ctx.doc_metadata['page_count']} pages")

        await credential.close()
        return asdict(ctx)

    except Exception as e:
        ctx.error = f"OCR failed: {str(e)}"
        logging.error(f"[{ctx.run_id}] {ctx.error}")
        return asdict(ctx)


# =============================================================================
# ACTIVITY: Chunk Document
# =============================================================================

@app.activity_trigger(input_name="ctx_dict")
async def activity_chunk_document(ctx_dict: dict) -> dict:
    """Chunk document using semantic/heading-aware chunking."""
    from azure.storage.blob.aio import BlobServiceClient
    from azure.identity.aio import DefaultAzureCredential
    import os
    import tiktoken
    import uuid

    ctx = IngestionContext(**ctx_dict)

    try:
        logging.info(f"[{ctx.run_id}] Chunking document")

        # Load OCR result
        credential = DefaultAzureCredential()
        storage_url = os.environ.get("ADLS_ACCOUNT_URL")
        blob_service = BlobServiceClient(storage_url, credential=credential)

        ocr_blob = blob_service.get_blob_client(container="processed", blob=ctx.ocr_path)
        download = await ocr_blob.download_blob()
        ocr_content = json.loads(await download.readall())

        # Tokenizer for counting
        encoding = tiktoken.get_encoding("cl100k_base")

        # Chunking parameters
        max_chunk_tokens = int(os.environ.get("CHUNK_MAX_TOKENS", "800"))
        overlap_percent = int(os.environ.get("CHUNK_OVERLAP_PERCENT", "10"))
        overlap_tokens = int(max_chunk_tokens * overlap_percent / 100)

        chunks = []
        full_text = ocr_content.get("full_text", "")

        # Simple token-based chunking with overlap
        # (In production, use semantic/heading-aware chunking)
        tokens = encoding.encode(full_text)

        chunk_order = 0
        start = 0

        while start < len(tokens):
            end = min(start + max_chunk_tokens, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = encoding.decode(chunk_tokens)

            chunk = {
                "chunk_id": str(uuid.uuid4()),
                "chunk_order": chunk_order,
                "chunk_text": chunk_text,
                "token_count": len(chunk_tokens),
                "char_count": len(chunk_text),
                "page_number": None,  # Would be set with better chunking
                "heading_path": None,
                "section_name": None
            }
            chunks.append(chunk)

            chunk_order += 1
            start = end - overlap_tokens if end < len(tokens) else end

        ctx.chunks = chunks
        logging.info(f"[{ctx.run_id}] Created {len(chunks)} chunks")

        await credential.close()
        return asdict(ctx)

    except Exception as e:
        ctx.error = f"Chunking failed: {str(e)}"
        logging.error(f"[{ctx.run_id}] {ctx.error}")
        return asdict(ctx)


# =============================================================================
# ACTIVITY: Generate Embeddings
# =============================================================================

@app.activity_trigger(input_name="input_data")
async def activity_generate_embeddings(input_data: dict) -> dict:
    """Generate embeddings for chunk batch using Azure OpenAI."""
    from openai import AsyncAzureOpenAI
    from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
    import os

    chunks = input_data.get("chunks", [])
    run_id = input_data.get("run_id")
    batch_index = input_data.get("batch_index", 0)

    try:
        logging.info(f"[{run_id}] Generating embeddings for batch {batch_index} ({len(chunks)} chunks)")

        # Initialize OpenAI client with managed identity
        credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            credential,
            "https://cognitiveservices.azure.com/.default"
        )

        client = AsyncAzureOpenAI(
            azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
            azure_ad_token_provider=token_provider,
            api_version="2024-02-01"
        )

        # Prepare texts for embedding
        texts = [chunk["chunk_text"] for chunk in chunks]

        # Generate embeddings
        response = await client.embeddings.create(
            model=os.environ.get("EMBEDDING_DEPLOYMENT", "text-embedding-3-large"),
            input=texts
        )

        # Attach embeddings to chunks
        embeddings = []
        for i, chunk in enumerate(chunks):
            chunk_with_embedding = chunk.copy()
            chunk_with_embedding["embedding"] = response.data[i].embedding
            chunk_with_embedding["embedding_model"] = "text-embedding-3-large"
            chunk_with_embedding["embedding_dimensions"] = len(response.data[i].embedding)
            embeddings.append(chunk_with_embedding)

        await credential.close()
        await client.close()

        logging.info(f"[{run_id}] Generated {len(embeddings)} embeddings for batch {batch_index}")
        return {"embeddings": embeddings, "batch_index": batch_index}

    except Exception as e:
        logging.error(f"[{run_id}] Embedding generation failed for batch {batch_index}: {e}")
        return {"embeddings": [], "error": str(e), "batch_index": batch_index}


# =============================================================================
# ACTIVITY: Index to AI Search
# =============================================================================

@app.activity_trigger(input_name="ctx_dict")
async def activity_index_chunks(ctx_dict: dict) -> dict:
    """Index chunks with embeddings to Azure AI Search."""
    from azure.search.documents.aio import SearchClient
    from azure.identity.aio import DefaultAzureCredential
    import os
    from datetime import datetime, timezone

    ctx = IngestionContext(**ctx_dict)

    try:
        logging.info(f"[{ctx.run_id}] Indexing {len(ctx.embeddings or [])} chunks to AI Search")

        credential = DefaultAzureCredential()
        search_endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT")
        index_name = os.environ.get("SEARCH_INDEX_NAME", "enterprise-knowledge-index")

        async with SearchClient(
            endpoint=search_endpoint,
            index_name=index_name,
            credential=credential
        ) as client:
            # Prepare documents for indexing
            documents = []
            for chunk in (ctx.embeddings or []):
                doc = {
                    "id": chunk["chunk_id"],
                    "chunk_id": chunk["chunk_id"],
                    "document_id": ctx.document_id or ctx.run_id,
                    "title": ctx.doc_metadata.get("title", ctx.source_uri.split("/")[-1]) if ctx.doc_metadata else ctx.source_uri.split("/")[-1],
                    "chunk_text": chunk["chunk_text"],
                    "chunk_order": chunk["chunk_order"],
                    "token_count": chunk["token_count"],
                    "heading_path": chunk.get("heading_path"),
                    "section_name": chunk.get("section_name"),
                    "page_number": chunk.get("page_number"),
                    "doc_type": ctx.doc_metadata.get("doc_type", "document") if ctx.doc_metadata else "document",
                    "business_unit": ctx.doc_metadata.get("business_unit") if ctx.doc_metadata else None,
                    "department": ctx.doc_metadata.get("department") if ctx.doc_metadata else None,
                    "region": ctx.doc_metadata.get("region") if ctx.doc_metadata else None,
                    "classification": ctx.doc_metadata.get("classification", "internal") if ctx.doc_metadata else "internal",
                    "status": "published",
                    "language": ctx.doc_metadata.get("language", "en") if ctx.doc_metadata else "en",
                    "source_system": ctx.source_system,
                    "source_uri": ctx.source_uri,
                    "embedding_model": chunk.get("embedding_model"),
                    "chunk_vector": chunk.get("embedding"),
                    "acl_groups": ctx.doc_metadata.get("acl_groups", []) if ctx.doc_metadata else [],
                    "acl_deny_groups": ctx.doc_metadata.get("acl_deny_groups", []) if ctx.doc_metadata else [],
                    "indexed_at": datetime.now(timezone.utc).isoformat()
                }
                documents.append(doc)

            # Upload in batches
            batch_size = 100
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                result = await client.upload_documents(documents=batch)
                success_count = sum(1 for r in result if r.succeeded)
                logging.info(f"[{ctx.run_id}] Indexed batch {i // batch_size + 1}: {success_count}/{len(batch)} succeeded")

        await credential.close()
        logging.info(f"[{ctx.run_id}] Indexing complete")
        return asdict(ctx)

    except Exception as e:
        ctx.error = f"Indexing failed: {str(e)}"
        logging.error(f"[{ctx.run_id}] {ctx.error}")
        return asdict(ctx)


# =============================================================================
# ACTIVITY: Update Metadata in SQL
# =============================================================================

@app.activity_trigger(input_name="ctx_dict")
async def activity_update_metadata(ctx_dict: dict) -> dict:
    """Update document and chunk metadata in Azure SQL."""
    import os
    import aioodbc
    from datetime import datetime, timezone

    ctx = IngestionContext(**ctx_dict)

    try:
        logging.info(f"[{ctx.run_id}] Updating metadata in SQL")

        # Connection string from Key Vault or env
        conn_str = os.environ.get("SQL_CONNECTION_STRING")

        async with aioodbc.connect(dsn=conn_str) as conn:
            async with conn.cursor() as cursor:
                now = datetime.now(timezone.utc).isoformat()

                # Insert or update document
                if ctx.document_id:
                    # Update existing
                    await cursor.execute("""
                        UPDATE [metadata].[Documents]
                        SET hash_sha256 = ?,
                            version = version + 1,
                            updated_at = ?,
                            word_count = ?,
                            page_count = ?,
                            has_tables = ?
                        WHERE document_id = ?
                    """, (
                        ctx.hash_sha256,
                        now,
                        ctx.doc_metadata.get("word_count") if ctx.doc_metadata else None,
                        ctx.doc_metadata.get("page_count") if ctx.doc_metadata else None,
                        1 if ctx.doc_metadata and ctx.doc_metadata.get("has_tables") else 0,
                        ctx.document_id
                    ))
                else:
                    # Insert new
                    import uuid
                    ctx.document_id = str(uuid.uuid4())
                    await cursor.execute("""
                        INSERT INTO [metadata].[Documents]
                        (document_id, source_system, source_uri, doc_type, title,
                         hash_sha256, blob_path, status, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 'published', ?, ?)
                    """, (
                        ctx.document_id,
                        ctx.source_system,
                        ctx.source_uri,
                        ctx.doc_metadata.get("doc_type", "document") if ctx.doc_metadata else "document",
                        ctx.doc_metadata.get("title", ctx.source_uri.split("/")[-1]) if ctx.doc_metadata else ctx.source_uri.split("/")[-1],
                        ctx.hash_sha256,
                        ctx.blob_path,
                        now,
                        now
                    ))

                # Insert chunks metadata
                for chunk in (ctx.chunks or []):
                    await cursor.execute("""
                        INSERT INTO [metadata].[Chunks]
                        (chunk_id, document_id, chunk_order, chunk_text, token_count,
                         char_count, embedding_model, embedding_version, vector_id,
                         search_index_name, is_indexed, indexed_at, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
                    """, (
                        chunk["chunk_id"],
                        ctx.document_id,
                        chunk["chunk_order"],
                        chunk["chunk_text"][:4000],  # Truncate for SQL
                        chunk["token_count"],
                        chunk["char_count"],
                        "text-embedding-3-large",
                        "1",
                        chunk["chunk_id"],
                        os.environ.get("SEARCH_INDEX_NAME", "enterprise-knowledge-index"),
                        now,
                        now,
                        now
                    ))

                # Insert ingestion run record
                await cursor.execute("""
                    INSERT INTO [ingestion].[IngestionRuns]
                    (run_id, document_id, run_type, status, chunks_created,
                     chunks_indexed, started_at, completed_at, triggered_by)
                    VALUES (?, ?, 'full', 'success', ?, ?, ?, ?, ?)
                """, (
                    ctx.run_id,
                    ctx.document_id,
                    len(ctx.chunks) if ctx.chunks else 0,
                    len(ctx.chunks) if ctx.chunks else 0,
                    now,
                    now,
                    ctx.doc_metadata.get("triggered_by", "api") if ctx.doc_metadata else "api"
                ))

                await conn.commit()

        logging.info(f"[{ctx.run_id}] Metadata updated for document {ctx.document_id}")
        return asdict(ctx)

    except Exception as e:
        ctx.error = f"Metadata update failed: {str(e)}"
        logging.error(f"[{ctx.run_id}] {ctx.error}")
        return asdict(ctx)


# =============================================================================
# ACTIVITY: Validate Ingestion
# =============================================================================

@app.activity_trigger(input_name="ctx_dict")
async def activity_validate_ingestion(ctx_dict: dict) -> dict:
    """Validate ingestion completed successfully and emit telemetry."""
    import os

    ctx = IngestionContext(**ctx_dict)

    try:
        logging.info(f"[{ctx.run_id}] Validating ingestion")

        # Validation checks
        validations = {
            "has_document_id": ctx.document_id is not None,
            "has_chunks": ctx.chunks is not None and len(ctx.chunks) > 0,
            "has_embeddings": ctx.embeddings is not None and len(ctx.embeddings) > 0,
            "hash_computed": ctx.hash_sha256 is not None
        }

        all_valid = all(validations.values())

        # Emit telemetry (would go to App Insights in production)
        telemetry = {
            "run_id": ctx.run_id,
            "document_id": ctx.document_id,
            "source_system": ctx.source_system,
            "chunks_count": len(ctx.chunks) if ctx.chunks else 0,
            "embeddings_count": len(ctx.embeddings) if ctx.embeddings else 0,
            "validation_result": "pass" if all_valid else "fail",
            "validations": validations
        }

        logging.info(f"[{ctx.run_id}] Validation complete: {telemetry}")

        return {
            "status": "success" if all_valid else "partial",
            "run_id": ctx.run_id,
            "document_id": ctx.document_id,
            "validations": validations
        }

    except Exception as e:
        logging.error(f"[{ctx.run_id}] Validation failed: {e}")
        return {
            "status": "error",
            "run_id": ctx.run_id,
            "error": str(e)
        }
