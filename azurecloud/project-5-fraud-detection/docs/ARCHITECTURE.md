# Project 5: Financial Fraud Detection Platform

## Executive Summary

An enterprise-grade fraud detection system combining traditional ML anomaly detection with GenAI-powered explainability. The platform processes financial transactions in real-time, flags suspicious activities, and generates human-readable explanations for fraud analysts.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                      FINANCIAL FRAUD DETECTION PLATFORM                              │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            DATA INGESTION LAYER                                      │
│                                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│  │ Core Banking │  │ Card Network │  │ Payment      │  │ External Data            │ │
│  │ System       │  │ (Visa/MC)    │  │ Gateways     │  │ (Credit Bureau, etc.)    │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └────────────┬─────────────┘ │
│         │                 │                  │                       │              │
│         └─────────────────┼──────────────────┼───────────────────────┘              │
│                           │                  │                                       │
│                           ▼                  ▼                                       │
│                    ┌─────────────────────────────────┐                              │
│                    │      Azure Event Hub            │                              │
│                    │      (Transaction Stream)       │                              │
│                    │      - Partitioned by account   │                              │
│                    │      - 7-day retention          │                              │
│                    └───────────────┬─────────────────┘                              │
└────────────────────────────────────┼────────────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────────────────┐
│                    REAL-TIME PROCESSING LAYER                                        │
│                                                                                      │
│         ┌──────────────────────────┼──────────────────────────┐                     │
│         │                          │                          │                     │
│         ▼                          ▼                          ▼                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐         │
│  │ Stream Analytics│    │ Azure Functions │    │ Azure ML Real-time      │         │
│  │ (Windowed Agg)  │    │ (Feature Eng)   │    │ Endpoint (Scoring)      │         │
│  │                 │    │                 │    │                         │         │
│  │ - Velocity      │    │ - Enrichment    │    │ - Anomaly Detection     │         │
│  │ - Patterns      │    │ - Graph Features│    │ - Classification        │         │
│  │ - Thresholds    │    │ - Historical    │    │ - Ensemble Model        │         │
│  └────────┬────────┘    └────────┬────────┘    └────────────┬────────────┘         │
│           │                      │                          │                       │
│           └──────────────────────┼──────────────────────────┘                       │
│                                  │                                                   │
│                                  ▼                                                   │
│                    ┌─────────────────────────────┐                                  │
│                    │     FRAUD DECISION ENGINE   │                                  │
│                    │                             │                                  │
│                    │  ┌───────────────────────┐  │                                  │
│                    │  │ Rules Engine          │  │                                  │
│                    │  │ - Business rules      │  │                                  │
│                    │  │ - Compliance checks   │  │                                  │
│                    │  │ - Velocity limits     │  │                                  │
│                    │  └───────────┬───────────┘  │                                  │
│                    │              │              │                                  │
│                    │  ┌───────────▼───────────┐  │                                  │
│                    │  │ ML Model Ensemble     │  │                                  │
│                    │  │ - Isolation Forest    │  │                                  │
│                    │  │ - XGBoost             │  │                                  │
│                    │  │ - Neural Network      │  │                                  │
│                    │  └───────────┬───────────┘  │                                  │
│                    │              │              │                                  │
│                    │  ┌───────────▼───────────┐  │                                  │
│                    │  │ Decision Aggregator   │  │                                  │
│                    │  │ - Risk Score 0-100    │  │                                  │
│                    │  │ - Confidence Level    │  │                                  │
│                    │  │ - Action: Allow/Block │  │                                  │
│                    │  └───────────────────────┘  │                                  │
│                    └──────────────┬──────────────┘                                  │
│                                   │                                                  │
└───────────────────────────────────┼──────────────────────────────────────────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         │                          │                          │
         ▼                          ▼                          ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────────┐
│ ALLOW           │      │ REVIEW          │      │ BLOCK               │
│ (Score < 30)    │      │ (30 < Score < 70)│     │ (Score >= 70)       │
│                 │      │                 │      │                     │
│ Log & Continue  │      │ Queue for       │      │ Block Transaction   │
│                 │      │ Human Review    │      │ Notify Customer     │
└─────────────────┘      └────────┬────────┘      └─────────────────────┘
                                  │
