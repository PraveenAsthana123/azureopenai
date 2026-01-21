"""
Ingestion Pipeline Azure Function App
Handles document ingestion, OCR, chunking, and embedding generation
"""
import azure.functions as func
import logging
import json
import os
from datetime import datetime
from typing import Any, Dict, List
import hashlib

app = func.FunctionApp()

# Configuration
STORAGE_CONNECTION = os.environ.get("AzureWebJobsStorage", "")
COSMOS_CONNECTION = os.environ.get("COSMOS_CONNECTION_STRING", "")
DOC_INTELLIGENCE_ENDPOINT = os.environ.get("DOC_INTELLIGENCE_ENDPOINT", "")
DOC_INTELLIGENCE_KEY = os.environ.get("DOC_INTELLIGENCE_KEY", "")
OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY", "")
SEARCH_ENDPOINT = os.environ.get("AZURE_SEARCH_ENDPOINT", "")
SEARCH_KEY = os.environ.get("AZURE_SEARCH_KEY", "")


# Blob trigger for automatic document processing
@app.blob_trigger(arg_name="blob", path="documents/{name}",
                  connection="AzureWebJobsStorage")
async def process_uploaded_document(blob: func.InputStream):
    """
    Triggered when a new document is uploaded to the 'documents' container
    Processes the document through the full ingestion pipeline
    """
    logging.info(f"Processing blob: {blob.name}, Size: {blob.length} bytes")

    try:
        # Read blob content
        content = blob.read()
        document_id = generate_document_id(blob.name, content)

        # Determine document type
        doc_type = get_document_type(blob.name)

        # Process based on document type
        if doc_type in ["pdf", "docx", "xlsx", "pptx", "image"]:
            result = await process_with_document_intelligence(
                content=content,
                document_id=document_id,
                filename=blob.name,
                doc_type=doc_type
            )
        elif doc_type in ["txt", "md", "json", "csv"]:
            result = await process_text_document(
                content=content.decode("utf-8"),
                document_id=document_id,
                filename=blob.name,
                doc_type=doc_type
            )
        else:
            logging.warning(f"Unsupported document type: {doc_type}")
            return

        logging.info(f"Document {document_id} processed successfully. Chunks: {result.get('chunks_count', 0)}")

    except Exception as e:
        logging.error(f"Error processing document {blob.name}: {str(e)}")
        raise


