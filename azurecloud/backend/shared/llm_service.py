"""
LLM Service - Azure OpenAI Integration
Implements LLD Model Layer specifications
"""
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import os


class ModelType(Enum):
    """Available models as per LLD"""
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_5 = "gpt-5"  # Future
    EMBEDDING_LARGE = "text-embedding-3-large"
    EMBEDDING_SMALL = "text-embedding-3-small"


@dataclass
class ModelConfig:
    """Model configuration as per LLD"""
    model: ModelType
    temperature: float
    top_p: float
    max_tokens: int
    use_functions: bool
    use_structured_output: bool


# LLD-specified model configurations
MODEL_CONFIGS = {
    "rag_answer": ModelConfig(
        model=ModelType.GPT_4O,
        temperature=0.1,  # 0.0-0.2 for RAG
        top_p=0.5,        # 0.4-0.6
        max_tokens=2000,
        use_functions=True,
        use_structured_output=True
    ),
    "query_rewrite": ModelConfig(
        model=ModelType.GPT_4O_MINI,  # Cost-effective for simple tasks
        temperature=0.3,
        top_p=0.6,
        max_tokens=500,
        use_functions=False,
        use_structured_output=False
    ),
    "summarization": ModelConfig(
        model=ModelType.GPT_4O_MINI,
        temperature=0.2,
        top_p=0.5,
        max_tokens=1000,
        use_functions=False,
        use_structured_output=False
    ),
    "complex_reasoning": ModelConfig(
        model=ModelType.GPT_4O,  # Use GPT-5 when available
        temperature=0.1,
        top_p=0.4,
        max_tokens=4000,
        use_functions=True,
        use_structured_output=True
    )
}


# LLD Answer Schema
ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string",
            "description": "The grounded answer based on context"
        },
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "docId": {"type": "string"},
                    "page": {"type": "integer"},
                    "quote": {"type": "string"}
                },
                "required": ["docId"]
            }
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
        },
        "followups": {
            "type": "array",
            "items": {"type": "string"}
        },
        "reasoning": {
            "type": "string",
            "description": "Hidden chain-of-thought reasoning (not shown to user)"
        }
    },
    "required": ["answer", "citations", "confidence"]
}


# System prompt skeleton as per LLD
SYSTEM_PROMPT_TEMPLATE = """You are an enterprise AI assistant for {company_name}.

## Role and Task
- Answer questions ONLY from the provided context documents
- Cite sources for all factual claims using [Source: docId, page X] format
- If information is not in the context, clearly state "I don't have information about this in the provided documents"

## Guidelines
1. Be accurate and factual - never make up information
2. Be concise but complete
3. Use professional language appropriate for enterprise settings
4. Maintain security - never reveal sensitive information
5. For procedural questions, provide step-by-step answers

## Output Format
Respond in JSON format with the following structure:
- answer: Your grounded response
- citations: List of sources used (docId, page, quote)
- confidence: Your confidence score (0-1)
- followups: Suggested follow-up questions

## Context Documents
{context}

## Conversation History
{conversation_history}

Now answer the user's question based solely on the above context."""


