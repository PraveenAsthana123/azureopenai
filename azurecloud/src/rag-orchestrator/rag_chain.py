"""
Enterprise AI Platform - RAG Orchestrator with LangChain
Pre-retrieval, Retrieval, Post-retrieval, and Generation pipeline
"""

import os
import logging
import hashlib
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone

from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainFilter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class UserContext:
    """User context from JWT claims"""
    user_id: str
    user_name: str
    groups: List[str]
    business_unit: Optional[str] = None
    department: Optional[str] = None
    locale: str = "en"
    timezone: str = "UTC"


@dataclass
class QueryContext:
    """Full context for a RAG query"""
    query: str
    session_id: Optional[str] = None
    user: Optional[UserContext] = None
    conversation_history: List[Dict] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)
    intent: Optional[str] = None
    rewritten_query: Optional[str] = None


class IntentClassification(BaseModel):
    """Intent classification output"""
    intent: str = Field(description="Query intent: qa, summarize, action, translate, clarify")
    confidence: float = Field(description="Confidence score 0-1")
    entities: List[str] = Field(description="Extracted entities", default_factory=list)
    suggested_filters: Dict[str, Any] = Field(description="Suggested metadata filters", default_factory=dict)


class RewrittenQuery(BaseModel):
    """Query rewrite output"""
    original: str = Field(description="Original query")
    rewritten: str = Field(description="Rewritten query for retrieval")
    expanded_terms: List[str] = Field(description="Expanded search terms", default_factory=list)
    reasoning: str = Field(description="Why the query was rewritten")


class RetrievalResult(BaseModel):
    """Single retrieval result"""
    chunk_id: str
    document_id: str
    title: str
    chunk_text: str
    score: float
    rerank_score: Optional[float] = None
    heading_path: Optional[str] = None
    page_number: Optional[int] = None
    source_uri: Optional[str] = None


class RAGResponse(BaseModel):
    """Final RAG response"""
    answer: str
    citations: List[Dict[str, Any]]
    confidence: float
    grounding_score: float
    intent: str
    was_cached: bool = False
    model_used: str
    tokens_used: Dict[str, int]
    latency_ms: Dict[str, int]


# =============================================================================
# RAG ORCHESTRATOR
# =============================================================================

class RAGOrchestrator:
    """
    Enterprise RAG orchestrator with:
    - Intent classification
    - Query rewriting
    - ACL-aware retrieval
    - Semantic reranking
    - Grounded generation
    - Response caching
    """

    def __init__(
        self,
        azure_openai_endpoint: str,
        embedding_deployment: str = "text-embedding-3-large",
        chat_deployment: str = "gpt-4o",
        chat_fallback_deployment: str = "gpt-4o-mini",
        search_endpoint: str = None,
        search_index: str = "enterprise-knowledge-index",
        cosmos_endpoint: str = None
    ):
        self.azure_openai_endpoint = azure_openai_endpoint
        self.embedding_deployment = embedding_deployment
        self.chat_deployment = chat_deployment
        self.chat_fallback_deployment = chat_fallback_deployment
        self.search_endpoint = search_endpoint
        self.search_index = search_index
        self.cosmos_endpoint = cosmos_endpoint

        # Initialize LLM clients
        self._init_clients()

        # Build chains
        self._build_chains()

    def _init_clients(self):
        """Initialize Azure OpenAI clients"""
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider

        credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            credential,
            "https://cognitiveservices.azure.com/.default"
        )

        # Main chat model
        self.llm = AzureChatOpenAI(
            azure_endpoint=self.azure_openai_endpoint,
            azure_deployment=self.chat_deployment,
            azure_ad_token_provider=token_provider,
            api_version="2024-02-01",
            temperature=0.1,
            max_tokens=2000
        )

        # Fallback model (for 429 or cost optimization)
        self.llm_fallback = AzureChatOpenAI(
            azure_endpoint=self.azure_openai_endpoint,
            azure_deployment=self.chat_fallback_deployment,
            azure_ad_token_provider=token_provider,
            api_version="2024-02-01",
            temperature=0.1,
            max_tokens=2000
        )

        # Embeddings
        self.embeddings = AzureOpenAIEmbeddings(
            azure_endpoint=self.azure_openai_endpoint,
            azure_deployment=self.embedding_deployment,
            azure_ad_token_provider=token_provider,
            api_version="2024-02-01"
        )

    def _build_chains(self):
        """Build LangChain chains for each stage"""

        # Intent Classification Chain
        intent_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an intent classifier for an enterprise knowledge assistant.
