"""
Automated Data Classification Pipeline for Enterprise RAG Platform.

Implements automatic sensitivity classification:
- Document-level classification
- Chunk-level sensitivity scoring
- PII/PHI detection integration
- Classification rules engine
- Label propagation
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


class ClassificationLevel(str, Enum):
    """Data classification levels."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    TOP_SECRET = "top_secret"


class DataCategory(str, Enum):
    """Categories of data content."""
    GENERAL = "general"
    FINANCIAL = "financial"
    HR = "hr"
    LEGAL = "legal"
    TECHNICAL = "technical"
    CUSTOMER = "customer"
    HEALTH = "health"
    SECURITY = "security"


class PIIType(str, Enum):
    """Types of PII that affect classification."""
    NONE = "none"
    BASIC = "basic"  # Names, emails
    SENSITIVE = "sensitive"  # SSN, DOB
    HEALTH = "health"  # PHI
    FINANCIAL = "financial"  # Bank accounts, cards


@dataclass
class ClassificationResult:
    """Result of document/chunk classification."""
    classification: ClassificationLevel
    sensitivity_score: int  # 0-100
    category: DataCategory
    pii_types: list[PIIType]
    confidence: float
    reasons: list[str]
    labels: list[str]
    requires_review: bool = False
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "classification": self.classification.value,
            "sensitivity_score": self.sensitivity_score,
            "category": self.category.value,
            "pii_types": [p.value for p in self.pii_types],
            "confidence": self.confidence,
            "reasons": self.reasons,
            "labels": self.labels,
            "requires_review": self.requires_review,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None
        }


class ClassificationRule:
    """A single classification rule."""

    def __init__(
        self,
        name: str,
        keywords: list[str] = None,
        patterns: list[str] = None,
        classification: ClassificationLevel = ClassificationLevel.INTERNAL,
        category: DataCategory = DataCategory.GENERAL,
        sensitivity_boost: int = 0,
        priority: int = 5
    ):
        self.name = name
        self.keywords = [k.lower() for k in (keywords or [])]
        self.patterns = [re.compile(p, re.IGNORECASE) for p in (patterns or [])]
        self.classification = classification
        self.category = category
        self.sensitivity_boost = sensitivity_boost
        self.priority = priority

    def matches(self, text: str) -> tuple[bool, list[str]]:
        """Check if rule matches text."""
        text_lower = text.lower()
        matched_keywords = [k for k in self.keywords if k in text_lower]
        matched_patterns = [p.pattern for p in self.patterns if p.search(text)]

        matches = matched_keywords + matched_patterns
        return len(matches) > 0, matches


