"""
Latency Benchmarking for RAG System
Measures P50, P95, P99 latencies under load.
"""

import argparse
import asyncio
import json
import statistics
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime

import httpx


@dataclass
class LatencyResult:
    """Single request latency result."""
    request_id: int
    query: str
    latency_ms: float
    status_code: int
    success: bool
    timestamp: str


@dataclass
class LatencyBenchmarkSummary:
    """Latency benchmark summary."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    min_latency_ms: float
    max_latency_ms: float
    mean_latency_ms: float
    median_latency_ms: float
    p50_latency_ms: float
    p90_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    requests_per_second: float
    duration_seconds: float
    passed_threshold: bool
    threshold_ms: float
    timestamp: str


class LatencyBenchmark:
    """Latency benchmarking framework."""

    TEST_QUERIES = [
        "What is our company's vacation policy?",
        "How do I submit an expense report?",
        "What are the password requirements?",
        "How do I request a new software license?",
        "What is the data retention policy?",
        "How do I report a security incident?",
        "What are the work from home guidelines?",
        "How do I access the VPN?",
        "What is the travel expense policy?",
        "How do I request time off?",
    ]

    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.results: list[LatencyResult] = []

    async def _make_request(
        self,
        request_id: int,
        query: str,
        client: httpx.AsyncClient,
    ) -> LatencyResult:
        """Make a single request and measure latency."""
        start = time.perf_counter()
        success = True
        status_code = 0

        try:
            response = await client.post(
                f"{self.endpoint}/query",
                json={"query": query},
                headers={"Content-Type": "application/json"},
                timeout=60.0,
            )
            status_code = response.status_code
            success = response.status_code == 200
        except Exception:
            success = False

        latency_ms = (time.perf_counter() - start) * 1000

        return LatencyResult(
            request_id=request_id,
            query=query,
            latency_ms=latency_ms,
            status_code=status_code,
            success=success,
            timestamp=datetime.utcnow().isoformat(),
        )

    async def run_benchmark(
        self,
        num_requests: int,
        concurrency: int,
    ) -> LatencyBenchmarkSummary:
        """Run latency benchmark with specified concurrency."""
        print(f"Starting benchmark: {num_requests} requests, {concurrency} concurrent")

        self.results = []
        semaphore = asyncio.Semaphore(concurrency)
        start_time = time.perf_counter()

        async def bounded_request(request_id: int, query: str, client: httpx.AsyncClient):
            async with semaphore:
                result = await self._make_request(request_id, query, client)
                self.results.append(result)

                if result.request_id % 10 == 0:
                    print(f"  Completed {result.request_id}/{num_requests} - {result.latency_ms:.0f}ms")

                return result

        async with httpx.AsyncClient() as client:
            tasks = [
                bounded_request(
                    i,
                    self.TEST_QUERIES[i % len(self.TEST_QUERIES)],
                    client,
                )
                for i in range(num_requests)
            ]
            await asyncio.gather(*tasks)

        duration = time.perf_counter() - start_time
        return self._generate_summary(duration)

    def _generate_summary(self, duration: float) -> LatencyBenchmarkSummary:
        """Generate benchmark summary."""
        successful = [r for r in self.results if r.success]
        latencies = sorted([r.latency_ms for r in successful])

        if not latencies:
            return LatencyBenchmarkSummary(
                total_requests=len(self.results),
                successful_requests=0,
                failed_requests=len(self.results),
                success_rate=0,
                min_latency_ms=0,
                max_latency_ms=0,
                mean_latency_ms=0,
                median_latency_ms=0,
                p50_latency_ms=0,
                p90_latency_ms=0,
                p95_latency_ms=0,
                p99_latency_ms=0,
                requests_per_second=0,
                duration_seconds=duration,
                passed_threshold=False,
                threshold_ms=0,
                timestamp=datetime.utcnow().isoformat(),
            )

        def percentile(data: list[float], p: float) -> float:
            k = (len(data) - 1) * p / 100
            f = int(k)
            c = f + 1 if f + 1 < len(data) else f
            return data[f] + (k - f) * (data[c] - data[f])

        return LatencyBenchmarkSummary(
            total_requests=len(self.results),
            successful_requests=len(successful),
            failed_requests=len(self.results) - len(successful),
            success_rate=len(successful) / len(self.results),
            min_latency_ms=min(latencies),
            max_latency_ms=max(latencies),
            mean_latency_ms=statistics.mean(latencies),
            median_latency_ms=statistics.median(latencies),
            p50_latency_ms=percentile(latencies, 50),
            p90_latency_ms=percentile(latencies, 90),
            p95_latency_ms=percentile(latencies, 95),
            p99_latency_ms=percentile(latencies, 99),
            requests_per_second=len(successful) / duration if duration > 0 else 0,
            duration_seconds=duration,
            passed_threshold=False,  # Set by caller
            threshold_ms=0,  # Set by caller
            timestamp=datetime.utcnow().isoformat(),
        )

    def save_results(self, output_path: str, threshold_ms: float) -> None:
        """Save results with threshold check."""
        summary = self._generate_summary(0)  # Duration already calculated
        summary.threshold_ms = threshold_ms
        summary.passed_threshold = summary.p95_latency_ms <= threshold_ms

        output = {
            "summary": asdict(summary),
            "results": [asdict(r) for r in self.results],
        }

        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)


async def main():
    parser = argparse.ArgumentParser(description="Latency Benchmark")
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--num-requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--output", required=True)
    parser.add_argument("--p95-threshold", type=float, default=3000)

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print("LATENCY BENCHMARK")
    print(f"{'='*60}")
    print(f"Endpoint:     {args.endpoint}")
    print(f"Requests:     {args.num_requests}")
    print(f"Concurrency:  {args.concurrency}")
    print(f"P95 Threshold: {args.p95_threshold}ms")
    print(f"{'='*60}\n")

    benchmark = LatencyBenchmark(args.endpoint)
    summary = await benchmark.run_benchmark(args.num_requests, args.concurrency)

    summary.threshold_ms = args.p95_threshold
    summary.passed_threshold = summary.p95_latency_ms <= args.p95_threshold

    benchmark.save_results(args.output, args.p95_threshold)

    print(f"\n{'='*60}")
    print("BENCHMARK RESULTS")
    print(f"{'='*60}")
    print(f"Total Requests:    {summary.total_requests}")
    print(f"Successful:        {summary.successful_requests}")
    print(f"Failed:            {summary.failed_requests}")
    print(f"Success Rate:      {summary.success_rate:.1%}")
    print(f"Duration:          {summary.duration_seconds:.1f}s")
    print(f"Requests/sec:      {summary.requests_per_second:.1f}")
    print(f"\nLatency Distribution:")
    print(f"  Min:     {summary.min_latency_ms:.0f}ms")
    print(f"  Mean:    {summary.mean_latency_ms:.0f}ms")
    print(f"  Median:  {summary.median_latency_ms:.0f}ms")
    print(f"  P90:     {summary.p90_latency_ms:.0f}ms")
    print(f"  P95:     {summary.p95_latency_ms:.0f}ms (threshold: {args.p95_threshold}ms)")
    print(f"  P99:     {summary.p99_latency_ms:.0f}ms")
    print(f"  Max:     {summary.max_latency_ms:.0f}ms")
    print(f"\nRESULT: {'PASSED' if summary.passed_threshold else 'FAILED'}")
    print(f"{'='*60}\n")

    if not summary.passed_threshold:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
