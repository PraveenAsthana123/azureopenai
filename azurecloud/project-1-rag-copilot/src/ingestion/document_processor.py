"""
Document Ingestion Pipeline - Durable Functions Orchestrator
=============================================================
Processes documents through OCR, chunking, embedding, and indexing
"""

import azure.functions as func
import azure.durable_functions as df
import logging
import json
import os
from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch
)
from openai import AzureOpenAI
import tiktoken

logger = logging.getLogger(__name__)

# ==============================================================================
# Configuration
# ==============================================================================

class Config:
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
    DOCUMENT_INTELLIGENCE_ENDPOINT = os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT")
    STORAGE_ACCOUNT_URL = os.getenv("STORAGE_ACCOUNT_URL")

    EMBEDDING_MODEL = "text-embedding-ada-002"
    SEARCH_INDEX = "documents-index"

    # Chunking parameters
    CHUNK_SIZE = 1000  # tokens
    CHUNK_OVERLAP = 200  # tokens


class DocumentType(Enum):
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"
    TXT = "txt"
    HTML = "html"


@dataclass
class DocumentChunk:
    """Represents a chunk of document content."""
    chunk_id: str
    document_id: str
    content: str
    title: str
    source: str
    page: int
    chunk_index: int
    token_count: int
    embedding: List[float] = None


# ==============================================================================
# Durable Functions App
# ==============================================================================

app = df.DFApp(http_auth_level=func.AuthLevel.FUNCTION)


# ==============================================================================
# Orchestrator Function
# ==============================================================================

@app.orchestration_trigger(context_name="context")
def document_processing_orchestrator(context: df.DurableOrchestrationContext):
    """
    Main orchestrator for document processing pipeline.

    Pipeline Steps:
    1. Download document from blob storage
    2. Extract text using Document Intelligence
    3. Chunk the document
    4. Generate embeddings for each chunk
    5. Index chunks in Azure AI Search
    """

    # Get input parameters
    input_data = context.get_input()
    blob_url = input_data["blob_url"]
    document_id = input_data["document_id"]

    logger.info(f"Starting document processing for: {document_id}")

    try:
        # Step 1: Download and analyze document
        extraction_result = yield context.call_activity(
            "ExtractDocumentContent",
            {"blob_url": blob_url, "document_id": document_id}
        )

        if not extraction_result["success"]:
            return {
                "status": "failed",
                "error": extraction_result["error"],
                "document_id": document_id
            }

        # Step 2: Chunk the document
        chunks = yield context.call_activity(
            "ChunkDocument",
            {
                "content": extraction_result["content"],
                "metadata": extraction_result["metadata"],
                "document_id": document_id
            }
        )

        # Step 3: Generate embeddings (fan-out pattern for parallelization)
        embedding_tasks = []
        for chunk_batch in batch_chunks(chunks, batch_size=10):
            embedding_tasks.append(
                context.call_activity("GenerateEmbeddings", chunk_batch)
            )

        embedded_chunks = yield context.task_all(embedding_tasks)

        # Flatten results
        all_embedded_chunks = []
        for batch_result in embedded_chunks:
            all_embedded_chunks.extend(batch_result)

        # Step 4: Index in Azure AI Search
        index_result = yield context.call_activity(
            "IndexDocuments",
            {"chunks": all_embedded_chunks, "document_id": document_id}
        )

        # Step 5: Update document status in metadata store
        yield context.call_activity(
            "UpdateDocumentStatus",
            {
                "document_id": document_id,
                "status": "indexed",
                "chunk_count": len(all_embedded_chunks),
                "index_result": index_result
            }
        )

        return {
            "status": "success",
            "document_id": document_id,
            "chunks_processed": len(all_embedded_chunks),
            "index_result": index_result
        }

    except Exception as e:
        logger.error(f"Orchestration failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "document_id": document_id
        }


