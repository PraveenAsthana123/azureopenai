# Project 6: Customer 360 Personalization Engine

## Executive Summary

A unified customer data platform that consolidates data from multiple sources to create comprehensive customer profiles, enabling real-time personalization, product recommendations, and AI-powered customer insights.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                     CUSTOMER 360 PERSONALIZATION ENGINE                              │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           DATA SOURCE LAYER                                          │
│                                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │
│  │ CRM          │  │ E-Commerce   │  │ Support      │  │ Marketing              │   │
│  │ (Salesforce/ │  │ (Shopify/    │  │ (Zendesk/    │  │ (Marketo/HubSpot)      │   │
│  │  Dynamics)   │  │  Magento)    │  │  ServiceNow) │  │                        │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └───────────┬────────────┘   │
│         │                 │                  │                      │               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │
│  │ Web/Mobile   │  │ IoT/Devices  │  │ Social       │  │ Third-Party            │   │
│  │ Analytics    │  │              │  │ Media        │  │ Data (Credit, etc.)    │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └───────────┬────────────┘   │
│         │                 │                  │                      │               │
└─────────┴─────────────────┴──────────────────┴──────────────────────┴───────────────┘
                                       │
┌──────────────────────────────────────┼──────────────────────────────────────────────┐
│                    DATA INGESTION & INTEGRATION                                      │
│                                      │                                              │
│                   ┌──────────────────▼──────────────────┐                           │
│                   │       Azure Data Factory            │                           │
│                   │                                     │                           │
│                   │  ┌─────────────┐ ┌─────────────┐   │                           │
│                   │  │ Batch       │ │ CDC/Real-   │   │                           │
│                   │  │ Pipelines   │ │ time Sync   │   │                           │
│                   │  └─────────────┘ └─────────────┘   │                           │
│                   └──────────────────┬──────────────────┘                           │
│                                      │                                              │
│         ┌────────────────────────────┼────────────────────────────┐                │
│         │                            │                            │                │
│         ▼                            ▼                            ▼                │
│  ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐            │
│  │ ADLS Gen2       │      │ Event Hub       │      │ Cosmos DB       │            │
│  │ (Raw Data Lake) │      │ (Real-time      │      │ (Change Feed)   │            │
│  │                 │      │  Events)        │      │                 │            │
│  └────────┬────────┘      └────────┬────────┘      └────────┬────────┘            │
│           │                        │                        │                      │
└───────────┼────────────────────────┼────────────────────────┼──────────────────────┘
            │                        │                        │
