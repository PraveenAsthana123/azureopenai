#!/usr/bin/env python3
"""
CI/CD Evaluation Runner for RAG Platform.

Runs offline evaluation for CI pipelines with:
- GitHub Actions integration
- Azure DevOps integration
- Baseline comparison
- Pass/fail gating
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Optional

import httpx
from openai import AsyncAzureOpenAI
from azure.identity import DefaultAzureCredential

from evaluate_rag import RAGEvaluator, load_eval_set, save_results, compare_scores

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def create_rag_callable(endpoint: Optional[str] = None):
    """
    Create a callable for the RAG API.

    Args:
        endpoint: Optional API endpoint. If None, uses mock data.

    Returns:
        Async callable that takes a question and returns RAG output
    """
    if endpoint:
        # Call actual RAG API
        async def call_api(question: str):
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    endpoint,
                    json={"question": question, "user_id": "eval-user", "session_id": "eval-session"},
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                return response.json()

        return call_api
    else:
        # Mock callable for offline testing
        async def mock_rag(question: str):
            # Simulate responses based on question patterns
            mock_responses = {
                "retention": {
                    "answer": "Logs are retained for 365 days per compliance requirements. [Source: policy.pdf, Page 4]",
                    "retrieved_chunks": [
                        {
                            "content": "All system logs must be retained for a minimum of 365 days to meet regulatory compliance requirements.",
                            "metadata": {"source_pdf": "policy.pdf", "page_number": 4}
                        }
                    ]
                },
                "rotation": {
                    "answer": "Keys must be rotated every 90 days according to security policy. [Source: security.pdf, Page 12]",
                    "retrieved_chunks": [
                        {
                            "content": "Cryptographic keys must be rotated every 90 days.",
                            "metadata": {"source_pdf": "security.pdf", "page_number": 12}
                        }
                    ]
                },
                "budget": {
                    "answer": "The Q3 budget for security tools is $2.4M. [Source: budget.pdf, Page 8]",
                    "retrieved_chunks": [
                        {
                            "content": "Q3 Security Tools Budget: $2.4M allocated",
                            "metadata": {"source_pdf": "budget.pdf", "page_number": 8}
                        }
                    ]
                }
            }

            # Find matching response
            q_lower = question.lower()
            for key, response in mock_responses.items():
                if key in q_lower:
                    return response

            # Default response
            return {
                "answer": f"Based on the available documents, I cannot find specific information about: {question}",
                "retrieved_chunks": [
                    {
                        "content": "General information from policy documents.",
                        "metadata": {"source_pdf": "general.pdf", "page_number": 1}
                    }
                ]
            }

        return mock_rag


async def run_evaluation(
    eval_set_path: str,
    output_path: str,
    baseline_path: Optional[str] = None,
    endpoint: Optional[str] = None,
    threshold: float = 0.10
) -> tuple[dict, bool]:
    """
    Run evaluation and optionally compare to baseline.

    Args:
        eval_set_path: Path to evaluation dataset (JSONL)
        output_path: Path to save results (JSON)
        baseline_path: Optional path to baseline results
        endpoint: Optional RAG API endpoint
        threshold: Regression threshold for comparison

    Returns:
        Tuple of (results dict, passed bool)
    """
    logger.info(f"Loading evaluation set from {eval_set_path}")
    eval_items = load_eval_set(eval_set_path)
    logger.info(f"Loaded {len(eval_items)} evaluation items")

    # Initialize evaluator
    credential = DefaultAzureCredential()

    client = AsyncAzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_ad_token_provider=lambda: credential.get_token(
            "https://cognitiveservices.azure.com/.default"
        ).token,
        api_version="2024-02-15-preview"
    )

    evaluator = RAGEvaluator(
        azure_openai_client=client,
        chat_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini"),
        embedding_deployment=os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT", "text-embedding-3-large")
    )

    # Create RAG callable
    rag_callable = await create_rag_callable(endpoint)

    # Run evaluation
    logger.info("Starting evaluation...")
    summary = await evaluator.evaluate_batch(eval_items, rag_callable)

    # Save results
    save_results(summary, output_path)
    logger.info(f"Results saved to {output_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Run ID:           {summary.run_id}")
    print(f"Timestamp:        {summary.timestamp}")
    print(f"Samples:          {summary.total_samples}")
    print(f"Groundedness:     {summary.groundedness_avg:.4f}")
    print(f"Relevance:        {summary.relevance_avg:.4f}")
    print(f"Citation Acc:     {summary.citation_accuracy_avg:.4f}")
    print(f"Table Understand: {summary.table_understanding_avg:.4f}")
    print(f"Overall:          {summary.overall_avg:.4f}")
    print(f"Pass Rate:        {summary.pass_rate:.2%}")
    print("=" * 60)

    # Compare to baseline if provided
    passed = True
    if baseline_path and os.path.exists(baseline_path):
        logger.info(f"Comparing to baseline: {baseline_path}")
        passed = compare_scores(baseline_path, output_path, threshold)
    elif baseline_path:
        logger.warning(f"Baseline not found: {baseline_path}")

    # Output for CI integration
    results = summary.to_dict()

    # GitHub Actions output
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.getenv("GITHUB_OUTPUT"), "a") as f:
            f.write(f"overall_avg={summary.overall_avg}\n")
            f.write(f"groundedness_avg={summary.groundedness_avg}\n")
            f.write(f"relevance_avg={summary.relevance_avg}\n")
            f.write(f"pass_rate={summary.pass_rate}\n")
            f.write(f"passed={str(passed).lower()}\n")

    # Azure DevOps output
    print(f"##vso[task.setvariable variable=evalOverall]{summary.overall_avg}")
    print(f"##vso[task.setvariable variable=evalPassRate]{summary.pass_rate}")
    print(f"##vso[task.setvariable variable=evalPassed]{str(passed).lower()}")

    return results, passed


def main():
    parser = argparse.ArgumentParser(
        description="Run RAG evaluation for CI/CD pipelines"
    )
    parser.add_argument(
        "--eval-set", "-e",
        required=True,
        help="Path to evaluation dataset (JSONL)"
    )
    parser.add_argument(
        "--output", "-o",
        default="eval_results.json",
        help="Path to save results (JSON)"
    )
    parser.add_argument(
        "--baseline", "-b",
        help="Path to baseline results for comparison"
    )
    parser.add_argument(
        "--endpoint",
        help="RAG API endpoint (if not provided, uses mock)"
    )
    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=0.10,
        help="Regression threshold (default: 0.10 = 10%%)"
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit with code 1 if regression detected"
    )

    args = parser.parse_args()

    results, passed = asyncio.run(run_evaluation(
        eval_set_path=args.eval_set,
        output_path=args.output,
        baseline_path=args.baseline,
        endpoint=args.endpoint,
        threshold=args.threshold
    ))

    if args.fail_on_regression and not passed:
        logger.error("Evaluation failed - regression detected")
        sys.exit(1)

    logger.info("Evaluation completed successfully")


if __name__ == "__main__":
    main()