Classify the user's query into one of these intents:
- qa: Question answering about documents/knowledge
- summarize: Summarization request
- action: Request to perform an action (create ticket, send email, etc.)
- translate: Translation request
- clarify: Query is unclear, needs clarification

Also extract relevant entities and suggest metadata filters.

Respond in JSON format matching the schema."""),
            ("human", "Query: {query}\n\nConversation context: {context}")
        ])

        self.intent_chain = (
            intent_prompt
            | self.llm.with_structured_output(IntentClassification)
        )

        # Query Rewrite Chain
        rewrite_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a query optimizer for enterprise search.
Rewrite the user's query to improve retrieval:
1. Expand acronyms commonly used in enterprise
2. Add synonyms for key terms
3. Normalize spelling and terminology
4. Make implicit context explicit
5. Handle conversational follow-ups using history

Keep the rewritten query concise but comprehensive."""),
            ("human", """Original query: {query}
Conversation history: {history}
User context: Business Unit={business_unit}, Department={department}

Provide the rewritten query in JSON format.""")
        ])

        self.rewrite_chain = (
            rewrite_prompt
            | self.llm.with_structured_output(RewrittenQuery)
        )

        # Generation Chain with Citations
        generation_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an enterprise knowledge assistant. Answer questions based ONLY on the provided context.

Rules:
1. Only use information from the provided context
2. If the context doesn't contain the answer, say so clearly
3. Cite sources using [1], [2], etc. format
4. Be concise but complete
5. If multiple sources agree, synthesize the information
6. Maintain professional tone

Context:
{context}

