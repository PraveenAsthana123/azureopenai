"""
RAG Evaluation Framework for Enterprise RAG Platform.

Implements Azure AI Foundry-aligned evaluation metrics:
- Groundedness: Is the answer supported by retrieved context?
- Relevance: Does the answer address the question?
- Citation Accuracy: Are citations valid and traceable?
- Table Understanding: Can the system reason over tabular data?

Compatible with LangSmith, Azure AI Foundry, and custom eval pipelines.
"""

import json
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from openai import AsyncAzureOpenAI
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class EvalResult:
    """Result of evaluating a single RAG query."""
    id: str
    question: str
    answer: str
    ground_truth: str
    groundedness: float
    relevance: float
    citation_accuracy: float
    table_understanding: float
    overall: float
    latency_ms: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "question": self.question,
            "answer": self.answer,
            "ground_truth": self.ground_truth,
            "groundedness": self.groundedness,
            "relevance": self.relevance,
            "citation_accuracy": self.citation_accuracy,
            "table_understanding": self.table_understanding,
            "overall": self.overall,
            "latency_ms": self.latency_ms,
            "metadata": self.metadata
        }


@dataclass
class EvalSummary:
    """Summary of evaluation run."""
    run_id: str
    timestamp: str
    total_samples: int
    groundedness_avg: float
    relevance_avg: float
    citation_accuracy_avg: float
    table_understanding_avg: float
    overall_avg: float
    pass_rate: float  # % of samples with overall >= threshold
    results: list[EvalResult]

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "total_samples": self.total_samples,
            "groundedness_avg": self.groundedness_avg,
            "relevance_avg": self.relevance_avg,
            "citation_accuracy_avg": self.citation_accuracy_avg,
            "table_understanding_avg": self.table_understanding_avg,
            "overall_avg": self.overall_avg,
            "pass_rate": self.pass_rate,
            "results": [r.to_dict() for r in self.results]
        }


