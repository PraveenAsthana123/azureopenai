"""
Self-Audit and Compliance Reporter for Enterprise RAG Platform.

Implements continuous self-auditing capabilities:
- Grounding verification (hallucination detection)
- PII leak detection in responses
- Cross-tenant contamination checks
- Model drift detection
- Compliance reporting and alerting
"""

import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from collections import defaultdict

from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential
from openai import AsyncAzureOpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AuditCheckType(str, Enum):
    """Types of audit checks."""
    GROUNDING = "grounding"
    PII_LEAK = "pii_leak"
    CROSS_TENANT = "cross_tenant"
    MODEL_DRIFT = "model_drift"
    POLICY_VIOLATION = "policy_violation"
    DATA_QUALITY = "data_quality"
    LATENCY_SLO = "latency_slo"
    ERROR_RATE = "error_rate"


class AuditSeverity(str, Enum):
    """Severity levels for audit findings."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AuditStatus(str, Enum):
    """Status of audit findings."""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


@dataclass
class AuditFinding:
    """Represents a single audit finding."""
    id: str
    check_type: AuditCheckType
    severity: AuditSeverity
    status: AuditStatus
    title: str
    description: str
    affected_resource: str
    tenant_id: str
    timestamp: datetime
    evidence: dict = field(default_factory=dict)
    remediation: str = ""
    auto_remediated: bool = False
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "check_type": self.check_type.value,
            "severity": self.severity.value,
            "status": self.status.value,
            "title": self.title,
            "description": self.description,
            "affected_resource": self.affected_resource,
            "tenant_id": self.tenant_id,
            "timestamp": self.timestamp.isoformat(),
            "evidence": self.evidence,
            "remediation": self.remediation,
            "auto_remediated": self.auto_remediated,
            "metadata": self.metadata
        }


@dataclass
class AuditContext:
    """Context for audit evaluation."""
    query: str
    response: str
    sources: list[dict]
    tenant_id: str
    user_id: str
    session_id: str
    model_id: str
    timestamp: datetime
    latency_ms: float
    metadata: dict = field(default_factory=dict)


class GroundingVerifier:
    """
    Verifies that LLM responses are grounded in source documents.
    Detects hallucinations by checking claim support.
    """

    def __init__(self, openai_client: AsyncAzureOpenAI, model: str = "gpt-4o-mini"):
        self.client = openai_client
        self.model = model
        self.grounding_threshold = 0.7

    async def verify_grounding(self, context: AuditContext) -> list[AuditFinding]:
        """Verify response is grounded in source documents."""
        findings = []

        if not context.sources:
            # No sources but response given - potential hallucination
            finding = AuditFinding(
                id=self._generate_finding_id(context, "no_sources"),
                check_type=AuditCheckType.GROUNDING,
                severity=AuditSeverity.HIGH,
                status=AuditStatus.OPEN,
                title="Response without source documents",
                description="LLM generated response without any source documents to ground the answer",
                affected_resource=f"session:{context.session_id}",
                tenant_id=context.tenant_id,
                timestamp=context.timestamp,
                evidence={
                    "query": context.query,
                    "response_preview": context.response[:500],
                    "source_count": 0
                },
                remediation="Review response for accuracy. Consider adding retrieval fallback."
            )
            findings.append(finding)
            return findings

        # Use LLM to verify grounding
        grounding_result = await self._check_claim_support(context)

        if grounding_result["grounding_score"] < self.grounding_threshold:
            finding = AuditFinding(
                id=self._generate_finding_id(context, "low_grounding"),
                check_type=AuditCheckType.GROUNDING,
                severity=self._score_to_severity(grounding_result["grounding_score"]),
                status=AuditStatus.OPEN,
                title="Low grounding score detected",
                description=f"Response grounding score ({grounding_result['grounding_score']:.2f}) below threshold ({self.grounding_threshold})",
                affected_resource=f"session:{context.session_id}",
                tenant_id=context.tenant_id,
                timestamp=context.timestamp,
                evidence={
                    "grounding_score": grounding_result["grounding_score"],
                    "unsupported_claims": grounding_result.get("unsupported_claims", []),
                    "query": context.query,
                    "response_preview": context.response[:500],
                    "source_count": len(context.sources)
                },
                remediation="Review flagged claims. Consider improving retrieval or adding guardrails."
            )
            findings.append(finding)

        return findings

    async def _check_claim_support(self, context: AuditContext) -> dict:
        """Use LLM to check if claims are supported by sources."""
        source_texts = "\n\n".join([
            f"Source {i+1}: {s.get('content', s.get('text', ''))[:1000]}"
            for i, s in enumerate(context.sources[:5])
        ])

        prompt = f"""Analyze whether the response is grounded in the source documents.

