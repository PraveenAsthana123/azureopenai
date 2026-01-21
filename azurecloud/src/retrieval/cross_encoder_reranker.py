"""
Cross-Encoder Reranker Implementation

Implements:
- LLM-based cross-encoder reranking
- Batch processing for efficiency
- Score normalization
- Anti-hallucination scoring
- Configurable reranking strategies
"""

from dataclasses import dataclass, field
from typing import Any
from enum import Enum
import asyncio
import json
from datetime import datetime

from openai import AsyncAzureOpenAI


class RerankStrategy(Enum):
    """Reranking strategy options."""
    RELEVANCE_ONLY = "relevance_only"
    RELEVANCE_WITH_SUPPORT = "relevance_with_support"
    FULL_ANALYSIS = "full_analysis"


@dataclass
class RerankConfig:
    """Configuration for reranking."""
    strategy: RerankStrategy = RerankStrategy.RELEVANCE_WITH_SUPPORT
    model: str = "gpt-4o-mini"
    batch_size: int = 10
    max_chunks_to_rerank: int = 30
    final_top_k: int = 8
    temperature: float = 0.0

    # Score combination weights
    relevance_weight: float = 0.6
    support_weight: float = 0.3
    original_score_weight: float = 0.1

    # Thresholds
    min_relevance_score: float = 0.3
    min_support_score: float = 0.2


@dataclass
class ChunkScore:
    """Scores for a single chunk."""
    chunk_id: str
    relevance_score: float
    support_score: float | None = None
    reasoning: str | None = None
    has_explicit_evidence: bool = False
    combined_score: float = 0.0


@dataclass
class RerankResult:
    """Result of reranking operation."""
    chunks: list[Any]  # RetrievedChunk with updated scores
    scores: list[ChunkScore]
    rerank_time_ms: float
    model_used: str
    strategy_used: RerankStrategy


