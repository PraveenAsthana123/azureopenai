"""
AI Safety and DLP (Data Loss Prevention) Module for Enterprise RAG Platform.

Implements comprehensive safety controls:
- Input content safety filtering
- Output content safety validation
- PII/PHI detection and redaction
- DLP policy enforcement
- Prompt injection detection
- Jailbreak prevention
"""

import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from openai import AsyncAzureOpenAI

logger = logging.getLogger(__name__)


class SafetyCategory(str, Enum):
    """Content safety categories."""
    VIOLENCE = "violence"
    HATE = "hate"
    SEXUAL = "sexual"
    SELF_HARM = "self_harm"
    JAILBREAK = "jailbreak"
    PROMPT_INJECTION = "prompt_injection"
    PII_LEAK = "pii_leak"
    CONFIDENTIAL_DATA = "confidential_data"
    UNAUTHORIZED_ACCESS = "unauthorized_access"


class SafetyAction(str, Enum):
    """Actions to take on safety violations."""
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    REDACT = "redact"
    ESCALATE = "escalate"


class SeverityLevel(str, Enum):
    """Severity levels for violations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SafetyResult:
    """Result of safety check."""
    is_safe: bool
    action: SafetyAction
    categories: list[SafetyCategory] = field(default_factory=list)
    severity: SeverityLevel = SeverityLevel.LOW
    details: dict = field(default_factory=dict)
    redacted_content: Optional[str] = None
    original_hash: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "action": self.action.value,
            "categories": [c.value for c in self.categories],
            "severity": self.severity.value,
            "details": self.details,
            "has_redaction": self.redacted_content is not None
        }


class PromptInjectionDetector:
    """
    Detects prompt injection attempts in user input.
    Uses pattern matching and LLM-based detection.
    """

    # Known prompt injection patterns
    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?(previous|above|prior)\s+instructions?",
        r"disregard\s+(all\s+)?(previous|above|prior)",
        r"forget\s+(all\s+)?(previous|everything)",
        r"you\s+are\s+now\s+(a|an)\s+",
        r"pretend\s+(you\s+are|to\s+be)",
        r"act\s+as\s+(if|a|an)",
        r"roleplay\s+as",
        r"simulate\s+(being|a)",
        r"new\s+instructions?:",
        r"system\s+prompt:",
        r"reveal\s+(your|the)\s+(system|instructions?|prompt)",
        r"print\s+(your|the|all)\s+(instructions?|prompt|system)",
        r"show\s+me\s+(your|the)\s+(source|code|prompt)",
        r"what\s+(are|is)\s+your\s+(instructions?|prompt|system)",
        r"bypass\s+(the\s+)?(filter|safety|security)",
        r"jailbreak",
        r"dan\s+mode",
        r"developer\s+mode",
        r"sudo\s+",
        r"admin\s+access",
        r"override\s+(safety|security|filter)",
    ]

    def __init__(self, openai_client: AsyncAzureOpenAI = None):
        self.openai_client = openai_client
        self.compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.INJECTION_PATTERNS
        ]

    def check_patterns(self, text: str) -> tuple[bool, list[str]]:
        """Check for known injection patterns."""
        matches = []
        for i, pattern in enumerate(self.compiled_patterns):
            if pattern.search(text):
                matches.append(self.INJECTION_PATTERNS[i])

        return len(matches) > 0, matches

    async def check_with_llm(self, text: str) -> tuple[bool, float]:
        """Use LLM to detect sophisticated injection attempts."""
        if not self.openai_client:
            return False, 0.0

        prompt = f"""Analyze this text for prompt injection attempts.

Text to analyze:
{text[:1000]}

A prompt injection is an attempt to:
- Override system instructions
- Extract system prompts
- Bypass safety filters
- Make the AI behave differently than intended

Return JSON:
{{
    "is_injection": true/false,
    "confidence": 0.0-1.0,
    "technique": "description of technique if detected"
}}"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            return result.get("is_injection", False), result.get("confidence", 0.0)
        except Exception as e:
            logger.error(f"LLM injection check failed: {e}")
            return False, 0.0