class LLMService:
    """
    LLM Service implementing LLD specifications
    - Model routing (GPT-4o for complex, GPT-4o-mini for simple)
    - Temperature control for RAG
    - Structured outputs with JSON schema
    - Hidden Chain-of-Thought reasoning
    """

    def __init__(self, endpoint: str = None, api_key: str = None):
        self.endpoint = endpoint or os.environ.get("AZURE_OPENAI_ENDPOINT")
        self.api_key = api_key or os.environ.get("AZURE_OPENAI_KEY")
        self.api_version = "2024-02-01"

    async def generate_answer(
        self,
        query: str,
        context: List[Dict[str, Any]],
        conversation_history: List[Dict] = None,
        config_name: str = "rag_answer",
        company_name: str = "Enterprise"
    ) -> Dict[str, Any]:
        """
        Generate grounded answer using Azure OpenAI
        """
        config = MODEL_CONFIGS.get(config_name, MODEL_CONFIGS["rag_answer"])

        # Format context
        context_str = self._format_context(context)

        # Format conversation history
        history_str = self._format_history(conversation_history or [])

        # Build system prompt
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            company_name=company_name,
            context=context_str,
            conversation_history=history_str
        )

        # Build messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

        # Build request
        request_body = {
            "messages": messages,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "max_tokens": config.max_tokens,
        }

        # Add structured output if enabled
        if config.use_structured_output:
            request_body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "answer_response",
                    "strict": True,
                    "schema": ANSWER_SCHEMA
                }
            }

        # Make API call (placeholder - implement with actual Azure OpenAI SDK)
        response = await self._call_openai(config.model.value, request_body)

        return response

    async def generate_embedding(
        self,
        text: str,
        model: str = "text-embedding-3-large"
    ) -> List[float]:
        """
        Generate embedding vector for text
        """
        request_body = {
            "input": text,
            "model": model
        }

        # Make API call (placeholder)
        response = await self._call_embedding(model, request_body)

        return response.get("embedding", [])

    async def generate_embeddings_batch(
        self,
        texts: List[str],
        model: str = "text-embedding-3-large"
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch
        """
        request_body = {
            "input": texts,
            "model": model
        }

        response = await self._call_embedding(model, request_body)

        return response.get("embeddings", [])

    async def rewrite_query(
        self,
        query: str,
        conversation_history: List[Dict] = None
    ) -> str:
        """
        Rewrite query for better retrieval
        Uses GPT-4o-mini for cost efficiency
        """
        config = MODEL_CONFIGS["query_rewrite"]

        system_prompt = """You are a query rewriter. Your task is to:
1. Clarify ambiguous queries
2. Expand abbreviations
3. Resolve pronouns using conversation context
4. Make the query more specific for document retrieval

Output only the rewritten query, nothing else."""

        history_context = ""
        if conversation_history:
            history_context = "\n\nConversation context:\n" + self._format_history(conversation_history[-3:])

        messages = [
            {"role": "system", "content": system_prompt + history_context},
            {"role": "user", "content": f"Rewrite this query: {query}"}
        ]

        request_body = {
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }

        response = await self._call_openai(config.model.value, request_body)

        return response.get("content", query)

    async def summarize_chunk(
        self,
        chunk: str,
        max_length: int = 200
    ) -> str:
        """
        Summarize a chunk for context compression
        """
        config = MODEL_CONFIGS["summarization"]

        messages = [
            {
                "role": "system",
                "content": f"Summarize the following text in at most {max_length} words, preserving key facts:"
            },
            {"role": "user", "content": chunk}
        ]

        request_body = {
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }

        response = await self._call_openai(config.model.value, request_body)

        return response.get("content", chunk)

    def _format_context(self, context: List[Dict[str, Any]]) -> str:
        """Format context documents for prompt"""
        formatted = []

        for i, doc in enumerate(context, 1):
            doc_info = f"[Document {i}]"
            if doc.get("docId"):
                doc_info += f" ID: {doc['docId']}"
            if doc.get("page"):
                doc_info += f", Page: {doc['page']}"
            if doc.get("metadata", {}).get("department"):
                doc_info += f", Dept: {doc['metadata']['department']}"

            formatted.append(f"{doc_info}\n{doc.get('text', '')}")

        return "\n\n---\n\n".join(formatted)

    def _format_history(self, history: List[Dict]) -> str:
        """Format conversation history for prompt"""
        if not history:
            return "No previous conversation."

        formatted = []
        for msg in history:
            role = msg.get("role", "user").capitalize()
            content = msg.get("content", "")
            formatted.append(f"{role}: {content}")

        return "\n".join(formatted)

    async def _call_openai(self, model: str, request_body: Dict) -> Dict[str, Any]:
        """
        Call Azure OpenAI API
        Placeholder - implement with actual SDK
        """
        # In production, use:
        # from openai import AzureOpenAI
        # client = AzureOpenAI(azure_endpoint=self.endpoint, api_key=self.api_key, api_version=self.api_version)
        # response = client.chat.completions.create(model=model, **request_body)

        # Placeholder response
        return {
            "content": "This is a placeholder response. Implement Azure OpenAI SDK call.",
            "model": model,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        }

    async def _call_embedding(self, model: str, request_body: Dict) -> Dict[str, Any]:
        """
        Call Azure OpenAI Embeddings API
        Placeholder - implement with actual SDK
        """
        # Placeholder response
        return {
            "embedding": [0.0] * 3072,  # text-embedding-3-large dimensions
            "model": model
        }


class CacheService:
    """
    Cache service implementing LLD caching strategy:
    - Query cache: 15-30 min TTL
    - Retrieval cache: 30-60 min TTL
    - Embedding cache: 30 days TTL
    """

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.cache_configs = {
            "query": {"prefix": "q:", "ttl": 900},      # 15 min
            "retrieval": {"prefix": "r:", "ttl": 1800},  # 30 min
            "embedding": {"prefix": "emb:", "ttl": 2592000}  # 30 days
        }

    def _get_key(self, cache_type: str, key_data: str) -> str:
        """Generate cache key"""
        import hashlib
        config = self.cache_configs.get(cache_type, {"prefix": "default:"})
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:32]
        return f"{config['prefix']}{key_hash}"

    async def get_query_cache(self, query: str, filters: Dict) -> Optional[Dict]:
        """Get cached query result"""
        key_data = f"{query}:{json.dumps(filters, sort_keys=True)}"
        key = self._get_key("query", key_data)

        if self.redis:
            cached = await self.redis.get(key)
            if cached:
                return json.loads(cached)
        return None

    async def set_query_cache(self, query: str, filters: Dict, result: Dict) -> None:
        """Cache query result"""
        key_data = f"{query}:{json.dumps(filters, sort_keys=True)}"
        key = self._get_key("query", key_data)
        ttl = self.cache_configs["query"]["ttl"]

        if self.redis:
            await self.redis.setex(key, ttl, json.dumps(result))

    async def get_retrieval_cache(self, query: str, filters: Dict) -> Optional[List[str]]:
        """Get cached chunk IDs"""
        key_data = f"{query}:{json.dumps(filters, sort_keys=True)}"
        key = self._get_key("retrieval", key_data)

        if self.redis:
            cached = await self.redis.get(key)
            if cached:
                return json.loads(cached)
        return None

    async def set_retrieval_cache(self, query: str, filters: Dict, chunk_ids: List[str]) -> None:
        """Cache retrieved chunk IDs"""
        key_data = f"{query}:{json.dumps(filters, sort_keys=True)}"
        key = self._get_key("retrieval", key_data)
        ttl = self.cache_configs["retrieval"]["ttl"]

        if self.redis:
            await self.redis.setex(key, ttl, json.dumps(chunk_ids))

    async def get_embedding_cache(
        self,
        doc_id: str,
        chunk_hash: str,
        model_version: str
    ) -> Optional[List[float]]:
        """Get cached embedding"""
        key_data = f"{doc_id}:{chunk_hash}:{model_version}"
        key = self._get_key("embedding", key_data)

        if self.redis:
            cached = await self.redis.get(key)
            if cached:
                return json.loads(cached)
        return None

    async def set_embedding_cache(
        self,
        doc_id: str,
        chunk_hash: str,
        model_version: str,
        embedding: List[float]
    ) -> None:
        """Cache embedding"""
        key_data = f"{doc_id}:{chunk_hash}:{model_version}"
        key = self._get_key("embedding", key_data)
        ttl = self.cache_configs["embedding"]["ttl"]

        if self.redis:
            await self.redis.setex(key, ttl, json.dumps(embedding))

    async def invalidate_doc_cache(self, doc_id: str) -> None:
        """Invalidate all caches for a document (on doc update)"""
        if self.redis:
            # Find and delete all keys with this doc_id
            pattern = f"*:{doc_id}:*"
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