def batch_chunks(chunks: List[Dict], batch_size: int = 10) -> List[List[Dict]]:
    """Split chunks into batches for parallel processing."""
    return [chunks[i:i + batch_size] for i in range(0, len(chunks), batch_size)]


# ==============================================================================
# Activity Functions
# ==============================================================================

@app.activity_trigger(input_name="input")
def ExtractDocumentContent(input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract text content from document using Azure Document Intelligence.

    Supports: PDF, DOCX, XLSX, PPTX, images with text
    """
    blob_url = input["blob_url"]
    document_id = input["document_id"]

    try:
        credential = DefaultAzureCredential()

        # Initialize Document Intelligence client
        doc_client = DocumentAnalysisClient(
            endpoint=Config.DOCUMENT_INTELLIGENCE_ENDPOINT,
            credential=credential
        )

        # Analyze document
        poller = doc_client.begin_analyze_document_from_url(
            model_id="prebuilt-layout",
            document_url=blob_url
        )
        result = poller.result()

        # Extract content by page
        pages_content = []
        for page_num, page in enumerate(result.pages, 1):
            page_text = ""

            # Extract text from lines
            for line in page.lines:
                page_text += line.content + "\n"

            pages_content.append({
                "page": page_num,
                "content": page_text.strip(),
                "tables": []
            })

        # Extract tables
        for table in result.tables:
            table_data = []
            current_row = []
            current_row_index = 0

            for cell in table.cells:
                if cell.row_index != current_row_index:
                    if current_row:
                        table_data.append(current_row)
                    current_row = []
                    current_row_index = cell.row_index
                current_row.append(cell.content)

            if current_row:
                table_data.append(current_row)

            # Find which page this table belongs to
            if table.bounding_regions:
                page_num = table.bounding_regions[0].page_number
                pages_content[page_num - 1]["tables"].append(table_data)

        # Combine all content
        full_content = ""
        for page in pages_content:
            full_content += f"\n--- Page {page['page']} ---\n"
            full_content += page["content"]

            for table in page["tables"]:
                full_content += "\n[TABLE]\n"
                for row in table:
                    full_content += " | ".join(row) + "\n"
                full_content += "[/TABLE]\n"

        # Extract document metadata
        metadata = {
            "title": extract_title_from_content(full_content),
            "source": blob_url.split("/")[-1],
            "page_count": len(result.pages),
            "document_id": document_id
        }

        return {
            "success": True,
            "content": full_content,
            "pages": pages_content,
            "metadata": metadata
        }

    except Exception as e:
        logger.error(f"Document extraction failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def extract_title_from_content(content: str) -> str:
    """Extract document title from first few lines."""
    lines = content.strip().split("\n")
    for line in lines[:5]:
        line = line.strip()
        if line and not line.startswith("---") and len(line) > 5:
            return line[:100]
    return "Untitled Document"


@app.activity_trigger(input_name="input")
def ChunkDocument(input: Dict[str, Any]) -> List[Dict]:
    """
    Split document content into overlapping chunks.

    Uses token-based chunking with configurable size and overlap.
    """
    content = input["content"]
    metadata = input["metadata"]
    document_id = input["document_id"]

    # Initialize tokenizer
    encoding = tiktoken.get_encoding("cl100k_base")

    chunks = []

    # Split by pages first, then by paragraphs
    pages = content.split("--- Page ")

    for page_section in pages:
        if not page_section.strip():
            continue

        # Extract page number
        try:
            page_num = int(page_section.split(" ---")[0])
            page_content = page_section.split(" ---\n", 1)[1] if " ---\n" in page_section else page_section
        except (ValueError, IndexError):
            page_num = 1
            page_content = page_section

        # Split into paragraphs
        paragraphs = page_content.split("\n\n")

        current_chunk = ""
        current_tokens = 0
        chunk_index = 0

        for para in paragraphs:
            para_tokens = len(encoding.encode(para))

            # If adding this paragraph exceeds chunk size
            if current_tokens + para_tokens > Config.CHUNK_SIZE and current_chunk:
                # Save current chunk
                chunks.append({
                    "chunk_id": f"{document_id}_p{page_num}_c{chunk_index}",
                    "document_id": document_id,
                    "content": current_chunk.strip(),
                    "title": metadata["title"],
                    "source": metadata["source"],
                    "page": page_num,
                    "chunk_index": chunk_index,
                    "token_count": current_tokens
                })

                # Start new chunk with overlap
                overlap_text = get_overlap_text(current_chunk, Config.CHUNK_OVERLAP, encoding)
                current_chunk = overlap_text + "\n\n" + para
                current_tokens = len(encoding.encode(current_chunk))
                chunk_index += 1
            else:
                current_chunk += "\n\n" + para if current_chunk else para
                current_tokens += para_tokens

        # Save last chunk
        if current_chunk.strip():
            chunks.append({
                "chunk_id": f"{document_id}_p{page_num}_c{chunk_index}",
                "document_id": document_id,
                "content": current_chunk.strip(),
                "title": metadata["title"],
                "source": metadata["source"],
                "page": page_num,
                "chunk_index": chunk_index,
                "token_count": current_tokens
            })

    logger.info(f"Created {len(chunks)} chunks for document {document_id}")
    return chunks


def get_overlap_text(text: str, overlap_tokens: int, encoding) -> str:
    """Get the last N tokens of text for overlap."""
    tokens = encoding.encode(text)
    if len(tokens) <= overlap_tokens:
        return text
    overlap_tokens_list = tokens[-overlap_tokens:]
    return encoding.decode(overlap_tokens_list)


@app.activity_trigger(input_name="chunks")
def GenerateEmbeddings(chunks: List[Dict]) -> List[Dict]:
    """
    Generate embeddings for document chunks using Azure OpenAI.
    """
    credential = DefaultAzureCredential()

    client = AzureOpenAI(
        azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
        azure_ad_token_provider=lambda: credential.get_token(
            "https://cognitiveservices.azure.com/.default"
        ).token,
        api_version="2024-06-01"
    )

    # Extract texts for batch embedding
    texts = [chunk["content"] for chunk in chunks]

    # Generate embeddings in batch
    response = client.embeddings.create(
        input=texts,
        model=Config.EMBEDDING_MODEL
    )

    # Add embeddings to chunks
    for i, embedding_data in enumerate(response.data):
        chunks[i]["embedding"] = embedding_data.embedding

    return chunks


@app.activity_trigger(input_name="input")
def IndexDocuments(input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Index document chunks in Azure AI Search.
    """
    chunks = input["chunks"]
    document_id = input["document_id"]

    credential = DefaultAzureCredential()

    # Ensure index exists
    ensure_search_index_exists(credential)

    # Initialize search client
    search_client = SearchClient(
        endpoint=Config.AZURE_SEARCH_ENDPOINT,
        index_name=Config.SEARCH_INDEX,
        credential=credential
    )

    # Prepare documents for indexing
    documents = []
    for chunk in chunks:
        documents.append({
            "id": chunk["chunk_id"],
            "documentId": chunk["document_id"],
            "content": chunk["content"],
            "title": chunk["title"],
            "source": chunk["source"],
            "page": chunk["page"],
            "chunkIndex": chunk["chunk_index"],
            "contentVector": chunk["embedding"]
        })

    # Upload documents in batches
    batch_size = 100
    indexed_count = 0

    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        result = search_client.upload_documents(documents=batch)
        indexed_count += len([r for r in result if r.succeeded])

    logger.info(f"Indexed {indexed_count}/{len(documents)} chunks for document {document_id}")

    return {
        "indexed_count": indexed_count,
        "total_chunks": len(documents),
        "success": indexed_count == len(documents)
    }


def ensure_search_index_exists(credential):
    """Create search index if it doesn't exist."""
    index_client = SearchIndexClient(
        endpoint=Config.AZURE_SEARCH_ENDPOINT,
        credential=credential
    )

    # Check if index exists
    try:
        index_client.get_index(Config.SEARCH_INDEX)
        return  # Index exists
    except Exception:
        pass  # Index doesn't exist, create it

    # Define index schema
    fields = [
        SearchField(name="id", type=SearchFieldDataType.String, key=True),
        SearchField(name="documentId", type=SearchFieldDataType.String, filterable=True),
        SearchField(name="content", type=SearchFieldDataType.String, searchable=True),
        SearchField(name="title", type=SearchFieldDataType.String, searchable=True, filterable=True),
        SearchField(name="source", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchField(name="page", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
        SearchField(name="chunkIndex", type=SearchFieldDataType.Int32, sortable=True),
        SearchField(
            name="contentVector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,
            vector_search_profile_name="vector-profile"
        )
    ]

    # Vector search configuration
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(name="hnsw-config")
        ],
        profiles=[
            VectorSearchProfile(
                name="vector-profile",
                algorithm_configuration_name="hnsw-config"
            )
        ]
    )

    # Semantic configuration
    semantic_config = SemanticConfiguration(
        name="default-semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="title"),
            content_fields=[SemanticField(field_name="content")]
        )
    )

    semantic_search = SemanticSearch(configurations=[semantic_config])

    # Create index
    index = SearchIndex(
        name=Config.SEARCH_INDEX,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search
    )

    index_client.create_index(index)
    logger.info(f"Created search index: {Config.SEARCH_INDEX}")