class ClassificationRulesEngine:
    """Engine for applying classification rules."""

    def __init__(self):
        self.rules: list[ClassificationRule] = []
        self._initialize_default_rules()

    def _initialize_default_rules(self):
        """Initialize default enterprise classification rules."""

        # Financial data rules
        self.add_rule(ClassificationRule(
            name="financial_statements",
            keywords=["revenue", "profit", "loss", "earnings", "ebitda", "balance sheet"],
            patterns=[r"q[1-4]\s+\d{4}\s+results", r"\$[\d,]+\s*(million|billion)"],
            classification=ClassificationLevel.CONFIDENTIAL,
            category=DataCategory.FINANCIAL,
            sensitivity_boost=30,
            priority=8
        ))

        self.add_rule(ClassificationRule(
            name="budget_data",
            keywords=["budget", "forecast", "projection", "cost center"],
            classification=ClassificationLevel.CONFIDENTIAL,
            category=DataCategory.FINANCIAL,
            sensitivity_boost=20,
            priority=7
        ))

        # HR data rules
        self.add_rule(ClassificationRule(
            name="salary_compensation",
            keywords=["salary", "compensation", "bonus", "stock options", "equity grant"],
            patterns=[r"annual\s+salary", r"base\s+pay"],
            classification=ClassificationLevel.RESTRICTED,
            category=DataCategory.HR,
            sensitivity_boost=40,
            priority=9
        ))

        self.add_rule(ClassificationRule(
            name="employee_records",
            keywords=["employee id", "hire date", "termination", "performance review"],
            classification=ClassificationLevel.CONFIDENTIAL,
            category=DataCategory.HR,
            sensitivity_boost=25,
            priority=7
        ))

        self.add_rule(ClassificationRule(
            name="recruitment",
            keywords=["candidate", "interview", "job offer", "background check"],
            classification=ClassificationLevel.CONFIDENTIAL,
            category=DataCategory.HR,
            sensitivity_boost=20,
            priority=6
        ))

        # Legal data rules
        self.add_rule(ClassificationRule(
            name="contracts",
            keywords=["agreement", "contract", "terms and conditions", "liability"],
            patterns=[r"party\s+of\s+the\s+first", r"hereinafter\s+referred"],
            classification=ClassificationLevel.CONFIDENTIAL,
            category=DataCategory.LEGAL,
            sensitivity_boost=25,
            priority=7
        ))

        self.add_rule(ClassificationRule(
            name="litigation",
            keywords=["lawsuit", "plaintiff", "defendant", "settlement", "arbitration"],
            classification=ClassificationLevel.RESTRICTED,
            category=DataCategory.LEGAL,
            sensitivity_boost=35,
            priority=8
        ))

        # Customer data rules
        self.add_rule(ClassificationRule(
            name="customer_pii",
            keywords=["customer name", "customer address", "customer phone"],
            patterns=[r"customer\s+id", r"account\s+number"],
            classification=ClassificationLevel.CONFIDENTIAL,
            category=DataCategory.CUSTOMER,
            sensitivity_boost=30,
            priority=8
        ))

        # Health data rules (PHI)
        self.add_rule(ClassificationRule(
            name="health_records",
            keywords=["diagnosis", "treatment", "medication", "medical history", "patient"],
            patterns=[r"icd-?\d+", r"cpt\s+code"],
            classification=ClassificationLevel.RESTRICTED,
            category=DataCategory.HEALTH,
            sensitivity_boost=50,
            priority=10
        ))

        # Security data rules
        self.add_rule(ClassificationRule(
            name="credentials",
            keywords=["password", "api key", "secret", "token", "private key"],
            patterns=[r"-----BEGIN.*KEY-----", r"[A-Za-z0-9+/]{40,}"],
            classification=ClassificationLevel.RESTRICTED,
            category=DataCategory.SECURITY,
            sensitivity_boost=60,
            priority=10
        ))

        self.add_rule(ClassificationRule(
            name="security_policy",
            keywords=["security policy", "access control", "firewall rules", "vulnerability"],
            classification=ClassificationLevel.CONFIDENTIAL,
            category=DataCategory.SECURITY,
            sensitivity_boost=25,
            priority=7
        ))

        # General internal
        self.add_rule(ClassificationRule(
            name="internal_memo",
            keywords=["internal use only", "not for distribution", "confidential"],
            classification=ClassificationLevel.INTERNAL,
            category=DataCategory.GENERAL,
            sensitivity_boost=10,
            priority=5
        ))

    def add_rule(self, rule: ClassificationRule):
        """Add a classification rule."""
        self.rules.append(rule)
        # Sort by priority descending
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def evaluate(self, text: str) -> tuple[list[ClassificationRule], int]:
        """Evaluate text against all rules."""
        matched_rules = []
        total_sensitivity_boost = 0

        for rule in self.rules:
            matches, match_details = rule.matches(text)
            if matches:
                matched_rules.append(rule)
                total_sensitivity_boost += rule.sensitivity_boost

        return matched_rules, total_sensitivity_boost


class PIIClassifier:
    """Classifies PII types in text for classification purposes."""

    PATTERNS = {
        PIIType.BASIC: [
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
            r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",  # Phone
        ],
        PIIType.SENSITIVE: [
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
            r"\b(?:DOB|Date of Birth)[\s:]+\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b",  # DOB
            r"\b[A-Z]{1,2}\d{6,9}\b",  # Passport
        ],
        PIIType.FINANCIAL: [
            r"\b(?:\d{4}[-\s]?){3}\d{4}\b",  # Credit card
            r"\b\d{9,17}\b(?=.*(?:account|routing|iban))",  # Bank account
        ],
        PIIType.HEALTH: [
            r"\b(?:diagnosis|treatment|medication|prescription)\b",
            r"\bicd-?\d+\b",
            r"\bpatient\s+(?:id|name|record)\b",
        ]
    }

    def __init__(self):
        self.compiled_patterns = {
            pii_type: [re.compile(p, re.IGNORECASE) for p in patterns]
            for pii_type, patterns in self.PATTERNS.items()
        }

    def classify(self, text: str) -> list[PIIType]:
        """Classify PII types present in text."""
        found_types = []

        for pii_type, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    found_types.append(pii_type)
                    break

        return found_types if found_types else [PIIType.NONE]