SOURCES:
{source_texts}

RESPONSE TO VERIFY:
{context.response}

Evaluate each factual claim in the response and determine if it's supported by the sources.

Return JSON:
{{
    "grounding_score": 0.0-1.0,
    "total_claims": number,
    "supported_claims": number,
    "unsupported_claims": ["list of unsupported claims"],
    "reasoning": "brief explanation"
}}"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Grounding check failed: {e}")
            return {"grounding_score": 0.5, "error": str(e)}

    def _generate_finding_id(self, context: AuditContext, suffix: str) -> str:
        """Generate deterministic finding ID."""
        data = f"{context.session_id}:{context.timestamp.isoformat()}:{suffix}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _score_to_severity(self, score: float) -> AuditSeverity:
        """Convert grounding score to severity."""
        if score < 0.3:
            return AuditSeverity.CRITICAL
        elif score < 0.5:
            return AuditSeverity.HIGH
        elif score < 0.7:
            return AuditSeverity.MEDIUM
        return AuditSeverity.LOW


class PIIDetector:
    """
    Detects PII leakage in LLM responses.
    Checks for SSN, credit cards, emails, phone numbers, etc.
    """

    # PII patterns
    PATTERNS = {
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone_us": r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "api_key": r"\b(?:sk-|pk-|api[_-]?key[=:\s]+)[A-Za-z0-9]{20,}\b",
        "azure_key": r"\b[A-Za-z0-9+/]{86}==\b",
    }

    # Severity by PII type
    SEVERITY_MAP = {
        "ssn": AuditSeverity.CRITICAL,
        "credit_card": AuditSeverity.CRITICAL,
        "api_key": AuditSeverity.CRITICAL,
        "azure_key": AuditSeverity.CRITICAL,
        "email": AuditSeverity.MEDIUM,
        "phone_us": AuditSeverity.MEDIUM,
        "ip_address": AuditSeverity.LOW,
    }

    def __init__(self, allowed_domains: list[str] = None):
        self.allowed_domains = allowed_domains or []
        self.compiled_patterns = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.PATTERNS.items()
        }

    async def detect_pii(self, context: AuditContext) -> list[AuditFinding]:
        """Detect PII in response."""
        findings = []

        for pii_type, pattern in self.compiled_patterns.items():
            matches = pattern.findall(context.response)

            # Filter allowed domains for emails
            if pii_type == "email" and self.allowed_domains:
                matches = [
                    m for m in matches
                    if not any(m.endswith(d) for d in self.allowed_domains)
                ]

            if matches:
                # Redact actual values for logging
                redacted_matches = [self._redact(m, pii_type) for m in matches]

                finding = AuditFinding(
                    id=self._generate_finding_id(context, pii_type),
                    check_type=AuditCheckType.PII_LEAK,
                    severity=self.SEVERITY_MAP.get(pii_type, AuditSeverity.MEDIUM),
                    status=AuditStatus.OPEN,
                    title=f"PII detected in response: {pii_type}",
                    description=f"Found {len(matches)} instance(s) of {pii_type} in LLM response",
                    affected_resource=f"session:{context.session_id}",
                    tenant_id=context.tenant_id,
                    timestamp=context.timestamp,
                    evidence={
                        "pii_type": pii_type,
                        "count": len(matches),
                        "redacted_samples": redacted_matches[:3],
                        "query": context.query
                    },
                    remediation=f"Review source documents for {pii_type}. Consider adding PII filtering to ingestion pipeline."
                )
                findings.append(finding)

        return findings

    def _redact(self, value: str, pii_type: str) -> str:
        """Redact PII value for safe logging."""
        if pii_type in ["ssn", "credit_card"]:
            return value[:3] + "*" * (len(value) - 7) + value[-4:]
        elif pii_type == "email":
            parts = value.split("@")
            return parts[0][:2] + "***@" + parts[1] if len(parts) == 2 else "***"
        elif pii_type in ["api_key", "azure_key"]:
            return value[:8] + "..." + value[-4:]
        return value[:3] + "***"

    def _generate_finding_id(self, context: AuditContext, pii_type: str) -> str:
        """Generate deterministic finding ID."""
        data = f"{context.session_id}:{context.timestamp.isoformat()}:pii:{pii_type}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]


