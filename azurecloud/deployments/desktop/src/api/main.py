"""
Desktop RAG API - FastAPI application.

Local development server that can connect to:
- Local services (Ollama, ChromaDB, SQLite)
- Azure services (OpenAI, Search, Cosmos)
- Or a hybrid mix

Run with: uvicorn src.api.main:app --reload
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.settings import settings, DeploymentMode
from src.services.llm_service import create_llm_service, BaseLLMService
from src.services.vector_service import create_vector_service, BaseVectorService

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# =============================================================================
# Global Services
# =============================================================================

llm_service: Optional[BaseLLMService] = None
vector_service: Optional[BaseVectorService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global llm_service, vector_service

    logger.info(f"Starting RAG API in {settings.deployment_mode.value} mode")
    logger.info(f"LLM Provider: {settings.llm_provider.value}")
    logger.info(f"Vector DB: {settings.vector_db_provider.value}")

    # Initialize services
    llm_service = create_llm_service(settings)
    vector_service = create_vector_service(settings)

    # Health checks
    llm_ok = await llm_service.health_check()
    vector_ok = await vector_service.health_check()

    if not llm_ok:
        logger.warning(f"LLM service ({settings.llm_provider.value}) not available!")
    if not vector_ok:
        logger.warning(f"Vector service ({settings.vector_db_provider.value}) not available!")

    logger.info("RAG API started successfully")

    yield

    logger.info("Shutting down RAG API")


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="Desktop RAG API",
    description="Local RAG API with support for Ollama, ChromaDB, and Azure services",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Authentication (Optional)
# =============================================================================

async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify API key if configured."""
    if settings.api_key:
        if not x_api_key or x_api_key != settings.api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")
    return True


# =============================================================================
# Request/Response Models
# =============================================================================

class ChatRequest(BaseModel):
    """Chat request model."""
    question: str = Field(..., min_length=1, max_length=10000)
    session_id: Optional[str] = None
    user_id: str = "local-user"
    stream: bool = False
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=1000, ge=1, le=4000)


class ChatResponse(BaseModel):
    """Chat response model."""
    answer: str
    sources: list[dict]
    session_id: str
    model: str
    usage: dict


class DocumentRequest(BaseModel):
    """Document ingestion request."""
    content: str
    metadata: Optional[dict] = None
    id: Optional[str] = None


class SearchRequest(BaseModel):
    """Search request model."""
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    filter: Optional[dict] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    deployment_mode: str
    services: dict


# =============================================================================
# Endpoints
# =============================================================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "name": "Desktop RAG API",
        "version": "1.0.0",
        "mode": settings.deployment_mode.value,
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    llm_ok = await llm_service.health_check() if llm_service else False
    vector_ok = await vector_service.health_check() if vector_service else False

    return HealthResponse(
        status="healthy" if (llm_ok and vector_ok) else "degraded",
        deployment_mode=settings.deployment_mode.value,
        services={
            "llm": {
                "provider": settings.llm_provider.value,
                "status": "ok" if llm_ok else "unavailable"
            },
            "vector_db": {
                "provider": settings.vector_db_provider.value,
                "status": "ok" if vector_ok else "unavailable"
            }
        }
    )


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(
    request: ChatRequest,
    _: bool = Depends(verify_api_key)
):
    """
    Chat with the RAG system.

    Retrieves relevant documents and generates an answer.
    """
    import uuid

    session_id = request.session_id or str(uuid.uuid4())

    try:
        # 1. Generate query embedding
        query_embeddings = await llm_service.embed(request.question)
        query_embedding = query_embeddings[0]

        # 2. Search for relevant documents
        search_results = await vector_service.search(
            query_embedding=query_embedding,
            top_k=settings.top_k
        )

        # 3. Build context from search results
        context_parts = []
        sources = []

        for i, result in enumerate(search_results):
            if result.score >= settings.min_relevance_score:
                context_parts.append(f"[Source {i+1}]: {result.content}")
                sources.append({
                    "id": result.id,
                    "score": round(result.score, 4),
                    "metadata": result.metadata
                })

        context = "\n\n".join(context_parts) if context_parts else "No relevant documents found."

        # 4. Build prompt
        system_prompt = """You are a helpful assistant that answers questions based on the provided context.
Rules:
- Only use information from the provided sources
- Cite sources when making claims: [Source N]
- If information is not in the context, say so
- Be concise but complete"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {request.question}"}
        ]

        # 5. Generate response
        answer = await llm_service.chat(
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=request.stream
        )

        return ChatResponse(
            answer=answer,
            sources=sources,
            session_id=session_id,
            model=settings.llm_provider.value,
            usage={
                "sources_found": len(sources),
                "context_length": len(context)
            }
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents", tags=["Documents"])
async def add_document(
    request: DocumentRequest,
    _: bool = Depends(verify_api_key)
):
    """Add a document to the vector store."""
    try:
        # Generate embedding
        embeddings = await llm_service.embed(request.content)

        # Add to vector store
        doc = {
            "id": request.id,
            "content": request.content,
            "metadata": request.metadata or {}
        }

        ids = await vector_service.add_documents([doc], embeddings)

        return {"status": "success", "id": ids[0]}

    except Exception as e:
        logger.error(f"Document ingestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search", tags=["Search"])
async def search(
    request: SearchRequest,
    _: bool = Depends(verify_api_key)
):
    """Search the vector store."""
    try:
        # Generate query embedding
        embeddings = await llm_service.embed(request.query)

        # Search
        results = await vector_service.search(
            query_embedding=embeddings[0],
            top_k=request.top_k,
            filter=request.filter
        )

        return {
            "results": [
                {
                    "id": r.id,
                    "content": r.content[:500],  # Truncate for response
                    "metadata": r.metadata,
                    "score": round(r.score, 4)
                }
                for r in results
            ]
        }

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config", tags=["Config"])
async def get_config(_: bool = Depends(verify_api_key)):
    """Get current configuration (safe fields only)."""
    return {
        "deployment_mode": settings.deployment_mode.value,
        "llm_provider": settings.llm_provider.value,
        "vector_db_provider": settings.vector_db_provider.value,
        "database_provider": settings.database_provider.value,
        "storage_provider": settings.storage_provider.value,
        "chunk_size": settings.chunk_size,
        "top_k": settings.top_k
    }


@app.get("/models", tags=["Models"])
async def list_models(_: bool = Depends(verify_api_key)):
    """List available models (for Ollama)."""
    from src.services.llm_service import OllamaService

    if isinstance(llm_service, OllamaService):
        models = await llm_service.list_models()
        return {"models": models, "current": settings.ollama.model}

    return {"models": [], "current": settings.llm_provider.value}


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
