# Project 26: Voice AI Outbound Platform

## Executive Summary

An AI-powered outbound voice platform for proactive customer engagement that leverages Azure OpenAI GPT-4o for GenAI-scripted outbound calls, Azure Communication Services for voice calling, and Azure Speech Services for real-time text-to-speech with neural voice synthesis. The platform enables campaign-driven outbound dialing with conversational AI, intelligent call scheduling based on customer availability patterns, TCPA/DNC compliance management, voicemail detection and message drop, sentiment-based escalation to human agents, multilingual voice support, and a comprehensive call analytics dashboard powered by Azure Stream Analytics and Power BI.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                          VOICE AI OUTBOUND PLATFORM                                  │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Campaign Mgmt  │     │  Agent Desktop  │     │  Analytics       │
│  Portal (React) │     │  (React/SignalR)│     │  Dashboard (PBI) │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Azure Front Door      │
                    │   (WAF + CDN + SSL)     │
                    └────────────┬────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   APIM Gateway  │   │  Static Web App │   │  Power BI       │
│  (Rate Limit,   │   │  (Campaign UI)  │   │  Embedded       │
│   Auth, Route)  │   │                 │   │  (Analytics)    │
└────────┬────────┘   └─────────────────┘   └─────────────────┘
         │
         │  ┌─────────────────────────────────────────────────────────────┐
         │  │                 PRIVATE VNET (10.0.0.0/16)                  │
         │  │  ┌───────────────────────────────────────────────────────┐  │
         │  │  │            Application Subnet (10.0.1.0/24)           │  │
         ▼  │  │                                                       │  │
┌───────────┴──┴──────┐                                                │  │
│  Azure Functions    │◄────────────────────────────────────────────┐  │  │
│  (Call Orchestrator) │                                            │  │  │
│                     │    ┌─────────────────┐  ┌────────────────┐  │  │  │
│  - Campaign Engine  │    │  Azure OpenAI   │  │ Azure Bot      │  │  │  │
│  - Compliance Check │◄───┤  (GPT-4o)       │  │ Service        │  │  │  │
│  - Call Scheduler   │    │  Script Gen +   │  │ (Dialog Mgmt)  │  │  │  │
│  - Outcome Logger   │    │  Conversation   │  │                │  │  │  │
│                     │    │  Steering       │  │                │  │  │  │
└────────┬────────────┘    └─────────────────┘  └────────────────┘  │  │  │
         │                                                          │  │  │
         │  ┌───────────────────────────────────────────────────┐   │  │  │
         │  │          Voice Services Subnet (10.0.2.0/24)      │   │  │  │
         │  │                                                    │   │  │  │
         │  │  ┌──────────────────┐    ┌──────────────────────┐  │   │  │  │
         │  │  │ Azure Communic.  │    │ Azure Speech         │  │   │  │  │
         ├──┼─►│ Services (ACS)   │    │ Services             │  │   │  │  │
         │  │  │ - Voice Calling  │    │ - Neural TTS         │  │   │  │  │
         │  │  │ - Call Recording │    │ - Real-time STT      │  │   │  │  │
         │  │  │ - DTMF Handling  │    │ - Custom Voice       │  │   │  │  │
         │  │  │ - Voicemail Det. │    │ - Multilingual       │  │   │  │  │
         │  │  └──────────────────┘    └──────────────────────┘  │   │  │  │
         │  │                                                    │   │  │  │
         │  │  ┌──────────────────┐    ┌──────────────────────┐  │   │  │  │
         │  │  │ Azure AI         │    │ Service Bus          │  │   │  │  │
         │  │  │ Language         │    │ (Call Queue Mgmt)    │  │   │  │  │
         │  │  │ - Sentiment      │    │ - Priority Queues    │  │   │  │  │
         │  │  │ - Intent Detect  │    │ - Dead Letter Queue  │  │   │  │  │
         │  │  └──────────────────┘    └──────────────────────┘  │   │  │  │
         │  └───────────────────────────────────────────────────┘   │  │  │
         │                                                          │  │  │
         │  ┌───────────────────────────────────────────────────┐   │  │  │
         │  │            Data Subnet (10.0.3.0/24)              │   │  │  │
         │  │                                                    │   │  │  │
         │  │  ┌──────────┐  ┌────────────┐  ┌───────────────┐  │   │  │  │
         │  │  │ Cosmos DB│  │ Blob Store │  │ Redis Cache   │  │   │  │  │
         │  │  │ -Campaign│  │ -Recordings│  │ -DNC List     │  │   │  │  │
         │  │  │ -Call Log│  │ -Voicemail │  │ -Call State   │  │   │  │  │
         │  │  │ -Scripts │  │ -Exports   │  │ -Rate Limits  │  │   │  │  │
         │  │  └──────────┘  └────────────┘  └───────────────┘  │   │  │  │
         │  └───────────────────────────────────────────────────┘   │  │  │
         │                                                          │  │  │
         │  ┌───────────────────────────────────────────────────┐   │  │  │
         │  │       Integration Subnet (10.0.4.0/24)            │   │  │  │
         │  │                                                    │   │  │  │
         │  │  ┌─────────────┐  ┌──────────────┐  ┌──────────┐  │   │  │  │
         │  │  │  Key Vault  │  │ Event Hub    │  │ Stream   │  │   │  │  │
         │  │  │  (Secrets)  │  │ (Call Events)│  │ Analytics│  │   │  │  │
         │  │  └─────────────┘  └──────────────┘  └──────────┘  │   │  │  │
         │  └───────────────────────────────────────────────────┘   │  │  │
         └──────────────────────────────────────────────────────────┘  │  │
                                                                       │  │