@app.route(route="ingest", methods=["POST"])
async def manual_ingest(req: func.HttpRequest) -> func.HttpResponse:
    """
    Manual ingestion endpoint for API-based document submission
    """
    logging.info("Manual ingestion endpoint called")

    try:
        # Check for file upload
        file = req.files.get("file")
        if file:
            content = file.read()
            filename = file.filename
        else:
            # Check for base64 encoded content
            req_body = req.get_json()
            if "content" not in req_body:
                return func.HttpResponse(
                    json.dumps({"error": "No file or content provided"}),
                    mimetype="application/json",
                    status_code=400
                )

            import base64
            content = base64.b64decode(req_body["content"])
            filename = req_body.get("filename", "document")

        document_id = generate_document_id(filename, content)
        doc_type = get_document_type(filename)

        # Process document
        if doc_type in ["pdf", "docx", "xlsx", "pptx", "image"]:
            result = await process_with_document_intelligence(
                content=content,
                document_id=document_id,
                filename=filename,
                doc_type=doc_type
            )
        elif doc_type in ["txt", "md", "json", "csv"]:
            result = await process_text_document(
                content=content.decode("utf-8") if isinstance(content, bytes) else content,
                document_id=document_id,
                filename=filename,
                doc_type=doc_type
            )
        else:
            return func.HttpResponse(
                json.dumps({"error": f"Unsupported document type: {doc_type}"}),
                mimetype="application/json",
                status_code=400
            )

        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json",
            status_code=202
        )

    except Exception as e:
        logging.error(f"Manual ingestion error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )


@app.route(route="batch-ingest", methods=["POST"])
async def batch_ingest(req: func.HttpRequest) -> func.HttpResponse:
    """
    Batch ingestion endpoint for processing multiple documents
    """
    logging.info("Batch ingestion endpoint called")

    try:
        req_body = req.get_json()
        documents = req_body.get("documents", [])

        if not documents:
            return func.HttpResponse(
                json.dumps({"error": "No documents provided"}),
                mimetype="application/json",
                status_code=400
            )

        results = []
        for doc in documents:
            try:
                # TODO: Process each document
                results.append({
                    "filename": doc.get("filename"),
                    "status": "queued",
                    "document_id": generate_document_id(doc.get("filename", ""), b"")
                })
            except Exception as e:
                results.append({
                    "filename": doc.get("filename"),
                    "status": "failed",
                    "error": str(e)
                })

        return func.HttpResponse(
            json.dumps({
                "batch_id": f"batch-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                "total": len(documents),
                "results": results
            }),
            mimetype="application/json",
            status_code=202
        )

    except Exception as e:
        logging.error(f"Batch ingestion error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )


# Helper functions
def generate_document_id(filename: str, content: bytes) -> str:
    """Generate unique document ID based on filename and content hash"""
    content_hash = hashlib.sha256(content).hexdigest()[:12]
    return f"doc-{content_hash}"


def get_document_type(filename: str) -> str:
    """Determine document type from filename"""
    extension = filename.lower().split(".")[-1] if "." in filename else ""

    type_mapping = {
        "pdf": "pdf",
        "docx": "docx",
        "doc": "docx",
        "xlsx": "xlsx",
        "xls": "xlsx",
        "pptx": "pptx",
        "ppt": "pptx",
        "txt": "txt",
        "md": "md",
        "json": "json",
        "csv": "csv",
        "png": "image",
        "jpg": "image",
        "jpeg": "image",
        "gif": "image",
        "bmp": "image",
        "tiff": "image"
    }

    return type_mapping.get(extension, "unknown")


async def process_with_document_intelligence(
    content: bytes,
    document_id: str,
    filename: str,
    doc_type: str
) -> Dict[str, Any]:
    """
    Process document using Azure Document Intelligence (Form Recognizer)
    Extracts text, tables, and structure
    """
    logging.info(f"Processing {filename} with Document Intelligence")

    # TODO: Implement Document Intelligence API call
    # 1. Call Document Intelligence analyze endpoint
    # 2. Extract text, tables, key-value pairs
    # 3. Chunk the extracted content
    # 4. Generate embeddings
    # 5. Index in Azure AI Search
    # 6. Save metadata to Cosmos DB

    # Placeholder implementation
    extracted_text = "Placeholder extracted text"
    chunks = await chunk_text(extracted_text, document_id, filename)
    embeddings = await generate_embeddings(chunks)
    await index_chunks(chunks, embeddings, document_id)
    await save_document_metadata(document_id, filename, doc_type, len(chunks))

    return {
        "document_id": document_id,
        "filename": filename,
        "doc_type": doc_type,
        "status": "processed",
        "chunks_count": len(chunks),
        "timestamp": datetime.utcnow().isoformat()
    }


async def process_text_document(
    content: str,
    document_id: str,
    filename: str,
    doc_type: str
) -> Dict[str, Any]:
    """
    Process plain text documents
    """
    logging.info(f"Processing text document: {filename}")

    chunks = await chunk_text(content, document_id, filename)
    embeddings = await generate_embeddings(chunks)
    await index_chunks(chunks, embeddings, document_id)
    await save_document_metadata(document_id, filename, doc_type, len(chunks))

    return {
        "document_id": document_id,
        "filename": filename,
        "doc_type": doc_type,
        "status": "processed",
        "chunks_count": len(chunks),
        "timestamp": datetime.utcnow().isoformat()
    }


async def chunk_text(
    text: str,
    document_id: str,
    filename: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> List[Dict[str, Any]]:
    """
    Chunk text using semantic + sliding window approach
    Target chunk size: 700-1200 tokens for optimal retrieval
    """
    chunks = []

    # Simple sliding window chunking
    # TODO: Implement semantic chunking with sentence boundaries
    words = text.split()
    current_chunk = []
    current_size = 0

    for word in words:
        current_chunk.append(word)
        current_size += len(word) + 1

        if current_size >= chunk_size:
            chunk_text = " ".join(current_chunk)
            chunk_id = f"{document_id}-chunk-{len(chunks)}"

            chunks.append({
                "chunk_id": chunk_id,
                "document_id": document_id,
                "filename": filename,
                "content": chunk_text,
                "chunk_index": len(chunks),
                "char_count": len(chunk_text)
            })

            # Keep overlap
            overlap_words = current_chunk[-chunk_overlap // 10:] if len(current_chunk) > chunk_overlap // 10 else []
            current_chunk = overlap_words
            current_size = sum(len(w) + 1 for w in current_chunk)

    # Add remaining text as final chunk
    if current_chunk:
        chunk_text = " ".join(current_chunk)
        chunk_id = f"{document_id}-chunk-{len(chunks)}"

        chunks.append({
            "chunk_id": chunk_id,
            "document_id": document_id,
            "filename": filename,
            "content": chunk_text,
            "chunk_index": len(chunks),
            "char_count": len(chunk_text)
        })

    return chunks


async def generate_embeddings(chunks: List[Dict[str, Any]]) -> List[List[float]]:
    """
    Generate embeddings for all chunks using Azure OpenAI
    """
    # TODO: Implement batch embedding generation
    return [[0.0] * 3072 for _ in chunks]  # Placeholder - 3072 dimensions for text-embedding-3-large


async def index_chunks(
    chunks: List[Dict[str, Any]],
    embeddings: List[List[float]],
    document_id: str
) -> None:
    """
    Index chunks in Azure AI Search
    """
    # TODO: Implement Azure AI Search indexing
    logging.info(f"Indexed {len(chunks)} chunks for document {document_id}")


async def save_document_metadata(
    document_id: str,
    filename: str,
    doc_type: str,
    chunks_count: int
) -> None:
    """
    Save document metadata to Cosmos DB
    """
    # TODO: Implement Cosmos DB save
    logging.info(f"Saved metadata for document {document_id}")


@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint"""
    return func.HttpResponse(
        json.dumps({
            "status": "healthy",
            "service": "ingestion-pipeline",
            "timestamp": datetime.utcnow().isoformat()
        }),
        mimetype="application/json",
        status_code=200
    )