Sources:
{sources}"""),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{query}")
        ])

        self.generation_chain = (
            generation_prompt
            | self.llm
            | StrOutputParser()
        )

    async def process_query(
        self,
        query: str,
        user: UserContext,
        session_id: Optional[str] = None,
        conversation_history: List[Dict] = None,
        filters: Dict[str, Any] = None
    ) -> RAGResponse:
        """
        Main entry point for RAG query processing.

        Pipeline:
        1. Check cache
        2. Classify intent
        3. Rewrite query
        4. Apply ACL filters
        5. Retrieve chunks
        6. Rerank
        7. Generate response
        8. Cache result
        """
        import time
        start_time = time.time()
        latencies = {}

        ctx = QueryContext(
            query=query,
            session_id=session_id,
            user=user,
            conversation_history=conversation_history or [],
            filters=filters or {}
        )

        try:
            # Step 1: Check Cache
            cache_start = time.time()
            cached = await self._check_cache(ctx)
            latencies["cache_check"] = int((time.time() - cache_start) * 1000)

            if cached:
                cached["was_cached"] = True
                cached["latency_ms"] = latencies
                return RAGResponse(**cached)

            # Step 2: Intent Classification
            intent_start = time.time()
            intent_result = await self._classify_intent(ctx)
            ctx.intent = intent_result.intent
            latencies["intent"] = int((time.time() - intent_start) * 1000)

            # Handle non-QA intents
            if ctx.intent in ["action", "clarify"]:
                return await self._handle_non_qa_intent(ctx, intent_result, latencies)

            # Step 3: Query Rewriting
            rewrite_start = time.time()
            rewrite_result = await self._rewrite_query(ctx)
            ctx.rewritten_query = rewrite_result.rewritten
            latencies["rewrite"] = int((time.time() - rewrite_start) * 1000)

            # Step 4: Apply ACL Filters
            acl_filters = self._build_acl_filters(user)
            ctx.filters.update(acl_filters)

            # Step 5: Retrieval
            retrieval_start = time.time()
            chunks = await self._retrieve_chunks(ctx)
            latencies["retrieval"] = int((time.time() - retrieval_start) * 1000)

            if not chunks:
                return self._no_results_response(ctx, latencies)

            # Step 6: Reranking
            rerank_start = time.time()
            reranked_chunks = await self._rerank_chunks(ctx, chunks)
            latencies["rerank"] = int((time.time() - rerank_start) * 1000)

            # Step 7: Generation
            generation_start = time.time()
            response = await self._generate_response(ctx, reranked_chunks)
            latencies["generation"] = int((time.time() - generation_start) * 1000)

            # Step 8: Cache Result
            cache_start = time.time()
            await self._cache_response(ctx, response)
            latencies["cache_write"] = int((time.time() - cache_start) * 1000)

            latencies["total"] = int((time.time() - start_time) * 1000)
            response.latency_ms = latencies

            return response

        except Exception as e:
            logger.error(f"RAG pipeline error: {e}")
            latencies["total"] = int((time.time() - start_time) * 1000)
            return RAGResponse(
                answer=f"I encountered an error processing your request. Please try again.",
                citations=[],
                confidence=0.0,
                grounding_score=0.0,
                intent=ctx.intent or "error",
                was_cached=False,
                model_used=self.chat_deployment,
                tokens_used={"prompt": 0, "completion": 0},
                latency_ms=latencies
            )

    async def _check_cache(self, ctx: QueryContext) -> Optional[Dict]:
        """Check Cosmos DB cache for existing response"""
        if not self.cosmos_endpoint:
            return None

        try:
            from azure.cosmos.aio import CosmosClient
            from azure.identity.aio import DefaultAzureCredential

            query_hash = self._compute_query_hash(ctx)

            credential = DefaultAzureCredential()
            async with CosmosClient(self.cosmos_endpoint, credential=credential) as client:
                database = client.get_database_client("genai_platform")
                container = database.get_container_client("answer_cache")

                query = "SELECT * FROM c WHERE c.query_hash = @hash"
                params = [{"name": "@hash", "value": query_hash}]

                items = [item async for item in container.query_items(
                    query=query,
                    parameters=params
                )]

                if items:
                    item = items[0]
                    # Increment hit count
                    item["hit_count"] = item.get("hit_count", 0) + 1
                    item["last_hit_at"] = datetime.now(timezone.utc).isoformat()
                    await container.upsert_item(item)

                    return {
                        "answer": item["response"]["answer"],
                        "citations": item.get("citations", []),
                        "confidence": item["response"].get("confidence", 0.8),
                        "grounding_score": item.get("grounding_score", 0.8),
                        "intent": "qa",
                        "model_used": item["response"].get("model_used", self.chat_deployment),
                        "tokens_used": item.get("tokens_used", {})
                    }

            return None

        except Exception as e:
            logger.warning(f"Cache check failed: {e}")
            return None

    async def _classify_intent(self, ctx: QueryContext) -> IntentClassification:
        """Classify query intent"""
        context_str = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in ctx.conversation_history[-3:]  # Last 3 turns
        ]) if ctx.conversation_history else "No prior context"

        result = await self.intent_chain.ainvoke({
            "query": ctx.query,
            "context": context_str
        })

        logger.info(f"Intent: {result.intent} (confidence: {result.confidence})")
        return result

    async def _rewrite_query(self, ctx: QueryContext) -> RewrittenQuery:
        """Rewrite query for better retrieval"""
        history_str = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in ctx.conversation_history[-5:]
        ]) if ctx.conversation_history else "No history"

        result = await self.rewrite_chain.ainvoke({
            "query": ctx.query,
            "history": history_str,
            "business_unit": ctx.user.business_unit if ctx.user else "Unknown",
            "department": ctx.user.department if ctx.user else "Unknown"
        })

        logger.info(f"Query rewritten: {ctx.query} -> {result.rewritten}")
        return result

    def _build_acl_filters(self, user: UserContext) -> Dict[str, Any]:
        """Build ACL filters based on user's group memberships"""
        if not user or not user.groups:
            return {"acl_groups": ["public"]}

        return {
            "acl_groups": user.groups,
            "acl_deny_groups_not": user.groups  # Exclude denied groups
        }

    async def _retrieve_chunks(self, ctx: QueryContext, top_k: int = 10) -> List[RetrievalResult]:
        """Retrieve chunks from AI Search with hybrid search"""
        from azure.search.documents.aio import SearchClient
        from azure.search.documents.models import VectorizedQuery
        from azure.identity.aio import DefaultAzureCredential

        try:
            # Generate query embedding
            query_embedding = await self.embeddings.aembed_query(
                ctx.rewritten_query or ctx.query
            )

            credential = DefaultAzureCredential()
            async with SearchClient(
                endpoint=self.search_endpoint,
                index_name=self.search_index,
                credential=credential
            ) as client:
                # Build filter string
                filter_parts = []

                # ACL filter
                if ctx.filters.get("acl_groups"):
                    groups_filter = " or ".join([
                        f"acl_groups/any(g: g eq '{g}')"
                        for g in ctx.filters["acl_groups"]
                    ])
                    filter_parts.append(f"({groups_filter})")

                # Metadata filters
                if ctx.filters.get("business_unit"):
                    filter_parts.append(f"business_unit eq '{ctx.filters['business_unit']}'")
                if ctx.filters.get("doc_type"):
                    filter_parts.append(f"doc_type eq '{ctx.filters['doc_type']}'")
                if ctx.filters.get("status"):
                    filter_parts.append(f"status eq '{ctx.filters['status']}'")
                else:
                    filter_parts.append("status eq 'published'")

                filter_str = " and ".join(filter_parts) if filter_parts else None

                # Hybrid search (vector + keyword)
                vector_query = VectorizedQuery(
                    vector=query_embedding,
                    k_nearest_neighbors=top_k,
                    fields="chunk_vector"
                )

                results = await client.search(
                    search_text=ctx.rewritten_query or ctx.query,
                    vector_queries=[vector_query],
                    filter=filter_str,
                    select=["chunk_id", "document_id", "title", "chunk_text",
                            "heading_path", "page_number", "source_uri"],
                    top=top_k,
                    query_type="semantic",
                    semantic_configuration_name="semantic-config"
                )

                chunks = []
                async for result in results:
                    chunks.append(RetrievalResult(
                        chunk_id=result["chunk_id"],
                        document_id=result["document_id"],
                        title=result["title"],
                        chunk_text=result["chunk_text"],
                        score=result["@search.score"],
                        heading_path=result.get("heading_path"),
                        page_number=result.get("page_number"),
                        source_uri=result.get("source_uri")
                    ))

                logger.info(f"Retrieved {len(chunks)} chunks")
                return chunks

        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return []

    async def _rerank_chunks(
        self,
        ctx: QueryContext,
        chunks: List[RetrievalResult],
        top_k: int = 5
    ) -> List[RetrievalResult]:
        """Rerank chunks using LLM-based relevance scoring"""
        if not chunks:
            return []

        # Simple LLM-based reranking
        rerank_prompt = ChatPromptTemplate.from_messages([
            ("system", """Score the relevance of each passage to the query on a scale of 0-10.
Consider:
- Direct answer relevance
- Contextual relevance
- Information completeness
- Recency if applicable

Return JSON array with chunk_id and score."""),
            ("human", """Query: {query}

Passages:
{passages}

Return JSON: [{{"chunk_id": "...", "score": X}}, ...]""")
        ])

        passages_str = "\n\n".join([
            f"[{i+1}] ID: {c.chunk_id}\n{c.chunk_text[:500]}..."
            for i, c in enumerate(chunks[:10])  # Limit to top 10 for reranking
        ])

        try:
            response = await self.llm.ainvoke(
                rerank_prompt.format(query=ctx.query, passages=passages_str)
            )

            import json
            scores = json.loads(response.content)
            score_map = {s["chunk_id"]: s["score"] for s in scores}

            # Apply rerank scores
            for chunk in chunks:
                chunk.rerank_score = score_map.get(chunk.chunk_id, chunk.score)

            # Sort by rerank score and return top_k
            reranked = sorted(chunks, key=lambda x: x.rerank_score or 0, reverse=True)
            return reranked[:top_k]

        except Exception as e:
            logger.warning(f"Reranking failed, using original order: {e}")
            return chunks[:top_k]

    async def _generate_response(
        self,
        ctx: QueryContext,
        chunks: List[RetrievalResult]
    ) -> RAGResponse:
        """Generate grounded response with citations"""

        # Build context
        context_parts = []
        sources = []
        for i, chunk in enumerate(chunks):
            context_parts.append(f"[{i+1}] {chunk.chunk_text}")
            sources.append(f"[{i+1}] {chunk.title} (p.{chunk.page_number or '?'})")

        context_str = "\n\n".join(context_parts)
        sources_str = "\n".join(sources)

        # Build conversation history for prompt
        history_messages = []
        for msg in ctx.conversation_history[-4:]:
            if msg["role"] == "user":
                history_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                history_messages.append(AIMessage(content=msg["content"]))

        try:
            response = await self.generation_chain.ainvoke({
                "context": context_str,
                "sources": sources_str,
                "history": history_messages,
                "query": ctx.query
            })

            # Build citations
            citations = []
            for i, chunk in enumerate(chunks):
                if f"[{i+1}]" in response:
                    citations.append({
                        "index": i + 1,
                        "document_id": chunk.document_id,
                        "title": chunk.title,
                        "chunk_id": chunk.chunk_id,
                        "excerpt": chunk.chunk_text[:200] + "...",
                        "page": chunk.page_number,
                        "source_uri": chunk.source_uri,
                        "score": chunk.rerank_score or chunk.score
                    })

            # Compute grounding score (simplified)
            grounding_score = min(1.0, len(citations) / max(len(chunks), 1))

            return RAGResponse(
                answer=response,
                citations=citations,
                confidence=0.85 if citations else 0.5,
                grounding_score=grounding_score,
                intent=ctx.intent or "qa",
                was_cached=False,
                model_used=self.chat_deployment,
                tokens_used={"prompt": 0, "completion": 0},  # Would come from callback
                latency_ms={}
            )

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise

    async def _cache_response(self, ctx: QueryContext, response: RAGResponse):
        """Cache response in Cosmos DB"""
        if not self.cosmos_endpoint:
            return

        try:
            from azure.cosmos.aio import CosmosClient
            from azure.identity.aio import DefaultAzureCredential

            query_hash = self._compute_query_hash(ctx)

            cache_doc = {
                "id": query_hash,
                "query_hash": query_hash,
                "query_normalized": ctx.rewritten_query or ctx.query,
                "query_original": ctx.query,
                "filters_hash": hashlib.sha256(
                    str(ctx.filters).encode()
                ).hexdigest()[:16],
                "filters": ctx.filters,
                "response": {
                    "answer": response.answer,
                    "confidence": response.confidence,
                    "model_used": response.model_used
                },
                "citations": response.citations,
                "grounding_score": response.grounding_score,
                "tokens_used": response.tokens_used,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "hit_count": 0,
                "ttl": 3600  # 1 hour
            }

            credential = DefaultAzureCredential()
            async with CosmosClient(self.cosmos_endpoint, credential=credential) as client:
                database = client.get_database_client("genai_platform")
                container = database.get_container_client("answer_cache")
                await container.upsert_item(cache_doc)

            logger.info(f"Cached response for query hash {query_hash[:16]}...")

        except Exception as e:
            logger.warning(f"Cache write failed: {e}")

    def _compute_query_hash(self, ctx: QueryContext) -> str:
        """Compute deterministic hash for query + filters"""
        normalized = (ctx.rewritten_query or ctx.query).lower().strip()
        filter_str = str(sorted(ctx.filters.items()))
        combined = f"{normalized}|{filter_str}"
        return hashlib.sha256(combined.encode()).hexdigest()

    async def _handle_non_qa_intent(
        self,
        ctx: QueryContext,
        intent: IntentClassification,
        latencies: Dict[str, int]
    ) -> RAGResponse:
        """Handle action/clarify intents"""
        if intent.intent == "clarify":
            return RAGResponse(
                answer="I'm not sure I understand your question. Could you please rephrase or provide more context?",
                citations=[],
                confidence=0.3,
                grounding_score=0.0,
                intent="clarify",
                was_cached=False,
                model_used=self.chat_deployment,
                tokens_used={"prompt": 0, "completion": 0},
                latency_ms=latencies
            )
        elif intent.intent == "action":
            return RAGResponse(
                answer="I can help you with that action. Let me route this to the appropriate tool.",
                citations=[],
                confidence=0.7,
                grounding_score=0.0,
                intent="action",
                was_cached=False,
                model_used=self.chat_deployment,
                tokens_used={"prompt": 0, "completion": 0},
                latency_ms=latencies
            )
        else:
            return self._no_results_response(ctx, latencies)

    def _no_results_response(self, ctx: QueryContext, latencies: Dict[str, int]) -> RAGResponse:
        """Response when no relevant documents found"""
        return RAGResponse(
            answer="I couldn't find any relevant information in the knowledge base to answer your question. Please try rephrasing or contact support for assistance.",
            citations=[],
            confidence=0.2,
            grounding_score=0.0,
            intent=ctx.intent or "qa",
            was_cached=False,
            model_used=self.chat_deployment,
            tokens_used={"prompt": 0, "completion": 0},
            latency_ms=latencies
        )
