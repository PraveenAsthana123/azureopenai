# Project 11: Legal Contract Analyzer

## Executive Summary

An AI-powered contract analysis platform that extracts key clauses, identifies risks, compares contract versions, and provides intelligent summaries using Azure Document Intelligence and OpenAI GPT-4o.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         LEGAL CONTRACT ANALYZER                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           CONTRACT INGESTION                                         │
│                                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │
│  │ Email        │  │ SharePoint   │  │ API Upload   │  │ Contract Mgmt          │   │
│  │ Attachments  │  │ Document Lib │  │ (Web Portal) │  │ System (CLM)           │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └───────────┬────────────┘   │
│         │                 │                  │                      │               │
│         └─────────────────┴──────────────────┴──────────────────────┘               │
│                                      │                                              │
│                           ┌──────────▼──────────┐                                   │
│                           │  Azure Blob Storage │                                   │
│                           │  /contracts/inbox/  │                                   │
│                           └──────────┬──────────┘                                   │
│                                      │                                              │
│                           ┌──────────▼──────────┐                                   │
│                           │    Event Grid       │                                   │
│                           └──────────┬──────────┘                                   │
└──────────────────────────────────────┼──────────────────────────────────────────────┘
                                       │
┌──────────────────────────────────────┼──────────────────────────────────────────────┐
│                    CONTRACT PROCESSING PIPELINE                                      │
│                    (Durable Functions)                                               │
│                                      │                                              │
│                   ┌──────────────────▼──────────────────┐                           │
│                   │        Orchestrator                  │                           │
│                   └──────────────────┬──────────────────┘                           │
│                                      │                                              │
│    ┌─────────────────────────────────┼─────────────────────────────────┐           │
│    │                                 │                                 │           │
│    ▼                                 ▼                                 ▼           │
│ ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────────────┐    │
│ │ 1. EXTRACTION    │     │ 2. CLASSIFICATION│     │ 3. CLAUSE ANALYSIS       │    │
│ │                  │     │                  │     │                          │    │
│ │ Document Intel.: │     │ Contract Type:   │     │ Key Clauses:             │    │
│ │ - Layout model   │     │ - NDA            │     │ - Parties                │    │
│ │ - Custom model   │     │ - MSA            │     │ - Effective Date         │    │
│ │   (contracts)    │     │ - SOW            │     │ - Term/Duration          │    │
│ │                  │     │ - Employment     │     │ - Payment Terms          │    │
│ │ Output:          │     │ - Lease          │     │ - Termination            │    │
│ │ - Full text      │     │ - License        │     │ - Liability              │    │
│ │ - Sections       │     │                  │     │ - Indemnification        │    │
│ │ - Tables         │     │ Classification   │     │ - IP Rights              │    │
│ │ - Signatures     │     │ Confidence: 95%  │     │ - Confidentiality        │    │
│ └────────┬─────────┘     └────────┬─────────┘     │ - Dispute Resolution     │    │
│          │                        │               │ - Governing Law          │    │
│          │                        │               └────────────┬─────────────┘    │
│          │                        │                            │                  │
│          └────────────────────────┼────────────────────────────┘                  │
│                                   │                                               │
│                   ┌───────────────▼───────────────┐                               │
│                   │     AZURE OPENAI GPT-4o       │                               │
│                   │                               │                               │
│                   │  Contract Analysis Tasks:     │                               │
│                   │                               │                               │
│                   │  ┌─────────────────────────┐  │                               │
│                   │  │ Clause Extraction       │  │                               │
│                   │  │ - Find specific clauses │  │                               │
│                   │  │ - Extract key terms     │  │                               │
│                   │  │ - Identify obligations  │  │                               │
│                   │  └─────────────────────────┘  │                               │
│                   │                               │                               │
│                   │  ┌─────────────────────────┐  │                               │
│                   │  │ Risk Assessment         │  │                               │
│                   │  │ - Unfavorable terms     │  │                               │
│                   │  │ - Missing clauses       │  │                               │
│                   │  │ - Compliance issues     │  │                               │
│                   │  │ - Risk score (1-10)     │  │                               │
│                   │  └─────────────────────────┘  │                               │
│                   │                               │                               │
│                   │  ┌─────────────────────────┐  │                               │
│                   │  │ Summary Generation      │  │                               │
│                   │  │ - Executive summary     │  │                               │
│                   │  │ - Key highlights        │  │                               │
│                   │  │ - Action items          │  │                               │
│                   │  └─────────────────────────┘  │                               │
│                   └───────────────┬───────────────┘                               │
│                                   │                                               │
└───────────────────────────────────┼───────────────────────────────────────────────┘
                                    │