┌──────────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │              CAMPAIGN & SCHEDULING PIPELINE                      │   │
│   │                                                                  │   │
│   │  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐  │   │
│   │  │ CRM Import   │   │ CSV/API      │   │ Customer Data        │  │   │
│   │  │ (Dynamics365)│   │ Upload       │   │ Platform (CDP)       │  │   │
│   │  └──────┬───────┘   └──────┬───────┘   └──────────┬───────────┘  │   │
│   │         │                  │                       │             │   │
│   │         └──────────────────┼───────────────────────┘             │   │
│   │                            ▼                                     │   │
│   │                 ┌──────────────────┐                              │   │
│   │                 │  Campaign Engine │                              │   │
│   │                 │  (Durable Func)  │                              │   │
│   │                 └────────┬─────────┘                              │   │
│   │                          │                                       │   │
│   │         ┌────────────────┼──────────────────┐                    │   │
│   │         ▼                ▼                  ▼                    │   │
│   │  ┌────────────┐  ┌────────────┐     ┌────────────────┐          │   │
│   │  │ DNC/TCPA   │  │ Schedule   │     │ Script Gen     │          │   │
│   │  │ Compliance │  │ Optimizer  │     │ (GPT-4o)       │          │   │
│   │  │ Check      │  │ (Avail.    │     │                │          │   │
│   │  │ (Redis)    │  │  Patterns) │     │                │          │   │
│   │  └────────────┘  └────────────┘     └────────────────┘          │   │
│   │         │                │                  │                    │   │
│   │         └────────────────┼──────────────────┘                    │   │
│   │                          ▼                                       │   │
│   │                 ┌──────────────────┐                              │   │
│   │                 │  Service Bus     │                              │   │
│   │                 │  (Call Queue)    │                              │   │
│   │                 └──────────────────┘                              │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                    OBSERVABILITY LAYER                            │   │
│   │                                                                  │   │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │   │
│   │  │ App Insights│  │Log Analytics│  │ Azure Monitor           │  │   │
│   │  │ (APM)       │  │ (Logs)      │  │ (Metrics/Alerts)        │  │   │
│   │  └─────────────┘  └─────────────┘  └─────────────────────────┘  │   │
│   │                                                                  │   │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │   │
│   │  │ Stream      │  │ Power BI    │  │ Defender for Cloud      │  │   │
│   │  │ Analytics   │  │ (Real-time  │  │ (Security Posture)      │  │   │
│   │  │ (Live KPI)  │  │  Dashboard) │  │                         │  │   │
│   │  └─────────────┘  └─────────────┘  └─────────────────────────┘  │   │
│   └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     OUTBOUND CALL FLOW WITH AI CONVERSATION              │
└─────────────────────────────────────────────────────────────────────────┘

    Campaign Trigger                                    Call Outcome
        │                                                   ▲
        ▼                                                   │
┌───────────────┐                                  ┌───────────────┐
│ 1. Load Call  │                                  │ 10. Classify  │
│ List from     │                                  │ Outcome       │
│ Cosmos DB     │                                  │ (GPT-4o)      │
└───────┬───────┘                                  └───────┬───────┘
        │                                                   │
        ▼                                                   │