class CrossTenantChecker:
    """
    Checks for cross-tenant data contamination.
    Ensures responses only contain data from the requesting tenant.
    """

    def __init__(self, cosmos_client: CosmosClient, database_name: str):
        self.cosmos_client = cosmos_client
        self.database_name = database_name
        self._tenant_markers_cache: dict[str, set[str]] = {}

    async def check_contamination(self, context: AuditContext) -> list[AuditFinding]:
        """Check for cross-tenant data contamination."""
        findings = []

        # Verify all sources belong to the requesting tenant
        foreign_sources = []
        for source in context.sources:
            source_tenant = source.get("tenant_id") or source.get("metadata", {}).get("tenant_id")
            if source_tenant and source_tenant != context.tenant_id:
                foreign_sources.append({
                    "source_id": source.get("id", "unknown"),
                    "source_tenant": source_tenant
                })

        if foreign_sources:
            finding = AuditFinding(
                id=self._generate_finding_id(context, "foreign_sources"),
                check_type=AuditCheckType.CROSS_TENANT,
                severity=AuditSeverity.CRITICAL,
                status=AuditStatus.OPEN,
                title="Cross-tenant data contamination detected",
                description=f"Response includes {len(foreign_sources)} source(s) from other tenants",
                affected_resource=f"session:{context.session_id}",
                tenant_id=context.tenant_id,
                timestamp=context.timestamp,
                evidence={
                    "foreign_sources": foreign_sources,
                    "requesting_tenant": context.tenant_id,
                    "query": context.query
                },
                remediation="Immediately review ACL filters. Check index configuration for tenant isolation."
            )
            findings.append(finding)

        # Check for tenant-specific markers in response that shouldn't be there
        contamination = await self._check_tenant_markers(context)
        if contamination:
            finding = AuditFinding(
                id=self._generate_finding_id(context, "tenant_markers"),
                check_type=AuditCheckType.CROSS_TENANT,
                severity=AuditSeverity.HIGH,
                status=AuditStatus.OPEN,
                title="Potential cross-tenant information in response",
                description="Response may contain information belonging to other tenants",
                affected_resource=f"session:{context.session_id}",
                tenant_id=context.tenant_id,
                timestamp=context.timestamp,
                evidence=contamination,
                remediation="Review response content. Check for data leakage in RAG pipeline."
            )
            findings.append(finding)

        return findings

    async def _check_tenant_markers(self, context: AuditContext) -> Optional[dict]:
        """Check for tenant-specific markers that shouldn't appear."""
        # This would check for company names, internal codes, etc.
        # that are unique to other tenants
        # Implementation depends on tenant-specific configuration
        return None

    def _generate_finding_id(self, context: AuditContext, suffix: str) -> str:
        """Generate deterministic finding ID."""
        data = f"{context.session_id}:{context.timestamp.isoformat()}:tenant:{suffix}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]