┌───────────┼────────────────────────┼────────────────────────┼──────────────────────┐
│           │     CUSTOMER DATA PLATFORM (CDP)                │                      │
│           │                        │                        │                      │
│           ▼                        ▼                        ▼                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                    IDENTITY RESOLUTION ENGINE                               │   │
│  │                                                                              │   │
│  │  ┌──────────────────────────────────────────────────────────────────────┐   │   │
│  │  │                                                                       │   │   │
│  │  │   Email ─────┐                                                        │   │   │
│  │  │   Phone ─────┼───► Probabilistic    ┌─────────────────────────────┐  │   │   │
│  │  │   Device ID ─┼───► + Deterministic ─►│    UNIFIED CUSTOMER ID      │  │   │   │
│  │  │   Cookie ────┼───► Matching         │    (Golden Record)          │  │   │   │
│  │  │   Social ID ─┘                      └─────────────────────────────┘  │   │   │
│  │  │                                                                       │   │   │
│  │  └──────────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                              │
│                                      ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                    UNIFIED CUSTOMER PROFILE                                  │   │
│  │                                                                              │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐│   │
│  │  │ Demographics │ │ Transactions │ │ Interactions │ │ Preferences          ││   │
│  │  │              │ │              │ │              │ │                      ││   │
│  │  │ - Name       │ │ - Purchases  │ │ - Support    │ │ - Communication      ││   │
│  │  │ - Age        │ │ - Returns    │ │ - Web visits │ │ - Product interests  ││   │
│  │  │ - Location   │ │ - LTV        │ │ - App usage  │ │ - Channel pref       ││   │
│  │  │ - Segment    │ │ - Frequency  │ │ - Campaigns  │ │ - Privacy settings   ││   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────────────┘│   │
│  │                                                                              │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐│   │
│  │  │ Computed     │ │ ML Scores    │ │ Real-time    │ │ Consent              ││   │
│  │  │ Metrics      │ │              │ │ Signals      │ │ & Privacy            ││   │
│  │  │              │ │ - Churn risk │ │              │ │                      ││   │
│  │  │ - RFM score  │ │ - Next prod  │ │ - Current    │ │ - GDPR consent       ││   │
│  │  │ - CLV        │ │ - Propensity │ │   session    │ │ - Data preferences   ││   │
│  │  │ - Engagement │ │ - Sentiment  │ │ - Cart state │ │ - Opt-outs           ││   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────────────┘│   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         ML & PERSONALIZATION ENGINE                                  │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                        Azure Machine Learning                                │    │
│  │                                                                              │    │
│  │  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────────────────┐ │    │
│  │  │ Recommendation   │ │ Churn Prediction │ │ Next Best Action             │ │    │
│  │  │ Model            │ │ Model            │ │ Model                        │ │    │
│  │  │                  │ │                  │ │                              │ │    │
│  │  │ - Collaborative  │ │ - Survival       │ │ - Multi-armed bandit         │ │    │
│  │  │   filtering      │ │   analysis       │ │ - Contextual optimization    │ │    │
│  │  │ - Content-based  │ │ - XGBoost        │ │ - Reinforcement learning     │ │    │
│  │  │ - Hybrid         │ │ - Feature store  │ │                              │ │    │
│  │  └──────────────────┘ └──────────────────┘ └──────────────────────────────┘ │    │
│  │                                                                              │    │
│  │  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────────────────┐ │    │
│  │  │ Customer         │ │ Propensity       │ │ Lifetime Value               │ │    │
│  │  │ Segmentation     │ │ Scoring          │ │ Prediction                   │ │    │
│  │  │                  │ │                  │ │                              │ │    │
│  │  │ - K-means        │ │ - Buy propensity │ │ - Revenue forecasting        │ │    │
│  │  │ - RFM analysis   │ │ - Response pred  │ │ - Customer value tiers       │ │    │
│  │  │ - Behavioral     │ │                  │ │                              │ │    │
│  │  └──────────────────┘ └──────────────────┘ └──────────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                      │                                              │
│                                      ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                    Azure OpenAI Personalization                              │    │
│  │                                                                              │    │
│  │  ┌──────────────────────────────────────────────────────────────────────┐   │    │
│  │  │                                                                       │   │    │
│  │  │  Customer Profile + Context + ML Scores                               │   │    │
│  │  │            │                                                          │   │    │
│  │  │            ▼                                                          │   │    │
│  │  │  ┌─────────────────────────────────────────────────────────────────┐ │   │    │
│  │  │  │ GPT-4o Personalization                                          │ │   │    │
│  │  │  │                                                                  │ │   │    │
│  │  │  │ - Personalized product descriptions                             │ │   │    │
│  │  │  │ - Custom email content                                          │ │   │    │
│  │  │  │ - Chatbot responses adapted to customer                         │ │   │    │
│  │  │  │ - Dynamic offer generation                                      │ │   │    │
│  │  │  └─────────────────────────────────────────────────────────────────┘ │   │    │
│  │  └──────────────────────────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         ACTIVATION & DELIVERY                                        │
│                                                                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐│
│  │ Real-time API│ │ Email        │ │ Web/Mobile   │ │ Ad Platforms │ │ CRM        ││
│  │ (Cosmos DB)  │ │ (SendGrid)   │ │ Personalization│ │ (Google/FB) │ │ Sync       ││
│  │              │ │              │ │              │ │              │ │            ││
│  │ <10ms lookup │ │ Triggered    │ │ Recommendations│ │ Audience    │ │ Bi-direct  ││
│  │ for profiles │ │ campaigns    │ │ Dynamic content│ │ segments    │ │ sync       ││
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘│
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         ANALYTICS & INSIGHTS                                         │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                          Power BI Dashboards                                 │    │
│  │                                                                              │    │
│  │  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────────────────┐ │    │
│  │  │ Customer         │ │ Segment          │ │ Campaign                     │ │    │
│  │  │ 360 View         │ │ Analysis         │ │ Performance                  │ │    │
│  │  │                  │ │                  │ │                              │ │    │
│  │  │ - Profile card   │ │ - Segment sizes  │ │ - Response rates             │ │    │
│  │  │ - Journey map    │ │ - Movement       │ │ - Conversion lift            │ │    │
│  │  │ - Interactions   │ │ - Value trends   │ │ - ROI by segment             │ │    │
│  │  └──────────────────┘ └──────────────────┘ └──────────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Customer Profile Schema

```json
{
  "customerId": "cust_abc123",
  "identities": {
    "email": ["john@example.com", "j.doe@work.com"],
    "phone": ["+1-555-1234"],
    "deviceIds": ["dev_xyz", "dev_abc"]
  },
  "demographics": {
    "firstName": "John",
    "lastName": "Doe",
    "age": 35,
    "gender": "M",
    "location": {"city": "Seattle", "state": "WA", "country": "US"}
  },
  "transactions": {
    "totalPurchases": 47,
    "totalSpend": 4250.00,
    "avgOrderValue": 90.43,
    "lastPurchase": "2024-01-10",
    "favoriteCategories": ["Electronics", "Books"]
  },
  "engagement": {
    "rfmScore": {"recency": 5, "frequency": 4, "monetary": 4},
    "engagementScore": 78,
    "preferredChannel": "email",
    "lastInteraction": "2024-01-14"
  },
  "mlScores": {
    "churnRisk": 0.15,
    "clv": 8500.00,
    "nextProductPropensity": {"product": "Laptop", "score": 0.72}
  },
  "consent": {
    "marketing": true,
    "analytics": true,
    "thirdParty": false
  }
}
```

---

## Azure Services Used

| Service | Purpose |
|---------|---------|
| Data Factory | Data integration, ETL |
| ADLS Gen2 | Raw data lake |
| Synapse Analytics | Data processing, aggregations |
| Cosmos DB | Real-time customer profiles |
| Azure ML | Recommendation, churn, CLV models |
| Azure OpenAI | Personalized content generation |
| Event Hub | Real-time event streaming |
| Power BI | Customer analytics dashboards |

---

## Interview Talking Points

1. **Identity Resolution Approach:**
   - Deterministic (exact match on email/phone)
   - Probabilistic (device fingerprint, behavior patterns)
   - Merge rules and conflict resolution

2. **Real-time vs Batch:**
   - Profile updates: Near real-time (minutes)
   - ML scoring: Batch (daily) + real-time inference
   - Personalization API: Real-time (<10ms)

3. **Privacy & Consent:**
   - Consent management per channel
   - Right to be forgotten (GDPR)
   - Data minimization practices