class LLMClassifier:
    """Uses LLM for advanced content classification."""

    def __init__(self, openai_client: AsyncAzureOpenAI, model: str = "gpt-4o-mini"):
        self.client = openai_client
        self.model = model

    async def classify(self, text: str, context: dict = None) -> dict:
        """Use LLM to classify content."""
        context_info = json.dumps(context) if context else "None"

        prompt = f"""Classify this document content for enterprise data governance.

Content (first 2000 chars):
{text[:2000]}

Document context:
{context_info}

Analyze and return JSON:
{{
    "classification": "public|internal|confidential|restricted",
    "category": "general|financial|hr|legal|technical|customer|health|security",
    "sensitivity_score": 0-100,
    "contains_pii": true/false,
    "pii_types": ["basic", "sensitive", "financial", "health"],
    "key_topics": ["list of main topics"],
    "risk_factors": ["specific risks identified"],
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}

Guidelines:
- public: Safe for anyone
- internal: Company employees only
- confidential: Need-to-know basis
- restricted: Highly sensitive, limited access"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            return {}


class DataClassificationPipeline:
    """
    Main pipeline for automated data classification.
    Combines rules, PII detection, and LLM classification.
    """

    def __init__(
        self,
        openai_client: AsyncAzureOpenAI,
        use_llm: bool = True,
        confidence_threshold: float = 0.7
    ):
        self.rules_engine = ClassificationRulesEngine()
        self.pii_classifier = PIIClassifier()
        self.llm_classifier = LLMClassifier(openai_client) if use_llm else None
        self.confidence_threshold = confidence_threshold

    async def classify_document(
        self,
        content: str,
        metadata: dict = None
    ) -> ClassificationResult:
        """Classify an entire document."""
        metadata = metadata or {}
        reasons = []
        labels = []

        # 1. Rule-based classification
        matched_rules, sensitivity_boost = self.rules_engine.evaluate(content)

        # Get highest priority classification from rules
        rule_classification = ClassificationLevel.PUBLIC
        rule_category = DataCategory.GENERAL
        if matched_rules:
            rule_classification = max(
                [r.classification for r in matched_rules],
                key=lambda c: list(ClassificationLevel).index(c)
            )
            rule_category = matched_rules[0].category
            reasons.extend([f"Rule: {r.name}" for r in matched_rules[:5]])
            labels.extend([r.name for r in matched_rules])

        # 2. PII classification
        pii_types = self.pii_classifier.classify(content)
        if PIIType.NONE not in pii_types:
            reasons.append(f"Contains PII: {[p.value for p in pii_types]}")

        # Calculate PII sensitivity boost
        pii_boost = 0
        if PIIType.HEALTH in pii_types:
            pii_boost = 50
        elif PIIType.SENSITIVE in pii_types:
            pii_boost = 40
        elif PIIType.FINANCIAL in pii_types:
            pii_boost = 30
        elif PIIType.BASIC in pii_types:
            pii_boost = 15

        # 3. LLM classification (if enabled)
        llm_result = {}
        if self.llm_classifier:
            llm_result = await self.llm_classifier.classify(content, metadata)

        # 4. Combine results
        base_score = 20  # Start at internal level
        total_sensitivity = base_score + sensitivity_boost + pii_boost

        # Adjust based on LLM if available
        if llm_result:
            llm_score = llm_result.get("sensitivity_score", 50)
            llm_confidence = llm_result.get("confidence", 0.5)

            # Weighted average with LLM
            total_sensitivity = int(
                total_sensitivity * (1 - llm_confidence * 0.5) +
                llm_score * (llm_confidence * 0.5)
            )

            if llm_result.get("key_topics"):
                labels.extend(llm_result["key_topics"][:3])

            if llm_result.get("risk_factors"):
                reasons.extend([f"Risk: {r}" for r in llm_result["risk_factors"][:3]])

        # Clamp sensitivity score
        total_sensitivity = max(0, min(100, total_sensitivity))

        # Determine final classification
        if total_sensitivity >= 80:
            final_classification = ClassificationLevel.RESTRICTED
        elif total_sensitivity >= 60:
            final_classification = ClassificationLevel.CONFIDENTIAL
        elif total_sensitivity >= 30:
            final_classification = ClassificationLevel.INTERNAL
        else:
            final_classification = ClassificationLevel.PUBLIC

        # Use LLM classification if confident
        if llm_result and llm_result.get("confidence", 0) > self.confidence_threshold:
            llm_class = llm_result.get("classification", "").lower()
            if llm_class in [c.value for c in ClassificationLevel]:
                final_classification = ClassificationLevel(llm_class)

        # Determine category
        final_category = rule_category
        if llm_result and llm_result.get("category"):
            llm_cat = llm_result.get("category", "").lower()
            if llm_cat in [c.value for c in DataCategory]:
                final_category = DataCategory(llm_cat)

        # Calculate confidence
        confidence = 0.5  # Base confidence
        if matched_rules:
            confidence += 0.2
        if llm_result:
            confidence = max(confidence, llm_result.get("confidence", 0.5))

        # Flag for review if uncertain
        requires_review = (
            confidence < 0.7 or
            final_classification in [ClassificationLevel.RESTRICTED, ClassificationLevel.TOP_SECRET]
        )

        return ClassificationResult(
            classification=final_classification,
            sensitivity_score=total_sensitivity,
            category=final_category,
            pii_types=pii_types,
            confidence=confidence,
            reasons=reasons[:10],
            labels=list(set(labels))[:10],
            requires_review=requires_review
        )

    async def classify_chunk(
        self,
        chunk_content: str,
        document_classification: ClassificationResult = None
    ) -> ClassificationResult:
        """Classify a single chunk, optionally inheriting from document."""
        # Quick rule-based classification for chunks
        matched_rules, sensitivity_boost = self.rules_engine.evaluate(chunk_content)
        pii_types = self.pii_classifier.classify(chunk_content)

        # Start with document classification if available
        if document_classification:
            base_score = document_classification.sensitivity_score
            base_classification = document_classification.classification
            base_category = document_classification.category
        else:
            base_score = 20
            base_classification = ClassificationLevel.INTERNAL
            base_category = DataCategory.GENERAL

        # Adjust based on chunk content
        chunk_sensitivity = base_score + sensitivity_boost

        # PII boost
        if PIIType.NONE not in pii_types:
            chunk_sensitivity += 20

        chunk_sensitivity = max(0, min(100, chunk_sensitivity))

        # Determine chunk classification
        if chunk_sensitivity >= 80:
            chunk_classification = ClassificationLevel.RESTRICTED
        elif chunk_sensitivity >= 60:
            chunk_classification = ClassificationLevel.CONFIDENTIAL
        elif chunk_sensitivity >= 30:
            chunk_classification = ClassificationLevel.INTERNAL
        else:
            chunk_classification = ClassificationLevel.PUBLIC

        # Chunk can't be less restricted than document
        classification_order = list(ClassificationLevel)
        if document_classification:
            doc_level = classification_order.index(document_classification.classification)
            chunk_level = classification_order.index(chunk_classification)
            if chunk_level < doc_level:
                chunk_classification = document_classification.classification

        return ClassificationResult(
            classification=chunk_classification,
            sensitivity_score=chunk_sensitivity,
            category=matched_rules[0].category if matched_rules else base_category,
            pii_types=pii_types,
            confidence=0.8 if matched_rules else 0.6,
            reasons=[r.name for r in matched_rules[:3]],
            labels=[],
            requires_review=False
        )


# Example usage
async def main():
    """Example usage of classification pipeline."""
    from openai import AsyncAzureOpenAI

    client = AsyncAzureOpenAI(
        azure_endpoint="https://your-openai.openai.azure.com/",
        api_key="your-api-key",
        api_version="2024-02-15-preview"
    )

    pipeline = DataClassificationPipeline(client, use_llm=True)

    # Classify a document
    content = """
    Q4 2024 Financial Results Summary

    Revenue: $5.2 billion (up 15% YoY)
    Net Profit: $890 million
    EBITDA: $1.2 billion

    Employee compensation adjustments will be processed in January.
    Contact HR at hr@company.com for questions.
    """

    result = await pipeline.classify_document(content)

    print(f"Classification: {result.classification.value}")
    print(f"Sensitivity Score: {result.sensitivity_score}")
    print(f"Category: {result.category.value}")
    print(f"PII Types: {[p.value for p in result.pii_types]}")
    print(f"Reasons: {result.reasons}")
    print(f"Requires Review: {result.requires_review}")


if __name__ == "__main__":
    asyncio.run(main())