class ModelDriftDetector:
    """
    Detects model drift by comparing current behavior to baselines.
    Monitors response quality, latency, and output characteristics.
    """

    def __init__(self, cosmos_client: CosmosClient, database_name: str):
        self.cosmos_client = cosmos_client
        self.database_name = database_name
        self._baselines: dict[str, dict] = {}

    async def load_baselines(self, model_id: str) -> dict:
        """Load baseline metrics for a model."""
        if model_id in self._baselines:
            return self._baselines[model_id]

        try:
            database = self.cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client("model_baselines")
            item = await container.read_item(item=model_id, partition_key=model_id)
            self._baselines[model_id] = item
            return item
        except Exception:
            # Return default baselines
            return {
                "avg_response_length": 500,
                "avg_latency_ms": 2000,
                "grounding_score": 0.85,
                "response_length_std": 200,
                "latency_std": 500
            }

    async def detect_drift(self, context: AuditContext, metrics: dict) -> list[AuditFinding]:
        """Detect drift from baseline behavior."""
        findings = []
        baseline = await self.load_baselines(context.model_id)

        # Check response length drift
        response_length = len(context.response)
        expected_length = baseline.get("avg_response_length", 500)
        length_std = baseline.get("response_length_std", 200)

        if abs(response_length - expected_length) > 3 * length_std:
            finding = AuditFinding(
                id=self._generate_finding_id(context, "response_length"),
                check_type=AuditCheckType.MODEL_DRIFT,
                severity=AuditSeverity.MEDIUM,
                status=AuditStatus.OPEN,
                title="Response length drift detected",
                description=f"Response length ({response_length}) deviates significantly from baseline ({expected_length}±{length_std})",
                affected_resource=f"model:{context.model_id}",
                tenant_id=context.tenant_id,
                timestamp=context.timestamp,
                evidence={
                    "current_length": response_length,
                    "baseline_length": expected_length,
                    "baseline_std": length_std,
                    "deviation_sigmas": abs(response_length - expected_length) / length_std
                },
                remediation="Monitor for consistent drift. May indicate prompt injection or model update."
            )
            findings.append(finding)

        # Check latency drift
        expected_latency = baseline.get("avg_latency_ms", 2000)
        latency_std = baseline.get("latency_std", 500)

        if context.latency_ms > expected_latency + 3 * latency_std:
            finding = AuditFinding(
                id=self._generate_finding_id(context, "latency"),
                check_type=AuditCheckType.MODEL_DRIFT,
                severity=AuditSeverity.HIGH if context.latency_ms > 10000 else AuditSeverity.MEDIUM,
                status=AuditStatus.OPEN,
                title="Latency drift detected",
                description=f"Response latency ({context.latency_ms:.0f}ms) exceeds baseline ({expected_latency}±{latency_std}ms)",
                affected_resource=f"model:{context.model_id}",
                tenant_id=context.tenant_id,
                timestamp=context.timestamp,
                evidence={
                    "current_latency_ms": context.latency_ms,
                    "baseline_latency_ms": expected_latency,
                    "baseline_std": latency_std
                },
                remediation="Check model endpoint health. Review for complex queries or rate limiting."
            )
            findings.append(finding)

        return findings

    def _generate_finding_id(self, context: AuditContext, suffix: str) -> str:
        """Generate deterministic finding ID."""
        data = f"{context.session_id}:{context.timestamp.isoformat()}:drift:{suffix}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]


