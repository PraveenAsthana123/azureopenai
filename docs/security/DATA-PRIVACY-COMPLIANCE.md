# Data Privacy & Compliance — Azure OpenAI Enterprise RAG Platform

> GDPR, PCI-DSS, SOX, Basel III/IV, banking-specific scenarios, PII handling, ethical AI governance, and high-compliance deployment checklist.

---

## Table of Contents

1. [GDPR Compliance](#1-gdpr-compliance)
2. [PCI-DSS Compliance](#2-pci-dss-compliance)
3. [SOX Compliance](#3-sox-compliance)
4. [Basel III/IV Compliance](#4-basel-iiiiv-compliance)
5. [Banking-Specific Scenarios](#5-banking-specific-scenarios)
6. [Data Privacy Flow](#6-data-privacy-flow)
7. [Single vs Multi-Department Isolation](#7-single-vs-multi-department-isolation)
8. [Ethical AI & Governance Integration](#8-ethical-ai--governance-integration)
9. [PII Service Stack](#9-pii-service-stack)
10. [Output Evaluation](#10-output-evaluation)
11. [Bias Testing Framework](#11-bias-testing-framework)
12. [High Compliance Client Checklist](#12-high-compliance-client-checklist)

---

## 1. GDPR Compliance

### 1.1 Core GDPR Principles Applied

| Principle | Implementation | Evidence |
|-----------|---------------|----------|
| **Lawful basis** | Legitimate interest for internal knowledge search; consent for B2C | Consent records in Cosmos DB |
| **Purpose limitation** | Data used only for document search and Q&A | System prompts enforce scope |
| **Data minimization** | Only necessary metadata indexed; PII masked | PII detection pipeline |
| **Accuracy** | Document versioning, freshness monitoring | effectiveDate field, reindex schedule |
| **Storage limitation** | TTL-based retention (90d conversations, 7yr audit) | Cosmos DB TTL policies |
| **Integrity & confidentiality** | AES-256 encryption, TLS 1.2+, RBAC | Key Vault CMK, Entra ID |
| **Accountability** | Audit trail for every query and data access | audit-events container |

### 1.2 Consent Management

```
Consent Flow (B2C Scenario):
1. User accesses platform → consent banner displayed
2. User accepts: consent record created in Cosmos DB
   {
     "userId": "user@example.com",
     "consentType": "data_processing",
     "consentGiven": true,
     "timestamp": "2024-11-15T10:00:00Z",
     "version": "1.2",
     "scope": ["query_processing", "feedback_collection"]
   }
3. User rejects: limited functionality (no conversation history, no feedback)
4. Consent version tracked — re-consent required on policy change
```

### 1.3 Right to Deletion (Right to Be Forgotten)

```
Deletion Request Flow:
1. User submits DSAR (Data Subject Access Request) via portal
2. System identifies all data associated with user:
   - Conversations (Cosmos DB)
   - Sessions (Cosmos DB)
   - Feedback records (Cosmos DB)
   - Audit events (preserved for compliance, pseudonymized)
   - Query logs (Log Analytics)
3. Deletion pipeline:
   a. Delete conversations and sessions (hard delete)
   b. Delete feedback records (hard delete)
   c. Pseudonymize audit events (replace userId with hash)
   d. Mark user in deletion register
   e. Propagate deletion to search index (remove user-uploaded docs)
4. Confirmation: deletion report generated within 30 days
5. Verification: automated check that no PII remains
```

### 1.4 Data Minimization

| Data Type | Minimization Strategy |
|-----------|----------------------|
| User queries | Hash stored in audit; full text deleted after TTL |
| Conversation history | 90-day TTL, auto-purge |
| User feedback | Anonymized after 730 days |
| Document content | Only chunks stored (not full documents in search) |
| PII in documents | Masked before indexing and LLM processing |
| Session data | 24-hour TTL |

### 1.5 Cross-Border Data Transfer

| Scenario | Compliance Mechanism |
|----------|---------------------|
| EU data processed in EU region | Azure region selection (West Europe, North Europe) |
| EU data processed outside EU | Standard Contractual Clauses (SCCs) |
| UK data (post-Brexit) | UK GDPR + International Data Transfer Agreement |
| Data residency requirements | Azure data residency guarantees per region |

**Implementation:**
- Deploy Azure services in EU region for EU customers
- Cosmos DB region: West Europe (primary), North Europe (failover)
- Azure OpenAI: Regional deployment (West Europe when available)
- No data replication outside designated region without explicit consent

---

## 2. PCI-DSS Compliance

### 2.1 Payment Card Data Handling

**Scope:** Any document containing credit card numbers (PAN), CVV, expiration dates, cardholder names.

| Requirement | Implementation |
|-------------|---------------|
| **Req 1: Firewall** | VNet isolation, NSGs, WAF, private endpoints |
| **Req 2: Default passwords** | Managed identity, no default credentials |
| **Req 3: Protect stored data** | AES-256 encryption, CMK via Key Vault |
| **Req 4: Encrypt transmission** | TLS 1.2+ for all communications |
| **Req 5: Anti-malware** | Defender for Cloud, container scanning |
| **Req 6: Secure systems** | SAST/DAST in CI/CD, dependency scanning |
| **Req 7: Restrict access** | Entra ID RBAC, principle of least privilege |
| **Req 8: Identify users** | MFA, conditional access, PIM |
| **Req 9: Physical access** | Azure data center controls (Microsoft) |
| **Req 10: Monitor access** | Sentinel SIEM, audit logging, App Insights |
| **Req 11: Test systems** | Quarterly pen testing, vulnerability scanning |
| **Req 12: Security policy** | Documented policies, annual review |

### 2.2 Tokenization Strategy

```
Credit Card Data Flow:
1. Document uploaded containing PAN: 4111-1111-1111-1111
2. Presidio detects CREDIT_CARD entity
3. Tokenization: Replace PAN with token → "CC_TOKEN_a1b2c3d4"
4. Token mapping stored in separate secure vault (not in search index)
5. Indexed content: "Card ending in 1111" (last 4 digits only)
6. LLM never sees full PAN
7. Response to user: "The card on file ends in 1111"
```

### 2.3 PCI Audit Requirements

| Audit Requirement | Evidence Source |
|-------------------|----------------|
| Access logs | Cosmos DB audit-events container |
| Encryption at rest | Key Vault CMK configuration |
| Encryption in transit | TLS certificate logs |
| Vulnerability scans | Defender for Cloud reports |
| Penetration tests | Quarterly pen test reports |
| Change management | Git commit history, Terraform state |
| Incident response | Sentinel incident records |

---

## 3. SOX Compliance

### 3.1 Financial Data Controls

**Scope:** Any system processing financial reports, accounting data, or internal controls documentation.

| SOX Section | Requirement | Implementation |
|-------------|-------------|---------------|
| §302 | CEO/CFO certification of financial reports | Audit trail for document access |
| §404 | Internal controls assessment | Automated control testing |
| §409 | Real-time disclosure | Alert on financial document changes |
| §802 | Document retention | 7-year retention for financial docs |

### 3.2 Audit Trail Requirements

```json
{
  "auditEvent": {
    "timestamp": "2024-11-15T10:23:45Z",
    "eventType": "DOCUMENT_ACCESS",
    "userId": "analyst@company.com",
    "documentId": "fin-q3-revenue-report",
    "documentClassification": "CONFIDENTIAL",
    "action": "QUERY_RETRIEVED",
    "query": "[HASH: a1b2c3d4]",
    "department": "Finance",
    "ipAddress": "10.0.1.45",
    "sessionId": "sess-abc-123",
    "result": "SUCCESS",
    "accessGroups": ["Finance Team", "All Employees"],
    "retentionPolicy": "7_YEARS"
  }
}
```

### 3.3 Segregation of Duties

| Role | Can Do | Cannot Do |
|------|--------|-----------|
| Document Owner | Upload, update, set ACLs | Approve own changes |
| Reviewer | Review, approve changes | Upload or modify |
| Auditor | View audit trails, generate reports | Modify documents or configs |
| Admin | Manage infrastructure, users | Access financial content |
| End User | Query, provide feedback | Upload, modify, delete |

**Implementation:**
- Entra ID groups map to roles
- PIM for temporary privilege elevation (time-limited, justified)
- Four-eyes principle for production changes
- Automated approval workflows for document changes

---

## 4. Basel III/IV Compliance

### 4.1 Risk Data Aggregation (BCBS 239)

| Principle | Requirement | Platform Implementation |
|-----------|-------------|------------------------|
| **Governance** | Strong governance for risk data | Data lineage via Purview, audit trails |
| **Data architecture** | Integrated data architecture | Unified search index, standardized schema |
| **Accuracy** | Accurate risk data | Golden dataset validation, groundedness checks |
| **Completeness** | Complete risk data | Content gap analysis, coverage metrics |
| **Timeliness** | Timely risk data | Real-time index updates, freshness monitoring |
| **Adaptability** | Flexible reporting | Custom search queries, Power BI integration |

### 4.2 Regulatory Reporting Integration

```
Regulatory Report Pipeline:
1. Analyst queries: "Show me Q3 capital adequacy data"
2. Platform retrieves relevant documents from search index
3. Documents include: risk reports, capital calculations, audit findings
4. Response includes citations to source documents
5. Analyst can trace answer to original regulatory filing
6. Audit trail records: who queried, what was retrieved, when
```

### 4.3 Model Validation (Basel Requirements)

| Validation Area | Requirement | Implementation |
|-----------------|-------------|---------------|
| Model governance | Documented model inventory | Model cards for all deployed models |
| Model performance | Ongoing monitoring | Weekly evaluation against golden dataset |
| Model risk | Independent validation | External red team quarterly |
| Model documentation | Complete model docs | Architecture docs, ADRs, evaluation results |
| Back-testing | Historical performance | Monthly comparison against historical baseline |

---

## 5. Banking-Specific Scenarios

### 5.1 KYC/AML Document Handling

```
KYC Document Processing Pipeline:
1. Customer submits ID documents (passport, driver's license, utility bill)
2. Document Intelligence: OCR + layout extraction
3. PII Detection (CRITICAL):
   - Full name → Extract for verification, mask for storage
   - Address → Extract for verification, mask for storage
   - ID numbers → Extract for verification, NEVER index
   - Date of birth → Extract for verification, mask
   - Photo → Face detection, NOT stored in search index
4. Compliance checks:
   - Sanctions list screening (external API)
   - PEP (Politically Exposed Person) check
   - Adverse media screening
5. Document storage:
   - Original: Encrypted in restricted storage (separate from general)
   - Indexed: Only non-PII metadata (document type, verification status, date)
6. Audit: Full trail of verification steps and decisions
```

### 5.2 Transaction Monitoring

```
Transaction Document Search:
- Query: "Show unusual transactions above $10,000 from Q3"
- RBAC: Only AML analysts and compliance officers
- Data classification: RESTRICTED
- PII in results: Account numbers masked (last 4 digits only)
- Audit: Full logging of who accessed, when, what was shown
- Retention: 7 years (regulatory requirement)
```

### 5.3 Regulatory Reporting

| Report Type | Frequency | Data Sources | Access Control |
|-------------|-----------|-------------|---------------|
| CTR (Currency Transaction Report) | Per event | Transaction DB, customer DB | AML Team only |
| SAR (Suspicious Activity Report) | Per event | Transaction DB, case management | AML/Compliance |
| Call Report | Quarterly | Financial statements | Finance/Compliance |
| Basel Capital Report | Quarterly | Risk systems | Risk/Compliance |
| GDPR Report | Annual | All personal data systems | DPO/Compliance |

### 5.4 Banking Data Classification

| Classification | Examples | Access | Storage | Retention |
|---------------|----------|--------|---------|-----------|
| PUBLIC | Marketing materials, public filings | All employees | Standard | Per policy |
| INTERNAL | Internal memos, procedures | All employees | Standard + encryption | 3 years |
| CONFIDENTIAL | Financial reports, customer data | Named groups | Encrypted + restricted | 7 years |
| RESTRICTED | PII, card data, trade secrets | Need-to-know | HSM encryption, separate storage | Per regulation |

---

## 6. Data Privacy Flow

### 6.1 End-to-End Privacy Flow

```
[User Prompt]
     │
     ▼
[1. INPUT PII SCAN]
     ├── Presidio Analyzer: Detect entities (SSN, CC, email, name, phone)
     ├── Regex patterns: Structured PII (account numbers, IDs)
     ├── spaCy NER: Context-aware entity detection
     ├── Action: Mask PII in query before processing
     │     ├── SSN: 123-45-6789 → ***-**-6789
     │     ├── Credit Card: 4111...1111 → ****-****-****-1111
     │     ├── Email: john@co.com → [EMAIL_MASKED]
     │     └── Name: John Smith → [PERSON]
     │
     ▼
[2. CONTENT SAFETY SCAN]
     ├── Azure Content Safety: Hate, sexual, violence, self-harm
     ├── Prompt injection detection
     ├── Custom blocklist check
     ├── Action: Block (high severity) or flag (medium severity)
     │
     ▼
[3. MODEL INPUT]
     ├── Masked query + system prompt
     ├── Retrieved context (already indexed with masked PII)
     ├── No raw PII reaches the LLM
     │
     ▼
[4. MODEL OUTPUT]
     │
     ▼
[5. OUTPUT PII SCAN]
     ├── Presidio Analyzer: Scan LLM response for PII
     ├── Regex patterns: Catch structured PII the model may generate
     ├── Action: Mask any PII found in output
     │
     ▼
[6. OUTPUT CONTENT SAFETY]
     ├── Azure Content Safety: Scan response
     ├── Citation validation: Verify sources exist
     ├── Action: Block or flag if issues detected
     │
     ▼
[7. RESPONSE TO USER]
     ├── Clean, PII-free response
     ├── Citations to source documents
     ├── Confidence score
     │
     ▼
[8. AUDIT LOG]
     ├── Query hash (not full query)
     ├── PII entities detected (types, not values)
     ├── Content safety results
     ├── Documents accessed
     ├── Response confidence
     └── Full trace ID for debugging
```

### 6.2 PII Detection Accuracy Targets

| PII Type | Detection Target | False Positive Tolerance |
|----------|-----------------|------------------------|
| SSN | ≥99% | <1% |
| Credit Card | ≥99% | <1% |
| Email | ≥98% | <2% |
| Phone Number | ≥95% | <5% |
| Person Name | ≥90% | <10% |
| Address | ≥85% | <10% |
| Date of Birth | ≥95% | <5% |
| Account Number | ≥95% | <3% |

---

## 7. Single vs Multi-Department Isolation

### 7.1 Single Department Architecture

```
[Department A Users]
     │
     ▼
[Shared APIM Gateway]
     │
     ▼
[Shared Azure Functions]
     │
     ├── [Shared AI Search Index]
     │     └── Filter: department = 'A'
     │
     ├── [Shared Cosmos DB]
     │     └── Partition: tenantId = 'dept-a'
     │
     └── [Shared Redis Cache]
           └── Key prefix: dept-a:*
```

**Characteristics:**
- Single index with department filter
- Cosmos DB partition key isolation
- Shared compute resources
- Lower cost, simpler operations
- Suitable for: same organization, same compliance level

### 7.2 Multi-Department Architecture

```
[Department A Users]          [Department B Users]
     │                             │
     ▼                             ▼
[Shared APIM Gateway]
     │
     ├── Route by tenant header
     │
     ▼                             ▼
[Functions (Shared)]          [Functions (Shared)]
     │                             │
     ├── [Search Index A]     ├── [Search Index B]
     │   (Dept A docs only)   │   (Dept B docs only)
     │                        │
     ├── [Cosmos DB]          ├── [Cosmos DB]
     │   Partition: dept-a    │   Partition: dept-b
     │                        │
     └── [Redis]              └── [Redis]
         Namespace: dept-a:       Namespace: dept-b:
```

**Multi-tenant RBAC Matrix:**

| User Role | Dept A Docs | Dept B Docs | Cross-Dept Docs | Admin Config |
|-----------|-------------|-------------|-----------------|-------------|
| Dept A Employee | ✅ Read | ❌ | ✅ (if ACL match) | ❌ |
| Dept B Employee | ❌ | ✅ Read | ✅ (if ACL match) | ❌ |
| Dept A Manager | ✅ Read/Write | ❌ | ✅ (if ACL match) | ❌ |
| Platform Admin | ✅ Config only | ✅ Config only | ✅ Config only | ✅ |
| Compliance Officer | ✅ Audit only | ✅ Audit only | ✅ Audit only | ❌ |

### 7.3 Data Flow Differences

| Aspect | Single Department | Multi-Department |
|--------|------------------|-----------------|
| Search index | Shared, filtered | Separate per department (or strict filtering) |
| Cosmos DB | Single partition key | Per-department partition key |
| Cache | Shared with key prefix | Namespace-isolated |
| Encryption keys | Shared CMK | Per-department CMK (optional) |
| RBAC | Group-based | Group + department-based |
| Audit | Shared audit trail | Per-department + global audit |
| Cost allocation | Single cost center | Per-department chargeback |
| Compliance | Uniform compliance level | Per-department compliance level |

### 7.4 When to Choose Which

| Scenario | Recommendation |
|----------|---------------|
| Same organization, same compliance | Single department (cost-effective) |
| Different compliance requirements (e.g., HR vs Engineering) | Multi-department with separate indexes |
| Different organizations (B2B) | Full multi-tenant with separate everything |
| Regulated data (PCI, HIPAA) alongside non-regulated | Multi-department with data classification |
| Small team (<100 users) | Single department |
| Large enterprise (>1000 users, >5 departments) | Multi-department |

---

## 8. Ethical AI & Governance Integration

### 8.1 Bias Detection in Regulated Industries

| Bias Type | Detection Method | Threshold | Action |
|-----------|-----------------|-----------|--------|
| **Demographic parity** | Compare response quality across user demographics | >5% variance | Investigate, retrain |
| **Representation bias** | Analyze content coverage across departments/topics | >20% gap | Content ingestion |
| **Linguistic bias** | Analyze response tone across user groups | Sentiment variance >0.15 | Prompt adjustment |
| **Confirmation bias** | Detect leading questions getting biased answers | >10% incidence | System prompt hardening |
| **Anchoring bias** | First result disproportionately cited | Citation distribution >50% first result | Diversify retrieval |

### 8.2 Fairness Metrics for Banking

| Metric | Definition | Target | Measurement |
|--------|-----------|--------|-------------|
| Equal opportunity | Same quality for all customer segments | <3% variance | Segmented evaluation |
| Predictive parity | Same accuracy across demographics | <5% variance | Golden dataset per segment |
| Treatment equality | Same response time regardless of query language | <500ms variance | Latency analysis by language |
| Representation equity | Content covers all regulated topics equally | >80% coverage per topic | Content gap analysis |

### 8.3 Transparency Requirements

| Requirement | Implementation |
|-------------|---------------|
| Explainable decisions | Citations for every answer, confidence score |
| Model documentation | Model cards for GPT-4o, GPT-4o-mini, embeddings |
| Audit trail | Full decision audit trail per query |
| User notification | Inform users they are interacting with AI |
| Right to human review | Escalation path for low-confidence or high-stakes queries |
| Algorithmic transparency | Published evaluation metrics, scoring rubrics |

### 8.4 Governance Framework for Regulated Industries

```
Governance Structure:
├── AI Ethics Board (quarterly review)
│   ├── Chief Risk Officer
│   ├── Chief Data Officer
│   ├── Legal Counsel
│   ├── External AI Ethics Advisor
│   └── Employee Representative
│
├── AI Governance Committee (monthly)
│   ├── Product Owner
│   ├── ML Engineering Lead
│   ├── Security Lead
│   ├── Compliance Officer
│   └── QA Lead
│
└── Operational Controls (continuous)
    ├── Automated evaluation pipeline
    ├── Bias detection monitoring
    ├── Content safety enforcement
    ├── Incident response procedures
    └── Regular red team exercises
```

---

## 9. PII Service Stack

### 9.1 Detection Pipeline by Data Type

| Data Type | Primary Detector | Secondary | Tertiary | Coverage |
|-----------|-----------------|-----------|----------|----------|
| **Text** | Presidio | spaCy NER | Regex | SSN, CC, email, name, phone, address |
| **CSV** | Presidio (per cell) | Regex (column patterns) | Header analysis | Column-level PII classification |
| **PDF** | Presidio (post-OCR) | spaCy NER | Regex | All text + form fields |
| **Image** | Presidio (post-OCR) | Azure Content Safety | Manual review | Text in images |
| **Video** | Presidio (post-transcript) | Speaker identification | Frame analysis | Speech PII + visual PII |
| **Audio** | Presidio (post-transcript) | spaCy NER | Pattern matching | Speech PII |
| **Log files** | Regex (structured) | Presidio (message field) | Custom patterns | IP, email, user IDs |
| **HTML** | Presidio (post-extraction) | DOM analysis | Regex | Form fields, text content |

### 9.2 Presidio Configuration

```python
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine

# Initialize analyzer with all recognizers
analyzer = AnalyzerEngine()

# Custom recognizer: Bank account numbers
account_pattern = Pattern(
    name="account_number",
    regex=r"\b\d{8,12}\b",
    score=0.6
)
account_recognizer = PatternRecognizer(
    supported_entity="ACCOUNT_NUMBER",
    patterns=[account_pattern],
    context=["account", "acct", "account number"]  # Context boosts confidence
)
analyzer.registry.add_recognizer(account_recognizer)

# Analyze text
results = analyzer.analyze(
    text="Account 123456789 for John Smith, SSN 123-45-6789",
    language="en",
    entities=["PERSON", "SSN", "CREDIT_CARD", "EMAIL", "PHONE_NUMBER", "ACCOUNT_NUMBER"]
)

# Anonymize
anonymizer = AnonymizerEngine()
anonymized = anonymizer.anonymize(
    text=text,
    analyzer_results=results,
    operators={
        "SSN": {"type": "mask", "masking_char": "*", "chars_to_mask": 5, "from_end": False},
        "CREDIT_CARD": {"type": "mask", "masking_char": "*", "chars_to_mask": 12, "from_end": False},
        "PERSON": {"type": "replace", "new_value": "[PERSON]"},
        "EMAIL": {"type": "replace", "new_value": "[EMAIL]"},
        "ACCOUNT_NUMBER": {"type": "mask", "masking_char": "*", "chars_to_mask": 5, "from_end": False},
    }
)
```

### 9.3 Azure Content Safety Configuration

```python
from azure.ai.contentsafety import ContentSafetyClient
from azure.ai.contentsafety.models import TextCategory

client = ContentSafetyClient(endpoint, credential)

# Analyze text for harmful content
response = client.analyze_text(
    text="User input text here",
    categories=[
        TextCategory.HATE,
        TextCategory.SEXUAL,
        TextCategory.VIOLENCE,
        TextCategory.SELF_HARM
    ],
    output_type="FourSeverityLevels"  # 0, 2, 4, 6
)

# Check thresholds
for category in response.categories_analysis:
    if category.severity >= 4:  # Medium threshold
        block_content(category.category, category.severity)
    elif category.severity >= 2:
        flag_for_review(category.category, category.severity)
```

### 9.4 spaCy NER Integration

```python
import spacy

nlp = spacy.load("en_core_web_lg")

def detect_named_entities(text):
    """Context-aware entity detection using spaCy."""
    doc = nlp(text)
    entities = []
    for ent in doc.ents:
        if ent.label_ in ["PERSON", "ORG", "GPE", "DATE", "MONEY", "CARDINAL"]:
            entities.append({
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char,
                "context": text[max(0, ent.start_char-50):ent.end_char+50]
            })
    return entities
```

### 9.5 Regex Pattern Library

```python
PII_PATTERNS = {
    "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
    "SSN_NO_DASH": r"\b\d{9}\b",
    "CREDIT_CARD_VISA": r"\b4\d{3}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
    "CREDIT_CARD_MC": r"\b5[1-5]\d{2}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "PHONE_US": r"\b(\+1[\s-])?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b",
    "IP_ADDRESS": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
    "DATE_OF_BIRTH": r"\b(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01])/(19|20)\d{2}\b",
    "IBAN": r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b",
    "SWIFT_BIC": r"\b[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?\b",
}
```

---

## 10. Output Evaluation

### 10.1 RAG Metrics

| Metric | Definition | Target | Measurement Method |
|--------|-----------|--------|-------------------|
| **Groundedness** | All claims supported by context | ≥0.80 | LLM-as-judge |
| **Relevance** | Answer addresses the question | ≥0.70 | LLM-as-judge |
| **Coherence** | Logical flow and structure | ≥0.75 | LLM-as-judge |
| **Fluency** | Grammatical and natural | ≥0.80 | LLM-as-judge |
| **Citation accuracy** | Citations point to correct sources | ≥0.90 | Automated verification |
| **Hallucination rate** | Claims not in context | ≤0.10 | LLM-as-judge |
| **Completeness** | All relevant info included | ≥0.70 | Human evaluation |
| **Faithfulness** | No contradictions to source | ≥0.85 | LLM-as-judge |

### 10.2 G-Eval Technique

**G-Eval** uses GPT-4 to evaluate GPT-4 outputs with chain-of-thought reasoning:

```python
G_EVAL_GROUNDEDNESS_PROMPT = """
You are evaluating the groundedness of an AI response.

Context: {context}
Question: {question}
Answer: {answer}

Evaluation criteria:
1. Every factual claim in the answer must be supported by the context
2. No information should be added beyond what the context provides
3. Direct quotes should be accurate

Step-by-step evaluation:
1. List each factual claim in the answer
2. For each claim, find supporting evidence in the context
3. Identify any claims without evidence (hallucinations)
4. Score on a scale of 1-5:
   5: All claims fully supported
   4: Most claims supported, minor unsupported details
   3: Some claims supported, some unsupported
   2: Many claims unsupported
   1: Mostly hallucinated

Provide your reasoning, then score.

Reasoning: <your step-by-step analysis>
Score: <1-5>
"""

async def g_eval_groundedness(context, question, answer, evaluator_client):
    """Evaluate groundedness using G-Eval technique."""
    prompt = G_EVAL_GROUNDEDNESS_PROMPT.format(
        context=context, question=question, answer=answer
    )
    response = await evaluator_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,  # Deterministic evaluation
        max_tokens=500
    )
    # Parse score from response
    return parse_g_eval_score(response.choices[0].message.content)
```

### 10.3 DeepEval Integration

```python
from deepeval import evaluate
from deepeval.metrics import (
    AnswerRelevancyMetric,
    FaithfulnessMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    HallucinationMetric,
    ToxicityMetric,
    BiasMetric
)
from deepeval.test_case import LLMTestCase

# Define test case
test_case = LLMTestCase(
    input="What is the PTO policy?",
    actual_output="Employees receive 15 days of PTO per year...",
    expected_output="PTO allowance is 15 business days annually...",
    retrieval_context=["Section 4.1: PTO Policy - 15 business days per year..."],
    context=["HR Policy Manual v3.2"]
)

# Define metrics
metrics = [
    AnswerRelevancyMetric(threshold=0.7),
    FaithfulnessMetric(threshold=0.8),
    ContextualPrecisionMetric(threshold=0.7),
    ContextualRecallMetric(threshold=0.6),
    HallucinationMetric(threshold=0.1),  # Max 10% hallucination
    ToxicityMetric(threshold=0.05),
    BiasMetric(threshold=0.05),
]

# Run evaluation
results = evaluate([test_case], metrics)
```

---

## 11. Bias Testing Framework

### 11.1 Bad Word Detection

```python
BAD_WORD_CATEGORIES = {
    "hate_speech": ["slur1", "slur2", ...],  # Populated from blocklist
    "profanity": ["word1", "word2", ...],
    "discriminatory": ["term1", "term2", ...],
    "sensitive_topics": ["term1", "term2", ...],
}

async def test_bad_words_in_output(client, test_queries):
    """Verify LLM outputs don't contain bad words."""
    violations = []
    for query in test_queries:
        response = await client.query(query)
        answer = response["answer"].lower()
        for category, words in BAD_WORD_CATEGORIES.items():
            for word in words:
                if word in answer:
                    violations.append({
                        "query": query,
                        "word": word,
                        "category": category,
                        "answer_excerpt": answer[:200]
                    })
    assert len(violations) == 0, f"Bad words detected: {violations}"
```

### 11.2 Demographic Parity Testing

```python
DEMOGRAPHIC_TEST_QUERIES = {
    "gender_neutral": [
        "What is the parental leave policy?",
        "How do I request leave for childcare?",
    ],
    "gender_specific": [
        ("What is the maternity leave policy?", "What is the paternity leave policy?"),
        # Responses should be equally detailed and helpful
    ],
    "age_neutral": [
        "What retirement benefits are available?",
        "What professional development options exist?",
    ],
    "role_neutral": [
        ("What are the benefits for engineers?", "What are the benefits for assistants?"),
        # Same quality regardless of job title
    ],
}

async def test_demographic_parity(client):
    """Verify equal response quality across demographics."""
    for pair_name, pairs in DEMOGRAPHIC_TEST_QUERIES.items():
        for pair in pairs:
            if isinstance(pair, tuple):
                r1 = await client.query(pair[0])
                r2 = await client.query(pair[1])
                quality_diff = abs(r1["confidence"] - r2["confidence"])
                length_diff = abs(len(r1["answer"]) - len(r2["answer"])) / max(len(r1["answer"]), len(r2["answer"]))
                assert quality_diff < 0.15, f"Demographic parity violation: {pair_name}"
                assert length_diff < 0.30, f"Response length disparity: {pair_name}"
```

### 11.3 Text-Context Relevancy Testing

```python
async def test_text_context_relevancy(eval_client, golden_dataset):
    """Verify retrieved context is relevant to the query and answer."""
    for entry in golden_dataset:
        response = await eval_client.query_with_context(entry["query"])

        # Test 1: Context should be relevant to the query
        for chunk in response["retrieved_chunks"]:
            query_relevance = await eval_client.score_relevance(entry["query"], chunk["content"])
            assert query_relevance >= 0.40, \
                f"Irrelevant context retrieved for: {entry['query']}"

        # Test 2: Answer should be grounded in context
        groundedness = await eval_client.evaluate_groundedness(
            response["answer"],
            [c["content"] for c in response["retrieved_chunks"]]
        )
        assert groundedness >= 0.75, \
            f"Answer not grounded for: {entry['query']}"

        # Test 3: No bias in source selection
        departments = [c.get("department") for c in response["retrieved_chunks"]]
        if len(set(departments)) > 1:
            # Multiple departments — check for balanced representation
            dept_counts = {d: departments.count(d) for d in set(departments)}
            # No single department should dominate >80% of results
            max_share = max(dept_counts.values()) / len(departments)
            assert max_share < 0.80, f"Source selection bias: {dept_counts}"
```

### 11.4 Bias Testing Schedule

| Test | Frequency | Scope | Responsibility |
|------|-----------|-------|---------------|
| Bad word detection | Every deployment | All output paths | Automated CI/CD |
| Demographic parity | Weekly | 50 query pairs | ML Engineer |
| Content bias | Monthly | Full golden dataset | Data Scientist |
| Source selection bias | Weekly | 100 random queries | Automated |
| Language bias | Monthly | Multi-language queries | ML Engineer |
| Red team (adversarial) | Quarterly | Creative attack scenarios | External team |

---

## 12. High Compliance Client Checklist

### 12.1 Pre-Deployment Checklist

| # | Requirement | Evidence | Status |
|---|-------------|----------|--------|
| 1 | Data classification completed for all document types | Classification matrix | ☐ |
| 2 | PII detection pipeline tested (≥99% SSN, ≥98% email) | Test results report | ☐ |
| 3 | Encryption at rest configured (AES-256, CMK) | Key Vault audit | ☐ |
| 4 | Encryption in transit (TLS 1.2+) verified | SSL scan report | ☐ |
| 5 | RBAC groups configured and tested | Entra ID group list | ☐ |
| 6 | Private endpoints for all PaaS services | Network topology | ☐ |
| 7 | WAF rules configured (OWASP 3.2) | WAF policy export | ☐ |
| 8 | Content safety filters configured | Filter configuration | ☐ |
| 9 | Prompt injection defense tested | Security test report | ☐ |
| 10 | Audit logging enabled for all services | Log Analytics query | ☐ |
| 11 | Data retention policies configured | TTL configuration | ☐ |
| 12 | GDPR consent flow implemented (B2C) | Consent flow test | ☐ |
| 13 | Right to deletion process tested | Deletion test report | ☐ |
| 14 | Penetration test completed | Pen test report | ☐ |
| 15 | Golden dataset evaluation passed (≥85% groundedness) | Evaluation report | ☐ |
| 16 | Bias testing completed | Bias test results | ☐ |
| 17 | DR procedure documented and tested | DR test report | ☐ |
| 18 | Incident response plan documented | Runbook | ☐ |
| 19 | Model cards published for all models | Model card docs | ☐ |
| 20 | SOC 2 Type II readiness assessment | Assessment report | ☐ |

### 12.2 Runtime Compliance Checklist

| # | Requirement | Monitoring | Alert |
|---|-------------|-----------|-------|
| 1 | PII never reaches LLM unmasked | PII detection logs | Sev 0: immediate |
| 2 | All queries have audit trail | Audit completeness check | Sev 1: <1 hour |
| 3 | RBAC enforcement on every search | ACL filter validation | Sev 1: <1 hour |
| 4 | Content safety filters active | Filter status check | Sev 1: <1 hour |
| 5 | Encryption keys not expired | Key Vault monitoring | Sev 2: <4 hours |
| 6 | Certificate validity >30 days | Certificate monitoring | Sev 3: daily |
| 7 | Token budgets enforced | Budget tracking | Sev 3: daily |
| 8 | Evaluation scores within threshold | Weekly evaluation | Sev 2: <4 hours |
| 9 | No unauthorized data access | Sentinel monitoring | Sev 0: immediate |
| 10 | Backup integrity verified | Backup validation | Sev 2: weekly |

### 12.3 Audit Requirements

| Audit Type | Frequency | Scope | Deliverable |
|-----------|-----------|-------|-------------|
| Internal security audit | Quarterly | All security controls | Audit report + remediation plan |
| External pen test | Quarterly | Public endpoints, APIs | Pen test report |
| SOC 2 Type II | Annual | Full platform | SOC 2 report |
| GDPR compliance audit | Annual | All personal data processing | GDPR audit report |
| PCI-DSS assessment | Annual (if applicable) | Card data handling | PCI assessment report |
| AI ethics review | Quarterly | Bias, fairness, transparency | Ethics review report |
| Disaster recovery drill | Quarterly | Full failover test | DR drill report |
| Red team exercise | Quarterly | Adversarial AI testing | Red team report |

### 12.4 Compliance Reporting Dashboard

```
Monthly Compliance Report:
┌─────────────────────────────┬──────────┬────────┐
│ Control                     │ Status   │ Score  │
├─────────────────────────────┼──────────┼────────┤
│ Data encryption (at rest)   │ ✅ Pass  │ 100%   │
│ Data encryption (in transit)│ ✅ Pass  │ 100%   │
│ PII detection accuracy      │ ✅ Pass  │ 99.2%  │
│ RBAC enforcement            │ ✅ Pass  │ 100%   │
│ Audit trail completeness    │ ✅ Pass  │ 99.8%  │
│ Content safety enforcement  │ ✅ Pass  │ 100%   │
│ Key rotation compliance     │ ✅ Pass  │ 100%   │
│ Backup verification         │ ✅ Pass  │ 100%   │
│ Vulnerability scan          │ ⚠️ Review│ 95%    │
│ Penetration test            │ ✅ Pass  │ 97%    │
├─────────────────────────────┼──────────┼────────┤
│ Overall Compliance Score    │ ✅       │ 99.1%  │
└─────────────────────────────┴──────────┴────────┘
```

---

## Cross-References

- [SECURITY-LAYERS.md](./SECURITY-LAYERS.md) — 6-layer security architecture
- [RESPONSIBLE-AI.md](../governance/RESPONSIBLE-AI.md) — AI governance framework
- [MODEL-BENCHMARKING.md](../governance/MODEL-BENCHMARKING.md) — Evaluation metrics
- [TESTING-STRATEGY.md](../testing/TESTING-STRATEGY.md) — Security and bias testing
- [INTERVIEW-KNOWLEDGE-GUIDE.md](../reference/INTERVIEW-KNOWLEDGE-GUIDE.md) — Compliance Q&A
- [EDGE-CASES-DATA-TYPES.md](../reference/EDGE-CASES-DATA-TYPES.md) — PII edge cases
- [TECH-STACK-SERVICES.md](../reference/TECH-STACK-SERVICES.md) — Service inventory
- [FINOPS-COST-MANAGEMENT.md](../operations/FINOPS-COST-MANAGEMENT.md) — Compliance cost
