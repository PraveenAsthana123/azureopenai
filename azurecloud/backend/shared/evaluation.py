"""
Evaluation and Testing Framework
Implements LLD Testing & Evaluation specifications
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import hashlib


class EvalMetric(Enum):
    """Evaluation metrics as per LLD"""
    GROUNDEDNESS = "groundedness"
    RELEVANCE = "relevance"
    COHERENCE = "coherence"
    FLUENCY = "fluency"
    CITATION_ACCURACY = "citation_accuracy"
    HALLUCINATION_RATE = "hallucination_rate"
    RETRIEVAL_PRECISION = "retrieval_precision"
    RETRIEVAL_RECALL = "retrieval_recall"
    LATENCY = "latency"
    TOKEN_EFFICIENCY = "token_efficiency"


@dataclass
class EvalResult:
    """Result of a single evaluation"""
    metric: EvalMetric
    score: float
    max_score: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestCase:
    """A test case for RAG evaluation"""
    id: str
    query: str
    expected_answer: str
    expected_sources: List[str]
    expected_citations: List[Dict[str, Any]]
    category: str  # "factual", "procedural", "comparative", etc.
    difficulty: str  # "easy", "medium", "hard"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """Result of running a test case"""
    test_case_id: str
    passed: bool
    actual_answer: str
    actual_sources: List[str]
    eval_results: List[EvalResult]
    latency_ms: float
    tokens_used: int
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class RAGEvaluator:
    """
    RAG Evaluation Framework
    Implements groundedness, relevance, coherence metrics
    """

    def __init__(self, llm_client=None, thresholds: Dict[str, float] = None):
        self.llm_client = llm_client
        self.thresholds = thresholds or {
            EvalMetric.GROUNDEDNESS: 0.8,
            EvalMetric.RELEVANCE: 0.7,
            EvalMetric.COHERENCE: 0.7,
            EvalMetric.CITATION_ACCURACY: 0.9,
            EvalMetric.HALLUCINATION_RATE: 0.1,  # Max acceptable
            EvalMetric.RETRIEVAL_PRECISION: 0.7,
            EvalMetric.RETRIEVAL_RECALL: 0.6
        }

    async def evaluate_response(
        self,
        query: str,
        answer: str,
        context: List[Dict[str, Any]],
        citations: List[Dict[str, Any]],
        expected: Optional[TestCase] = None
    ) -> List[EvalResult]:
        """
        Comprehensive evaluation of a RAG response

        Args:
            query: User query
            answer: Generated answer
            context: Retrieved context chunks
            citations: Citations in the answer
            expected: Expected test case (if available)

        Returns:
            List of evaluation results
        """
        results = []

        # Groundedness evaluation
        groundedness = await self._evaluate_groundedness(answer, context)
        results.append(groundedness)

        # Relevance evaluation
        relevance = await self._evaluate_relevance(query, answer)
        results.append(relevance)

        # Coherence evaluation
        coherence = await self._evaluate_coherence(answer)
        results.append(coherence)

        # Citation accuracy
        citation_accuracy = self._evaluate_citation_accuracy(citations, context)
        results.append(citation_accuracy)

        # Hallucination detection
        hallucination = await self._detect_hallucination(answer, context)
        results.append(hallucination)

        # If expected answer is provided, evaluate against it
        if expected:
            retrieval_precision = self._evaluate_retrieval_precision(
                [c.get("docId") for c in context],
                expected.expected_sources
            )
            results.append(retrieval_precision)

            retrieval_recall = self._evaluate_retrieval_recall(
                [c.get("docId") for c in context],
                expected.expected_sources
            )
            results.append(retrieval_recall)

        return results

    async def _evaluate_groundedness(
        self,
        answer: str,
        context: List[Dict[str, Any]]
    ) -> EvalResult:
        """
        Evaluate how well the answer is grounded in context
        Score: 0-1 (1 = fully grounded)
        """
        if not context:
            return EvalResult(
                metric=EvalMetric.GROUNDEDNESS,
                score=0.0,
                max_score=1.0,
                details={"reason": "No context provided"}
            )

        # Extract all context text
        context_text = " ".join([
            c.get("text", c.get("content", ""))
            for c in context
        ]).lower()

        # Split answer into sentences/claims
        answer_sentences = self._split_into_claims(answer)

        grounded_count = 0
        claim_details = []

        for sentence in answer_sentences:
            # Check if sentence content exists in context
            sentence_words = set(sentence.lower().split())
            context_words = set(context_text.split())

            # Calculate overlap
            if sentence_words:
                overlap = len(sentence_words & context_words) / len(sentence_words)
                is_grounded = overlap > 0.5

                claim_details.append({
                    "claim": sentence[:100],
                    "grounded": is_grounded,
                    "overlap_score": overlap
                })

                if is_grounded:
                    grounded_count += 1

        score = grounded_count / len(answer_sentences) if answer_sentences else 0

        return EvalResult(
            metric=EvalMetric.GROUNDEDNESS,
            score=round(score, 2),
            max_score=1.0,
            details={
                "claims_analyzed": len(answer_sentences),
                "claims_grounded": grounded_count,
                "claim_details": claim_details[:5]  # First 5
            }
        )

    async def _evaluate_relevance(
        self,
        query: str,
        answer: str
    ) -> EvalResult:
        """
        Evaluate how relevant the answer is to the query
        """
        query_terms = set(query.lower().split())
        answer_terms = set(answer.lower().split())

        # Remove stop words (simplified)
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "what", "how", "why", "when", "where", "who"}
        query_terms -= stop_words
        answer_terms -= stop_words

        if not query_terms:
            return EvalResult(
                metric=EvalMetric.RELEVANCE,
                score=0.5,
                max_score=1.0,
                details={"reason": "Empty query after processing"}
            )

        # Calculate coverage of query terms in answer
        coverage = len(query_terms & answer_terms) / len(query_terms)

        # Check for direct question answering
        question_words = {"what", "how", "why", "when", "where", "who"}
        is_question = bool(query_terms & question_words)

        # Bonus for answers that start with relevant info
        answer_start = answer[:200].lower()
        start_relevance = len(query_terms & set(answer_start.split())) / len(query_terms)

        # Combined score
        score = 0.6 * coverage + 0.4 * start_relevance

        return EvalResult(
            metric=EvalMetric.RELEVANCE,
            score=round(min(score, 1.0), 2),
            max_score=1.0,
            details={
                "query_term_coverage": round(coverage, 2),
                "start_relevance": round(start_relevance, 2),
                "is_question": is_question
            }
        )

    async def _evaluate_coherence(self, answer: str) -> EvalResult:
        """
        Evaluate coherence and fluency of the answer
        """
        sentences = self._split_into_claims(answer)

        if len(sentences) < 2:
            return EvalResult(
                metric=EvalMetric.COHERENCE,
                score=0.8,  # Short answers are usually coherent
                max_score=1.0,
                details={"reason": "Answer too short to evaluate transitions"}
            )

        # Check for transition indicators
        transition_words = {
            "however", "therefore", "moreover", "additionally", "furthermore",
            "in addition", "on the other hand", "as a result", "consequently",
            "first", "second", "third", "finally", "also", "then", "next"
        }

        answer_lower = answer.lower()
        transition_count = sum(1 for word in transition_words if word in answer_lower)

        # Check for repetition (incoherence indicator)
        sentence_hashes = [hash(s.lower()) for s in sentences]
        unique_sentences = len(set(sentence_hashes))
        repetition_ratio = unique_sentences / len(sentences)

        # Calculate coherence score
        transition_score = min(transition_count / (len(sentences) / 2), 1.0)
        coherence_score = 0.6 * repetition_ratio + 0.4 * transition_score

        return EvalResult(
            metric=EvalMetric.COHERENCE,
            score=round(coherence_score, 2),
            max_score=1.0,
            details={
                "sentence_count": len(sentences),
                "transition_count": transition_count,
                "repetition_ratio": round(repetition_ratio, 2)
            }
        )

    def _evaluate_citation_accuracy(
        self,
        citations: List[Dict[str, Any]],
        context: List[Dict[str, Any]]
    ) -> EvalResult:
        """
        Evaluate accuracy of citations
        """
        if not citations:
            return EvalResult(
                metric=EvalMetric.CITATION_ACCURACY,
                score=0.0,
                max_score=1.0,
                details={"reason": "No citations provided"}
            )

        context_doc_ids = {c.get("docId", c.get("doc_id", "")) for c in context}
        valid_citations = 0
        citation_details = []

        for citation in citations:
            doc_id = citation.get("docId", citation.get("doc_id", ""))
            is_valid = doc_id in context_doc_ids

            citation_details.append({
                "docId": doc_id,
                "valid": is_valid
            })

            if is_valid:
                valid_citations += 1

        score = valid_citations / len(citations)

        return EvalResult(
            metric=EvalMetric.CITATION_ACCURACY,
            score=round(score, 2),
            max_score=1.0,
            details={
                "total_citations": len(citations),
                "valid_citations": valid_citations,
                "citation_details": citation_details
            }
        )

    async def _detect_hallucination(
        self,
        answer: str,
        context: List[Dict[str, Any]]
    ) -> EvalResult:
        """
        Detect potential hallucinations in the answer
        Returns hallucination rate (lower is better)
        """
        context_text = " ".join([
            c.get("text", c.get("content", ""))
            for c in context
        ]).lower()

        # Extract factual claims (simplified: sentences with numbers, dates, names)
        claims = self._extract_factual_claims(answer)

        if not claims:
            return EvalResult(
                metric=EvalMetric.HALLUCINATION_RATE,
                score=0.0,
                max_score=1.0,
                details={"reason": "No factual claims detected"}
            )

        hallucinated_count = 0
        hallucination_details = []

        for claim in claims:
            # Check if claim is supported by context
            claim_lower = claim.lower()
            is_supported = any(
                word in context_text
                for word in claim_lower.split()
                if len(word) > 4  # Skip short words
            )

            if not is_supported:
                hallucinated_count += 1
                hallucination_details.append({
                    "claim": claim[:100],
                    "supported": False
                })

        hallucination_rate = hallucinated_count / len(claims)

        return EvalResult(
            metric=EvalMetric.HALLUCINATION_RATE,
            score=round(hallucination_rate, 2),
            max_score=1.0,  # Lower is better, threshold is max acceptable
            details={
                "total_claims": len(claims),
                "hallucinated_claims": hallucinated_count,
                "details": hallucination_details[:5]
            }
        )

    def _evaluate_retrieval_precision(
        self,
        retrieved_docs: List[str],
        expected_docs: List[str]
    ) -> EvalResult:
        """
        Precision: What fraction of retrieved docs are relevant?
        """
        if not retrieved_docs:
            return EvalResult(
                metric=EvalMetric.RETRIEVAL_PRECISION,
                score=0.0,
                max_score=1.0,
                details={"reason": "No documents retrieved"}
            )

        retrieved_set = set(retrieved_docs)
        expected_set = set(expected_docs)

        relevant_retrieved = len(retrieved_set & expected_set)
        precision = relevant_retrieved / len(retrieved_set)

        return EvalResult(
            metric=EvalMetric.RETRIEVAL_PRECISION,
            score=round(precision, 2),
            max_score=1.0,
            details={
                "retrieved_count": len(retrieved_docs),
                "relevant_count": relevant_retrieved
            }
        )

    def _evaluate_retrieval_recall(
        self,
        retrieved_docs: List[str],
        expected_docs: List[str]
    ) -> EvalResult:
        """
        Recall: What fraction of relevant docs were retrieved?
        """
        if not expected_docs:
            return EvalResult(
                metric=EvalMetric.RETRIEVAL_RECALL,
                score=1.0,
                max_score=1.0,
                details={"reason": "No expected documents"}
            )

        retrieved_set = set(retrieved_docs)
        expected_set = set(expected_docs)

        relevant_retrieved = len(retrieved_set & expected_set)
        recall = relevant_retrieved / len(expected_set)

        return EvalResult(
            metric=EvalMetric.RETRIEVAL_RECALL,
            score=round(recall, 2),
            max_score=1.0,
            details={
                "expected_count": len(expected_docs),
                "retrieved_relevant": relevant_retrieved
            }
        )

    def _split_into_claims(self, text: str) -> List[str]:
        """Split text into individual claims/sentences"""
        import re
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]

    def _extract_factual_claims(self, text: str) -> List[str]:
        """Extract sentences that contain factual claims"""
        import re
        sentences = self._split_into_claims(text)

        factual_patterns = [
            r'\d+',  # Numbers
            r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\b',
            r'\b\d{4}\b',  # Years
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # Proper nouns
        ]

        factual_claims = []
        for sentence in sentences:
            for pattern in factual_patterns:
                if re.search(pattern, sentence):
                    factual_claims.append(sentence)
                    break

        return factual_claims

    def check_release_gate(self, results: List[EvalResult]) -> Tuple[bool, List[str]]:
        """
        Check if evaluation results pass release gate
        As per LLD: Block deployment if groundedness < threshold

        Returns:
            (passed: bool, failure_reasons: List[str])
        """
        failures = []

        for result in results:
            threshold = self.thresholds.get(result.metric)
            if threshold is None:
                continue

            if result.metric == EvalMetric.HALLUCINATION_RATE:
                # For hallucination, lower is better
                if result.score > threshold:
                    failures.append(
                        f"{result.metric.value}: {result.score:.2f} > max {threshold:.2f}"
                    )
            else:
                # For other metrics, higher is better
                if result.score < threshold:
                    failures.append(
                        f"{result.metric.value}: {result.score:.2f} < min {threshold:.2f}"
                    )

        return (len(failures) == 0, failures)


class PromptRegressionTester:
    """
    Prompt regression testing
    Compares outputs against golden outputs stored in Git
    """

    def __init__(self, golden_outputs_path: str = None):
        self.golden_outputs_path = golden_outputs_path or "tests/golden_outputs"
        self.golden_outputs: Dict[str, Dict] = {}

    def load_golden_outputs(self) -> None:
        """Load golden outputs from storage"""
        # In production, load from Git/storage
        pass

    def add_golden_output(
        self,
        test_id: str,
        query: str,
        expected_output: str,
        model_version: str
    ) -> None:
        """Add a golden output for regression testing"""
        self.golden_outputs[test_id] = {
            "query": query,
            "expected_output": expected_output,
            "model_version": model_version,
            "created_at": datetime.utcnow().isoformat()
        }

    def check_regression(
        self,
        test_id: str,
        actual_output: str,
        similarity_threshold: float = 0.8
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if actual output regresses from golden output

        Returns:
            (passed: bool, details: Dict)
        """
        golden = self.golden_outputs.get(test_id)
        if not golden:
            return True, {"reason": "No golden output for comparison"}

        expected = golden["expected_output"]

        # Calculate similarity
        similarity = self._calculate_similarity(expected, actual_output)

        passed = similarity >= similarity_threshold

        return passed, {
            "similarity": round(similarity, 3),
            "threshold": similarity_threshold,
            "golden_version": golden.get("model_version"),
            "query": golden.get("query")
        }

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using word overlap"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0