class ComplianceReporter:
    """
    Generates compliance reports and manages audit findings.
    Supports SOC2, HIPAA, GDPR reporting formats.
    """

    def __init__(self, cosmos_client: CosmosClient, database_name: str):
        self.cosmos_client = cosmos_client
        self.database_name = database_name

    async def store_finding(self, finding: AuditFinding) -> None:
        """Store audit finding in Cosmos DB."""
        try:
            database = self.cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client("audit_findings")
            await container.upsert_item(finding.to_dict())
            logger.info(f"Stored audit finding: {finding.id} ({finding.check_type.value})")
        except Exception as e:
            logger.error(f"Failed to store audit finding: {e}")

    async def get_findings(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime,
        check_types: list[AuditCheckType] = None,
        severities: list[AuditSeverity] = None,
        status: list[AuditStatus] = None
    ) -> list[AuditFinding]:
        """Query audit findings with filters."""
        try:
            database = self.cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client("audit_findings")

            query = """
                SELECT * FROM c
                WHERE c.tenant_id = @tenant_id
                AND c.timestamp >= @start_date
                AND c.timestamp <= @end_date
            """
            params = [
                {"name": "@tenant_id", "value": tenant_id},
                {"name": "@start_date", "value": start_date.isoformat()},
                {"name": "@end_date", "value": end_date.isoformat()}
            ]

            if check_types:
                query += " AND ARRAY_CONTAINS(@check_types, c.check_type)"
                params.append({"name": "@check_types", "value": [ct.value for ct in check_types]})

            if severities:
                query += " AND ARRAY_CONTAINS(@severities, c.severity)"
                params.append({"name": "@severities", "value": [s.value for s in severities]})

            if status:
                query += " AND ARRAY_CONTAINS(@statuses, c.status)"
                params.append({"name": "@statuses", "value": [s.value for s in status]})

            findings = []
            async for item in container.query_items(query=query, parameters=params):
                findings.append(self._dict_to_finding(item))

            return findings
        except Exception as e:
            logger.error(f"Failed to query findings: {e}")
            return []

    async def generate_compliance_report(
        self,
        tenant_id: str,
        report_type: str,
        start_date: datetime,
        end_date: datetime
    ) -> dict:
        """Generate compliance report in specified format."""
        findings = await self.get_findings(tenant_id, start_date, end_date)

        # Aggregate by type and severity
        by_type = defaultdict(list)
        by_severity = defaultdict(list)
        for f in findings:
            by_type[f.check_type.value].append(f)
            by_severity[f.severity.value].append(f)

        report = {
            "report_id": hashlib.sha256(f"{tenant_id}:{start_date}:{end_date}:{report_type}".encode()).hexdigest()[:16],
            "tenant_id": tenant_id,
            "report_type": report_type,
            "generated_at": datetime.utcnow().isoformat(),
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_findings": len(findings),
                "by_severity": {k: len(v) for k, v in by_severity.items()},
                "by_type": {k: len(v) for k, v in by_type.items()},
                "open_findings": len([f for f in findings if f.status == AuditStatus.OPEN]),
                "resolved_findings": len([f for f in findings if f.status == AuditStatus.RESOLVED])
            },
            "compliance_status": self._calculate_compliance_status(findings, report_type),
            "findings": [f.to_dict() for f in findings[:100]]  # Limit to 100 in report
        }

        if report_type == "soc2":
            report["soc2_controls"] = self._map_to_soc2_controls(findings)
        elif report_type == "hipaa":
            report["hipaa_safeguards"] = self._map_to_hipaa_safeguards(findings)
        elif report_type == "gdpr":
            report["gdpr_articles"] = self._map_to_gdpr_articles(findings)

        return report

    def _calculate_compliance_status(self, findings: list[AuditFinding], report_type: str) -> dict:
        """Calculate overall compliance status."""
        critical_open = len([
            f for f in findings
            if f.severity == AuditSeverity.CRITICAL and f.status == AuditStatus.OPEN
        ])
        high_open = len([
            f for f in findings
            if f.severity == AuditSeverity.HIGH and f.status == AuditStatus.OPEN
        ])

        if critical_open > 0:
            status = "non_compliant"
            message = f"{critical_open} critical finding(s) require immediate attention"
        elif high_open > 5:
            status = "at_risk"
            message = f"{high_open} high severity findings exceed threshold"
        elif high_open > 0:
            status = "needs_attention"
            message = f"{high_open} high severity finding(s) should be reviewed"
        else:
            status = "compliant"
            message = "No critical or high severity open findings"

        return {
            "status": status,
            "message": message,
            "critical_open": critical_open,
            "high_open": high_open
        }

    def _map_to_soc2_controls(self, findings: list[AuditFinding]) -> dict:
        """Map findings to SOC2 trust service criteria."""
        mapping = {
            "CC6.1": {"name": "Logical Access Controls", "findings": []},
            "CC6.7": {"name": "Data Transmission Protection", "findings": []},
            "CC7.2": {"name": "System Monitoring", "findings": []},
            "CC8.1": {"name": "Change Management", "findings": []},
            "PI1.1": {"name": "Privacy Notice", "findings": []}
        }

        for f in findings:
            if f.check_type == AuditCheckType.CROSS_TENANT:
                mapping["CC6.1"]["findings"].append(f.id)
            elif f.check_type == AuditCheckType.PII_LEAK:
                mapping["PI1.1"]["findings"].append(f.id)
            elif f.check_type == AuditCheckType.MODEL_DRIFT:
                mapping["CC7.2"]["findings"].append(f.id)

        return mapping

    def _map_to_hipaa_safeguards(self, findings: list[AuditFinding]) -> dict:
        """Map findings to HIPAA safeguards."""
        return {
            "access_control": {
                "164.312(a)(1)": len([f for f in findings if f.check_type == AuditCheckType.CROSS_TENANT])
            },
            "audit_controls": {
                "164.312(b)": len([f for f in findings if f.check_type == AuditCheckType.POLICY_VIOLATION])
            },
            "integrity": {
                "164.312(c)(1)": len([f for f in findings if f.check_type == AuditCheckType.GROUNDING])
            }
        }

    def _map_to_gdpr_articles(self, findings: list[AuditFinding]) -> dict:
        """Map findings to GDPR articles."""
        return {
            "article_5": {
                "name": "Principles of Processing",
                "findings": len([f for f in findings if f.check_type in [AuditCheckType.PII_LEAK, AuditCheckType.CROSS_TENANT]])
            },
            "article_25": {
                "name": "Data Protection by Design",
                "findings": len([f for f in findings if f.check_type == AuditCheckType.PII_LEAK])
            },
            "article_32": {
                "name": "Security of Processing",
                "findings": len([f for f in findings if f.check_type == AuditCheckType.CROSS_TENANT])
            }
        }

    def _dict_to_finding(self, d: dict) -> AuditFinding:
        """Convert dict to AuditFinding."""
        return AuditFinding(
            id=d["id"],
            check_type=AuditCheckType(d["check_type"]),
            severity=AuditSeverity(d["severity"]),
            status=AuditStatus(d["status"]),
            title=d["title"],
            description=d["description"],
            affected_resource=d["affected_resource"],
            tenant_id=d["tenant_id"],
            timestamp=datetime.fromisoformat(d["timestamp"]),
            evidence=d.get("evidence", {}),
            remediation=d.get("remediation", ""),
            auto_remediated=d.get("auto_remediated", False),
            metadata=d.get("metadata", {})
        )