┌───────────────┐                                  ┌───────────────┐
│ 2. DNC/TCPA   │                                  │ 9. End Call   │
│ Check         │──── BLOCKED ──► Log & Skip       │ & Store       │
│ (Redis Cache) │                                  │ Recording     │
└───────┬───────┘                                  └───────┬───────┘
        │ CLEAR                                            │
        ▼                                                   │
┌───────────────┐                                  ┌───────────────┐
│ 3. Schedule   │                                  │ 8. Sentiment  │
│ Check (Avail. │                                  │ Escalation?   │
│ Window OK?)   │                                  │ (AI Language) │
└───────┬───────┘                                  └───────┬───────┘
        │                                                   │
        ▼                                                   │
┌───────────────┐      ┌───────────────┐          ┌───────────────┐
│ 4. Queue Call │─────►│ 5. Dial via   │─────────►│ 6. Voicemail  │
│ (Service Bus) │      │ ACS Voice     │          │ Detection     │
└───────────────┘      │ Calling       │          │               │
                       └───────────────┘          └───────┬───────┘
                                                          │
                              ┌────────────────────────────┤
                              │ HUMAN ANSWERED             │ VOICEMAIL
                              ▼                            ▼
                       ┌───────────────┐          ┌───────────────┐
                       │ 7a. AI        │          │ 7b. Drop      │
                       │ Conversation  │          │ Pre-recorded  │
                       │ (GPT-4o +     │          │ Message       │
                       │  TTS/STT)     │          │ (Neural TTS)  │
                       └───────────────┘          └───────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                    COMPLIANCE CHECK FLOW                                  │
└─────────────────────────────────────────────────────────────────────────┘

    Phone Number
        │
        ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ 1. Redis DNC  │────►│ 2. Time Zone  │────►│ 3. Consent    │
│ Cache Lookup  │     │ Validation    │     │ Verification  │
│ (Federal +    │     │ (8am-9pm      │     │ (Opt-in DB)   │
│  State Lists) │     │  local time)  │     │               │
└───────────────┘     └───────────────┘     └───────┬───────┘
                                                     │
                            ┌────────────────────────┤
                            │ VALID                  │ INVALID
                            ▼                        ▼
                     ┌───────────────┐        ┌───────────────┐
                     │ 4a. Approve   │        │ 4b. Block &   │
                     │ for Dialing   │        │ Log Reason    │
                     └───────────────┘        └───────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                    CALL ANALYTICS FLOW                                    │
└─────────────────────────────────────────────────────────────────────────┘

    Call Events (ACS)
        │
        ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ 1. Event Hub  │────►│ 2. Stream     │────►│ 3. Power BI   │
│ (Ingest)      │     │ Analytics     │     │ (Real-time    │
│               │     │ (Aggregate)   │     │  Dashboard)   │
└───────────────┘     └───────────────┘     └───────────────┘
        │                     │
        ▼                     ▼