┌───────────────────────────────────┼───────────────────────────────────────────────┐
│                    ADVANCED ANALYSIS FEATURES                                      │
│                                   │                                               │
│    ┌──────────────────────────────┼──────────────────────────────┐               │
│    │                              │                              │               │
│    ▼                              ▼                              ▼               │
│ ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────────────────┐  │
│ │ VERSION COMPARE  │   │ PLAYBOOK CHECK   │   │ SEMANTIC SEARCH              │  │
│ │                  │   │                  │   │                              │  │
│ │ Compare two      │   │ Compare against  │   │ AI Search Index:             │  │
│ │ contract versions│   │ company playbook │   │                              │  │
│ │                  │   │                  │   │ - All contracts              │  │
│ │ - Side-by-side   │   │ - Standard terms │   │ - Clause embeddings          │  │
│ │ - Redline view   │   │ - Deviations     │   │ - Semantic search            │  │
│ │ - Material changes│  │ - Approval needed│   │                              │  │
│ │ - Risk delta     │   │ - Auto-approve   │   │ Queries:                     │  │
│ │                  │   │   criteria       │   │ - "All NDAs expiring Q1"     │  │
│ │ Output:          │   │                  │   │ - "Contracts with auto-renew"│  │
│ │ - Change summary │   │ Output:          │   │ - "Unlimited liability"      │  │
│ │ - New risks      │   │ - Compliance %   │   │                              │  │
│ │                  │   │ - Exceptions list│   │                              │  │
│ └──────────────────┘   └──────────────────┘   └──────────────────────────────┘  │
│                                                                                   │
└───────────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────────────┐
│                           DATA STORAGE                                             │
│                                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────┐  │
│  │                           Cosmos DB                                          │  │
│  │                                                                              │  │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────────────┐ │  │
│  │  │ contracts        │  │ clauses          │  │ risks                      │ │  │
│  │  │                  │  │                  │  │                            │ │  │
│  │  │ - id             │  │ - contract_id    │  │ - contract_id              │ │  │
│  │  │ - type           │  │ - clause_type    │  │ - risk_type                │ │  │
│  │  │ - parties        │  │ - text           │  │ - severity (1-10)          │ │  │
│  │  │ - effective_date │  │ - position       │  │ - description              │ │  │
│  │  │ - expiry_date    │  │ - confidence     │  │ - recommendation           │ │  │
│  │  │ - value          │  │ - is_standard    │  │ - status                   │ │  │
│  │  │ - status         │  │                  │  │                            │ │  │
│  │  │ - summary        │  │                  │  │                            │ │  │
│  │  └──────────────────┘  └──────────────────┘  └────────────────────────────┘ │  │
│  └─────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                    │
│  ┌──────────────────────────────────┐  ┌────────────────────────────────────────┐ │
│  │ Azure AI Search                  │  │ Blob Storage                           │ │
│  │ (Contract Index)                 │  │                                        │ │
│  │                                  │  │ /contracts/                            │ │
│  │ - Vector embeddings              │  │   ├── /originals/                     │ │
│  │ - Full-text search               │  │   ├── /processed/                     │ │
│  │ - Faceted search                 │  │   └── /versions/                      │ │
│  │ - Clause-level search            │  │                                        │ │
│  └──────────────────────────────────┘  └────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACES                                          │
│                                                                                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────────────────┐   │
│  │ Web Portal       │  │ API              │  │ Power BI                       │   │
│  │ (React)          │  │ (APIM)           │  │ Dashboard                      │   │
│  │                  │  │                  │  │                                │   │
│  │ - Upload contract│  │ - /analyze       │  │ - Contract portfolio           │   │
│  │ - View analysis  │  │ - /compare       │  │ - Risk distribution            │   │
│  │ - Search         │  │ - /search        │  │ - Expiry calendar              │   │
│  │ - Export reports │  │ - /summarize     │  │ - Compliance metrics           │   │
│  └──────────────────┘  └──────────────────┘  └────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────────────────────┘
```

---

## Clause Extraction Prompt

```
SYSTEM: You are a legal contract analyst. Analyze the following contract and extract key information.

CONTRACT TEXT:
{contract_text}

Extract the following in JSON format:
{
  "parties": {
    "party_a": {"name": "", "role": ""},
    "party_b": {"name": "", "role": ""}
  },
  "dates": {
    "effective_date": "",
    "expiry_date": "",
    "renewal_terms": ""
  },
  "financial_terms": {
    "total_value": "",
    "payment_schedule": "",
    "penalties": ""
  },
  "key_clauses": [
    {
      "type": "termination|liability|indemnification|confidentiality|ip_rights",
      "text": "exact clause text",
      "summary": "plain English summary",
      "risk_level": "low|medium|high",
      "risk_reason": ""
    }
  ],
  "risks": [
    {
      "description": "",
      "severity": 1-10,
      "recommendation": ""
    }
  ],
  "executive_summary": "2-3 paragraph summary"
}
```

---

## Risk Assessment Categories

| Risk Type | Severity Criteria | Example |
|-----------|-------------------|---------|
| **Unlimited Liability** | High (8-10) | No cap on damages |
| **Auto-Renewal** | Medium (4-6) | Without 90-day notice |
| **Broad Indemnification** | High (7-9) | Indemnify against all claims |
| **IP Assignment** | High (8-10) | All work product assigned |
| **Unilateral Termination** | Medium (5-7) | Other party can terminate without cause |
| **Missing Clauses** | Variable | No data protection clause |

---

## Azure Services Used

| Service | Purpose |
|---------|---------|
| Document Intelligence | OCR, layout extraction |
| Azure OpenAI | Clause analysis, summarization |
| AI Search | Contract search, semantic |
| Functions | Processing pipeline |
| Cosmos DB | Contract metadata |
| Blob Storage | Document storage |
| APIM | API management |

---

## Interview Talking Points

1. **Why GPT for contract analysis vs traditional NLP?**
   - Understands legal language nuances
   - Handles varied clause phrasing
   - Generates actionable summaries
   - Identifies implicit risks

2. **Handling contract confidentiality:**
   - Data stays in Azure tenant
   - Private endpoints
   - No training on customer data
   - Role-based access to contracts

3. **Version comparison approach:**
   - Semantic diff (not just text diff)
   - Identify material vs cosmetic changes
   - Risk delta calculation
