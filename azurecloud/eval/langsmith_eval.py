"""
LangSmith Evaluation Integration for Enterprise RAG Platform.

Provides LangSmith-native evaluation with:
- RAG triad evaluators (Groundedness, Relevance, Citation Accuracy)
- Custom evaluators for table understanding
- Experiment tracking and comparison
- Dataset management

Compatible with Azure AI Foundry evaluation metrics.
"""

import os
import re
import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

from langsmith import Client
from langsmith.evaluation import evaluate, LangChainStringEvaluator
from langsmith.schemas import Example, Run

# Import openevals for LLM-as-judge patterns
try:
    from openevals.llm import create_llm_as_judge
    from openevals.prompts import RAG_GROUNDEDNESS_PROMPT, RAG_ANSWER_RELEVANCE_PROMPT
    HAS_OPENEVALS = True
except ImportError:
    HAS_OPENEVALS = False

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

class LangSmithConfig:
    """Configuration for LangSmith integration."""

    def __init__(
        self,
        api_key: str = None,
        project_name: str = "rag-evaluation",
        dataset_name: str = "rag_eval_set",
        model: str = "openai:gpt-4o-mini"
    ):
        self.api_key = api_key or os.getenv("LANGCHAIN_API_KEY")
        self.project_name = project_name
        self.dataset_name = dataset_name
        self.model = model

        # Enable LangSmith tracing
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        if self.api_key:
            os.environ["LANGCHAIN_API_KEY"] = self.api_key


# =============================================================================
# Custom Evaluators
# =============================================================================

def groundedness_evaluator(run: Run, example: Example) -> Dict[str, Any]:
    """
    Evaluate if the answer is grounded in the provided context.

    Uses LLM-as-judge approach aligned with Azure AI Foundry's
    GroundednessProEvaluator.
    """
    if HAS_OPENEVALS:
        # Use openevals LLM-as-judge
        judge = create_llm_as_judge(
            prompt=RAG_GROUNDEDNESS_PROMPT,
            feedback_key="groundedness",
            model="openai:gpt-4o-mini",
        )
        return judge(run, example)

    # Fallback: Simple keyword-based check
    answer = run.outputs.get("answer", "")
    context = run.outputs.get("context", "")

    if not context:
        chunks = run.outputs.get("retrieved_chunks", [])
        context = "\n".join([c.get("content", "") for c in chunks])

    # Simple overlap scoring
    answer_words = set(answer.lower().split())
    context_words = set(context.lower().split())
    overlap = len(answer_words & context_words) / len(answer_words) if answer_words else 0

    return {
        "key": "groundedness",
        "score": min(1.0, overlap * 2),  # Scale up
        "comment": f"Word overlap: {overlap:.2%}"
    }


def relevance_evaluator(run: Run, example: Example) -> Dict[str, Any]:
    """
    Evaluate if the answer is relevant to the question.

    Uses embedding similarity or LLM-as-judge.
    """
    if HAS_OPENEVALS:
        judge = create_llm_as_judge(
            prompt=RAG_ANSWER_RELEVANCE_PROMPT,
            feedback_key="relevance",
            model="openai:gpt-4o-mini",
        )
        return judge(run, example)

    # Fallback: Question-answer keyword overlap
    question = example.inputs.get("question", "")
    answer = run.outputs.get("answer", "")

    q_words = set(question.lower().split())
    a_words = set(answer.lower().split())
    overlap = len(q_words & a_words) / len(q_words) if q_words else 0

    return {
        "key": "relevance",
        "score": min(1.0, overlap * 3),
        "comment": f"Question-answer overlap: {overlap:.2%}"
    }


def citation_accuracy_evaluator(run: Run, example: Example) -> Dict[str, Any]:
    """
    Evaluate if cited sources in the answer exist in retrieved chunks.

    Binary check: Are all citations valid?
    """
    answer = run.outputs.get("answer", "")
    chunks = run.outputs.get("retrieved_chunks", [])

    # Extract citations from answer
    patterns = [
        r"\[Source:\s*([^,\]]+\.pdf)",
        r"\[([^\]]+\.pdf)\]",
    ]

    cited_sources = set()
    for pattern in patterns:
        matches = re.findall(pattern, answer, re.IGNORECASE)
        for match in matches:
            cited_sources.add(match.strip().lower())

    if not cited_sources:
        return {
            "key": "citation_accuracy",
            "score": 0.5,  # Neutral if no citations
            "comment": "No citations found in answer"
        }

    # Get sources from retrieved chunks
    retrieved_sources = set()
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        source = metadata.get("source_pdf", metadata.get("source", ""))
        if source:
            retrieved_sources.add(source.lower())

    if not retrieved_sources:
        return {
            "key": "citation_accuracy",
            "score": 0.0,
            "comment": "No sources in retrieved chunks"
        }

    # Calculate accuracy
    valid = cited_sources & retrieved_sources
    accuracy = len(valid) / len(cited_sources)

    return {
        "key": "citation_accuracy",
        "score": accuracy,
        "comment": f"Valid: {list(valid)}, Invalid: {list(cited_sources - retrieved_sources)}"
    }


