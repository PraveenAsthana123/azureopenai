"""
Azure AI Foundry Cloud Evaluation Job Specification.

Provides server-side evaluation capabilities:
- Batch evaluation without local compute
- Managed evaluator execution in Foundry
- Experiment tracking and comparison
- CI/CD integration via SDK

Aligned with Azure AI Foundry Evaluation SDK patterns.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    EvaluationJob,
    EvaluationJobInput,
    EvaluationJobOutput,
    DatasetReference,
)
from azure.ai.evaluation import evaluate
from azure.ai.evaluation.evaluators import (
    GroundednessEvaluator,
    RelevanceEvaluator,
    ResponseCompletenessEvaluator,
    FluencyEvaluator,
    CoherenceEvaluator,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class FoundryEvalConfig:
    """Configuration for Azure AI Foundry evaluation."""
    project_connection_string: str = field(
        default_factory=lambda: os.getenv("FOUNDRY_PROJECT_CONNECTION_STRING", "")
    )
    dataset_name: str = "rag_eval_dataset"
    evaluation_name: str = "rag-cloud-eval"
    compute_target: str = "serverless"  # or specific compute name
    timeout_minutes: int = 60
    max_concurrent_evaluations: int = 10

    # Evaluator configuration
    enable_groundedness: bool = True
    enable_relevance: bool = True
    enable_completeness: bool = True
    enable_fluency: bool = False
    enable_coherence: bool = False

    # Custom evaluators
    custom_evaluators: List[str] = field(default_factory=list)


# =============================================================================
# Cloud Evaluation Job Specification
# =============================================================================

class FoundryCloudEvaluator:
    """
    Azure AI Foundry cloud-based evaluation runner.

    Runs evaluations in Foundry's managed compute without local resources.
    """

    def __init__(self, config: FoundryEvalConfig):
        self.config = config
        self._project: Optional[AIProjectClient] = None
        self._credential: Optional[DefaultAzureCredential] = None

    def _get_project(self) -> AIProjectClient:
        """Get or create AIProjectClient."""
        if self._project is None:
            self._credential = DefaultAzureCredential()
            self._project = AIProjectClient.from_connection_string(
                credential=self._credential,
                conn_str=self.config.project_connection_string
            )
        return self._project

    def _get_evaluators(self) -> Dict[str, Any]:
        """Build evaluator configuration based on config."""
        project = self._get_project()
        evaluators = {}

        if self.config.enable_groundedness:
            evaluators["groundedness"] = GroundednessEvaluator(project=project)

        if self.config.enable_relevance:
            evaluators["relevance"] = RelevanceEvaluator(project=project)

        if self.config.enable_completeness:
            evaluators["completeness"] = ResponseCompletenessEvaluator(project=project)

        if self.config.enable_fluency:
            evaluators["fluency"] = FluencyEvaluator(project=project)

        if self.config.enable_coherence:
            evaluators["coherence"] = CoherenceEvaluator(project=project)

        return evaluators

    async def submit_cloud_evaluation(
        self,
        target_fn: Callable,
        data: str | List[Dict],
        evaluation_name: str = None
    ) -> Dict[str, Any]:
        """
        Submit a cloud evaluation job to Foundry.

        Args:
            target_fn: Async callable that processes examples
            data: Dataset name (in Foundry) or list of examples
            evaluation_name: Optional custom evaluation name

        Returns:
            Evaluation results summary
        """
        project = self._get_project()
        evaluators = self._get_evaluators()

        evaluation_name = evaluation_name or self.config.evaluation_name

        logger.info(f"Starting cloud evaluation: {evaluation_name}")
        logger.info(f"Evaluators: {list(evaluators.keys())}")

        # Run evaluation
        results = await evaluate(
            target_fn=target_fn,
            data=data,
            evaluators=evaluators,
            project=project,
            evaluation_name=evaluation_name,
            _run_async=True
        )

        # Process and return summary
        summary = self._process_results(results)
        logger.info(f"Evaluation complete: {summary}")

        return summary

    def _process_results(self, results) -> Dict[str, Any]:
        """Process evaluation results into summary format."""
        summary = {
            "run_id": getattr(results, "run_id", "unknown"),
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {},
            "samples_evaluated": 0
        }

        # Extract metrics from results
        if hasattr(results, "metrics"):
            summary["metrics"] = results.metrics
        elif hasattr(results, "summary"):
            summary["metrics"] = results.summary

        if hasattr(results, "rows"):
            summary["samples_evaluated"] = len(results.rows)

        # Calculate overall score
        metrics = summary["metrics"]
        if all(k in metrics for k in ["groundedness", "relevance"]):
            summary["overall_avg"] = (
                0.4 * metrics.get("groundedness", 0) +
                0.3 * metrics.get("relevance", 0) +
                0.2 * metrics.get("completeness", metrics.get("relevance", 0)) +
                0.1 * 1.0  # Placeholder for table understanding
            )

        return summary


# =============================================================================
# Batch Evaluation Job Specification (YAML-compatible)
# =============================================================================

@dataclass
class BatchEvaluationJobSpec:
    """
    Specification for batch evaluation job.

    Can be serialized to YAML for Azure ML pipeline integration.
    """
    name: str
    display_name: str
    description: str
    dataset_name: str
    evaluators: List[str]
    compute_target: str
    timeout_minutes: int
    environment: Dict[str, str]
    outputs: Dict[str, str]

    def to_yaml(self) -> str:
        """Convert spec to YAML format."""
        import yaml
        return yaml.dump(self.to_dict(), default_flow_style=False)

    def to_dict(self) -> Dict:
        """Convert spec to dictionary."""
        return {
            "$schema": "https://azuremlschemas.azureedge.net/latest/pipelineJob.schema.json",
            "type": "pipeline",
            "experiment_name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "settings": {
                "default_compute": self.compute_target,
            },
            "inputs": {
                "dataset": {
                    "type": "uri_file",
                    "path": f"azureml:{self.dataset_name}@latest"
                }
            },
            "outputs": self.outputs,
            "jobs": {
                "evaluate": {
                    "type": "command",
                    "component": "azureml://registries/azureml/components/rag_evaluation/versions/latest",
                    "inputs": {
                        "dataset": "${{parent.inputs.dataset}}",
                        "evaluators": ",".join(self.evaluators)
                    },
                    "outputs": {
                        "evaluation_results": "${{parent.outputs.results}}"
                    },
                    "environment_variables": self.environment,
                    "timeout": self.timeout_minutes * 60
                }
            }
        }


def create_batch_eval_job_spec(
    name: str = "rag-batch-eval",
    dataset_name: str = "rag_eval_dataset",
    evaluators: List[str] = None
) -> BatchEvaluationJobSpec:
    """
    Create a batch evaluation job specification.

    Args:
        name: Job name
        dataset_name: Foundry dataset name
        evaluators: List of evaluator names

    Returns:
        BatchEvaluationJobSpec ready for submission
    """
    if evaluators is None:
        evaluators = ["groundedness", "relevance", "completeness"]

    return BatchEvaluationJobSpec(
        name=name,
        display_name=f"RAG Batch Evaluation - {datetime.utcnow().strftime('%Y%m%d')}",
        description="Automated batch evaluation of RAG system quality metrics",
        dataset_name=dataset_name,
        evaluators=evaluators,
        compute_target="serverless",
        timeout_minutes=60,
        environment={
            "AZURE_OPENAI_ENDPOINT": "${AZURE_OPENAI_ENDPOINT}",
            "AZURE_OPENAI_DEPLOYMENT": "gpt-4o-mini"
        },
        outputs={
            "results": {
                "type": "uri_folder",
                "path": f"azureml://datastores/workspaceblobstore/paths/eval_results/{name}"
            }
        }
    )


# =============================================================================
# Pipeline Job YAML Generator
# =============================================================================

def generate_foundry_eval_pipeline_yaml(
    output_path: str = "foundry-eval-pipeline.yaml",
    config: FoundryEvalConfig = None
) -> str:
    """
    Generate Azure ML pipeline YAML for Foundry evaluation.

    Args:
        output_path: Path to save YAML file
        config: Evaluation configuration

    Returns:
        Path to generated YAML file
    """
    config = config or FoundryEvalConfig()

    evaluators = []
    if config.enable_groundedness:
        evaluators.append("groundedness")
    if config.enable_relevance:
        evaluators.append("relevance")
    if config.enable_completeness:
        evaluators.append("completeness")
    if config.enable_fluency:
        evaluators.append("fluency")
    if config.enable_coherence:
        evaluators.append("coherence")

    spec = create_batch_eval_job_spec(
        name=config.evaluation_name,
        dataset_name=config.dataset_name,
        evaluators=evaluators
    )

    yaml_content = spec.to_yaml()

    with open(output_path, "w") as f:
        f.write(yaml_content)

    logger.info(f"Generated pipeline YAML: {output_path}")
    return output_path


# =============================================================================
# Dataset Registration
# =============================================================================

async def register_eval_dataset(
    project_connection_string: str,
    jsonl_path: str,
    dataset_name: str = "rag_eval_dataset",
    description: str = "RAG evaluation dataset"
) -> str:
    """
    Register evaluation dataset in Foundry.

    Args:
        project_connection_string: Foundry project connection string
        jsonl_path: Path to local JSONL file
        dataset_name: Name for registered dataset
        description: Dataset description

    Returns:
        Dataset ID
    """
    from azure.ai.ml import MLClient
    from azure.ai.ml.entities import Data
    from azure.ai.ml.constants import AssetTypes

    credential = DefaultAzureCredential()

    # Parse connection string for workspace details
    # Format: <region>.<subscription_id>.<resource_group>.<workspace_name>
    parts = project_connection_string.split(".")
    if len(parts) >= 4:
        subscription_id = parts[1]
        resource_group = parts[2]
        workspace_name = parts[3]
    else:
        raise ValueError("Invalid project connection string format")

    ml_client = MLClient(
        credential=credential,
        subscription_id=subscription_id,
        resource_group_name=resource_group,
        workspace_name=workspace_name
    )

    # Create dataset
    data = Data(
        name=dataset_name,
        description=description,
        path=jsonl_path,
        type=AssetTypes.URI_FILE
    )

    registered = ml_client.data.create_or_update(data)
    logger.info(f"Registered dataset: {registered.name} v{registered.version}")

    return f"{registered.name}:{registered.version}"


# =============================================================================
# CI/CD Integration
# =============================================================================

async def run_foundry_ci_evaluation(
    project_connection_string: str,
    dataset_name: str,
    baseline_metrics: Dict[str, float] = None,
    regression_threshold: float = 0.10
) -> Dict[str, Any]:
    """
    Run Foundry evaluation for CI/CD pipelines.

    Args:
        project_connection_string: Foundry connection string
        dataset_name: Registered dataset name
        baseline_metrics: Baseline metrics for comparison
        regression_threshold: Allowed regression percentage

    Returns:
        Results with pass/fail status
    """
    config = FoundryEvalConfig(
        project_connection_string=project_connection_string,
        dataset_name=dataset_name
    )

    evaluator = FoundryCloudEvaluator(config)

    # Define target function (uses deployed RAG endpoint)
    async def rag_target(example: Dict) -> Dict:
        # In CI, this would call your deployed RAG API
        # For cloud eval, Foundry handles the data flow
        return {
            "inputs": {"question": example.get("question", "")},
            "outputs": {"response": ""},  # Populated by Foundry
            "context": ""
        }

    results = await evaluator.submit_cloud_evaluation(
        target_fn=rag_target,
        data=dataset_name
    )

    # Compare to baseline if provided
    passed = True
    regression_detected = []

    if baseline_metrics:
        for metric, baseline in baseline_metrics.items():
            current = results.get("metrics", {}).get(metric, 0)
            if baseline > 0:
                drop = (baseline - current) / baseline
                if drop > regression_threshold:
                    passed = False
                    regression_detected.append({
                        "metric": metric,
                        "baseline": baseline,
                        "current": current,
                        "drop_percent": drop * 100
                    })

    results["passed"] = passed
    results["regression_detected"] = regression_detected

    return results


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    async def main():
        # Generate pipeline YAML
        config = FoundryEvalConfig(
            dataset_name="rag_eval_dataset",
            evaluation_name="rag-prod-eval"
        )

        yaml_path = generate_foundry_eval_pipeline_yaml(
            output_path="foundry-eval-pipeline.yaml",
            config=config
        )

        print(f"Generated: {yaml_path}")

        # Print the spec
        spec = create_batch_eval_job_spec()
        print("\nJob Specification:")
        print(spec.to_yaml())

    asyncio.run(main())
