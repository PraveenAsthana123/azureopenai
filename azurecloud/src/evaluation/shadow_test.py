"""
Shadow Testing Framework
Mirrors production traffic to staging environment for comparison.
"""

import argparse
import asyncio
import json
import random
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any

import httpx


@dataclass
class ShadowTestResult:
    """Result of a single shadow test."""
    query: str
    production_response: str
    staging_response: str
    production_latency_ms: float
    staging_latency_ms: float
    latency_diff_pct: float
    responses_match: bool
    similarity_score: float
    timestamp: str


@dataclass
class ShadowTestSummary:
    """Aggregated shadow test summary."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_production_latency_ms: float
    avg_staging_latency_ms: float
    avg_latency_diff_pct: float
    response_match_rate: float
    avg_similarity_score: float
    duration_minutes: float
    timestamp: str


class ShadowTester:
    """Shadow testing framework for RAG system validation."""

    def __init__(
        self,
        production_endpoint: str,
        staging_endpoint: str,
        sample_rate: float = 0.1,
    ):
        self.production_endpoint = production_endpoint
        self.staging_endpoint = staging_endpoint
        self.sample_rate = sample_rate
        self.results: list[ShadowTestResult] = []

    async def _call_endpoint(
        self,
        endpoint: str,
        query: str,
        filters: dict | None = None,
    ) -> tuple[str, float]:
        """Call an endpoint and return response and latency."""
        start = time.perf_counter()

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{endpoint}/query",
                    json={"query": query, "filters": filters or {}},
                    headers={"Content-Type": "application/json"},
                    timeout=60.0,
                )
                response.raise_for_status()
                data = response.json()
                answer = data.get("answer", "")
            except Exception as e:
                answer = f"ERROR: {str(e)}"

        latency_ms = (time.perf_counter() - start) * 1000
        return answer, latency_ms

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity (simple word overlap for demo)."""
        if not text1 or not text2:
            return 0.0

        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0

    async def run_shadow_test(
        self,
        query: str,
        filters: dict | None = None,
    ) -> ShadowTestResult:
        """Run a single shadow test."""
        # Call both endpoints in parallel
        prod_task = self._call_endpoint(self.production_endpoint, query, filters)
        staging_task = self._call_endpoint(self.staging_endpoint, query, filters)

        (prod_response, prod_latency), (staging_response, staging_latency) = await asyncio.gather(
            prod_task, staging_task
        )

        # Calculate metrics
        latency_diff_pct = (
            (staging_latency - prod_latency) / prod_latency * 100
            if prod_latency > 0
            else 0
        )

        similarity = self._calculate_similarity(prod_response, staging_response)
        responses_match = similarity > 0.9  # 90% similarity threshold

        result = ShadowTestResult(
            query=query,
            production_response=prod_response[:500],  # Truncate for storage
            staging_response=staging_response[:500],
            production_latency_ms=prod_latency,
            staging_latency_ms=staging_latency,
            latency_diff_pct=latency_diff_pct,
            responses_match=responses_match,
            similarity_score=similarity,
            timestamp=datetime.utcnow().isoformat(),
        )

        self.results.append(result)
        return result

    async def run_continuous_shadow(
        self,
        queries: list[dict[str, Any]],
        duration_minutes: int,
    ) -> ShadowTestSummary:
        """Run shadow testing for a specified duration."""
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)

        while time.time() < end_time:
            # Sample queries based on sample rate
            for query_data in queries:
                if random.random() > self.sample_rate:
                    continue

                query = query_data.get("query", "")
                filters = query_data.get("filters")

                try:
                    result = await self.run_shadow_test(query, filters)
                    print(
                        f"[Shadow] Query: {query[:40]}... | "
                        f"Prod: {result.production_latency_ms:.0f}ms | "
                        f"Stage: {result.staging_latency_ms:.0f}ms | "
                        f"Similarity: {result.similarity_score:.2f}"
                    )
                except Exception as e:
                    print(f"[Shadow] Error: {e}")

                # Small delay to avoid overwhelming endpoints
                await asyncio.sleep(0.1)

            # Wait before next iteration
            await asyncio.sleep(1)

        return self._generate_summary(duration_minutes)

    def _generate_summary(self, duration_minutes: float) -> ShadowTestSummary:
        """Generate summary from collected results."""
        if not self.results:
            return ShadowTestSummary(
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                avg_production_latency_ms=0,
                avg_staging_latency_ms=0,
                avg_latency_diff_pct=0,
                response_match_rate=0,
                avg_similarity_score=0,
                duration_minutes=duration_minutes,
                timestamp=datetime.utcnow().isoformat(),
            )

        successful = [r for r in self.results if "ERROR" not in r.production_response]
        failed = len(self.results) - len(successful)

        prod_latencies = [r.production_latency_ms for r in successful]
        staging_latencies = [r.staging_latency_ms for r in successful]
        latency_diffs = [r.latency_diff_pct for r in successful]
        similarities = [r.similarity_score for r in successful]
        matches = [r for r in successful if r.responses_match]

        return ShadowTestSummary(
            total_requests=len(self.results),
            successful_requests=len(successful),
            failed_requests=failed,
            avg_production_latency_ms=sum(prod_latencies) / len(prod_latencies) if prod_latencies else 0,
            avg_staging_latency_ms=sum(staging_latencies) / len(staging_latencies) if staging_latencies else 0,
            avg_latency_diff_pct=sum(latency_diffs) / len(latency_diffs) if latency_diffs else 0,
            response_match_rate=len(matches) / len(successful) if successful else 0,
            avg_similarity_score=sum(similarities) / len(similarities) if similarities else 0,
            duration_minutes=duration_minutes,
            timestamp=datetime.utcnow().isoformat(),
        )

    def save_results(self, output_path: str) -> None:
        """Save results to file."""
        output = {
            "summary": asdict(self._generate_summary(0)),
            "results": [asdict(r) for r in self.results],
        }

        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)