class RAGEvaluator:
    """
    Evaluator for RAG systems using LLM-as-judge and embedding similarity.

    Supports both local evaluation and Azure AI Foundry cloud evaluation.
    """

    def __init__(
        self,
        azure_openai_client: AsyncAzureOpenAI,
        chat_deployment: str = "gpt-4o-mini",
        embedding_deployment: str = "text-embedding-3-large",
        pass_threshold: float = 0.7
    ):
        self.client = azure_openai_client
        self.chat_deployment = chat_deployment
        self.embedding_deployment = embedding_deployment
        self.pass_threshold = pass_threshold
        self._embedding_cache: dict[str, list[float]] = {}

    async def embed(self, text: str) -> list[float]:
        """Get embedding for text with caching."""
        if text in self._embedding_cache:
            return self._embedding_cache[text]

        response = await self.client.embeddings.create(
            model=self.embedding_deployment,
            input=text
        )
        embedding = response.data[0].embedding
        self._embedding_cache[text] = embedding
        return embedding

    async def groundedness_score(
        self,
        answer: str,
        contexts: list[str]
    ) -> float:
        """
        Evaluate if answer is grounded in the provided contexts.
        Uses LLM-as-judge approach aligned with Azure AI Foundry.
        """
        if not contexts:
            return 0.0

        context_text = "\n\n---\n\n".join(contexts[:5])  # Top 5 chunks

        prompt = f"""You are an expert evaluator assessing answer groundedness.

TASK: Determine if the ANSWER is fully supported by the CONTEXT.

CONTEXT:
{context_text}

ANSWER:
{answer}

EVALUATION CRITERIA:
- Score 1.0: Every claim in the answer is directly supported by the context
- Score 0.7: Most claims are supported, minor inferences acceptable
- Score 0.5: Some claims supported, some unsupported
- Score 0.3: Few claims supported, mostly unsupported
- Score 0.0: Answer contradicts context or is completely unsupported

Respond with ONLY a JSON object:
{{"score": <float 0.0-1.0>, "reasoning": "<brief explanation>"}}"""

        try:
            response = await self.client.chat.completions.create(
                model=self.chat_deployment,
                temperature=0,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )
            result = json.loads(response.choices[0].message.content)
            return float(result.get("score", 0.0))
        except Exception as e:
            logger.warning(f"Groundedness evaluation failed: {e}")
            return 0.5  # Default to middle score on error

    async def relevance_score(
        self,
        question: str,
        answer: str
    ) -> float:
        """
        Evaluate answer relevance to the question using embedding similarity.
        """
        try:
            q_emb = await self.embed(question)
            a_emb = await self.embed(answer)
            similarity = cosine_similarity([q_emb], [a_emb])[0][0]
            return float(max(0.0, min(1.0, similarity)))
        except Exception as e:
            logger.warning(f"Relevance evaluation failed: {e}")
            return 0.5

    def citation_accuracy_score(
        self,
        answer: str,
        retrieved_chunks: list[dict]
    ) -> float:
        """
        Check if cited sources in answer exist in retrieved chunks.
        """
        import re

        # Extract citations from answer (multiple formats)
        patterns = [
            r"\[Source:\s*(.*?\.pdf),\s*Page\s*(\d+)\]",
            r"\[([^\]]+\.pdf)\]",
            r"Source:\s*([^\],]+)",
        ]

        cited_sources = set()
        for pattern in patterns:
            matches = re.findall(pattern, answer, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    cited_sources.add(match[0].strip().lower())
                else:
                    cited_sources.add(match.strip().lower())

        if not cited_sources:
            # No citations in answer - check if context was used
            # Give partial credit if answer seems grounded
            return 0.5 if len(answer) > 50 else 0.0

        # Get sources from retrieved chunks
        retrieved_sources = set()
        for chunk in retrieved_chunks:
            metadata = chunk.get("metadata", {})
            source = metadata.get("source_pdf", metadata.get("source", ""))
            if source:
                retrieved_sources.add(source.lower())

        if not retrieved_sources:
            return 0.0

        # Calculate overlap
        valid_citations = cited_sources & retrieved_sources
        accuracy = len(valid_citations) / len(cited_sources) if cited_sources else 0.0
        return accuracy

    async def table_understanding_score(
        self,
        question: str,
        answer: str,
        ground_truth: str,
        requires_table: bool
    ) -> float:
        """
        Evaluate table/structured data reasoning capability.
        """
        if not requires_table:
            return 1.0  # N/A for non-table questions

        # Use embedding similarity between answer and ground truth
        try:
            a_emb = await self.embed(answer)
            gt_emb = await self.embed(ground_truth)
            similarity = cosine_similarity([a_emb], [gt_emb])[0][0]

            # Also check for numeric accuracy
            import re
            answer_numbers = set(re.findall(r'\$?[\d,]+\.?\d*[MKB]?', answer))
            gt_numbers = set(re.findall(r'\$?[\d,]+\.?\d*[MKB]?', ground_truth))

            if gt_numbers:
                number_accuracy = len(answer_numbers & gt_numbers) / len(gt_numbers)
                # Combine semantic similarity with numeric accuracy
                return float(0.6 * similarity + 0.4 * number_accuracy)

            return float(max(0.0, min(1.0, similarity)))
        except Exception as e:
            logger.warning(f"Table understanding evaluation failed: {e}")
            return 0.5

    async def evaluate_single(
        self,
        item: dict,
        rag_output: dict
    ) -> EvalResult:
        """Evaluate a single RAG query result."""
        answer = rag_output.get("answer", "")
        chunks = rag_output.get("retrieved_chunks", [])
        contexts = [c.get("content", "") for c in chunks]

        # Run all evaluations concurrently
        groundedness, relevance, table_score = await asyncio.gather(
            self.groundedness_score(answer, contexts),
            self.relevance_score(item["question"], answer),
            self.table_understanding_score(
                item["question"],
                answer,
                item.get("ground_truth", ""),
                item.get("requires_table", False)
            )
        )

        citation_accuracy = self.citation_accuracy_score(answer, chunks)

        # Weighted overall score
        overall = (
            0.40 * groundedness +
            0.30 * relevance +
            0.20 * citation_accuracy +
            0.10 * table_score
        )

        return EvalResult(
            id=item.get("id", "unknown"),
            question=item["question"],
            answer=answer,
            ground_truth=item.get("ground_truth", ""),
            groundedness=round(groundedness, 4),
            relevance=round(relevance, 4),
            citation_accuracy=round(citation_accuracy, 4),
            table_understanding=round(table_score, 4),
            overall=round(overall, 4),
            latency_ms=rag_output.get("latency_ms", 0),
            metadata={
                "chunk_count": len(chunks),
                "requires_table": item.get("requires_table", False)
            }
        )

    async def evaluate_batch(
        self,
        eval_items: list[dict],
        rag_callable: Callable[[str], Any],
        run_id: str = None
    ) -> EvalSummary:
        """
        Run evaluation on a batch of items.

        Args:
            eval_items: List of evaluation items with question, ground_truth, etc.
            rag_callable: Async function that takes a question and returns RAG output
            run_id: Optional run identifier
        """
        import uuid
        run_id = run_id or str(uuid.uuid4())[:8]
        results = []

        for item in eval_items:
            try:
                import time
                start = time.time()
                rag_output = await rag_callable(item["question"])
                latency = (time.time() - start) * 1000
                rag_output["latency_ms"] = latency

                result = await self.evaluate_single(item, rag_output)
                results.append(result)

                logger.info(
                    f"Evaluated {item['id']}: "
                    f"G={result.groundedness:.2f} R={result.relevance:.2f} "
                    f"C={result.citation_accuracy:.2f} T={result.table_understanding:.2f} "
                    f"Overall={result.overall:.2f}"
                )
            except Exception as e:
                logger.error(f"Failed to evaluate {item.get('id')}: {e}")
                results.append(EvalResult(
                    id=item.get("id", "unknown"),
                    question=item["question"],
                    answer="ERROR",
                    ground_truth=item.get("ground_truth", ""),
                    groundedness=0.0,
                    relevance=0.0,
                    citation_accuracy=0.0,
                    table_understanding=0.0,
                    overall=0.0
                ))

        # Calculate summary statistics
        n = len(results)
        pass_count = sum(1 for r in results if r.overall >= self.pass_threshold)

        summary = EvalSummary(
            run_id=run_id,
            timestamp=datetime.utcnow().isoformat(),
            total_samples=n,
            groundedness_avg=round(sum(r.groundedness for r in results) / n, 4) if n else 0,
            relevance_avg=round(sum(r.relevance for r in results) / n, 4) if n else 0,
            citation_accuracy_avg=round(sum(r.citation_accuracy for r in results) / n, 4) if n else 0,
            table_understanding_avg=round(sum(r.table_understanding for r in results) / n, 4) if n else 0,
            overall_avg=round(sum(r.overall for r in results) / n, 4) if n else 0,
            pass_rate=round(pass_count / n, 4) if n else 0,
            results=results
        )

        return summary


def load_eval_set(path: str = "eval_set.jsonl") -> list[dict]:
    """Load evaluation dataset from JSONL file."""
    items = []
    with open(path, "r") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    return items


def save_results(summary: EvalSummary, path: str):
    """Save evaluation results to JSON file."""
    with open(path, "w") as f:
        json.dump(summary.to_dict(), f, indent=2)


def compare_scores(
    baseline_path: str,
    new_path: str,
    threshold: float = 0.10
) -> bool:
    """
    Compare new evaluation results against baseline.
    Returns True if new scores are acceptable (not regressed beyond threshold).
    """
    with open(baseline_path) as f:
        baseline = json.load(f)
    with open(new_path) as f:
        new = json.load(f)

    baseline_overall = baseline.get("overall_avg", 0)
    new_overall = new.get("overall_avg", 0)

    if baseline_overall == 0:
        return True  # No baseline to compare

    drop = (baseline_overall - new_overall) / baseline_overall

    print(f"Baseline: {baseline_overall:.4f}")
    print(f"New:      {new_overall:.4f}")
    print(f"Change:   {-drop*100:+.2f}%")

    if drop > threshold:
        print(f"FAIL: Score dropped by {drop*100:.2f}% (threshold: {threshold*100}%)")
        return False

    print("PASS: Score within acceptable range")
    return True


# Example usage
if __name__ == "__main__":
    import os

    async def main():
        # Initialize Azure OpenAI client
        client = AsyncAzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version="2024-02-15-preview"
        )

        evaluator = RAGEvaluator(
            azure_openai_client=client,
            chat_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini"),
            embedding_deployment=os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT", "text-embedding-3-large")
        )

        # Load evaluation set
        eval_items = load_eval_set("eval_set.jsonl")

        # Mock RAG callable for testing
        async def mock_rag(question: str):
            return {
                "answer": f"Based on the documents, the answer to '{question}' is in the policy. [Source: policy.pdf, Page 4]",
                "retrieved_chunks": [
                    {
                        "content": "Logs are retained for 365 days per compliance requirements.",
                        "metadata": {"source_pdf": "policy.pdf", "page_number": 4}
                    }
                ]
            }

        # Run evaluation
        summary = await evaluator.evaluate_batch(eval_items, mock_rag)

        # Save results
        save_results(summary, "eval_results.json")

        print("\n=== Evaluation Summary ===")
        print(f"Samples:      {summary.total_samples}")
        print(f"Groundedness: {summary.groundedness_avg:.4f}")
        print(f"Relevance:    {summary.relevance_avg:.4f}")
        print(f"Citation:     {summary.citation_accuracy_avg:.4f}")
        print(f"Table:        {summary.table_understanding_avg:.4f}")
        print(f"Overall:      {summary.overall_avg:.4f}")
        print(f"Pass Rate:    {summary.pass_rate*100:.1f}%")

    asyncio.run(main())