┌─────────────────────────────────┼───────────────────────────────────────────────────┐
│                    GENAI EXPLAINABILITY LAYER                                        │
│                                  │                                                   │
│                                  ▼                                                   │
│                    ┌─────────────────────────────┐                                  │
│                    │    Azure OpenAI (GPT-4o)    │                                  │
│                    │                             │                                  │
│                    │  Generate:                  │                                  │
│                    │  - Case Summaries           │                                  │
│                    │  - Risk Explanations        │                                  │
│                    │  - Recommended Actions      │                                  │
│                    │  - Similar Case Analysis    │                                  │
│                    └──────────────┬──────────────┘                                  │
│                                   │                                                  │
│                                   ▼                                                  │
│                    ┌─────────────────────────────┐                                  │
│                    │   Fraud Analyst Dashboard   │                                  │
│                    │                             │                                  │
│                    │  ┌───────────────────────┐  │                                  │
│                    │  │ Case Queue            │  │                                  │
│                    │  │ - Priority sorted     │  │                                  │
│                    │  │ - AI explanations     │  │                                  │
│                    │  │ - Similar cases       │  │                                  │
│                    │  └───────────────────────┘  │                                  │
│                    │                             │                                  │
│                    │  ┌───────────────────────┐  │                                  │
│                    │  │ Decision Actions      │  │                                  │
│                    │  │ - Approve             │  │                                  │
│                    │  │ - Decline             │  │                                  │
│                    │  │ - Request Info        │  │                                  │
│                    │  └───────────────────────┘  │                                  │
│                    └─────────────────────────────┘                                  │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                          DATA & ANALYTICS LAYER                                      │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                        Azure Synapse Analytics                               │    │
│  │                                                                              │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │    │
│  │  │ Raw Zone     │  │ Curated Zone │  │ Feature Store│  │ Model Registry   │ │    │
│  │  │ (ADLS Gen2)  │  │ (Delta Lake) │  │ (Offline)    │  │ (MLflow)         │ │    │
│  │  │              │  │              │  │              │  │                  │ │    │
│  │  │ - Raw txns   │  │ - Cleaned    │  │ - Customer   │  │ - Model versions │ │    │
│  │  │ - Events     │  │ - Aggregated │  │   features   │  │ - Experiments    │ │    │
│  │  │ - Logs       │  │ - Enriched   │  │ - Historical │  │ - A/B tests      │ │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
│  ┌──────────────────────────────────────────┐  ┌────────────────────────────────┐   │
│  │        Azure ML Workspace                │  │     Power BI Dashboards        │   │
│  │                                          │  │                                │   │
│  │  - Model Training Pipeline               │  │  - Fraud Metrics               │   │
│  │  - Feature Engineering                   │  │  - False Positive Rate         │   │
│  │  - Hyperparameter Tuning                 │  │  - Detection Latency           │   │
│  │  - Model Deployment                      │  │  - Financial Impact            │   │
│  └──────────────────────────────────────────┘  └────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           SECURITY & COMPLIANCE                                      │
│                                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │
│  │ Key Vault    │  │ Purview      │  │ Defender     │  │ Compliance Manager     │   │
│  │ (Secrets)    │  │ (Data Gov)   │  │ (Security)   │  │ (PCI-DSS, SOX)         │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────────────────┘   │
│                                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │
│  │ Private Link │  │ Managed ID   │  │ Encryption   │  │ Audit Logging          │   │
│  │ (Network)    │  │ (No secrets) │  │ (CMK)        │  │ (Immutable)            │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## ML Model Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                       FRAUD DETECTION ML PIPELINE                                    │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            FEATURE ENGINEERING                                       │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                         Transaction Features                                  │   │
│  │                                                                               │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐   │   │
│  │  │ Basic Features  │  │ Velocity        │  │ Behavioral                  │   │   │
│  │  │                 │  │ Features        │  │ Features                    │   │   │
│  │  │ - Amount        │  │                 │  │                             │   │   │
│  │  │ - Currency      │  │ - Txn/hour      │  │ - Deviation from pattern   │   │   │
│  │  │ - Merchant type │  │ - Txn/day       │  │ - Time since last txn      │   │   │
│  │  │ - Channel       │  │ - Amount/hour   │  │ - Geographic distance      │   │   │
│  │  │ - Time of day   │  │ - Unique merch  │  │ - Device fingerprint match │   │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                         Customer Profile Features                             │   │
│  │                                                                               │   │
│  │  - Account age                    - Credit utilization                        │   │
│  │  - Average transaction amount     - Payment history                           │   │
│  │  - Typical merchants              - Risk segment                              │   │
│  │  - Geographic patterns            - Previous fraud history                    │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                         Graph/Network Features                                │   │
│  │                                                                               │   │
│  │  - Shared device connections      - Merchant risk network                     │   │
│  │  - Account link patterns          - Money flow patterns                       │   │
│  │  - Ring detection features        - Community detection                       │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            MODEL ENSEMBLE                                            │
│                                                                                      │
│     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────────┐         │
│     │ Isolation Forest│     │    XGBoost      │     │   Neural Network    │         │
│     │                 │     │                 │     │                     │         │
│     │ - Unsupervised  │     │ - Supervised    │     │ - Deep Learning     │         │
│     │ - Anomaly Score │     │ - Probability   │     │ - Sequence patterns │         │
│     │ - Novel fraud   │     │ - Interpretable │     │ - Complex features  │         │
│     └────────┬────────┘     └────────┬────────┘     └──────────┬──────────┘         │
│              │                       │                          │                    │
│              │     0.30              │      0.45                │     0.25           │
│              │                       │                          │                    │
│              └───────────────────────┼──────────────────────────┘                    │
│                                      │                                               │
│                                      ▼                                               │
│                    ┌─────────────────────────────────┐                              │
│                    │    Weighted Ensemble Score      │                              │
│                    │    Final Risk Score: 0-100      │                              │
│                    └─────────────────────────────────┘                              │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         MODEL TRAINING PIPELINE                                      │
│                                                                                      │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────────────┐   │
│  │ Data    │───►│ Feature │───►│ Train/  │───►│ Evaluate│───►│ Register &      │   │
│  │ Extract │    │ Engineer│    │ Validate│    │ Model   │    │ Deploy          │   │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────────────┘   │
│                                                                                      │
│  Metrics tracked:                                                                    │
│  - Precision @ 95% Recall                                                            │
│  - False Positive Rate                                                               │
│  - AUC-ROC / AUC-PR                                                                  │
│  - Detection Latency (P50, P99)                                                      │
│  - $ Fraud Prevented vs $ False Decline                                              │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## GenAI Explainability System

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        GENAI EXPLAINABILITY PIPELINE                                 │
└─────────────────────────────────────────────────────────────────────────────────────┘

            Flagged Transaction
                    │
                    ▼
     ┌──────────────────────────────┐
     │    Context Aggregation       │
     │                              │
     │  - Transaction details       │
     │  - Customer profile          │
     │  - Risk score breakdown      │
     │  - Feature importance (SHAP) │
     │  - Similar past cases        │
     └──────────────┬───────────────┘
                    │
                    ▼
     ┌──────────────────────────────┐
     │     Prompt Construction      │
     │                              │
     │  System: You are a fraud     │
     │  analysis expert...          │
     │                              │
     │  Context: {transaction_data} │
     │  Risk Factors: {shap_values} │
     │  Similar Cases: {cases}      │
     │                              │
     │  Generate:                   │
     │  1. Risk summary             │
     │  2. Key concerns             │
     │  3. Recommended action       │
     └──────────────┬───────────────┘
                    │
                    ▼
     ┌──────────────────────────────┐
     │    Azure OpenAI GPT-4o       │
     │                              │
     │  - Structured output         │
     │  - Grounded in evidence      │
     │  - Consistent format         │
     └──────────────┬───────────────┘
                    │
                    ▼
     ┌──────────────────────────────┐
     │    Explanation Output        │
     │                              │
     │  {                           │
     │    "summary": "...",         │
     │    "risk_factors": [...],    │
     │    "confidence": 0.85,       │
     │    "recommended_action":     │
     │      "REVIEW",               │
     │    "similar_cases": [...]    │
     │  }                           │
     └──────────────────────────────┘