┌───────────────┐     ┌───────────────┐
│ 4. Cosmos DB  │     │ 5. Blob Store │
│ (Call Detail  │     │ (Recordings   │
│  Records)     │     │  Archive)     │
└───────────────┘     └───────────────┘
```

---

## Component Details

### 1. Frontend Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| Campaign Management Portal | React + TypeScript | Create/manage outbound campaigns, upload call lists |
| Agent Desktop | React + SignalR | Live call monitoring, escalation handling, agent workspace |
| Analytics Dashboard | Power BI Embedded | Real-time call KPIs, campaign performance, sentiment trends |

### 2. API Gateway Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Azure Front Door | WAF Policy, SSL, geo-routing | Global load balancing, DDoS protection |
| APIM | OAuth2/JWT, rate limits, request routing | API management, throttling, developer portal |

### 3. Voice & AI Layer

| Component | Model/Service | Purpose |
|-----------|---------------|---------|
| Azure OpenAI | GPT-4o (gpt-4o-2024-08-06) | Script generation, real-time conversation steering, outcome classification |
| Azure Communication Services | Voice Calling SDK | Outbound dialing, call recording, DTMF, voicemail detection |
| Azure Speech Services | Neural TTS (en-US-JennyNeural) | Natural voice synthesis, real-time text-to-speech, multilingual |
| Azure Speech Services | Whisper STT | Real-time speech-to-text for conversation transcription |
| Azure AI Language | Sentiment Analysis v3 | Real-time sentiment scoring for escalation triggers |
| Azure Bot Service | Bot Framework Composer | Dialog management, conversation flow control |

### 4. Orchestration Layer

| Component | Runtime | Purpose |
|-----------|---------|---------|
| Call Orchestrator | Azure Functions (Python 3.11) | Call lifecycle management, compliance gating, voice pipeline |
| Campaign Engine | Durable Functions | Campaign scheduling, call list processing, retry logic |
| Schedule Optimizer | Azure Functions | Customer availability pattern analysis, optimal call timing |
| Compliance Engine | Azure Functions | DNC checking, TCPA validation, consent verification |

### 5. Messaging & Event Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Service Bus | Premium tier, partitioned queues | Call queue management, priority routing, dead letter handling |
| Event Hub | Standard tier, 4 partitions | Real-time call event ingestion for analytics |
| Stream Analytics | 6 SU (streaming units) | Real-time aggregation of call metrics, windowed analytics |

### 6. Data Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Cosmos DB | Multi-region, serverless | Campaign data, call logs, conversation scripts, CDR |
| Blob Storage | Hot + Cool tiers, immutable | Call recordings, voicemail audio, compliance exports |
| Redis Cache | P1 Premium, 6GB | DNC list cache, active call state, rate limiting |

### 7. Security & Monitoring Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Key Vault | RBAC, soft delete, purge protection | API keys, connection strings, encryption keys |
| App Insights | Workspace-based | APM, distributed tracing, call performance metrics |
| Log Analytics | 90-day retention | Centralized logging, KQL queries, compliance audit |
| Azure Monitor | Alert rules, action groups | SLA monitoring, threshold alerts, auto-scaling triggers |
| Managed Identity | System-assigned | Passwordless service authentication across all resources |
| Entra ID | OAuth2/OIDC, RBAC | Campaign operator and agent authentication |
| Private Link | All PaaS services | Network isolation for voice and data services |

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SECURITY LAYERS                                   │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: PERIMETER SECURITY                                              │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Azure Front │  │ WAF Policy  │  │ DDoS        │  │ Geo-filtering   │  │
│ │ Door        │  │ (OWASP 3.2) │  │ Protection  │  │ (US-only for    │  │
│ │             │  │             │  │ Standard    │  │  TCPA scope)    │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: IDENTITY & ACCESS                                               │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Entra ID    │  │ Conditional │  │ MFA         │  │ PIM (Just-in-   │  │
│ │ (SSO)       │  │ Access      │  │ Enforcement │  │ time access)    │  │
│ │ Campaign    │  │ (Device +   │  │ (All Admin  │  │ Campaign Admin  │  │
│ │ Operators   │  │  Location)  │  │  Actions)   │  │ elevated roles  │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: NETWORK SECURITY                                                │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ VNET        │  │ NSG Rules   │  │ Private     │  │ Service         │  │
│ │ Isolation   │  │ (Least Priv)│  │ Endpoints   │  │ Endpoints       │  │
│ │ (4 Subnets) │  │ Voice +Data │  │ (All PaaS)  │  │ (ACS Isolated)  │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: TCPA COMPLIANCE & CALL RECORDING CONSENT                        │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ DNC List    │  │ TCPA Time   │  │ Call Record │  │ Consent         │  │
│ │ Management  │  │ Window      │  │ Consent     │  │ Database        │  │
│ │ (Federal +  │  │ Enforcement │  │ Announcement│  │ (Opt-in/out     │  │
│ │  State DNC) │  │ (8am-9pm)   │  │ (Auto-play) │  │  tracking)      │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 5: DATA SECURITY                                                   │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Encryption  │  │ Key Vault   │  │ PII Masking │  │ Immutable Blob  │  │
│ │ at Rest/    │  │ (CMK for    │  │ (Phone Nums │  │ (Call Recording │  │
│ │ Transit     │  │  recordings)│  │  in Logs)   │  │  retention)     │  │
│ │ (TLS 1.3)   │  │             │  │             │  │                 │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 6: MONITORING & AUDIT COMPLIANCE                                   │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Defender    │  │ Sentinel    │  │ Audit Logs  │  │ Compliance      │  │
│ │ for Cloud   │  │ (SIEM)      │  │ (All Call   │  │ Reporting       │  │
│ │ (Threat     │  │ Call Fraud  │  │  Actions    │  │ (TCPA/DNC       │  │
│ │  Detection) │  │ Detection   │  │  Immutable) │  │  audit trail)   │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture

```yaml
# Multi-Environment Deployment Strategy

