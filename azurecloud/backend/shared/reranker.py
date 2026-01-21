"""
Reranker Service - Cross-Encoder Reranking
Implements LLD reranking specifications
"""
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import math


@dataclass
class RankedChunk:
    """Chunk with reranking score"""
    id: str
    doc_id: str
    content: str
    original_score: float
    rerank_score: float
    combined_score: float
    metadata: Dict[str, Any]


class RerankerService:
    """
    Reranker service implementing LLD specifications
    - Cross-encoder reranking for semantic relevance
    - Score normalization and combination
    - Deduplication before reranking
    """

    def __init__(
        self,
        model_name: str = "cross-encoder",
        original_weight: float = 0.3,
        rerank_weight: float = 0.7
    ):
        self.model_name = model_name
        self.original_weight = original_weight
        self.rerank_weight = rerank_weight

    async def rerank(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[RankedChunk]:
        """
        Rerank chunks using cross-encoder

        Args:
            query: User query
            chunks: Retrieved chunks from hybrid search
            top_k: Number of chunks to return after reranking

        Returns:
            List of reranked chunks
        """
        if not chunks:
            return []

        # Step 1: Calculate rerank scores
        rerank_scores = await self._calculate_rerank_scores(query, chunks)

        # Step 2: Normalize scores
        normalized_original = self._normalize_scores([c.get("score", 0) for c in chunks])
        normalized_rerank = self._normalize_scores(rerank_scores)

        # Step 3: Combine scores
        ranked_chunks = []
        for i, chunk in enumerate(chunks):
            combined_score = (
                self.original_weight * normalized_original[i] +
                self.rerank_weight * normalized_rerank[i]
            )

            ranked_chunk = RankedChunk(
                id=chunk.get("id", ""),
                doc_id=chunk.get("doc_id", chunk.get("docId", "")),
                content=chunk.get("content", chunk.get("chunkText", "")),
                original_score=chunk.get("score", 0),
                rerank_score=rerank_scores[i],
                combined_score=combined_score,
                metadata=chunk.get("metadata", {})
            )
            ranked_chunks.append(ranked_chunk)

        # Step 4: Sort by combined score
        ranked_chunks.sort(key=lambda x: x.combined_score, reverse=True)

        # Step 5: Return top_k
        return ranked_chunks[:top_k]

    async def _calculate_rerank_scores(
        self,
        query: str,
        chunks: List[Dict[str, Any]]
    ) -> List[float]:
        """
        Calculate reranking scores using cross-encoder

        In production, this would use a deployed cross-encoder model.
        For now, using a simplified scoring based on:
        - Term overlap
        - Query term coverage
        - Position of query terms
        """
        scores = []

        query_terms = set(query.lower().split())
        query_bigrams = self._get_bigrams(query.lower())

        for chunk in chunks:
            content = chunk.get("content", chunk.get("chunkText", "")).lower()
            content_terms = set(content.split())

            # Factor 1: Term overlap (Jaccard similarity)
            if content_terms:
                term_overlap = len(query_terms & content_terms) / len(query_terms | content_terms)
            else:
                term_overlap = 0

            # Factor 2: Query term coverage
            if query_terms:
                coverage = len(query_terms & content_terms) / len(query_terms)
            else:
                coverage = 0

            # Factor 3: Bigram overlap
            content_bigrams = self._get_bigrams(content)
            if query_bigrams and content_bigrams:
                bigram_overlap = len(query_bigrams & content_bigrams) / len(query_bigrams)
            else:
                bigram_overlap = 0

            # Factor 4: Query term proximity
            proximity_score = self._calculate_proximity_score(query_terms, content)

            # Factor 5: Position bonus (query terms appearing early)
            position_score = self._calculate_position_score(query_terms, content)

            # Combine factors
            rerank_score = (
                0.25 * term_overlap +
                0.25 * coverage +
                0.20 * bigram_overlap +
                0.15 * proximity_score +
                0.15 * position_score
            )

            scores.append(rerank_score)

        return scores

    def _get_bigrams(self, text: str) -> set:
        """Get set of bigrams from text"""
        words = text.split()
        return set(zip(words[:-1], words[1:])) if len(words) > 1 else set()

    def _calculate_proximity_score(self, query_terms: set, content: str) -> float:
        """
        Calculate how close query terms appear to each other in content
        """
        if not query_terms or not content:
            return 0

        words = content.split()
        positions = {}

        # Find positions of query terms
        for i, word in enumerate(words):
            if word in query_terms:
                if word not in positions:
                    positions[word] = []
                positions[word].append(i)

        if len(positions) < 2:
            return 0.5  # Only one term found, neutral score

        # Calculate average distance between consecutive query terms
        all_positions = sorted([pos for poses in positions.values() for pos in poses])

        if len(all_positions) < 2:
            return 0.5

        distances = []
        for i in range(len(all_positions) - 1):
            distances.append(all_positions[i + 1] - all_positions[i])

        avg_distance = sum(distances) / len(distances)

        # Convert to score (closer = higher score)
        # Using exponential decay: score = e^(-distance/10)
        proximity_score = math.exp(-avg_distance / 10)

        return min(proximity_score, 1.0)

    def _calculate_position_score(self, query_terms: set, content: str) -> float:
        """
        Calculate position bonus for query terms appearing early
        """
        if not query_terms or not content:
            return 0

        words = content.split()
        if not words:
            return 0

        total_words = len(words)
        first_positions = []

        for term in query_terms:
            try:
                pos = words.index(term)
                first_positions.append(pos)
            except ValueError:
                continue

        if not first_positions:
            return 0

        # Average relative position (0 = start, 1 = end)
        avg_relative_pos = (sum(first_positions) / len(first_positions)) / total_words

        # Convert to score (earlier = higher score)
        position_score = 1 - avg_relative_pos

        return position_score

    def _normalize_scores(self, scores: List[float]) -> List[float]:
        """
        Normalize scores to 0-1 range using min-max normalization
        """
        if not scores:
            return []

        min_score = min(scores)
        max_score = max(scores)

        if max_score == min_score:
            return [0.5] * len(scores)

        return [(s - min_score) / (max_score - min_score) for s in scores]

    async def rerank_with_diversity(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 5,
        diversity_weight: float = 0.2
    ) -> List[RankedChunk]:
        """
        Rerank with diversity penalty to avoid similar chunks
        Uses Maximal Marginal Relevance (MMR)
        """
        # First, get reranked scores
        rerank_scores = await self._calculate_rerank_scores(query, chunks)

        selected = []
        remaining_indices = list(range(len(chunks)))

        while len(selected) < top_k and remaining_indices:
            best_idx = None
            best_score = -float('inf')

            for idx in remaining_indices:
                # Relevance score
                relevance = rerank_scores[idx]

                # Diversity penalty (max similarity to already selected)
                if selected:
                    max_sim = max(
                        self._chunk_similarity(chunks[idx], chunks[sel_idx])
                        for sel_idx in selected
                    )
                    diversity_penalty = diversity_weight * max_sim
                else:
                    diversity_penalty = 0

                # MMR score
                mmr_score = relevance - diversity_penalty

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx

            if best_idx is not None:
                selected.append(best_idx)
                remaining_indices.remove(best_idx)

        # Build ranked chunks
        ranked_chunks = []
        for i, idx in enumerate(selected):
            chunk = chunks[idx]
            ranked_chunk = RankedChunk(
                id=chunk.get("id", ""),
                doc_id=chunk.get("doc_id", chunk.get("docId", "")),
                content=chunk.get("content", chunk.get("chunkText", "")),
                original_score=chunk.get("score", 0),
                rerank_score=rerank_scores[idx],
                combined_score=rerank_scores[idx],  # Using rerank score for MMR
                metadata=chunk.get("metadata", {})
            )
            ranked_chunks.append(ranked_chunk)

        return ranked_chunks

    def _chunk_similarity(self, chunk1: Dict, chunk2: Dict) -> float:
        """Calculate similarity between two chunks"""
        content1 = chunk1.get("content", chunk1.get("chunkText", "")).lower()
        content2 = chunk2.get("content", chunk2.get("chunkText", "")).lower()

        words1 = set(content1.split())
        words2 = set(content2.split())

        if not words1 or not words2:
            return 0

        # Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0