```

---

## Azure Services Mapping

| Layer | Service | Purpose |
|-------|---------|---------|
| **Ingestion** | Event Hub | High-throughput transaction streaming |
| **Ingestion** | Data Factory | Batch data integration |
| **Processing** | Stream Analytics | Real-time aggregations |
| **Processing** | Azure Functions | Feature engineering, routing |
| **ML** | Azure ML | Model training, registry, deployment |
| **ML** | ML Endpoints | Real-time inference |
| **GenAI** | Azure OpenAI | Case summarization, explainability |
| **Storage** | ADLS Gen2 | Data lake (raw, curated) |
| **Storage** | Synapse | Analytics, feature store |
| **Storage** | Azure SQL | Transaction metadata, case management |
| **Storage** | Cosmos DB | Real-time feature lookup |
| **Analytics** | Power BI | Dashboards, reporting |
| **Security** | Key Vault | Secrets management |
| **Security** | Purview | Data governance, lineage |
| **Security** | Defender | Threat protection |
| **Monitoring** | App Insights | Application telemetry |
| **Monitoring** | Monitor | Infrastructure metrics |

---

## Key Performance Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Detection Latency (P99) | < 200ms | Time to score a transaction |
| False Positive Rate | < 0.5% | Legitimate transactions flagged |
| True Positive Rate | > 95% | Fraud correctly detected |
| Case Review Time | < 5 min | Avg time to review flagged txn |
| Model Drift Detection | Daily | Automated performance monitoring |

---

## Interview Talking Points

### Technical Decisions

1. **Why Ensemble Model?**
   - Different models catch different fraud patterns
   - Isolation Forest: novel/unknown fraud patterns
   - XGBoost: known fraud patterns, interpretable
   - Neural Network: complex temporal patterns
   - Weighted combination reduces false positives

2. **Why GenAI for Explainability?**
   - SHAP values are technical, not analyst-friendly
   - GPT generates natural language explanations
   - Reduces analyst cognitive load
   - Consistent explanation format
   - Can synthesize multiple evidence sources

3. **Real-time vs Batch Trade-offs**
   - Real-time: scoring (must be < 200ms)
   - Near-real-time: feature updates (minutes)
   - Batch: model training, historical analysis (daily)

4. **Handling Class Imbalance**
   - Fraud is ~0.1% of transactions
   - SMOTE for training data
   - Cost-sensitive learning
   - Precision@Recall threshold optimization

## Business Domain, Security, Governance & Compliance

### Business Domain
- **Classification:** B2C / B2B (Consumer Transactions + Merchant Partners)
- **Visibility:** Internal (Ops) + Regulatory — fraud ops team + regulatory reporting
- **Project Score:** 9.5 / 10 (Critical)

### Security Controls
| Layer | Control | Implementation |
|-------|---------|----------------|
| Network | Network Isolation | Dedicated VNet, NSG rules, no public endpoints |
| Network | Private Link | Event Hub, ML Workspace, Cosmos DB, OpenAI via private endpoints |
| Identity | Managed Identity | Zero-secret architecture for all services |
| Identity | RBAC | Strict role separation: data scientists, ops, auditors |
| Data | PCI DSS Level 1 | Cardholder data encrypted, tokenized, masked |
| Data | TDE | Transparent data encryption on all databases |
| Data | Data Masking | Dynamic masking for non-privileged users |
| Data | Key Vault | CMK for encryption, model signing keys |
| Application | Model Governance | Signed models, tamper detection, version control |
| Application | Explainability | SHAP + GenAI explanations for every fraud decision |
| Monitoring | Sentinel | Real-time security event correlation |
| Monitoring | SOX Audit Trail | Immutable decision logs with full lineage |

### Governance & Compliance
| Area | Policy | Details |
|------|--------|---------|
| SOX Compliance | Enforced | Complete audit trail for all fraud decisions |
| FinCEN/SAR | Automated | Suspicious Activity Reports auto-generated |
| Model Governance | ML Registry | Model versions, metrics, approvals tracked in Azure ML |
| Explainability | Mandatory | Every fraud flag includes human-readable explanation |
| Data Retention | 7 years | Transaction and decision data retained per regulation |
| Bias Monitoring | Continuous | Fair lending / ECOA compliance monitoring |

### Regulatory Applicability
- **PCI DSS Level 1:** Cardholder data protection
- **SOX:** Financial reporting integrity and audit trail
- **BSA/AML:** Anti-money laundering screening
- **ECOA/Fair Lending:** Bias monitoring in fraud scoring
- **FFIEC:** Federal financial institution examination standards