class SelfAuditEngine:
    """
    Main self-audit engine that orchestrates all audit checks.
    Runs continuously to monitor RAG platform health and compliance.
    """

    def __init__(
        self,
        cosmos_endpoint: str,
        openai_endpoint: str,
        openai_api_key: str,
        openai_api_version: str = "2024-02-15-preview"
    ):
        self.cosmos_endpoint = cosmos_endpoint
        self.openai_endpoint = openai_endpoint
        self.openai_api_key = openai_api_key
        self.openai_api_version = openai_api_version

        self._cosmos_client: Optional[CosmosClient] = None
        self._openai_client: Optional[AsyncAzureOpenAI] = None

        self.grounding_verifier: Optional[GroundingVerifier] = None
        self.pii_detector: Optional[PIIDetector] = None
        self.cross_tenant_checker: Optional[CrossTenantChecker] = None
        self.drift_detector: Optional[ModelDriftDetector] = None
        self.reporter: Optional[ComplianceReporter] = None

        self._initialized = False

    async def initialize(self) -> None:
        """Initialize audit engine components."""
        if self._initialized:
            return

        credential = DefaultAzureCredential()
        self._cosmos_client = CosmosClient(self.cosmos_endpoint, credential=credential)
        self._openai_client = AsyncAzureOpenAI(
            azure_endpoint=self.openai_endpoint,
            api_key=self.openai_api_key,
            api_version=self.openai_api_version
        )

        self.grounding_verifier = GroundingVerifier(self._openai_client)
        self.pii_detector = PIIDetector(allowed_domains=["@contoso.com", "@internal.corp"])
        self.cross_tenant_checker = CrossTenantChecker(self._cosmos_client, "rag_platform")
        self.drift_detector = ModelDriftDetector(self._cosmos_client, "rag_platform")
        self.reporter = ComplianceReporter(self._cosmos_client, "rag_platform")

        self._initialized = True
        logger.info("Self-audit engine initialized")

    async def audit_response(self, context: AuditContext) -> list[AuditFinding]:
        """Run all audit checks on a single response."""
        if not self._initialized:
            await self.initialize()

        all_findings = []

        # Run checks in parallel
        check_tasks = [
            self.grounding_verifier.verify_grounding(context),
            self.pii_detector.detect_pii(context),
            self.cross_tenant_checker.check_contamination(context),
            self.drift_detector.detect_drift(context, {})
        ]

        results = await asyncio.gather(*check_tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Audit check failed: {result}")
            elif isinstance(result, list):
                all_findings.extend(result)

        # Store all findings
        for finding in all_findings:
            await self.reporter.store_finding(finding)

        return all_findings

    async def run_scheduled_audit(
        self,
        tenant_id: str,
        hours_back: int = 24
    ) -> dict:
        """Run scheduled audit on historical data."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(hours=hours_back)

        # Generate compliance report
        report = await self.reporter.generate_compliance_report(
            tenant_id=tenant_id,
            report_type="soc2",
            start_date=start_date,
            end_date=end_date
        )

        logger.info(
            f"Scheduled audit complete for {tenant_id}: "
            f"{report['summary']['total_findings']} findings"
        )

        return report

    async def close(self) -> None:
        """Close connections."""
        if self._cosmos_client:
            await self._cosmos_client.close()
        if self._openai_client:
            await self._openai_client.close()


# Example usage
async def main():
    """Example usage of self-audit engine."""
    engine = SelfAuditEngine(
        cosmos_endpoint="https://your-cosmos.documents.azure.com:443/",
        openai_endpoint="https://your-openai.openai.azure.com/",
        openai_api_key="your-api-key"
    )

    await engine.initialize()

    # Audit a single response
    context = AuditContext(
        query="What is our refund policy?",
        response="Our refund policy allows returns within 30 days. Contact support@contoso.com for assistance.",
        sources=[
            {"id": "doc1", "content": "Returns are accepted within 30 days of purchase.", "tenant_id": "tenant-123"}
        ],
        tenant_id="tenant-123",
        user_id="user-456",
        session_id="session-789",
        model_id="gpt-4o",
        timestamp=datetime.utcnow(),
        latency_ms=1500
    )

    findings = await engine.audit_response(context)
    print(f"Found {len(findings)} issues")

    for finding in findings:
        print(f"  - [{finding.severity.value}] {finding.title}")

    await engine.close()


if __name__ == "__main__":
    asyncio.run(main())
