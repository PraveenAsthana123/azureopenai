# API Specification — Azure OpenAI Enterprise RAG Platform

> Complete REST API reference for the Enterprise RAG Copilot platform, covering all endpoints, authentication, schemas, and SDK integration guidance aligned with **CMMI Level 3 | ISO/IEC 42001 | NIST AI RMF**.

---

## Table of Contents

1. [API Overview](#1-api-overview)
2. [Authentication & Authorization](#2-authentication--authorization)
3. [Query API](#3-query-api)
4. [Ingestion API](#4-ingestion-api)
5. [Feedback API](#5-feedback-api)
6. [Health & Readiness Endpoints](#6-health--readiness-endpoints)
7. [Admin Endpoints](#7-admin-endpoints)
8. [Pagination](#8-pagination)
9. [Webhook Callbacks](#9-webhook-callbacks)
10. [Error Response Schema](#10-error-response-schema)
11. [Rate Limiting](#11-rate-limiting)
12. [Request Tracing](#12-request-tracing)
13. [Request & Response Size Limits](#13-request--response-size-limits)
14. [CORS Configuration](#14-cors-configuration)
15. [API Versioning Strategy](#15-api-versioning-strategy)
16. [SDK Usage Examples](#16-sdk-usage-examples)
17. [Postman Collection Structure](#17-postman-collection-structure)
18. [Document Control](#18-document-control)

---

## 1. API Overview

### 1.1 Base URL

All API endpoints are served behind **Azure API Management (APIM)** with the following base URL pattern:

```
https://api.{environment}.enterprise-rag.contoso.com
```

| Environment | Base URL | Purpose |
|-------------|----------|---------|
| Production | `https://api.prod.enterprise-rag.contoso.com` | Live traffic |
| Staging | `https://api.staging.enterprise-rag.contoso.com` | Pre-production validation |
| Development | `https://api.dev.enterprise-rag.contoso.com` | Feature development |

### 1.2 OpenAPI 3.0 Endpoint Summary

The platform exposes a complete **OpenAPI 3.0** specification at `/swagger/v1/swagger.json`. The following table summarizes all available endpoints:

| Method | Path | Description | Auth Required | Rate Limit (req/min) |
|--------|------|-------------|---------------|----------------------|
| `POST` | `/v1/query` | Submit a RAG query | Yes | 60 |
| `POST` | `/v1/ingest` | Upload documents for ingestion | Yes | 20 |
| `GET` | `/v1/ingest/{job_id}` | Poll ingestion job status | Yes | 120 |
| `POST` | `/v1/feedback` | Submit user feedback on a response | Yes | 120 |
| `GET` | `/v1/history` | Retrieve conversation history | Yes | 60 |
| `GET` | `/v1/audit` | Retrieve audit log entries | Yes (Admin) | 30 |
| `GET` | `/v1/admin/tenants` | List configured tenants | Yes (Admin) | 30 |
| `GET` | `/v1/admin/usage` | Retrieve usage metrics | Yes (Admin) | 30 |
| `GET` | `/health` | Liveness probe | No | 300 |
| `GET` | `/ready` | Readiness probe | No | 300 |
| `GET` | `/swagger/v1/swagger.json` | OpenAPI 3.0 specification | No | 60 |

### 1.3 Common Request Headers

All authenticated requests **must** include the following headers:

| Header | Required | Description | Example |
|--------|----------|-------------|---------|
| `Authorization` | Yes | Bearer JWT token from Entra ID | `Bearer eyJhbGciOiJSUzI1NiIs...` |
| `Content-Type` | Yes | Media type of the request body | `application/json` |
| `Accept` | Recommended | Expected response media type | `application/json` |
| `X-Request-Id` | Recommended | Client-generated unique request ID (UUIDv4) | `550e8400-e29b-41d4-a716-446655440000` |
| `X-Correlation-Id` | Optional | Correlation ID for distributed tracing | `corr-20240115-abc123` |
| `X-Tenant-Id` | Conditional | Tenant identifier for multi-tenant isolation | `tenant-contoso-hr` |
| `Accept-Language` | Optional | Preferred response language | `en-US` |

### 1.4 Content Negotiation

The API exclusively supports **JSON** for request and response bodies, with one exception: the ingestion endpoint accepts `multipart/form-data` for document uploads.

| Endpoint | Request Content-Type | Response Content-Type |
|----------|---------------------|-----------------------|
| `/v1/query` | `application/json` | `application/json` |
| `/v1/ingest` | `multipart/form-data` | `application/json` |
| `/v1/feedback` | `application/json` | `application/json` |
| All `GET` endpoints | N/A | `application/json` |

---

## 2. Authentication & Authorization

### 2.1 Microsoft Entra ID OAuth2 Flow

All authenticated API calls require a **Bearer JWT** token obtained via the **OAuth 2.0 Authorization Code with PKCE** flow or the **Client Credentials** flow (for service-to-service).

**OAuth2 Authorization Code Flow (ASCII Diagram):**

```
┌──────────────┐                              ┌─────────────────────┐
│              │  1. Authorization Request     │                     │
│   Client     │─────────────────────────────► │  Microsoft Entra ID │
│   (Browser/  │                               │  (login.microsoft   │
│    SPA)      │  2. Authorization Code        │   online.com)       │
│              │◄───────────────────────────── │                     │
│              │                               └─────────────────────┘
│              │  3. Token Request (Code +              │
│              │     PKCE Verifier)                     │
│              │──────────────────────────────►         │
│              │                                        │
│              │  4. Access Token (JWT) +               │
│              │     Refresh Token                      │
│              │◄──────────────────────────────         │
│              │                               ┌─────────────────────┐
│              │  5. API Call with Bearer Token │                     │
│              │─────────────────────────────► │   Azure API         │
│              │                               │   Management        │
│              │  6. APIM validates JWT,        │   (APIM)            │
│              │     extracts claims,           │                     │
│              │     enforces RBAC              │        │            │
│              │                               │        ▼            │
│              │                               │  ┌──────────────┐   │
│              │  7. JSON Response              │  │ Azure        │   │
│              │◄───────────────────────────── │  │ Functions    │   │
│              │                               │  └──────────────┘   │
└──────────────┘                               └─────────────────────┘
```

**Client Credentials Flow (Service-to-Service):**

```
┌──────────────────┐                        ┌─────────────────────┐
│  Backend Service  │  1. POST /token        │                     │
│  (Daemon / Job)   │  grant_type=           │  Microsoft Entra ID │
│                   │  client_credentials    │                     │
│                   │  client_id=...         │                     │
│                   │  client_secret=...     │                     │
│                   │  scope=api://...       │                     │
│                   │───────────────────────►│                     │
│                   │                        │                     │
│                   │  2. Access Token (JWT) │                     │
│                   │◄───────────────────────│                     │
│                   │                        └─────────────────────┘
│                   │                        ┌─────────────────────┐
│                   │  3. API Call + Bearer   │                     │
│                   │───────────────────────►│   APIM / Functions  │
│                   │                        │                     │
│                   │  4. Response            │                     │
│                   │◄───────────────────────│                     │
└──────────────────┘                        └─────────────────────┘
```

### 2.2 JWT Token Structure

The access token **must** contain the following claims. APIM and the backend functions validate these claims on every request.

| Claim | Type | Required | Description | Example Value |
|-------|------|----------|-------------|---------------|
| `iss` | string | Yes | Token issuer (Entra ID authority) | `https://login.microsoftonline.com/{tenant-id}/v2.0` |
| `aud` | string | Yes | Audience (API Application ID URI) | `api://enterprise-rag-prod` |
| `sub` | string | Yes | Subject identifier (user principal) | `AbC123dEf-4567-890a-bcde-f01234567890` |
| `oid` | string | Yes | Object ID of the authenticated user/principal | `12345678-abcd-ef01-2345-6789abcdef01` |
| `tid` | string | Yes | Tenant ID of the Entra ID directory | `a1b2c3d4-e5f6-7890-abcd-ef0123456789` |
| `roles` | string[] | Yes | Application roles assigned to the user | `["RAG.Query", "RAG.Ingest"]` |
| `name` | string | No | Display name of the user | `Jane Smith` |
| `preferred_username` | string | No | User principal name | `jsmith@contoso.com` |
| `exp` | integer | Yes | Token expiration (Unix timestamp) | `1705363200` |
| `iat` | integer | Yes | Token issued-at (Unix timestamp) | `1705359600` |
| `nbf` | integer | Yes | Token not-before (Unix timestamp) | `1705359600` |

### 2.3 Role-Based Access Control (RBAC)

Endpoints are gated by **application roles** defined in the Entra ID App Registration:

| Role | Endpoints Accessible | Description |
|------|---------------------|-------------|
| `RAG.Query` | `POST /v1/query`, `GET /v1/history`, `POST /v1/feedback` | Standard end-user access |
| `RAG.Ingest` | `POST /v1/ingest`, `GET /v1/ingest/{job_id}` | Document upload and status |
| `RAG.Admin` | `GET /v1/admin/tenants`, `GET /v1/admin/usage`, `GET /v1/audit` | Platform administration |
| `RAG.Webhook` | Webhook callback registration and management | Webhook subscriber role |

**RBAC Enforcement Matrix:**

| Endpoint | RAG.Query | RAG.Ingest | RAG.Admin | RAG.Webhook | Unauthenticated |
|----------|-----------|------------|-----------|-------------|-----------------|
| `POST /v1/query` | Yes | No | Yes | No | No |
| `POST /v1/ingest` | No | Yes | Yes | No | No |
| `GET /v1/ingest/{job_id}` | No | Yes | Yes | No | No |
| `POST /v1/feedback` | Yes | No | Yes | No | No |
| `GET /v1/history` | Yes | No | Yes | No | No |
| `GET /v1/audit` | No | No | Yes | No | No |
| `GET /v1/admin/tenants` | No | No | Yes | No | No |
| `GET /v1/admin/usage` | No | No | Yes | No | No |
| `GET /health` | Yes | Yes | Yes | Yes | Yes |
| `GET /ready` | Yes | Yes | Yes | Yes | Yes |

---

## 3. Query API

### 3.1 POST /v1/query

Submit a **natural language query** against the enterprise RAG knowledge base. The platform performs hybrid search (vector + BM25 + semantic ranking), retrieves relevant document chunks, and generates a grounded response via Azure OpenAI GPT-4o.

**Request Schema:**

```json
{
  "query": "What is the company's parental leave policy?",
  "conversation_id": "conv-a1b2c3d4-e5f6-7890-abcd-ef0123456789",
  "options": {
    "top_k": 5,
    "temperature": 0.1,
    "max_tokens": 2048,
    "include_citations": true,
    "include_scores": false,
    "search_mode": "hybrid",
    "semantic_ranker": true,
    "filters": {
      "department": "HR",
      "document_type": "policy",
      "date_range": {
        "start": "2023-01-01",
        "end": "2024-12-31"
      }
    }
  },
  "user_context": {
    "locale": "en-US",
    "timezone": "America/New_York"
  }
}
```

**Request Fields:**

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `query` | string | Yes | 1-2000 characters | The natural language question |
| `conversation_id` | string | No | UUID v4 format | Existing conversation ID for multi-turn context |
| `options.top_k` | integer | No | 1-20, default 5 | Number of document chunks to retrieve |
| `options.temperature` | float | No | 0.0-1.0, default 0.1 | LLM generation temperature |
| `options.max_tokens` | integer | No | 1-4096, default 2048 | Maximum tokens in the response |
| `options.include_citations` | boolean | No | default `true` | Include source citations in response |
| `options.include_scores` | boolean | No | default `false` | Include relevance scores per citation |
| `options.search_mode` | string | No | `hybrid`, `vector`, `keyword` | Search strategy (default `hybrid`) |
| `options.semantic_ranker` | boolean | No | default `true` | Enable Azure AI Search semantic ranker |
| `options.filters` | object | No | — | Metadata filters to scope the search |
| `options.filters.department` | string | No | — | Department scope filter |
| `options.filters.document_type` | string | No | — | Document type filter |
| `options.filters.date_range` | object | No | ISO 8601 dates | Date range filter for documents |
| `user_context.locale` | string | No | BCP 47 format | User locale preference |
| `user_context.timezone` | string | No | IANA timezone | User timezone for date formatting |

**Response Schema (200 OK):**

```json
{
  "response_id": "resp-f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "conversation_id": "conv-a1b2c3d4-e5f6-7890-abcd-ef0123456789",
  "answer": "The company offers 16 weeks of paid parental leave for all eligible employees. Birth parents receive an additional 2 weeks of recovery leave. Eligibility requires a minimum of 12 months of continuous employment. Leave can be taken within 12 months of the birth or adoption date.",
  "citations": [
    {
      "citation_id": "cite-001",
      "document_id": "doc-8a7b6c5d-4e3f-2a1b-0c9d-8e7f6a5b4c3d",
      "document_title": "Parental Leave Policy 2024",
      "chunk_id": "chunk-0042",
      "chunk_text": "All eligible employees are entitled to 16 weeks of paid parental leave...",
      "page_number": 3,
      "section": "Section 4.2 - Leave Duration",
      "relevance_score": 0.9542,
      "source_url": "https://docs.contoso.com/hr/parental-leave-2024.pdf"
    },
    {
      "citation_id": "cite-002",
      "document_id": "doc-1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
      "document_title": "Employee Benefits Handbook",
      "chunk_id": "chunk-0187",
      "chunk_text": "Birth parents receive an additional 2 weeks of recovery leave...",
      "page_number": 12,
      "section": "Chapter 7 - Family Benefits",
      "relevance_score": 0.9103,
      "source_url": "https://docs.contoso.com/hr/benefits-handbook-2024.pdf"
    }
  ],
  "metadata": {
    "model": "gpt-4o",
    "model_version": "2024-08-06",
    "prompt_tokens": 3842,
    "completion_tokens": 287,
    "total_tokens": 4129,
    "search_duration_ms": 245,
    "generation_duration_ms": 1842,
    "total_duration_ms": 2087,
    "groundedness_score": 0.94,
    "chunks_retrieved": 5,
    "chunks_used": 2
  },
  "created_at": "2024-01-15T14:32:18.456Z"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `response_id` | string | Unique identifier for this response |
| `conversation_id` | string | Conversation ID (new or existing) |
| `answer` | string | The generated, grounded response text |
| `citations` | array | List of source citations used in the answer |
| `citations[].citation_id` | string | Unique citation reference ID |
| `citations[].document_id` | string | Source document identifier |
| `citations[].document_title` | string | Human-readable document title |
| `citations[].chunk_id` | string | Specific chunk identifier |
| `citations[].chunk_text` | string | Excerpt of the source text |
| `citations[].page_number` | integer | Page number in the source document |
| `citations[].section` | string | Section heading in the source document |
| `citations[].relevance_score` | float | Relevance score (0.0-1.0), present when `include_scores=true` |
| `citations[].source_url` | string | URL to the original document |
| `metadata.model` | string | LLM model used for generation |
| `metadata.prompt_tokens` | integer | Tokens consumed by the prompt |
| `metadata.completion_tokens` | integer | Tokens in the generated response |
| `metadata.total_duration_ms` | integer | Total end-to-end latency in milliseconds |
| `metadata.groundedness_score` | float | Groundedness evaluation score (0.0-1.0) |
| `created_at` | string | ISO 8601 timestamp of response creation |

### 3.2 Query API Error Codes

| HTTP Status | Error Code | Description | Resolution |
|-------------|------------|-------------|------------|
| `400` | `INVALID_QUERY` | Query text is empty or exceeds 2000 characters | Ensure query is 1-2000 characters |
| `400` | `INVALID_PARAMETER` | Invalid value for a request parameter | Check parameter constraints in the schema |
| `401` | `UNAUTHORIZED` | Missing or invalid Bearer token | Obtain a valid JWT from Entra ID |
| `403` | `FORBIDDEN` | Token valid but lacks `RAG.Query` role | Request the `RAG.Query` role from your admin |
| `403` | `TENANT_ACCESS_DENIED` | User not authorized for the specified tenant | Verify tenant assignment in Entra ID |
| `429` | `RATE_LIMIT_EXCEEDED` | Request rate limit exceeded | Wait for `Retry-After` seconds, then retry |
| `500` | `INTERNAL_ERROR` | Unexpected server error | Retry with exponential backoff; contact support if persistent |
| `503` | `SERVICE_UNAVAILABLE` | Backend dependency (OpenAI/Search) unavailable | Retry after `Retry-After` seconds |
| `503` | `MODEL_OVERLOADED` | Azure OpenAI model capacity exceeded | Retry with exponential backoff |

---

## 4. Ingestion API

### 4.1 POST /v1/ingest

Upload one or more documents for asynchronous ingestion into the RAG knowledge base. Documents are chunked, embedded, and indexed into **Azure AI Search**.

**Request:** `multipart/form-data`

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `file` | binary | Yes | Max 100MB per file | The document file to ingest |
| `metadata` | string (JSON) | No | Valid JSON | Document metadata as a JSON string |
| `tenant_id` | string | Yes | — | Target tenant for the document |
| `overwrite` | string | No | `true` or `false`, default `false` | Overwrite existing document with same name |
| `chunking_strategy` | string | No | `fixed`, `semantic`, `page`, default `semantic` | Chunking method |
| `chunk_size` | string | No | 256-2048 tokens, default 512 | Target chunk size in tokens |
| `chunk_overlap` | string | No | 0-256 tokens, default 128 | Overlap between consecutive chunks |

**Supported File Types:**

| Format | Extension | Max Size | Notes |
|--------|-----------|----------|-------|
| PDF | `.pdf` | 100 MB | OCR-enabled via Azure AI Document Intelligence |
| Word | `.docx` | 50 MB | Styles and headings preserved as metadata |
| Excel | `.xlsx` | 50 MB | Each sheet processed separately |
| PowerPoint | `.pptx` | 50 MB | Slide text and notes extracted |
| Plain Text | `.txt` | 20 MB | UTF-8 encoding required |
| Markdown | `.md` | 20 MB | Headings used for section metadata |
| HTML | `.html` | 20 MB | Cleaned and converted to plain text |
| CSV | `.csv` | 50 MB | Row-level chunking with header context |

**Example Request (cURL):**

```bash
curl -X POST "https://api.prod.enterprise-rag.contoso.com/v1/ingest" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Request-Id: $(uuidgen)" \
  -H "X-Tenant-Id: tenant-contoso-hr" \
  -F "file=@/path/to/parental-leave-policy-2024.pdf" \
  -F "tenant_id=tenant-contoso-hr" \
  -F 'metadata={"department":"HR","document_type":"policy","effective_date":"2024-01-01","classification":"internal","owner":"hr-policies@contoso.com"}' \
  -F "chunking_strategy=semantic" \
  -F "chunk_size=512" \
  -F "chunk_overlap=128"
```

**Response (202 Accepted):**

```json
{
  "job_id": "ingest-7f3a8b2c-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
  "status": "accepted",
  "file_name": "parental-leave-policy-2024.pdf",
  "file_size_bytes": 2456789,
  "tenant_id": "tenant-contoso-hr",
  "estimated_duration_seconds": 120,
  "status_url": "/v1/ingest/ingest-7f3a8b2c-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
  "created_at": "2024-01-15T10:15:32.123Z"
}
```

### 4.2 GET /v1/ingest/{job_id}

Poll the status of an ingestion job. The client should poll at a **recommended interval of 5 seconds** until the job reaches a terminal state (`completed`, `failed`, or `cancelled`).

**Ingestion Job Lifecycle:**

```
┌──────────┐     ┌────────────┐     ┌────────────┐     ┌──────────────┐     ┌───────────┐
│ accepted │────►│ processing │────►│  chunking   │────►│  embedding   │────►│ completed │
└──────────┘     └────────────┘     └────────────┘     └──────────────┘     └───────────┘
                       │                  │                    │
                       ▼                  ▼                    ▼
                 ┌──────────┐       ┌──────────┐        ┌──────────┐
                 │  failed  │       │  failed  │        │  failed  │
                 └──────────┘       └──────────┘        └──────────┘
```

**Response (200 OK — In Progress):**

```json
{
  "job_id": "ingest-7f3a8b2c-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
  "status": "embedding",
  "progress_percent": 72,
  "file_name": "parental-leave-policy-2024.pdf",
  "tenant_id": "tenant-contoso-hr",
  "steps": [
    { "name": "upload", "status": "completed", "duration_ms": 1234 },
    { "name": "extraction", "status": "completed", "duration_ms": 8765 },
    { "name": "chunking", "status": "completed", "duration_ms": 3210, "chunks_created": 47 },
    { "name": "embedding", "status": "in_progress", "chunks_embedded": 34, "chunks_total": 47 },
    { "name": "indexing", "status": "pending" }
  ],
  "created_at": "2024-01-15T10:15:32.123Z",
  "updated_at": "2024-01-15T10:17:14.567Z"
}
```

**Response (200 OK — Completed):**

```json
{
  "job_id": "ingest-7f3a8b2c-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
  "status": "completed",
  "progress_percent": 100,
  "file_name": "parental-leave-policy-2024.pdf",
  "tenant_id": "tenant-contoso-hr",
  "result": {
    "document_id": "doc-8a7b6c5d-4e3f-2a1b-0c9d-8e7f6a5b4c3d",
    "chunks_created": 47,
    "chunks_indexed": 47,
    "total_tokens": 24350,
    "embedding_model": "text-embedding-3-large",
    "embedding_dimensions": 3072
  },
  "steps": [
    { "name": "upload", "status": "completed", "duration_ms": 1234 },
    { "name": "extraction", "status": "completed", "duration_ms": 8765 },
    { "name": "chunking", "status": "completed", "duration_ms": 3210, "chunks_created": 47 },
    { "name": "embedding", "status": "completed", "duration_ms": 12456, "chunks_embedded": 47 },
    { "name": "indexing", "status": "completed", "duration_ms": 5678, "chunks_indexed": 47 }
  ],
  "created_at": "2024-01-15T10:15:32.123Z",
  "completed_at": "2024-01-15T10:17:48.234Z"
}
```

**Ingestion Error Codes:**

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| `400` | `UNSUPPORTED_FILE_TYPE` | File format not in supported list |
| `400` | `FILE_TOO_LARGE` | File exceeds maximum size limit |
| `400` | `INVALID_METADATA` | Metadata JSON is malformed |
| `401` | `UNAUTHORIZED` | Missing or invalid Bearer token |
| `403` | `FORBIDDEN` | Token lacks `RAG.Ingest` role |
| `404` | `JOB_NOT_FOUND` | Ingestion job ID does not exist |
| `409` | `DOCUMENT_EXISTS` | Document already exists and `overwrite=false` |
| `429` | `RATE_LIMIT_EXCEEDED` | Too many ingestion requests |
| `500` | `EXTRACTION_FAILED` | Document content extraction failed |
| `500` | `EMBEDDING_FAILED` | Embedding generation failed |
| `500` | `INDEXING_FAILED` | Search index update failed |

---

## 5. Feedback API

### 5.1 POST /v1/feedback

Submit user feedback on a query response. Feedback is stored in **Azure Cosmos DB** and used for continuous improvement of the RAG pipeline through the evaluation framework.

**Request Schema:**

```json
{
  "response_id": "resp-f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "conversation_id": "conv-a1b2c3d4-e5f6-7890-abcd-ef0123456789",
  "rating": "positive",
  "rating_score": 5,
  "feedback_type": "accuracy",
  "comment": "The answer correctly referenced the updated 2024 policy with accurate leave duration.",
  "citation_feedback": [
    {
      "citation_id": "cite-001",
      "relevant": true
    },
    {
      "citation_id": "cite-002",
      "relevant": true
    }
  ]
}
```

**Request Fields:**

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `response_id` | string | Yes | Valid response ID | The response being rated |
| `conversation_id` | string | No | Valid conversation ID | Associated conversation |
| `rating` | string | Yes | `positive`, `negative`, `neutral` | Thumbs up/down/neutral |
| `rating_score` | integer | No | 1-5 | Granular satisfaction score |
| `feedback_type` | string | No | `accuracy`, `completeness`, `relevance`, `clarity`, `other` | Category of feedback |
| `comment` | string | No | Max 2000 characters | Free-text feedback comment |
| `citation_feedback` | array | No | — | Per-citation relevance feedback |
| `citation_feedback[].citation_id` | string | Yes | Valid citation ID | Citation being rated |
| `citation_feedback[].relevant` | boolean | Yes | — | Whether the citation was relevant |

**Response (201 Created):**

```json
{
  "feedback_id": "fb-9c8b7a6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d",
  "response_id": "resp-f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "recorded",
  "created_at": "2024-01-15T14:35:42.789Z"
}
```

---

## 6. Health & Readiness Endpoints

### 6.1 GET /health

**Liveness probe** used by Azure Container Apps / Kubernetes to determine if the application process is running. This endpoint does **not** check downstream dependencies.

**Response (200 OK):**

```json
{
  "status": "healthy",
  "version": "1.4.2",
  "timestamp": "2024-01-15T14:00:00.000Z"
}
```

**Response (503 Service Unavailable):**

```json
{
  "status": "unhealthy",
  "version": "1.4.2",
  "timestamp": "2024-01-15T14:00:00.000Z"
}
```

### 6.2 GET /ready

**Readiness probe** that validates connectivity to all critical downstream dependencies. Traffic is not routed to instances that fail this check.

**Response (200 OK):**

```json
{
  "status": "ready",
  "version": "1.4.2",
  "checks": [
    {
      "name": "azure_openai",
      "status": "healthy",
      "latency_ms": 45,
      "endpoint": "https://contoso-openai-prod.openai.azure.com"
    },
    {
      "name": "azure_ai_search",
      "status": "healthy",
      "latency_ms": 23,
      "endpoint": "https://contoso-search-prod.search.windows.net"
    },
    {
      "name": "cosmos_db",
      "status": "healthy",
      "latency_ms": 12,
      "endpoint": "https://contoso-cosmos-prod.documents.azure.com"
    },
    {
      "name": "blob_storage",
      "status": "healthy",
      "latency_ms": 8,
      "endpoint": "https://contosostgprod.blob.core.windows.net"
    },
    {
      "name": "redis_cache",
      "status": "healthy",
      "latency_ms": 3,
      "endpoint": "contoso-redis-prod.redis.cache.windows.net"
    }
  ],
  "timestamp": "2024-01-15T14:00:00.000Z"
}
```

**Response (503 Service Unavailable):**

```json
{
  "status": "not_ready",
  "version": "1.4.2",
  "checks": [
    {
      "name": "azure_openai",
      "status": "healthy",
      "latency_ms": 45
    },
    {
      "name": "azure_ai_search",
      "status": "degraded",
      "latency_ms": 5200,
      "error": "Connection timeout after 5000ms"
    },
    {
      "name": "cosmos_db",
      "status": "healthy",
      "latency_ms": 12
    }
  ],
  "timestamp": "2024-01-15T14:00:00.000Z"
}
```

**Health Check Status Values:**

| Status | Description | HTTP Code |
|--------|-------------|-----------|
| `healthy` | All dependency checks pass | 200 |
| `ready` | All dependency checks pass (readiness) | 200 |
| `degraded` | One or more non-critical dependencies slow or failing | 200 |
| `unhealthy` | Application process is failing | 503 |
| `not_ready` | One or more critical dependencies are failing | 503 |

---

## 7. Admin Endpoints

### 7.1 GET /v1/admin/tenants

Retrieve the list of configured tenants with their current status and configuration. **Requires `RAG.Admin` role.**

**Response (200 OK):**

```json
{
  "tenants": [
    {
      "tenant_id": "tenant-contoso-hr",
      "display_name": "Contoso HR Department",
      "status": "active",
      "index_name": "idx-contoso-hr",
      "document_count": 342,
      "chunk_count": 15847,
      "storage_size_mb": 245.6,
      "created_at": "2023-06-15T09:00:00.000Z",
      "last_ingestion_at": "2024-01-14T16:32:00.000Z",
      "configuration": {
        "embedding_model": "text-embedding-3-large",
        "embedding_dimensions": 3072,
        "default_top_k": 5,
        "semantic_ranker_enabled": true,
        "max_query_rate_per_minute": 60,
        "allowed_file_types": [".pdf", ".docx", ".xlsx", ".md"]
      }
    },
    {
      "tenant_id": "tenant-contoso-legal",
      "display_name": "Contoso Legal Department",
      "status": "active",
      "index_name": "idx-contoso-legal",
      "document_count": 128,
      "chunk_count": 8934,
      "storage_size_mb": 187.3,
      "created_at": "2023-08-20T11:00:00.000Z",
      "last_ingestion_at": "2024-01-12T09:15:00.000Z",
      "configuration": {
        "embedding_model": "text-embedding-3-large",
        "embedding_dimensions": 3072,
        "default_top_k": 10,
        "semantic_ranker_enabled": true,
        "max_query_rate_per_minute": 30,
        "allowed_file_types": [".pdf", ".docx"]
      }
    }
  ],
  "total_count": 2
}
```

### 7.2 GET /v1/admin/usage

Retrieve aggregated usage metrics across the platform. Supports date range filtering via query parameters.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `start_date` | string | No | 30 days ago | Start of reporting period (ISO 8601) |
| `end_date` | string | No | Today | End of reporting period (ISO 8601) |
| `tenant_id` | string | No | All tenants | Filter by specific tenant |
| `granularity` | string | No | `daily` | `hourly`, `daily`, `weekly`, `monthly` |

**Response (200 OK):**

```json
{
  "period": {
    "start": "2024-01-01T00:00:00.000Z",
    "end": "2024-01-15T23:59:59.999Z"
  },
  "summary": {
    "total_queries": 14523,
    "total_ingestions": 87,
    "total_documents_ingested": 87,
    "total_chunks_created": 4120,
    "total_feedback_submitted": 2341,
    "positive_feedback_rate": 0.82,
    "average_latency_ms": 2150,
    "p95_latency_ms": 3200,
    "p99_latency_ms": 4800,
    "total_tokens_consumed": 58234567,
    "estimated_cost_usd": 1245.67,
    "unique_users": 234,
    "average_groundedness_score": 0.91,
    "hallucination_rate": 0.04
  },
  "by_tenant": [
    {
      "tenant_id": "tenant-contoso-hr",
      "total_queries": 10234,
      "total_tokens_consumed": 42156789,
      "estimated_cost_usd": 892.34,
      "unique_users": 187,
      "average_latency_ms": 2050
    },
    {
      "tenant_id": "tenant-contoso-legal",
      "total_queries": 4289,
      "total_tokens_consumed": 16077778,
      "estimated_cost_usd": 353.33,
      "unique_users": 47,
      "average_latency_ms": 2390
    }
  ],
  "daily_breakdown": [
    {
      "date": "2024-01-15",
      "queries": 1023,
      "tokens": 4123456,
      "cost_usd": 87.45,
      "unique_users": 156,
      "avg_latency_ms": 2100
    }
  ]
}
```

---

## 8. Pagination

### 8.1 Cursor-Based Pagination

The following endpoints support **cursor-based pagination** for efficient traversal of large result sets:

- `GET /v1/history` — Conversation history
- `GET /v1/audit` — Audit log entries

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `cursor` | string | No | — | Opaque cursor from previous response (base64-encoded) |
| `limit` | integer | No | 25 | Number of items per page (1-100) |
| `sort_order` | string | No | `desc` | `asc` or `desc` by timestamp |

**Example Request:**

```bash
curl -X GET "https://api.prod.enterprise-rag.contoso.com/v1/history?limit=10&sort_order=desc" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Tenant-Id: tenant-contoso-hr"
```

**Response (200 OK):**

```json
{
  "items": [
    {
      "conversation_id": "conv-a1b2c3d4-e5f6-7890-abcd-ef0123456789",
      "query": "What is the parental leave policy?",
      "response_id": "resp-f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "answer_preview": "The company offers 16 weeks of paid parental leave...",
      "user_id": "12345678-abcd-ef01-2345-6789abcdef01",
      "tenant_id": "tenant-contoso-hr",
      "created_at": "2024-01-15T14:32:18.456Z",
      "tokens_used": 4129,
      "feedback_rating": "positive"
    }
  ],
  "pagination": {
    "cursor_next": "eyJjcmVhdGVkX2F0IjoiMjAyNC0wMS0xNVQxNDozMjoxOC40NTZaIiwiaWQiOiJyZXNwLWY0N2FjMTBiIn0=",
    "cursor_previous": null,
    "has_more": true,
    "total_count": 1523,
    "returned_count": 10
  }
}
```

**Pagination Flow (ASCII Diagram):**

```
  Page 1 (no cursor)         Page 2                     Page 3 (last)
┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
│ GET /v1/history     │   │ GET /v1/history     │   │ GET /v1/history     │
│   ?limit=10         │   │   ?limit=10         │   │   ?limit=10         │
│                     │   │   &cursor=eyJj...   │   │   &cursor=eyJk...   │
│                     │   │                     │   │                     │
│ Response:           │   │ Response:           │   │ Response:           │
│  items: [10 items]  │   │  items: [10 items]  │   │  items: [3 items]   │
│  cursor_next: eyJj  │──►│  cursor_next: eyJk  │──►│  cursor_next: null  │
│  has_more: true     │   │  has_more: true     │   │  has_more: false    │
└─────────────────────┘   └─────────────────────┘   └─────────────────────┘
```

### 8.2 GET /v1/audit

Retrieve audit log entries for compliance and security review. **Requires `RAG.Admin` role.**

**Additional Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `event_type` | string | No | Filter by event type: `query`, `ingest`, `feedback`, `auth`, `admin` |
| `user_id` | string | No | Filter by specific user OID |
| `start_date` | string | No | Start of date range (ISO 8601) |
| `end_date` | string | No | End of date range (ISO 8601) |

**Response Item Schema:**

```json
{
  "items": [
    {
      "audit_id": "aud-2c3d4e5f-6a7b-8c9d-0e1f-2a3b4c5d6e7f",
      "event_type": "query",
      "action": "POST /v1/query",
      "user_id": "12345678-abcd-ef01-2345-6789abcdef01",
      "user_name": "jsmith@contoso.com",
      "tenant_id": "tenant-contoso-hr",
      "ip_address": "10.0.1.42",
      "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
      "request_id": "550e8400-e29b-41d4-a716-446655440000",
      "correlation_id": "corr-20240115-abc123",
      "status_code": 200,
      "duration_ms": 2087,
      "metadata": {
        "query_length": 42,
        "response_tokens": 287,
        "model_used": "gpt-4o"
      },
      "timestamp": "2024-01-15T14:32:18.456Z"
    }
  ],
  "pagination": {
    "cursor_next": "eyJ0aW1lc3RhbXAiOiIyMDI0LTAxLTE1VDE0OjMyOjE4LjQ1NloifQ==",
    "has_more": true,
    "total_count": 45230,
    "returned_count": 25
  }
}
```

---

## 9. Webhook Callbacks

### 9.1 Ingestion Completion Webhook

When a document ingestion job completes (successfully or with failure), the platform sends an **HTTP POST** callback to the registered webhook URL. Webhooks are configured per tenant via the admin API.

**Webhook Delivery Flow:**

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────────┐
│  Client submits  │     │  Platform         │     │  Client Webhook      │
│  POST /v1/ingest │     │  processes job    │     │  Endpoint            │
│                  │     │                   │     │                      │
│  ◄── 202 ───────│     │  (async)          │     │                      │
│                  │     │                   │     │                      │
│                  │     │  Job completes    │     │                      │
│                  │     │  ──── POST ──────►│     │  Receives callback   │
│                  │     │                   │     │  Returns 200 OK      │
│                  │     │  ◄── 200 ─────── │     │                      │
│                  │     │                   │     │                      │
│                  │     │  If no 2xx in     │     │                      │
│                  │     │  3 attempts:      │     │                      │
│                  │     │  Dead-letter queue│     │                      │
└──────────────────┘     └──────────────────┘     └──────────────────────┘
```

**Webhook Payload (POST to registered URL):**

```json
{
  "webhook_id": "wh-3e4f5a6b-7c8d-9e0f-1a2b-3c4d5e6f7a8b",
  "event_type": "ingestion.completed",
  "event_version": "1.0",
  "timestamp": "2024-01-15T10:17:48.234Z",
  "data": {
    "job_id": "ingest-7f3a8b2c-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
    "status": "completed",
    "file_name": "parental-leave-policy-2024.pdf",
    "tenant_id": "tenant-contoso-hr",
    "document_id": "doc-8a7b6c5d-4e3f-2a1b-0c9d-8e7f6a5b4c3d",
    "chunks_created": 47,
    "chunks_indexed": 47,
    "total_tokens": 24350,
    "duration_seconds": 136
  },
  "signature": "sha256=a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2"
}
```

**Webhook Event Types:**

| Event Type | Description | Trigger |
|------------|-------------|---------|
| `ingestion.completed` | Document ingestion finished successfully | Job status transitions to `completed` |
| `ingestion.failed` | Document ingestion failed | Job status transitions to `failed` |
| `ingestion.progress` | Ingestion progress update (optional) | Job progress crosses 25%, 50%, 75% |

**Webhook Security:**

| Aspect | Implementation |
|--------|----------------|
| **Authentication** | HMAC-SHA256 signature in `signature` field using shared secret |
| **Transport** | HTTPS only (TLS 1.2+) |
| **Retry Policy** | 3 attempts with exponential backoff (1s, 5s, 30s) |
| **Timeout** | 10-second response timeout per attempt |
| **Dead Letter** | Failed deliveries stored in Azure Service Bus dead-letter queue for 7 days |
| **Idempotency** | `webhook_id` is unique; receivers should deduplicate by this ID |

**Webhook Signature Verification (Python):**

```python
import hmac
import hashlib

def verify_webhook_signature(payload_bytes: bytes, signature: str, secret: str) -> bool:
    """Verify the HMAC-SHA256 signature of a webhook payload."""
    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

---

## 10. Error Response Schema

### 10.1 Standard Error Envelope

All API errors follow a **consistent error envelope** modeled after the Microsoft REST API Guidelines:

```json
{
  "error": {
    "code": "INVALID_QUERY",
    "message": "The query text exceeds the maximum allowed length of 2000 characters.",
    "target": "query",
    "details": [
      {
        "code": "MAX_LENGTH_EXCEEDED",
        "message": "Field 'query' has 2347 characters, maximum is 2000.",
        "target": "query"
      }
    ],
    "innererror": {
      "code": "VALIDATION_ERROR",
      "timestamp": "2024-01-15T14:32:18.456Z",
      "request_id": "550e8400-e29b-41d4-a716-446655440000",
      "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736"
    }
  }
}
```

**Error Envelope Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `error` | object | Yes | Top-level error container |
| `error.code` | string | Yes | Machine-readable error code (UPPER_SNAKE_CASE) |
| `error.message` | string | Yes | Human-readable error description |
| `error.target` | string | No | The specific field or parameter that caused the error |
| `error.details` | array | No | Array of additional error details for multi-field validation |
| `error.details[].code` | string | Yes | Detail-level error code |
| `error.details[].message` | string | Yes | Detail-level error message |
| `error.details[].target` | string | No | Specific field for this detail |
| `error.innererror` | object | No | Internal diagnostic information |
| `error.innererror.code` | string | No | Internal error classification |
| `error.innererror.timestamp` | string | No | ISO 8601 timestamp of the error |
| `error.innererror.request_id` | string | No | Request ID for correlation |
| `error.innererror.trace_id` | string | No | Distributed trace ID (W3C Trace Context) |

### 10.2 Error Code Reference

| HTTP Status | Error Code | Description | Retryable |
|-------------|------------|-------------|-----------|
| `400` | `INVALID_QUERY` | Query text validation failed | No |
| `400` | `INVALID_PARAMETER` | Request parameter validation failed | No |
| `400` | `INVALID_METADATA` | Metadata JSON is malformed | No |
| `400` | `UNSUPPORTED_FILE_TYPE` | File type not supported for ingestion | No |
| `400` | `FILE_TOO_LARGE` | File exceeds maximum size | No |
| `400` | `MALFORMED_REQUEST` | Request body is not valid JSON | No |
| `401` | `UNAUTHORIZED` | Missing, expired, or invalid JWT | No |
| `401` | `TOKEN_EXPIRED` | JWT has expired | No (re-authenticate) |
| `403` | `FORBIDDEN` | Valid token but insufficient permissions | No |
| `403` | `TENANT_ACCESS_DENIED` | User not authorized for specified tenant | No |
| `404` | `NOT_FOUND` | Requested resource does not exist | No |
| `404` | `JOB_NOT_FOUND` | Ingestion job ID not found | No |
| `404` | `CONVERSATION_NOT_FOUND` | Conversation ID not found | No |
| `409` | `DOCUMENT_EXISTS` | Document already exists (no overwrite) | No |
| `413` | `PAYLOAD_TOO_LARGE` | Request body exceeds size limit | No |
| `429` | `RATE_LIMIT_EXCEEDED` | Request rate limit exceeded | Yes (after `Retry-After`) |
| `500` | `INTERNAL_ERROR` | Unexpected server error | Yes (with backoff) |
| `500` | `EXTRACTION_FAILED` | Document extraction error | Yes |
| `500` | `EMBEDDING_FAILED` | Embedding generation error | Yes |
| `500` | `INDEXING_FAILED` | Search index update error | Yes |
| `502` | `BAD_GATEWAY` | Downstream service returned invalid response | Yes |
| `503` | `SERVICE_UNAVAILABLE` | Platform or dependency unavailable | Yes (after `Retry-After`) |
| `503` | `MODEL_OVERLOADED` | Azure OpenAI capacity exceeded | Yes (with backoff) |

---

## 11. Rate Limiting

### 11.1 Rate Limit Headers

Every API response includes the following **rate limiting headers** to enable clients to implement proactive throttling:

| Header | Type | Description | Example |
|--------|------|-------------|---------|
| `X-RateLimit-Limit` | integer | Maximum requests allowed per window | `60` |
| `X-RateLimit-Remaining` | integer | Requests remaining in the current window | `42` |
| `X-RateLimit-Reset` | integer | Unix timestamp when the window resets | `1705324800` |
| `Retry-After` | integer | Seconds to wait before retrying (only on 429) | `15` |

**Example Response Headers (Normal):**

```
HTTP/1.1 200 OK
Content-Type: application/json
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 42
X-RateLimit-Reset: 1705324800
X-Request-Id: 550e8400-e29b-41d4-a716-446655440000
```

**Example Response Headers (Rate Limited):**

```
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1705324800
Retry-After: 15
```

### 11.2 Rate Limits by Endpoint and Role

| Endpoint | Default (req/min) | RAG.Admin (req/min) | Burst Allowed |
|----------|--------------------|---------------------|---------------|
| `POST /v1/query` | 60 | 120 | 10 over limit |
| `POST /v1/ingest` | 20 | 40 | 5 over limit |
| `GET /v1/ingest/{job_id}` | 120 | 240 | 20 over limit |
| `POST /v1/feedback` | 120 | 240 | 20 over limit |
| `GET /v1/history` | 60 | 120 | 10 over limit |
| `GET /v1/audit` | — | 30 | 5 over limit |
| `GET /v1/admin/tenants` | — | 30 | 5 over limit |
| `GET /v1/admin/usage` | — | 30 | 5 over limit |
| `GET /health` | 300 | 300 | Unlimited |
| `GET /ready` | 300 | 300 | Unlimited |

### 11.3 Recommended Retry Strategy

Clients **must** implement exponential backoff with jitter when receiving `429` or `503` responses:

```
┌──────────────┐
│  API Call     │
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌───────────────────┐
│ Status 2xx?  │─Yes─►  Return Response  │
└──────┬───────┘     └───────────────────┘
       │ No
       ▼
┌──────────────┐     ┌───────────────────┐
│ Status 429   │─No──►  Return Error     │
│ or 503?      │     │  (non-retryable)  │
└──────┬───────┘     └───────────────────┘
       │ Yes
       ▼
┌──────────────────────────────┐
│ Wait: Retry-After header     │
│ OR base_delay * 2^attempt    │
│    + random_jitter(0, 1s)    │
│                              │
│ Attempt 1: ~1s               │
│ Attempt 2: ~2s               │
│ Attempt 3: ~4s               │
│ Attempt 4: ~8s               │
│ Max attempts: 4              │
└──────────────┬───────────────┘
               │
               ▼
         Retry API Call
```

---

## 12. Request Tracing

### 12.1 Distributed Tracing Headers

The platform supports **W3C Trace Context** and custom tracing headers for end-to-end observability across distributed components.

| Header | Direction | Description | Format |
|--------|-----------|-------------|--------|
| `X-Request-Id` | Client → Server | Client-generated unique request identifier | UUIDv4 |
| `X-Correlation-Id` | Client → Server | Cross-request correlation identifier | Free-form string, max 128 chars |
| `X-Request-Id` | Server → Client | Echoed back or server-generated if not provided | UUIDv4 |
| `traceparent` | Client → Server | W3C Trace Context propagation header | `00-{trace-id}-{span-id}-{flags}` |
| `tracestate` | Client → Server | W3C Trace Context vendor-specific state | Vendor key-value pairs |

**Tracing Flow Through the Platform:**

```
┌─────────┐    ┌──────┐    ┌───────────┐    ┌──────────┐    ┌───────────────┐
│ Client  │───►│ APIM │───►│ Functions │───►│ AI Search│    │ App Insights  │
│         │    │      │    │           │───►│ OpenAI   │    │ (telemetry)   │
│ X-Req:  │    │      │    │           │    │ Cosmos   │    │               │
│ abc-123 │    │      │    │           │    │          │    │ All spans     │
│         │    │      │    │           │    │          │    │ correlated by │
│         │◄───│      │◄───│           │◄───│          │    │ X-Request-Id  │
│         │    │      │    │           │    │          │    │ & trace-id    │
└─────────┘    └──────┘    └───────────┘    └──────────┘    └───────────────┘
                  │              │                │                  ▲
                  │              │                │                  │
                  └──────────────┴────────────────┴──────────────────┘
                           Telemetry → Application Insights
```

### 12.2 Tracing in Responses

Every API response includes the following tracing headers for diagnostic correlation:

```
HTTP/1.1 200 OK
X-Request-Id: 550e8400-e29b-41d4-a716-446655440000
X-Correlation-Id: corr-20240115-abc123
X-Processing-Time-Ms: 2087
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
```

---

## 13. Request & Response Size Limits

### 13.1 Size Constraints

The following size limits are enforced across the platform at the **APIM gateway** level:

| Constraint | Limit | Enforced At | Error Code |
|------------|-------|-------------|------------|
| Query text length | 2,000 characters | APIM + Backend | `INVALID_QUERY` |
| Document upload size | 100 MB per file | APIM | `FILE_TOO_LARGE` |
| Request body (JSON) | 1 MB | APIM | `PAYLOAD_TOO_LARGE` |
| Response body | 32 KB | Backend | Truncated with `truncated: true` flag |
| Feedback comment | 2,000 characters | Backend | `INVALID_PARAMETER` |
| Metadata JSON | 8 KB | Backend | `INVALID_METADATA` |
| URL path length | 2,048 characters | APIM | `400 Bad Request` |
| Header total size | 64 KB | APIM | `431 Request Header Fields Too Large` |
| Concurrent uploads per tenant | 5 | Backend | `429 Too Many Requests` |
| Maximum file name length | 255 characters | Backend | `INVALID_PARAMETER` |

### 13.2 Response Truncation

When a generated response exceeds the **32 KB** limit, the platform truncates the response and sets a truncation indicator:

```json
{
  "response_id": "resp-f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "answer": "...(truncated response text)...",
  "truncated": true,
  "full_answer_length": 42350,
  "metadata": {
    "total_tokens": 8192,
    "truncation_reason": "response_size_limit_exceeded"
  }
}
```

---

## 14. CORS Configuration

### 14.1 Allowed Origins

Cross-Origin Resource Sharing is configured at the **APIM gateway** level. The following CORS policy is enforced for browser-based clients:

| CORS Setting | Value | Description |
|--------------|-------|-------------|
| **Allowed Origins** | `https://copilot.contoso.com` | Production web client |
| | `https://copilot-staging.contoso.com` | Staging web client |
| | `https://localhost:3000` | Local development (dev only) |
| **Allowed Methods** | `GET, POST, OPTIONS` | Permitted HTTP methods |
| **Allowed Headers** | `Authorization, Content-Type, Accept, X-Request-Id, X-Correlation-Id, X-Tenant-Id` | Permitted request headers |
| **Exposed Headers** | `X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset, X-Request-Id, X-Processing-Time-Ms, Retry-After` | Headers visible to browser JavaScript |
| **Max Age** | `3600` (1 hour) | Preflight cache duration in seconds |
| **Allow Credentials** | `true` | Allow cookies and Authorization headers |

### 14.2 CORS Policy (APIM XML)

```xml
<cors allow-credentials="true">
    <allowed-origins>
        <origin>https://copilot.contoso.com</origin>
        <origin>https://copilot-staging.contoso.com</origin>
    </allowed-origins>
    <allowed-methods preflight-result-max-age="3600">
        <method>GET</method>
        <method>POST</method>
        <method>OPTIONS</method>
    </allowed-methods>
    <allowed-headers>
        <header>Authorization</header>
        <header>Content-Type</header>
        <header>Accept</header>
        <header>X-Request-Id</header>
        <header>X-Correlation-Id</header>
        <header>X-Tenant-Id</header>
    </allowed-headers>
    <expose-headers>
        <header>X-RateLimit-Limit</header>
        <header>X-RateLimit-Remaining</header>
        <header>X-RateLimit-Reset</header>
        <header>X-Request-Id</header>
        <header>X-Processing-Time-Ms</header>
        <header>Retry-After</header>
    </expose-headers>
</cors>
```

---

## 15. API Versioning Strategy

### 15.1 Version Scheme

The platform uses **URL path versioning** as the primary versioning mechanism:

```
https://api.prod.enterprise-rag.contoso.com/v1/query
https://api.prod.enterprise-rag.contoso.com/v2/query   (future)
```

**Versioning Rules:**

| Rule | Description |
|------|-------------|
| **Major version in URL** | Breaking changes increment the major version (`/v1/` → `/v2/`) |
| **Backward-compatible changes** | Additive fields, new optional parameters — no version change |
| **Deprecation notice** | Minimum 6 months notice before a version is retired |
| **Sunset header** | Deprecated versions return `Sunset: <date>` and `Deprecation: true` headers |
| **Parallel operation** | Minimum 2 major versions supported simultaneously |
| **Health endpoints** | Not versioned (`/health`, `/ready`) — shared across all versions |

### 15.2 Version Lifecycle

```
┌────────────────────────────────────────────────────────────────────────┐
│                        API Version Lifecycle                          │
├──────────┬──────────┬──────────┬──────────┬──────────┬────────────────┤
│  Phase   │  Alpha   │  Beta    │   GA     │ Deprecated│   Retired    │
├──────────┼──────────┼──────────┼──────────┼──────────┼────────────────┤
│  v1      │ 2023-Q3  │ 2023-Q4  │ 2024-Q1  │ TBD      │  TBD         │
│  v2      │ TBD      │ TBD      │ TBD      │ —        │  —           │
├──────────┼──────────┼──────────┼──────────┼──────────┼────────────────┤
│ SLA      │  None    │  99%     │  99.9%   │  99.9%   │  None        │
│ Support  │  None    │  Best    │  Full    │  Critical│  None        │
│          │          │  effort  │          │  only    │              │
└──────────┴──────────┴──────────┴──────────┴──────────┴────────────────┘
```

### 15.3 Deprecation Headers

When a version is deprecated, responses include the following headers:

```
HTTP/1.1 200 OK
Deprecation: true
Sunset: Sat, 01 Jul 2025 00:00:00 GMT
Link: <https://api.prod.enterprise-rag.contoso.com/v2/query>; rel="successor-version"
```

---

## 16. SDK Usage Examples

### 16.1 Python (requests + azure-identity)

```python
"""
Enterprise RAG Platform — Python SDK Example
Requires: pip install requests azure-identity
"""
import requests
from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential
import uuid
import json


# --- Configuration ---
API_BASE_URL = "https://api.prod.enterprise-rag.contoso.com"
API_SCOPE = "api://enterprise-rag-prod/.default"
TENANT_ID = "tenant-contoso-hr"


def get_access_token() -> str:
    """Obtain an access token from Microsoft Entra ID."""
    try:
        # Attempts managed identity, environment variables, Azure CLI, etc.
        credential = DefaultAzureCredential()
        token = credential.get_token(API_SCOPE)
        return token.token
    except Exception:
        # Fallback to interactive browser login for local development
        credential = InteractiveBrowserCredential()
        token = credential.get_token(API_SCOPE)
        return token.token


def query_rag(question: str, conversation_id: str = None) -> dict:
    """Submit a query to the RAG platform."""
    token = get_access_token()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Request-Id": str(uuid.uuid4()),
        "X-Tenant-Id": TENANT_ID,
    }

    payload = {
        "query": question,
        "options": {
            "top_k": 5,
            "temperature": 0.1,
            "include_citations": True,
            "search_mode": "hybrid",
        },
    }

    if conversation_id:
        payload["conversation_id"] = conversation_id

    response = requests.post(
        f"{API_BASE_URL}/v1/query",
        headers=headers,
        json=payload,
        timeout=30,
    )

    # Check rate limiting
    remaining = response.headers.get("X-RateLimit-Remaining")
    if remaining and int(remaining) < 5:
        print(f"Warning: Only {remaining} requests remaining in current window")

    response.raise_for_status()
    return response.json()


def ingest_document(file_path: str, metadata: dict) -> dict:
    """Upload a document for ingestion."""
    token = get_access_token()

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Request-Id": str(uuid.uuid4()),
        "X-Tenant-Id": TENANT_ID,
    }

    with open(file_path, "rb") as f:
        files = {"file": (file_path.split("/")[-1], f)}
        data = {
            "tenant_id": TENANT_ID,
            "metadata": json.dumps(metadata),
            "chunking_strategy": "semantic",
            "chunk_size": "512",
        }

        response = requests.post(
            f"{API_BASE_URL}/v1/ingest",
            headers=headers,
            files=files,
            data=data,
            timeout=60,
        )

    response.raise_for_status()
    return response.json()


# --- Usage ---
if __name__ == "__main__":
    result = query_rag("What is the company's parental leave policy?")
    print(f"Answer: {result['answer']}")
    print(f"Citations: {len(result['citations'])} sources")
    print(f"Latency: {result['metadata']['total_duration_ms']}ms")
```

### 16.2 C# (HttpClient)

```csharp
// Enterprise RAG Platform — C# SDK Example
// Requires: Azure.Identity NuGet package

using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using Azure.Identity;

namespace Contoso.Rag.Client;

public class RagApiClient : IDisposable
{
    private readonly HttpClient _httpClient;
    private readonly DefaultAzureCredential _credential;
    private readonly string _apiScope;
    private readonly string _tenantId;

    public RagApiClient(string baseUrl, string apiScope, string tenantId)
    {
        _httpClient = new HttpClient { BaseAddress = new Uri(baseUrl) };
        _credential = new DefaultAzureCredential();
        _apiScope = apiScope;
        _tenantId = tenantId;
    }

    private async Task<string> GetAccessTokenAsync()
    {
        var tokenResult = await _credential.GetTokenAsync(
            new Azure.Core.TokenRequestContext(new[] { _apiScope }));
        return tokenResult.Token;
    }

    public async Task<JsonDocument> QueryAsync(
        string question,
        string? conversationId = null,
        int topK = 5)
    {
        var token = await GetAccessTokenAsync();

        var request = new HttpRequestMessage(HttpMethod.Post, "/v1/query");
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        request.Headers.Add("X-Request-Id", Guid.NewGuid().ToString());
        request.Headers.Add("X-Tenant-Id", _tenantId);

        var payload = new
        {
            query = question,
            conversation_id = conversationId,
            options = new
            {
                top_k = topK,
                temperature = 0.1,
                include_citations = true,
                search_mode = "hybrid"
            }
        };

        request.Content = new StringContent(
            JsonSerializer.Serialize(payload),
            Encoding.UTF8,
            "application/json");

        var response = await _httpClient.SendAsync(request);

        // Log rate limit status
        if (response.Headers.TryGetValues("X-RateLimit-Remaining", out var remaining))
        {
            Console.WriteLine($"Rate limit remaining: {remaining.First()}");
        }

        response.EnsureSuccessStatusCode();

        var stream = await response.Content.ReadAsStreamAsync();
        return await JsonDocument.ParseAsync(stream);
    }

    public void Dispose()
    {
        _httpClient.Dispose();
    }
}

// Usage:
// var client = new RagApiClient(
//     "https://api.prod.enterprise-rag.contoso.com",
//     "api://enterprise-rag-prod/.default",
//     "tenant-contoso-hr");
// var result = await client.QueryAsync("What is the parental leave policy?");
```

### 16.3 JavaScript (fetch)

```javascript
/**
 * Enterprise RAG Platform — JavaScript/TypeScript SDK Example
 * For browser-based SPA clients using MSAL.js
 * Requires: @azure/msal-browser
 */

import { PublicClientApplication } from "@azure/msal-browser";

const msalConfig = {
  auth: {
    clientId: "your-client-id-here",
    authority: "https://login.microsoftonline.com/your-tenant-id",
    redirectUri: "https://copilot.contoso.com",
  },
};

const msalInstance = new PublicClientApplication(msalConfig);

const API_BASE_URL = "https://api.prod.enterprise-rag.contoso.com";
const API_SCOPE = "api://enterprise-rag-prod/RAG.Query";
const TENANT_ID = "tenant-contoso-hr";

/**
 * Acquire an access token silently (or via popup if needed).
 */
async function getAccessToken() {
  const account = msalInstance.getAllAccounts()[0];
  const request = { scopes: [API_SCOPE], account };

  try {
    const response = await msalInstance.acquireTokenSilent(request);
    return response.accessToken;
  } catch (error) {
    const response = await msalInstance.acquireTokenPopup(request);
    return response.accessToken;
  }
}

/**
 * Submit a query to the RAG platform.
 * @param {string} question - The natural language query
 * @param {string|null} conversationId - Optional conversation ID for multi-turn
 * @returns {Promise<object>} The query response
 */
async function queryRag(question, conversationId = null) {
  const token = await getAccessToken();
  const requestId = crypto.randomUUID();

  const payload = {
    query: question,
    ...(conversationId && { conversation_id: conversationId }),
    options: {
      top_k: 5,
      temperature: 0.1,
      include_citations: true,
      search_mode: "hybrid",
    },
  };

  const response = await fetch(`${API_BASE_URL}/v1/query`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-Request-Id": requestId,
      "X-Tenant-Id": TENANT_ID,
    },
    body: JSON.stringify(payload),
  });

  // Check rate limiting
  const remaining = response.headers.get("X-RateLimit-Remaining");
  if (remaining !== null && parseInt(remaining) < 5) {
    console.warn(`Rate limit warning: ${remaining} requests remaining`);
  }

  if (response.status === 429) {
    const retryAfter = parseInt(response.headers.get("Retry-After") || "5");
    console.warn(`Rate limited. Retrying after ${retryAfter}s...`);
    await new Promise((resolve) => setTimeout(resolve, retryAfter * 1000));
    return queryRag(question, conversationId); // Retry
  }

  if (!response.ok) {
    const errorBody = await response.json();
    throw new Error(
      `API Error ${response.status}: ${errorBody.error?.message || "Unknown error"}`
    );
  }

  return response.json();
}

// Usage:
// const result = await queryRag("What is the parental leave policy?");
// console.log(result.answer);
// console.log(`Sources: ${result.citations.length}`);
```

---

## 17. Postman Collection Structure

### 17.1 Collection Organization

The platform provides a **Postman collection** for interactive API testing and exploration. Import from:

```
https://api.prod.enterprise-rag.contoso.com/postman/collection.json
```

**Collection Folder Structure:**

| Folder | Requests | Description |
|--------|----------|-------------|
| `01 - Authentication` | Get Token (Auth Code), Get Token (Client Credentials) | Token acquisition flows |
| `02 - Query API` | Query (Basic), Query (With Filters), Query (Multi-Turn) | RAG query variants |
| `03 - Ingestion API` | Upload Document, Poll Status, List Jobs | Document ingestion workflow |
| `04 - Feedback API` | Submit Positive, Submit Negative, Submit Detailed | Feedback submission |
| `05 - History & Audit` | Get History, Get Audit Logs | Paginated list retrieval |
| `06 - Admin` | List Tenants, Get Usage, Get Usage by Tenant | Administration endpoints |
| `07 - Health` | Health Check, Readiness Check | Operational endpoints |

### 17.2 Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `base_url` | API base URL | `https://api.dev.enterprise-rag.contoso.com` |
| `client_id` | Entra ID app client ID | `abcdef01-2345-6789-abcd-ef0123456789` |
| `client_secret` | Client secret (service-to-service only) | `***` |
| `tenant_id` | Entra ID directory tenant ID | `a1b2c3d4-e5f6-7890-abcd-ef0123456789` |
| `api_scope` | OAuth2 scope for token request | `api://enterprise-rag-prod/.default` |
| `rag_tenant_id` | Platform tenant identifier | `tenant-contoso-hr` |
| `access_token` | Auto-populated by pre-request script | `eyJhbGciOi...` |

### 17.3 Pre-Request Script (Token Acquisition)

The collection includes a **pre-request script** that automatically acquires and caches an access token:

```javascript
// Postman Pre-Request Script — Auto Token Acquisition
const tokenUrl = `https://login.microsoftonline.com/${pm.environment.get("tenant_id")}/oauth2/v2.0/token`;

const tokenRequest = {
  url: tokenUrl,
  method: "POST",
  header: { "Content-Type": "application/x-www-form-urlencoded" },
  body: {
    mode: "urlencoded",
    urlencoded: [
      { key: "grant_type", value: "client_credentials" },
      { key: "client_id", value: pm.environment.get("client_id") },
      { key: "client_secret", value: pm.environment.get("client_secret") },
      { key: "scope", value: pm.environment.get("api_scope") },
    ],
  },
};

pm.sendRequest(tokenRequest, (err, res) => {
  if (!err) {
    const token = res.json().access_token;
    pm.environment.set("access_token", token);
    console.log("Token acquired successfully");
  }
});
```

---

## 18. Document Control

| Field | Value |
|-------|-------|
| **Document Title** | API Specification — Azure OpenAI Enterprise RAG Platform |
| **Version** | 1.0 |
| **Classification** | Internal |
| **Owner** | Platform Team |
| **Last Updated** | 2024-01 |
| **Review Cycle** | Quarterly |
| **Approved By** | Chief Architect, Platform Engineering Lead |
| **Distribution** | Engineering, DevOps, Security, QA, Partner Integrations |
| **Change Log** | v1.0 — Initial API specification release |

---

*This document is part of the Azure OpenAI Enterprise RAG Platform documentation suite. For architecture details, see the [Azure Service Deep Dive](./AZURE-SERVICE-DEEP-DIVE.md). For demo workflows, see the [Demo Playbook](./DEMO-PLAYBOOK.md).*