environments:
  development:
    subscription: dev-subscription
    resource_group: rg-voice-ai-outbound-dev
    location: eastus
    sku_tier: basic
    max_concurrent_calls: 10
    dnc_refresh_interval: "24h"

  staging:
    subscription: staging-subscription
    resource_group: rg-voice-ai-outbound-stg
    location: eastus
    sku_tier: standard
    max_concurrent_calls: 100
    dnc_refresh_interval: "6h"

  production:
    subscription: prod-subscription
    resource_group: rg-voice-ai-outbound-prod
    location: eastus
    secondary_location: westus2  # DR
    sku_tier: premium
    max_concurrent_calls: 1000
    dnc_refresh_interval: "1h"

voice_platform:
  communication_services:
    phone_numbers: toll-free + local DIDs
    recording_policy: dual-channel
    voicemail_detection: enabled
    max_ring_time_seconds: 30
  speech_services:
    tts_voice: en-US-JennyNeural
    stt_model: whisper-large
    supported_languages:
      - en-US
      - es-US
      - fr-CA
      - de-DE
      - pt-BR

compliance:
  tcpa:
    calling_hours: "08:00-21:00"
    timezone_enforcement: per-recipient-local
    dnc_sources:
      - federal_dnc_registry
      - state_dnc_lists
      - internal_opt_out_list
    consent_tracking: opt-in-required
    recording_consent: two-party-where-required
  data_retention:
    call_recordings: 90_days
    call_detail_records: 7_years
    compliance_logs: 7_years

deployment_strategy:
  type: blue-green
  rollback_enabled: true
  canary_percentage: 5
  health_check_path: /health
  pre_deploy_checks:
    - dnc_cache_populated
    - speech_services_healthy
    - acs_phone_numbers_active