async def main():
    parser = argparse.ArgumentParser(description="Shadow Testing Framework")
    parser.add_argument("--production-endpoint", required=True)
    parser.add_argument("--staging-endpoint", required=True)
    parser.add_argument("--duration-minutes", type=int, default=60)
    parser.add_argument("--sample-rate", type=float, default=0.1)
    parser.add_argument("--output", required=True)
    parser.add_argument("--queries-file", help="JSONL file with test queries")

    args = parser.parse_args()

    # Load test queries
    queries = []
    if args.queries_file:
        with open(args.queries_file) as f:
            queries = [json.loads(line) for line in f]
    else:
        # Default test queries
        queries = [
            {"query": "What is our vacation policy?"},
            {"query": "How do I submit an expense report?"},
            {"query": "What are the password requirements?"},
            {"query": "How do I request software?"},
            {"query": "What is our data retention policy?"},
        ]

    print(f"\n{'='*60}")
    print("SHADOW TESTING")
    print(f"{'='*60}")
    print(f"Production: {args.production_endpoint}")
    print(f"Staging:    {args.staging_endpoint}")
    print(f"Duration:   {args.duration_minutes} minutes")
    print(f"Sample Rate: {args.sample_rate:.0%}")
    print(f"{'='*60}\n")

    tester = ShadowTester(
        production_endpoint=args.production_endpoint,
        staging_endpoint=args.staging_endpoint,
        sample_rate=args.sample_rate,
    )

    summary = await tester.run_continuous_shadow(queries, args.duration_minutes)
    tester.save_results(args.output)

    print(f"\n{'='*60}")
    print("SHADOW TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total Requests:        {summary.total_requests}")
    print(f"Successful:            {summary.successful_requests}")
    print(f"Failed:                {summary.failed_requests}")
    print(f"Avg Prod Latency:      {summary.avg_production_latency_ms:.0f}ms")
    print(f"Avg Staging Latency:   {summary.avg_staging_latency_ms:.0f}ms")
    print(f"Avg Latency Diff:      {summary.avg_latency_diff_pct:+.1f}%")
    print(f"Response Match Rate:   {summary.response_match_rate:.1%}")
    print(f"Avg Similarity:        {summary.avg_similarity_score:.2f}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