class PIIDetector:
    """
    Detects and optionally redacts PII (Personally Identifiable Information).
    """

    PII_PATTERNS = {
        "ssn": {
            "pattern": r"\b\d{3}-\d{2}-\d{4}\b",
            "severity": SeverityLevel.CRITICAL,
            "redact_with": "[SSN REDACTED]"
        },
        "credit_card": {
            "pattern": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
            "severity": SeverityLevel.CRITICAL,
            "redact_with": "[CARD REDACTED]"
        },
        "email": {
            "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "severity": SeverityLevel.MEDIUM,
            "redact_with": "[EMAIL REDACTED]"
        },
        "phone_us": {
            "pattern": r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
            "severity": SeverityLevel.MEDIUM,
            "redact_with": "[PHONE REDACTED]"
        },
        "ip_address": {
            "pattern": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            "severity": SeverityLevel.LOW,
            "redact_with": "[IP REDACTED]"
        },
        "date_of_birth": {
            "pattern": r"\b(?:DOB|Date of Birth|Born)[\s:]+\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b",
            "severity": SeverityLevel.HIGH,
            "redact_with": "[DOB REDACTED]"
        },
        "passport": {
            "pattern": r"\b[A-Z]{1,2}\d{6,9}\b",
            "severity": SeverityLevel.CRITICAL,
            "redact_with": "[PASSPORT REDACTED]"
        },
        "bank_account": {
            "pattern": r"\b\d{8,17}\b(?=.*(?:account|routing|iban|swift))",
            "severity": SeverityLevel.CRITICAL,
            "redact_with": "[ACCOUNT REDACTED]"
        }
    }

    def __init__(self, allowed_email_domains: list[str] = None):
        self.allowed_email_domains = allowed_email_domains or []
        self.compiled_patterns = {
            name: re.compile(info["pattern"], re.IGNORECASE)
            for name, info in self.PII_PATTERNS.items()
        }

    def detect(self, text: str) -> dict[str, list[str]]:
        """Detect all PII in text."""
        found_pii = {}

        for pii_type, pattern in self.compiled_patterns.items():
            matches = pattern.findall(text)

            # Filter allowed email domains
            if pii_type == "email" and self.allowed_email_domains:
                matches = [
                    m for m in matches
                    if not any(m.lower().endswith(d.lower()) for d in self.allowed_email_domains)
                ]

            if matches:
                found_pii[pii_type] = matches

        return found_pii

    def redact(self, text: str, pii_types: list[str] = None) -> tuple[str, dict]:
        """Redact PII from text."""
        redacted_text = text
        redaction_log = {}

        types_to_redact = pii_types or list(self.PII_PATTERNS.keys())

        for pii_type in types_to_redact:
            if pii_type not in self.compiled_patterns:
                continue

            pattern = self.compiled_patterns[pii_type]
            matches = pattern.findall(redacted_text)

            if matches:
                redact_with = self.PII_PATTERNS[pii_type]["redact_with"]
                redacted_text = pattern.sub(redact_with, redacted_text)
                redaction_log[pii_type] = len(matches)

        return redacted_text, redaction_log

    def get_severity(self, detected_pii: dict[str, list[str]]) -> SeverityLevel:
        """Get highest severity from detected PII."""
        if not detected_pii:
            return SeverityLevel.LOW

        severity_order = [
            SeverityLevel.LOW,
            SeverityLevel.MEDIUM,
            SeverityLevel.HIGH,
            SeverityLevel.CRITICAL
        ]

        max_severity = SeverityLevel.LOW
        for pii_type in detected_pii.keys():
            if pii_type in self.PII_PATTERNS:
                pii_severity = self.PII_PATTERNS[pii_type]["severity"]
                if severity_order.index(pii_severity) > severity_order.index(max_severity):
                    max_severity = pii_severity

        return max_severity