def table_understanding_evaluator(run: Run, example: Example) -> Dict[str, Any]:
    """
    Evaluate table/structured data reasoning capability.

    Only scored for examples marked with requires_table=True.
    """
    requires_table = example.inputs.get("requires_table", False)

    if not requires_table:
        return {
            "key": "table_understanding",
            "score": 1.0,
            "comment": "N/A - not a table question"
        }

    answer = run.outputs.get("answer", "")
    ground_truth = example.outputs.get("ground_truth", "")

    # Check for numeric accuracy
    answer_numbers = set(re.findall(r'\$?[\d,]+\.?\d*[MKB]?', answer))
    gt_numbers = set(re.findall(r'\$?[\d,]+\.?\d*[MKB]?', ground_truth))

    if not gt_numbers:
        return {
            "key": "table_understanding",
            "score": 0.5,
            "comment": "No numbers in ground truth"
        }

    overlap = len(answer_numbers & gt_numbers) / len(gt_numbers)

    return {
        "key": "table_understanding",
        "score": overlap,
        "comment": f"Found: {answer_numbers}, Expected: {gt_numbers}"
    }


# =============================================================================
# Dataset Management
# =============================================================================

class LangSmithDatasetManager:
    """Manage LangSmith datasets for RAG evaluation."""

    def __init__(self, config: LangSmithConfig):
        self.config = config
        self.client = Client()

    def create_dataset_from_jsonl(
        self,
        jsonl_path: str,
        dataset_name: str = None
    ) -> str:
        """
        Create or update a LangSmith dataset from JSONL file.

        Args:
            jsonl_path: Path to JSONL file with evaluation examples
            dataset_name: Dataset name (defaults to config)

        Returns:
            Dataset ID
        """
        import json

        dataset_name = dataset_name or self.config.dataset_name

        # Check if dataset exists
        datasets = list(self.client.list_datasets(dataset_name=dataset_name))
        if datasets:
            dataset = datasets[0]
            logger.info(f"Using existing dataset: {dataset_name}")
        else:
            dataset = self.client.create_dataset(
                dataset_name=dataset_name,
                description="RAG evaluation dataset for enterprise platform"
            )
            logger.info(f"Created new dataset: {dataset_name}")

        # Load examples from JSONL
        with open(jsonl_path, "r") as f:
            for line in f:
                if not line.strip():
                    continue

                item = json.loads(line)

                # Create example in LangSmith format
                self.client.create_example(
                    inputs={
                        "question": item["question"],
                        "requires_table": item.get("requires_table", False)
                    },
                    outputs={
                        "ground_truth": item.get("ground_truth", "")
                    },
                    dataset_id=dataset.id,
                    metadata={"id": item.get("id")}
                )

        logger.info(f"Dataset populated with examples from {jsonl_path}")
        return dataset.id

    def list_datasets(self) -> List[Dict]:
        """List all available datasets."""
        return [
            {"id": d.id, "name": d.name, "created": d.created_at}
            for d in self.client.list_datasets()
        ]


# =============================================================================
# Evaluation Runner
# =============================================================================

