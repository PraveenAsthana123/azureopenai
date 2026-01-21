"""
Document Ingestion Function - Azure Functions HTTP trigger.

Handles document upload, processing, chunking, and indexing.
"""

import azure.functions as func
import json
import logging
import os
import uuid
import hashlib
from datetime import datetime
from typing import Optional

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.search.documents import SearchClient
from azure.cosmos import CosmosClient
from openai import AzureOpenAI

logger = logging.getLogger(__name__)

# Initialize clients
credential = DefaultAzureCredential()

# Azure OpenAI client
aoai_client = AzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    azure_ad_token_provider=lambda: credential.get_token(
        "https://cognitiveservices.azure.com/.default"
    ).token,
    api_version="2024-02-15-preview"
)

# Azure Search client
search_client = SearchClient(
    endpoint=os.environ["AZURE_SEARCH_ENDPOINT"],
    index_name=os.environ.get("AZURE_SEARCH_INDEX", "rag-multimodal-index"),
    credential=credential
)

# Blob Storage client
blob_service = BlobServiceClient(
    account_url=os.environ["AZURE_STORAGE_ACCOUNT_URL"],
    credential=credential
)

# Cosmos DB client
cosmos_client = CosmosClient(
    url=os.environ["COSMOS_ENDPOINT"],
    credential=credential
)
cosmos_db = cosmos_client.get_database_client(os.environ.get("COSMOS_DATABASE", "rag_platform"))
documents_container = cosmos_db.get_container_client("documents")


async def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Document ingestion endpoint.

    POST /api/ingest
    Content-Type: multipart/form-data

    Fields:
    - file: The document file
    - metadata: JSON string with document metadata
    - category: Document category for partitioning
    """
    logger.info("Ingest request received")

    try:
        # Get file from request
        file = req.files.get("file")
        if not file:
            return func.HttpResponse(
                json.dumps({"error": "No file provided"}),
                status_code=400,
                mimetype="application/json"
            )

        # Get metadata
        metadata_str = req.form.get("metadata", "{}")
        metadata = json.loads(metadata_str)
        category = req.form.get("category", "general")

        # Read file content
        content = file.read()
        filename = file.filename
        content_type = file.content_type or "application/octet-stream"

        # Generate document ID
        doc_id = hashlib.sha256(content).hexdigest()[:16]

        # 1. Store original document in Blob Storage
        blob_path = await _store_blob(doc_id, filename, content, content_type)

        # 2. Extract text from document
        text_content = await _extract_text(content, content_type, filename)

        # 3. Chunk the text
        chunks = _chunk_text(text_content)

        # 4. Generate embeddings for chunks
        embeddings = await _generate_embeddings([c["text"] for c in chunks])

        # 5. Index chunks in Azure Search
        indexed_ids = await _index_chunks(
            doc_id=doc_id,
            chunks=chunks,
            embeddings=embeddings,
            metadata={
                **metadata,
                "filename": filename,
                "category": category,
                "blob_path": blob_path
            }
        )

        # 6. Store document metadata in Cosmos DB
        doc_record = {
            "id": doc_id,
            "filename": filename,
            "category": category,
            "content_type": content_type,
            "size_bytes": len(content),
            "blob_path": blob_path,
            "chunk_count": len(chunks),
            "chunk_ids": indexed_ids,
            "metadata": metadata,
            "created_at": datetime.utcnow().isoformat(),
            "status": "indexed"
        }

        documents_container.upsert_item(body=doc_record)

        # Response
        response = {
            "document_id": doc_id,
            "filename": filename,
            "chunks_created": len(chunks),
            "indexed_ids": indexed_ids,
            "blob_path": blob_path,
            "status": "success"
        }

        logger.info(f"Ingested document {doc_id}: {len(chunks)} chunks")

        return func.HttpResponse(
            json.dumps(response),
            status_code=201,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Ingest error: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


async def _store_blob(
    doc_id: str,
    filename: str,
    content: bytes,
    content_type: str
) -> str:
    """Store document in Blob Storage."""
    container_name = os.environ.get("BLOB_CONTAINER", "documents")
    container_client = blob_service.get_container_client(container_name)

    blob_path = f"{doc_id[:2]}/{doc_id}/{filename}"
    blob_client = container_client.get_blob_client(blob_path)

    blob_client.upload_blob(
        content,
        content_settings={"content_type": content_type},
        overwrite=True
    )

    return blob_path


async def _extract_text(
    content: bytes,
    content_type: str,
    filename: str
) -> str:
    """Extract text from document."""
    # Determine extraction method based on content type
    if content_type == "application/pdf" or filename.endswith(".pdf"):
        return _extract_pdf(content)
    elif content_type in [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ] or filename.endswith(".docx"):
        return _extract_docx(content)
    elif content_type == "text/plain" or filename.endswith(".txt"):
        return content.decode("utf-8")
    elif filename.endswith(".md"):
        return content.decode("utf-8")
    else:
        # Try as text
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError(f"Unsupported file type: {content_type}")


def _extract_pdf(content: bytes) -> str:
    """Extract text from PDF."""
    import io
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    text_parts = []

    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text)

    return "\n\n".join(text_parts)


def _extract_docx(content: bytes) -> str:
    """Extract text from DOCX."""
    import io
    from docx import Document

    doc = Document(io.BytesIO(content))
    text_parts = []

    for para in doc.paragraphs:
        if para.text.strip():
            text_parts.append(para.text)

    return "\n\n".join(text_parts)


def _chunk_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> list[dict]:
    """Split text into overlapping chunks."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    chunks = splitter.split_text(text)

    return [
        {
            "text": chunk,
            "index": i,
            "char_start": sum(len(c) for c in chunks[:i]),
            "char_end": sum(len(c) for c in chunks[:i+1])
        }
        for i, chunk in enumerate(chunks)
    ]


async def _generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for texts using Azure OpenAI."""
    embedding_deployment = os.environ.get("EMBEDDING_DEPLOYMENT", "text-embedding-3-large")

    # Batch embeddings (max 16 at a time for efficiency)
    embeddings = []
    batch_size = 16

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]

        response = aoai_client.embeddings.create(
            model=embedding_deployment,
            input=batch
        )

        for item in response.data:
            embeddings.append(item.embedding)

    return embeddings


async def _index_chunks(
    doc_id: str,
    chunks: list[dict],
    embeddings: list[list[float]],
    metadata: dict
) -> list[str]:
    """Index chunks in Azure AI Search."""
    documents = []

    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        chunk_id = f"{doc_id}_chunk_{i}"

        documents.append({
            "id": chunk_id,
            "document_id": doc_id,
            "content_text": chunk["text"],
            "content_vector": embedding,
            "chunk_index": i,
            "char_start": chunk["char_start"],
            "char_end": chunk["char_end"],
            "title": metadata.get("filename", "Untitled"),
            "category": metadata.get("category", "general"),
            "metadata": metadata,
            "created_at": datetime.utcnow().isoformat()
        })

    # Upload to search index
    result = search_client.upload_documents(documents=documents)

    return [doc["id"] for doc in documents]