class CrossEncoderReranker:
    """
    LLM-based cross-encoder reranker.

    Uses GPT-4o-mini to score query-chunk relevance with:
    - Relevance scoring (0-3 scale)
    - Evidence support scoring
    - Explicit evidence detection
    """

    RELEVANCE_PROMPT = """You are an expert at judging relevance between a question and a text passage.

Rate the relevance of the passage to answering the question.

Scoring guide:
- 0: Not relevant at all, completely off-topic
- 1: Tangentially related but doesn't help answer the question
- 2: Somewhat relevant, provides partial or indirect information
- 3: Highly relevant, directly helps answer the question

Question: {query}

Passage:
{content}

Respond with ONLY a JSON object:
{{"score": <0-3>, "reasoning": "<brief explanation>"}}"""

    SUPPORT_PROMPT = """You are an expert at evaluating whether a passage provides explicit evidence to answer a question.

Evaluate whether this passage contains EXPLICIT information that directly supports answering the question.
Do NOT give credit for implicit or inferred information.

Question: {query}

Passage:
{content}

Respond with ONLY a JSON object:
{{
  "support_score": <0.0-1.0>,
  "has_explicit_evidence": <true/false>,
  "evidence_quote": "<direct quote if explicit evidence exists, null otherwise>"
}}"""

    FULL_ANALYSIS_PROMPT = """You are an expert at evaluating document relevance for retrieval-augmented generation.

Analyze the passage's value for answering the given question.

Question: {query}

Passage:
{content}

Consider:
1. Direct relevance to the question
2. Presence of explicit supporting evidence
3. Completeness of information provided
4. Whether the passage could lead to hallucination if used (vague or tangential info)

Respond with ONLY a JSON object:
{{
  "relevance_score": <0-3>,
  "support_score": <0.0-1.0>,
  "has_explicit_evidence": <true/false>,
  "hallucination_risk": <"low"|"medium"|"high">,
  "reasoning": "<brief explanation>"
}}"""

    def __init__(
        self,
        openai_client: AsyncAzureOpenAI,
        config: RerankConfig | None = None,
    ):
        self.client = openai_client
        self.config = config or RerankConfig()

    async def rerank(
        self,
        query: str,
        chunks: list[Any],  # RetrievedChunk
        override_config: RerankConfig | None = None,
    ) -> RerankResult:
        """
        Rerank chunks using cross-encoder scoring.

        Args:
            query: User's search query
            chunks: List of RetrievedChunk to rerank
            override_config: Optional config override

        Returns:
            RerankResult with reordered chunks
        """
        start_time = datetime.utcnow()
        config = override_config or self.config

        # Limit chunks to rerank
        chunks_to_rerank = chunks[:config.max_chunks_to_rerank]

        # Score chunks in batches
        all_scores = await self._score_batches(
            query=query,
            chunks=chunks_to_rerank,
            config=config,
        )

        # Calculate combined scores
        for score in all_scores:
            score.combined_score = self._calculate_combined_score(score, config)

        # Create chunk_id -> score mapping
        score_map = {s.chunk_id: s for s in all_scores}

        # Update chunk scores and filter
        scored_chunks = []
        for chunk in chunks_to_rerank:
            if chunk.id in score_map:
                score = score_map[chunk.id]

                # Skip chunks below threshold
                if score.relevance_score / 3.0 < config.min_relevance_score:
                    continue

                # Update chunk's final score
                chunk.final_score = score.combined_score
                chunk.rerank_score = score.relevance_score
                chunk.support_score = score.support_score
                chunk.rerank_reasoning = score.reasoning

                scored_chunks.append(chunk)

        # Sort by combined score
        scored_chunks.sort(key=lambda c: c.final_score, reverse=True)

        # Take top-k
        final_chunks = scored_chunks[:config.final_top_k]

        # Calculate timing
        end_time = datetime.utcnow()
        rerank_time_ms = (end_time - start_time).total_seconds() * 1000

        return RerankResult(
            chunks=final_chunks,
            scores=all_scores,
            rerank_time_ms=rerank_time_ms,
            model_used=config.model,
            strategy_used=config.strategy,
        )

    async def _score_batches(
        self,
        query: str,
        chunks: list[Any],
        config: RerankConfig,
    ) -> list[ChunkScore]:
        """Score chunks in batches for efficiency."""
        all_scores = []

        # Process in batches
        for i in range(0, len(chunks), config.batch_size):
            batch = chunks[i:i + config.batch_size]

            # Score batch in parallel
            tasks = [
                self._score_single_chunk(query, chunk, config)
                for chunk in batch
            ]
            batch_scores = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle results
            for chunk, score_result in zip(batch, batch_scores):
                if isinstance(score_result, Exception):
                    # Default score on error
                    all_scores.append(ChunkScore(
                        chunk_id=chunk.id,
                        relevance_score=1.0,  # Neutral score
                        support_score=0.5,
                        reasoning=f"Scoring error: {str(score_result)}",
                    ))
                else:
                    all_scores.append(score_result)

        return all_scores

    async def _score_single_chunk(
        self,
        query: str,
        chunk: Any,
        config: RerankConfig,
    ) -> ChunkScore:
        """Score a single chunk based on strategy."""
        content = chunk.content_md or chunk.content

        # Truncate very long content
        if len(content) > 4000:
            content = content[:4000] + "..."

        if config.strategy == RerankStrategy.RELEVANCE_ONLY:
            return await self._score_relevance_only(query, content, chunk.id, config)

        elif config.strategy == RerankStrategy.RELEVANCE_WITH_SUPPORT:
            return await self._score_with_support(query, content, chunk.id, config)

        else:  # FULL_ANALYSIS
            return await self._score_full_analysis(query, content, chunk.id, config)

    async def _score_relevance_only(
        self,
        query: str,
        content: str,
        chunk_id: str,
        config: RerankConfig,
    ) -> ChunkScore:
        """Simple relevance scoring."""
        prompt = self.RELEVANCE_PROMPT.format(query=query, content=content)

        response = await self.client.chat.completions.create(
            model=config.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=config.temperature,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)

        return ChunkScore(
            chunk_id=chunk_id,
            relevance_score=float(result.get("score", 1)),
            reasoning=result.get("reasoning"),
        )

    async def _score_with_support(
        self,
        query: str,
        content: str,
        chunk_id: str,
        config: RerankConfig,
    ) -> ChunkScore:
        """Score relevance and evidence support."""
        # Run both prompts in parallel
        relevance_task = self._call_llm(
            self.RELEVANCE_PROMPT.format(query=query, content=content),
            config,
        )
        support_task = self._call_llm(
            self.SUPPORT_PROMPT.format(query=query, content=content),
            config,
        )

        relevance_result, support_result = await asyncio.gather(
            relevance_task, support_task
        )

        return ChunkScore(
            chunk_id=chunk_id,
            relevance_score=float(relevance_result.get("score", 1)),
            support_score=float(support_result.get("support_score", 0.5)),
            has_explicit_evidence=support_result.get("has_explicit_evidence", False),
            reasoning=relevance_result.get("reasoning"),
        )

    async def _score_full_analysis(
        self,
        query: str,
        content: str,
        chunk_id: str,
        config: RerankConfig,
    ) -> ChunkScore:
        """Full analysis with hallucination risk."""
        prompt = self.FULL_ANALYSIS_PROMPT.format(query=query, content=content)
        result = await self._call_llm(prompt, config)

        # Adjust score based on hallucination risk
        relevance = float(result.get("relevance_score", 1))
        hallucination_risk = result.get("hallucination_risk", "medium")

        # Penalize high hallucination risk
        if hallucination_risk == "high":
            relevance *= 0.7
        elif hallucination_risk == "medium":
            relevance *= 0.9

        return ChunkScore(
            chunk_id=chunk_id,
            relevance_score=relevance,
            support_score=float(result.get("support_score", 0.5)),
            has_explicit_evidence=result.get("has_explicit_evidence", False),
            reasoning=result.get("reasoning"),
        )

    async def _call_llm(self, prompt: str, config: RerankConfig) -> dict:
        """Make LLM call and parse JSON response."""
        try:
            response = await self.client.chat.completions.create(
                model=config.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=config.temperature,
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            return {}
        except Exception:
            return {}

    def _calculate_combined_score(
        self,
        score: ChunkScore,
        config: RerankConfig,
    ) -> float:
        """Calculate weighted combined score."""
        # Normalize relevance to 0-1
        relevance_normalized = score.relevance_score / 3.0

        # Support score is already 0-1
        support = score.support_score or 0.5

        # Weighted combination
        combined = (
            relevance_normalized * config.relevance_weight +
            support * config.support_weight
        )

        # Bonus for explicit evidence
        if score.has_explicit_evidence:
            combined *= 1.1

        return min(combined, 1.0)


class TableAwareReranker(CrossEncoderReranker):
    """
    Specialized reranker for table chunks.

    Uses table-specific prompts and scoring.
    """

    TABLE_RELEVANCE_PROMPT = """You are an expert at judging whether a table contains relevant data for answering a question.

Question: {query}

Table (in markdown format):
{content}

Table headers: {headers}

Consider:
1. Do the column headers relate to the question?
2. Does the table contain data that could answer the question?
3. Is this the right granularity of data (e.g., daily vs monthly)?

Score 0-3:
- 0: Table is completely unrelated
- 1: Table topic is related but data doesn't help
- 2: Table contains some relevant data
- 3: Table directly contains the answer

Respond with ONLY a JSON object:
{{"score": <0-3>, "relevant_columns": [<list of relevant column names>], "reasoning": "<brief explanation>"}}"""

    async def rerank_tables(
        self,
        query: str,
        table_chunks: list[Any],
        config: RerankConfig | None = None,
    ) -> RerankResult:
        """Rerank table chunks with table-aware scoring."""
        config = config or self.config
        start_time = datetime.utcnow()

        all_scores = []

        for chunk in table_chunks[:config.max_chunks_to_rerank]:
            content = chunk.content_md or chunk.content
            headers = ", ".join(chunk.table_headers or [])

            prompt = self.TABLE_RELEVANCE_PROMPT.format(
                query=query,
                content=content[:4000],
                headers=headers,
            )

            try:
                result = await self._call_llm(prompt, config)

                score = ChunkScore(
                    chunk_id=chunk.id,
                    relevance_score=float(result.get("score", 1)),
                    reasoning=result.get("reasoning"),
                )

                # Boost if headers match
                relevant_cols = result.get("relevant_columns", [])
                if relevant_cols:
                    score.relevance_score *= 1.2

            except Exception as e:
                score = ChunkScore(
                    chunk_id=chunk.id,
                    relevance_score=1.0,
                    reasoning=f"Error: {str(e)}",
                )

            score.combined_score = score.relevance_score / 3.0
            all_scores.append(score)

        # Update chunks and sort
        score_map = {s.chunk_id: s for s in all_scores}
        scored_chunks = []

        for chunk in table_chunks:
            if chunk.id in score_map:
                score = score_map[chunk.id]
                chunk.final_score = score.combined_score
                chunk.rerank_score = score.relevance_score
                scored_chunks.append(chunk)

        scored_chunks.sort(key=lambda c: c.final_score, reverse=True)

        end_time = datetime.utcnow()

        return RerankResult(
            chunks=scored_chunks[:config.final_top_k],
            scores=all_scores,
            rerank_time_ms=(end_time - start_time).total_seconds() * 1000,
            model_used=config.model,
            strategy_used=RerankStrategy.RELEVANCE_ONLY,
        )