class LangSmithEvaluator:
    """
    Run LangSmith evaluations for RAG systems.

    Supports both local and remote (LangSmith cloud) evaluation.
    """

    def __init__(self, config: LangSmithConfig):
        self.config = config
        self.client = Client()

    async def run_evaluation(
        self,
        target: Callable,
        dataset_name: str = None,
        experiment_prefix: str = "rag-eval",
        evaluators: List[Callable] = None
    ) -> Dict[str, Any]:
        """
        Run evaluation against a dataset.

        Args:
            target: Async callable that takes example inputs and returns RAG output
            dataset_name: Dataset to evaluate against
            experiment_prefix: Prefix for experiment name
            evaluators: Custom evaluators (defaults to RAG triad)

        Returns:
            Evaluation results summary
        """
        dataset_name = dataset_name or self.config.dataset_name

        # Default evaluators
        if evaluators is None:
            evaluators = [
                groundedness_evaluator,
                relevance_evaluator,
                citation_accuracy_evaluator,
                table_understanding_evaluator,
            ]

        # Run evaluation
        results = evaluate(
            target,
            data=dataset_name,
            evaluators=evaluators,
            experiment_prefix=experiment_prefix,
            max_concurrency=4
        )

        # Aggregate results
        summary = self._aggregate_results(results)

        logger.info(f"Evaluation complete: {summary}")
        return summary

    def _aggregate_results(self, results) -> Dict[str, Any]:
        """Aggregate evaluation results into summary."""
        scores = {
            "groundedness": [],
            "relevance": [],
            "citation_accuracy": [],
            "table_understanding": []
        }

        for result in results:
            for feedback in result.get("feedback", []):
                key = feedback.get("key")
                score = feedback.get("score", 0)
                if key in scores:
                    scores[key].append(score)

        summary = {}
        for key, values in scores.items():
            if values:
                summary[f"{key}_avg"] = sum(values) / len(values)
                summary[f"{key}_count"] = len(values)

        # Overall score
        if all(f"{k}_avg" in summary for k in ["groundedness", "relevance", "citation_accuracy"]):
            summary["overall_avg"] = (
                0.4 * summary["groundedness_avg"] +
                0.3 * summary["relevance_avg"] +
                0.2 * summary["citation_accuracy_avg"] +
                0.1 * summary.get("table_understanding_avg", 1.0)
            )

        return summary

    def compare_experiments(
        self,
        experiment_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Compare multiple experiments.

        Args:
            experiment_ids: List of experiment IDs to compare

        Returns:
            Comparison summary
        """
        comparisons = []

        for exp_id in experiment_ids:
            # Get experiment runs
            runs = list(self.client.list_runs(
                project_name=self.config.project_name,
                filter=f'eq(session_id, "{exp_id}")'
            ))

            if runs:
                scores = self._calculate_experiment_scores(runs)
                comparisons.append({
                    "experiment_id": exp_id,
                    "run_count": len(runs),
                    **scores
                })

        return {"comparisons": comparisons}

    def _calculate_experiment_scores(self, runs: List) -> Dict[str, float]:
        """Calculate aggregate scores for experiment runs."""
        scores = {
            "groundedness": [],
            "relevance": [],
            "citation_accuracy": []
        }

        for run in runs:
            if run.feedback_stats:
                for key in scores:
                    if key in run.feedback_stats:
                        scores[key].append(run.feedback_stats[key].get("avg", 0))

        return {
            f"{k}_avg": sum(v) / len(v) if v else 0
            for k, v in scores.items()
        }


# =============================================================================
# CI/CD Integration
# =============================================================================

async def run_langsmith_ci_eval(
    jsonl_path: str,
    rag_callable: Callable,
    experiment_prefix: str = "ci-eval",
    api_key: str = None
) -> Dict[str, Any]:
    """
    Run LangSmith evaluation for CI/CD pipelines.

    Args:
        jsonl_path: Path to evaluation dataset
        rag_callable: Async callable for RAG system
        experiment_prefix: Experiment name prefix
        api_key: LangSmith API key

    Returns:
        Evaluation summary with pass/fail status
    """
    config = LangSmithConfig(api_key=api_key)

    # Create/update dataset
    dataset_manager = LangSmithDatasetManager(config)
    dataset_manager.create_dataset_from_jsonl(jsonl_path)

    # Run evaluation
    evaluator = LangSmithEvaluator(config)
    summary = await evaluator.run_evaluation(
        target=rag_callable,
        experiment_prefix=experiment_prefix
    )

    # Determine pass/fail
    passed = summary.get("overall_avg", 0) >= 0.7

    return {
        **summary,
        "passed": passed,
        "experiment_prefix": experiment_prefix
    }


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    import json

    async def main():
        # Initialize
        config = LangSmithConfig()
        evaluator = LangSmithEvaluator(config)

        # Mock RAG target
        async def mock_rag(inputs: Dict) -> Dict:
            question = inputs["question"]
            return {
                "answer": f"Answer to: {question} [Source: policy.pdf, Page 4]",
                "retrieved_chunks": [
                    {
                        "content": "Sample content from policy document.",
                        "metadata": {"source_pdf": "policy.pdf", "page_number": 4}
                    }
                ],
                "context": "Sample context from policy document."
            }

        # Run evaluation
        results = await evaluator.run_evaluation(
            target=mock_rag,
            experiment_prefix="test-eval"
        )

        print(json.dumps(results, indent=2))

    asyncio.run(main())