```

---

## Cost Estimation (Production)

| Service | SKU | Monthly Cost (USD) |
|---------|-----|-------------------|
| Azure OpenAI (GPT-4o) | Pay-as-you-go (script gen + steering) | ~$3,000-8,000 |
| Azure Communication Services | Voice calling (50K calls/mo) | ~$2,500-5,000 |
| Azure Speech Services | Neural TTS + STT (50K calls) | ~$1,500-3,000 |
| Azure AI Language | Sentiment analysis | ~$200 |
| Azure Bot Service | S1 Standard | ~$500 |
| Azure Functions | Premium EP2 (call concurrency) | ~$400 |
| Cosmos DB | Autoscale (campaign + CDR) | ~$300 |
| Event Hub | Standard (4 partitions) | ~$200 |
| Stream Analytics | 6 SU | ~$500 |
| Service Bus | Premium (call queues) | ~$700 |
| Blob Storage | Hot 2TB (recordings) | ~$40 |
| Redis Cache | P1 Premium (DNC cache) | ~$250 |
| Key Vault | Standard | ~$5 |
| APIM | Standard | ~$150 |
| Power BI Embedded | A2 | ~$750 |
| Application Insights | Pay-as-you-go | ~$150 |
| Log Analytics | Pay-as-you-go (90-day) | ~$200 |
| Private Link | 8 endpoints | ~$60 |
| **Total Estimated** | | **~$11,000-20,500** |

---

## Interview Talking Points

### Architecture Decisions

1. **Why Azure Communication Services over third-party telephony?**
   - Native Azure integration with Speech Services and OpenAI
   - Built-in call recording with dual-channel support
   - Voicemail detection without third-party AMD (answering machine detection)
   - Private Link support for enterprise network isolation
   - Simplified billing through single Azure subscription

2. **Why real-time TTS instead of pre-recorded audio?**
   - GPT-4o steers conversation dynamically based on customer responses
   - Neural TTS (JennyNeural) produces natural-sounding speech indistinguishable from human
   - Enables personalized messaging with customer name, account details
   - Multilingual support without recording separate audio for each language
   - Script changes deploy instantly without re-recording

3. **Why Redis Cache for DNC list management?**
   - Sub-millisecond lookup for phone number compliance checks
   - Federal + state DNC lists loaded in-memory for instant validation
   - Avoids database round-trip latency before every outbound call
   - TTL-based refresh ensures DNC data stays current (hourly refresh in production)
   - Supports bloom filter pattern for memory-efficient large list storage

4. **Why Service Bus for call queue management?**
   - Priority queues allow high-value campaigns to dial first
   - Dead letter queue captures failed calls for retry analysis
   - Session-based ordering ensures call lists process in campaign sequence
   - Competing consumers pattern scales dial-out workers horizontally
   - Built-in duplicate detection prevents calling the same number twice

5. **How does sentiment-based escalation work?**
   - Azure AI Language analyzes real-time STT transcript every 5 seconds
   - Negative sentiment threshold (below 0.3) triggers escalation flag
   - Call Orchestrator routes to available human agent via Service Bus priority queue
   - Agent Desktop receives full conversation transcript and context via SignalR
   - Warm handoff preserves call recording continuity

6. **TCPA Compliance approach?**
   - Three-layer compliance check: DNC list, time zone window, consent status
   - All checks execute before any call is placed (pre-dial compliance gate)
   - Immutable audit logs in Log Analytics for regulatory evidence
   - Call recording consent announcement auto-plays in two-party-consent states
   - Comprehensive opt-out mechanism: DTMF press, voice command, or post-call SMS

### Scalability Considerations

- Azure Functions Premium EP2 with burst scaling handles concurrent call spikes
- Service Bus partitioned queues distribute dial-out load across workers
- Event Hub 4 partitions with consumer groups for parallel analytics processing
- Cosmos DB autoscale adjusts throughput for campaign launch bursts
- Redis Cache P1 handles 100K+ DNC lookups per second
- Stream Analytics scales streaming units dynamically for real-time dashboard
- ACS supports up to 1000 concurrent outbound calls per resource

## Business Domain, Security, Governance & Compliance

### Business Domain
- **Classification:** B2C (Outbound Ops + Compliance)
- **Visibility:** Outbound Ops + Compliance — campaign operators, compliance officers, and outbound call recipients
- **Project Score:** 9.0 / 10 (Critical)

### Security Controls
| Layer | Control | Implementation |
|-------|---------|----------------|
| Network | Private Link | All PaaS services via private endpoints |
| Network | VNET Isolation | 4-subnet topology (App/Voice/Data/Integration) |
| Network | Geo-filtering | US-only access for TCPA-scoped operations |
| Identity | Entra ID SSO | OAuth2/OIDC with MFA for campaign operators |
| Identity | PIM | Just-in-time elevated access for compliance admin |
| Data | TCPA DNC Management | Federal + state Do-Not-Call list enforcement via Redis |
| Data | Voice Biometric Privacy | No voice biometric data collection without explicit consent |
| Data | Call Recording Consent | Dual-party consent auto-announcement in required states |
| Data | PII Masking | Phone number masking in logs and analytics |
| Data | Encryption | AES-256 at rest, TLS 1.3 in transit, CMK for recordings |
| Data | Immutable Logs | WORM-compliant audit logs for 7-year regulatory retention |
| Application | Content Filtering | Azure OpenAI responsible AI for script generation |
| Monitoring | Sentinel SIEM | Call fraud detection and compliance anomaly monitoring |
| Monitoring | Defender for Cloud | Continuous security assessment of voice platform |

### Governance & Compliance
| Area | Policy | Details |
|------|--------|---------|
| TCPA §227 | Enforced | Automated dialing restrictions, prior express consent required |
| STIR/SHAKEN | Implemented | Caller ID authentication to prevent spoofing |
| FCC Regulations | Aligned | Federal Communications Commission telemarketing rules |
| TSR | Enforced | Telemarketing Sales Rule — FTC compliance |
| State DNC | Enforced | State-level Do-Not-Call list compliance (all 50 states) |
| Call Time Windows | Automated | 8am–9pm local time enforcement per TCPA |
| Consent Management | Tracked | Opt-in/opt-out status tracked per phone number |
| Data Retention | Policy | Call recordings 90-day hot, CDR/compliance logs 7-year archive |

### Regulatory Applicability
- **TCPA §227:** Telephone Consumer Protection Act — prior express consent, DNC compliance
- **STIR/SHAKEN:** Caller ID authentication framework to prevent robocall spoofing
- **FCC Declaratory Rulings:** Federal Communications Commission telemarketing enforcement
- **TSR (Telemarketing Sales Rule):** FTC rule governing telemarketing practices
- **State TCPA Variants:** State-specific telemarketing laws (FL, CA, TX mini-TCPA statutes)
- **GDPR:** Applicable for calls to EU-based numbers (international campaigns)
- **BIPA/Voice Privacy:** Biometric Information Privacy Act for voice data handling