@app.activity_trigger(input_name="input")
def UpdateDocumentStatus(input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update document processing status in metadata store.
    """
    # This would typically update a metadata record in Cosmos DB
    # to track document processing status

    document_id = input["document_id"]
    status = input["status"]
    chunk_count = input["chunk_count"]

    logger.info(f"Document {document_id} status updated to {status} with {chunk_count} chunks")

    return {
        "document_id": document_id,
        "status": status,
        "chunk_count": chunk_count
    }


# ==============================================================================
# HTTP Starter Function
# ==============================================================================

@app.route(route="ingest", methods=["POST"])
@app.durable_client_input(client_name="client")
async def start_document_ingestion(req: func.HttpRequest, client) -> func.HttpResponse:
    """
    HTTP endpoint to start document ingestion.

    Request Body:
    {
        "blob_url": "https://storage.blob.core.windows.net/documents/doc.pdf",
        "document_id": "unique-document-id"
    }
    """
    try:
        req_body = req.get_json()
        blob_url = req_body.get("blob_url")
        document_id = req_body.get("document_id")

        if not blob_url or not document_id:
            return func.HttpResponse(
                json.dumps({"error": "blob_url and document_id are required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Start orchestration
        instance_id = await client.start_new(
            "document_processing_orchestrator",
            client_input={
                "blob_url": blob_url,
                "document_id": document_id
            }
        )

        return func.HttpResponse(
            json.dumps({
                "instance_id": instance_id,
                "status_query_url": f"/api/ingest/status/{instance_id}"
            }),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Failed to start ingestion: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="ingest/status/{instance_id}", methods=["GET"])
@app.durable_client_input(client_name="client")
async def get_ingestion_status(req: func.HttpRequest, client) -> func.HttpResponse:
    """Get status of document ingestion job."""
    instance_id = req.route_params.get("instance_id")

    status = await client.get_status(instance_id)

    if not status:
        return func.HttpResponse(
            json.dumps({"error": "Instance not found"}),
            status_code=404,
            mimetype="application/json"
        )

    return func.HttpResponse(
        json.dumps({
            "instance_id": instance_id,
            "runtime_status": status.runtime_status.name,
            "output": status.output,
            "created_time": status.created_time.isoformat() if status.created_time else None,
            "last_updated_time": status.last_updated_time.isoformat() if status.last_updated_time else None
        }),
        mimetype="application/json"
    )