class ContentSafetyFilter:
    """
    Main content safety filter using Azure AI Content Safety or LLM-based detection.
    """

    def __init__(
        self,
        openai_client: AsyncAzureOpenAI,
        content_safety_endpoint: str = None,
        content_safety_key: str = None
    ):
        self.openai_client = openai_client
        self.content_safety_endpoint = content_safety_endpoint
        self.content_safety_key = content_safety_key

    async def check_content(self, text: str) -> dict[SafetyCategory, float]:
        """Check content for safety violations."""
        # Use LLM-based content safety check
        prompt = f"""Analyze this text for content safety issues.

Text:
{text[:2000]}

Check for:
- Violence or threats
- Hate speech or discrimination
- Inappropriate sexual content
- Self-harm encouragement
- Attempts to bypass safety

Return JSON with scores 0.0-1.0:
{{
    "violence": 0.0,
    "hate": 0.0,
    "sexual": 0.0,
    "self_harm": 0.0,
    "bypass_attempt": 0.0,
    "reasoning": "brief explanation"
}}"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)

            return {
                SafetyCategory.VIOLENCE: result.get("violence", 0.0),
                SafetyCategory.HATE: result.get("hate", 0.0),
                SafetyCategory.SEXUAL: result.get("sexual", 0.0),
                SafetyCategory.SELF_HARM: result.get("self_harm", 0.0),
                SafetyCategory.JAILBREAK: result.get("bypass_attempt", 0.0)
            }
        except Exception as e:
            logger.error(f"Content safety check failed: {e}")
            return {}


class DLPPolicy:
    """
    Data Loss Prevention policy configuration.
    """

    def __init__(
        self,
        name: str,
        blocked_keywords: list[str] = None,
        blocked_patterns: list[str] = None,
        max_sensitivity_score: int = 80,
        allowed_classifications: list[str] = None
    ):
        self.name = name
        self.blocked_keywords = blocked_keywords or []
        self.blocked_patterns = [re.compile(p, re.IGNORECASE) for p in (blocked_patterns or [])]
        self.max_sensitivity_score = max_sensitivity_score
        self.allowed_classifications = allowed_classifications or ["public", "internal"]

    def evaluate(self, text: str, metadata: dict = None) -> tuple[bool, list[str]]:
        """Evaluate text against DLP policy."""
        violations = []
        metadata = metadata or {}

        # Check blocked keywords
        text_lower = text.lower()
        for keyword in self.blocked_keywords:
            if keyword.lower() in text_lower:
                violations.append(f"Blocked keyword: {keyword}")

        # Check blocked patterns
        for pattern in self.blocked_patterns:
            if pattern.search(text):
                violations.append(f"Blocked pattern match")

        # Check sensitivity score
        sensitivity = metadata.get("sensitivity_score", 0)
        if sensitivity > self.max_sensitivity_score:
            violations.append(f"Sensitivity score {sensitivity} exceeds max {self.max_sensitivity_score}")

        # Check classification
        classification = metadata.get("classification", "public")
        if classification.lower() not in [c.lower() for c in self.allowed_classifications]:
            violations.append(f"Classification '{classification}' not allowed")

        return len(violations) == 0, violations


class AISafetyEngine:
    """
    Main AI Safety Engine that orchestrates all safety checks.
    """

    def __init__(
        self,
        openai_client: AsyncAzureOpenAI,
        pii_allowed_domains: list[str] = None,
        dlp_policies: list[DLPPolicy] = None
    ):
        self.openai_client = openai_client
        self.injection_detector = PromptInjectionDetector(openai_client)
        self.pii_detector = PIIDetector(pii_allowed_domains or [])
        self.content_filter = ContentSafetyFilter(openai_client)
        self.dlp_policies = dlp_policies or []

        # Safety thresholds
        self.content_threshold = 0.7  # Block if score > 0.7
        self.injection_threshold = 0.8

    async def check_input(
        self,
        text: str,
        user_id: str,
        tenant_id: str,
        metadata: dict = None
    ) -> SafetyResult:
        """
        Check input text for safety violations before RAG processing.
        """
        categories = []
        details = {"checks_performed": []}

        # 1. Check for prompt injection
        pattern_match, patterns = self.injection_detector.check_patterns(text)
        if pattern_match:
            categories.append(SafetyCategory.PROMPT_INJECTION)
            details["injection_patterns"] = patterns

        # LLM-based injection check
        is_injection, confidence = await self.injection_detector.check_with_llm(text)
        details["checks_performed"].append("injection_detection")
        if is_injection and confidence > self.injection_threshold:
            categories.append(SafetyCategory.PROMPT_INJECTION)
            details["injection_confidence"] = confidence

        # 2. Content safety check
        content_scores = await self.content_filter.check_content(text)
        details["checks_performed"].append("content_safety")
        details["content_scores"] = {k.value: v for k, v in content_scores.items()}

        for category, score in content_scores.items():
            if score > self.content_threshold:
                categories.append(category)

        # 3. PII check (for input - warn but don't block)
        detected_pii = self.pii_detector.detect(text)
        details["checks_performed"].append("pii_detection")
        if detected_pii:
            details["pii_detected"] = list(detected_pii.keys())

        # 4. DLP policy check
        for policy in self.dlp_policies:
            is_compliant, violations = policy.evaluate(text, metadata)
            if not is_compliant:
                categories.append(SafetyCategory.CONFIDENTIAL_DATA)
                details[f"dlp_{policy.name}_violations"] = violations

        # Determine action and severity
        if SafetyCategory.PROMPT_INJECTION in categories:
            action = SafetyAction.BLOCK
            severity = SeverityLevel.CRITICAL
        elif any(c in categories for c in [SafetyCategory.VIOLENCE, SafetyCategory.HATE]):
            action = SafetyAction.BLOCK
            severity = SeverityLevel.HIGH
        elif categories:
            action = SafetyAction.WARN
            severity = SeverityLevel.MEDIUM
        else:
            action = SafetyAction.ALLOW
            severity = SeverityLevel.LOW

        return SafetyResult(
            is_safe=action == SafetyAction.ALLOW,
            action=action,
            categories=categories,
            severity=severity,
            details=details,
            original_hash=hashlib.sha256(text.encode()).hexdigest()[:16]
        )

    async def check_output(
        self,
        text: str,
        user_id: str,
        tenant_id: str,
        source_chunks: list[dict] = None,
        user_clearance: list[str] = None
    ) -> SafetyResult:
        """
        Check output text before returning to user.
        Apply redaction if necessary.
        """
        categories = []
        details = {"checks_performed": []}
        redacted_text = text

        # 1. PII detection and redaction
        detected_pii = self.pii_detector.detect(text)
        details["checks_performed"].append("pii_detection")

        if detected_pii:
            categories.append(SafetyCategory.PII_LEAK)
            details["pii_found"] = {k: len(v) for k, v in detected_pii.items()}

            # Redact if user doesn't have clearance
            user_clearance = user_clearance or []
            pii_to_redact = [
                pii_type for pii_type in detected_pii.keys()
                if f"pii:{pii_type}" not in user_clearance
            ]

            if pii_to_redact:
                redacted_text, redaction_log = self.pii_detector.redact(text, pii_to_redact)
                details["redactions"] = redaction_log

        # 2. Content safety check
        content_scores = await self.content_filter.check_content(text)
        details["checks_performed"].append("content_safety")

        for category, score in content_scores.items():
            if score > self.content_threshold:
                categories.append(category)

        # 3. Check source chunk confidentiality
        if source_chunks:
            details["checks_performed"].append("source_classification")
            for chunk in source_chunks:
                classification = chunk.get("metadata", {}).get("classification", "public")
                if classification.lower() in ["confidential", "restricted"]:
                    if f"classification:{classification}" not in (user_clearance or []):
                        categories.append(SafetyCategory.CONFIDENTIAL_DATA)
                        details["unauthorized_classification"] = classification
                        break

        # Determine action
        if SafetyCategory.CONFIDENTIAL_DATA in categories:
            action = SafetyAction.BLOCK
            severity = SeverityLevel.CRITICAL
        elif SafetyCategory.PII_LEAK in categories and detected_pii:
            # Redact and allow
            action = SafetyAction.REDACT
            severity = self.pii_detector.get_severity(detected_pii)
        elif categories:
            action = SafetyAction.WARN
            severity = SeverityLevel.MEDIUM
        else:
            action = SafetyAction.ALLOW
            severity = SeverityLevel.LOW

        return SafetyResult(
            is_safe=action in [SafetyAction.ALLOW, SafetyAction.REDACT],
            action=action,
            categories=categories,
            severity=severity,
            details=details,
            redacted_content=redacted_text if redacted_text != text else None,
            original_hash=hashlib.sha256(text.encode()).hexdigest()[:16]
        )

    def get_safe_response(self, category: SafetyCategory) -> str:
        """Get appropriate safe response for blocked content."""
        responses = {
            SafetyCategory.PROMPT_INJECTION: "I cannot process that request.",
            SafetyCategory.VIOLENCE: "I'm not able to help with that topic.",
            SafetyCategory.HATE: "I'm not able to help with that topic.",
            SafetyCategory.SEXUAL: "I'm not able to help with that topic.",
            SafetyCategory.SELF_HARM: "I'm not able to help with that topic. If you need support, please reach out to a trusted person.",
            SafetyCategory.CONFIDENTIAL_DATA: "You don't have access to view this information.",
            SafetyCategory.UNAUTHORIZED_ACCESS: "You're not authorized to access this content.",
            SafetyCategory.PII_LEAK: "Some information has been redacted for privacy."
        }
        return responses.get(category, "I cannot process that request.")


# Example usage
async def main():
    """Example usage of AI Safety Engine."""
    from openai import AsyncAzureOpenAI

    client = AsyncAzureOpenAI(
        azure_endpoint="https://your-openai.openai.azure.com/",
        api_key="your-api-key",
        api_version="2024-02-15-preview"
    )

    safety = AISafetyEngine(
        openai_client=client,
        pii_allowed_domains=["@company.com"],
        dlp_policies=[
            DLPPolicy(
                name="standard",
                blocked_keywords=["top secret", "classified"],
                max_sensitivity_score=70
            )
        ]
    )

    # Check input
    input_result = await safety.check_input(
        text="What is the salary for John Smith? His SSN is 123-45-6789.",
        user_id="user@company.com",
        tenant_id="tenant-1"
    )
    print(f"Input safe: {input_result.is_safe}, Action: {input_result.action.value}")

    # Check output
    output_result = await safety.check_output(
        text="John's salary is $150,000. Contact him at john@gmail.com.",
        user_id="user@company.com",
        tenant_id="tenant-1"
    )
    print(f"Output safe: {output_result.is_safe}, Redacted: {output_result.redacted_content}")


if __name__ == "__main__":
    asyncio.run(main())
