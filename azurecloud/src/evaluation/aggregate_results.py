"""
Aggregate multiple evaluation results and determine overall pass/fail.
"""

import argparse
import json
import sys
from datetime import datetime


def aggregate_results(result_files: list[str], output_path: str, fail_on_threshold: bool) -> bool:
    """Aggregate evaluation results from multiple files."""
    summaries = []
    all_passed = True

    for file_path in result_files:
        with open(file_path) as f:
            data = json.load(f)
            summary = data["summary"]
            summaries.append(summary)

            if not summary["passed_threshold"]:
                all_passed = False

    # Calculate overall metrics
    total_samples = sum(s["total_samples"] for s in summaries)
    total_passed = sum(s["passed_samples"] for s in summaries)

    aggregated = {
        "timestamp": datetime.utcnow().isoformat(),
        "overall_passed": all_passed,
        "total_evaluations": len(summaries),
        "total_samples": total_samples,
        "total_passed": total_passed,
        "overall_pass_rate": total_passed / total_samples if total_samples > 0 else 0,
        "evaluations": summaries,
        "summary_by_type": {
            s["eval_type"]: {
                "pass_rate": s["pass_rate"],
                "average_score": s["average_score"],
                "passed_threshold": s["passed_threshold"],
            }
            for s in summaries
        },
    }

    with open(output_path, "w") as f:
        json.dump(aggregated, f, indent=2)

    # Print summary
    print("\n" + "=" * 70)
    print("AGGREGATED EVALUATION RESULTS")
    print("=" * 70)

    for s in summaries:
        status = "PASS" if s["passed_threshold"] else "FAIL"
        print(f"  {s['eval_type']:15} | Pass Rate: {s['pass_rate']:.1%} | Avg Score: {s['average_score']:.3f} | [{status}]")

    print("-" * 70)
    print(f"  {'OVERALL':15} | Pass Rate: {aggregated['overall_pass_rate']:.1%} | Status: {'PASSED' if all_passed else 'FAILED'}")
    print("=" * 70 + "\n")

    if fail_on_threshold and not all_passed:
        print("ERROR: One or more evaluations failed to meet threshold requirements")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(description="Aggregate evaluation results")
    parser.add_argument("--results", nargs="+", required=True, help="Result JSON files")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument("--fail-on-threshold", action="store_true",
                       help="Exit with error if any evaluation fails threshold")

    args = parser.parse_args()

    success = aggregate_results(args.results, args.output, args.fail_on_threshold)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
