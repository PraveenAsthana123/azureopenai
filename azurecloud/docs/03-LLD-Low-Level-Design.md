# Low-Level Design (LLD) Document
# Enterprise GenAI Knowledge Copilot Platform

**Document Version:** 1.0
**Date:** November 2024
**Status:** Approved

---

## 1. Document Overview

### 1.1 Purpose
This Low-Level Design document provides detailed technical specifications for the Enterprise GenAI Knowledge Copilot Platform, including database schemas, API specifications, class diagrams, sequence diagrams, and implementation details.

### 1.2 Scope
This document covers:
- Detailed database design
- API specifications
- Class/Module structure
- Sequence diagrams
- Error handling
- Configuration management

---

## 2. Database Design

### 2.1 Cosmos DB Schema Design

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           COSMOS DB SCHEMA DESIGN                                 │
│                              Database: copilot-db                                 │
└──────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  Container: conversations                                                        │
│  Partition Key: /userId                                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  {                                                                              │
│    "id": "conv-uuid-1234",                    // Unique conversation ID        │
│    "userId": "user@domain.com",               // Partition key                 │
│    "title": "Q3 Revenue Discussion",          // Auto-generated title          │
│    "createdAt": "2024-11-24T10:30:00Z",       // ISO timestamp                 │
│    "updatedAt": "2024-11-24T11:45:00Z",       // Last update                   │
│    "messages": [                                                                │
│      {                                                                          │
│        "id": "msg-uuid-001",                                                   │
│        "role": "user",                        // user | assistant | system     │
│        "content": "What was our Q3 revenue?",                                  │
│        "timestamp": "2024-11-24T10:30:00Z"                                     │
│      },                                                                         │
│      {                                                                          │
│        "id": "msg-uuid-002",                                                   │
│        "role": "assistant",                                                    │
│        "content": "Based on the Q3 report...",                                 │
│        "sources": [                                                            │
│          {                                                                      │
│            "documentId": "doc-uuid-789",                                       │
│            "title": "Q3 Financial Report.pdf",                                 │
│            "page": 5,                                                          │
│            "relevanceScore": 0.95                                              │
│          }                                                                      │
│        ],                                                                       │
│        "timestamp": "2024-11-24T10:30:05Z",                                    │
│        "tokensUsed": 450                                                       │
│      }                                                                          │
│    ],                                                                           │
│    "metadata": {                                                                │
│      "totalTokens": 1250,                                                      │
│      "modelUsed": "gpt-4o-mini",                                               │
│      "feedbackRating": 5                                                       │
│    },                                                                           │
│    "_ts": 1700820300                          // Cosmos DB timestamp           │
│  }                                                                              │
│                                                                                 │
│  Indexing Policy:                                                               │
│  • includedPaths: ["/userId/?", "/createdAt/?", "/title/?"]                    │
│  • excludedPaths: ["/messages/*"]                                              │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  Container: documents-metadata                                                   │
│  Partition Key: /category                                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  {                                                                              │
│    "id": "doc-uuid-789",                      // Unique document ID            │
│    "category": "financial-reports",           // Partition key                 │
│    "title": "Q3 Financial Report.pdf",                                         │
│    "fileName": "Q3_Financial_Report_2024.pdf",                                 │
│    "fileType": "application/pdf",                                              │
│    "fileSize": 2458624,                       // Bytes                         │
│    "blobPath": "documents/financial/2024/q3-report.pdf",                       │
│    "uploadedBy": "user@domain.com",                                            │
│    "uploadedAt": "2024-10-15T09:00:00Z",                                       │
│    "processedAt": "2024-10-15T09:05:30Z",                                      │
│    "status": "indexed",                       // uploaded|processing|indexed|failed│
│    "processingDetails": {                                                       │
│      "pageCount": 45,                                                          │
│      "chunkCount": 128,                                                        │
│      "embeddingModel": "text-embedding-3-small",                               │
│      "processingTimeMs": 330000                                                │
│    },                                                                           │
│    "extractedMetadata": {                                                       │
│      "author": "Finance Team",                                                 │
│      "createdDate": "2024-10-01",                                              │
│      "keywords": ["revenue", "profit", "expenses", "Q3", "2024"]               │
│    },                                                                           │
│    "permissions": {                                                             │
│      "readGroups": ["finance-team", "executives"],                             │
│      "isPublic": false                                                         │
│    },                                                                           │
│    "_ts": 1697360730                                                           │
│  }                                                                              │
│                                                                                 │
│  Indexing Policy:                                                               │
│  • includedPaths: ["/category/?", "/status/?", "/uploadedAt/?", "/title/?"]    │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  Container: user-sessions                                                        │
│  Partition Key: /userId                                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  {                                                                              │
│    "id": "session-uuid-456",                                                   │
│    "userId": "user@domain.com",                                                │
│    "sessionStart": "2024-11-24T08:00:00Z",                                     │
│    "lastActivity": "2024-11-24T11:45:00Z",                                     │
│    "preferences": {                                                             │
│      "theme": "dark",                                                          │
│      "language": "en",                                                         │
│      "defaultSearchScope": ["all"]                                             │
│    },                                                                           │
│    "recentSearches": [                                                          │
│      "Q3 revenue",                                                             │
│      "employee benefits",                                                      │
│      "project timeline"                                                        │
│    ],                                                                           │
│    "usageStats": {                                                              │
│      "queriesThisSession": 15,                                                 │
│      "documentsViewed": 8,                                                     │
│      "totalTokensUsed": 4500                                                   │
│    }                                                                            │
│  }                                                                              │
│                                                                                 │
│  TTL: 86400 seconds (24 hours)                                                 │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  Container: audit-logs                                                           │
│  Partition Key: /date                                                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  {                                                                              │
│    "id": "audit-uuid-789",                                                     │
│    "date": "2024-11-24",                      // Partition by date             │
│    "timestamp": "2024-11-24T10:30:00.000Z",                                    │
│    "userId": "user@domain.com",                                                │
│    "action": "QUERY_SUBMITTED",               // Action type                   │
│    "resource": "conversation",                                                 │
│    "resourceId": "conv-uuid-1234",                                             │
│    "details": {                                                                 │
│      "query": "What was our Q3 revenue?",                                      │
│      "responseTime": 2500,                                                     │
│      "tokensUsed": 450,                                                        │
│      "sourcesReturned": 3                                                      │
│    },                                                                           │
│    "ipAddress": "10.0.3.45",                                                   │
│    "userAgent": "Mozilla/5.0..."                                               │
│  }                                                                              │
│                                                                                 │
│  TTL: 7776000 seconds (90 days)                                                │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  Container: embeddings-cache                                                     │
│  Partition Key: /documentId                                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  {                                                                              │
│    "id": "chunk-uuid-001",                                                     │
│    "documentId": "doc-uuid-789",                                               │
│    "chunkIndex": 0,                                                            │
│    "content": "The Q3 2024 revenue reached $45.2M...",                         │
│    "contentHash": "sha256:abc123...",         // For deduplication             │
│    "embedding": [0.023, -0.145, 0.089, ...],  // 1536 dimensions              │
│    "metadata": {                                                                │
│      "pageNumber": 5,                                                          │
│      "sectionTitle": "Revenue Summary",                                        │
│      "tokenCount": 256                                                         │
│    },                                                                           │
│    "createdAt": "2024-10-15T09:05:00Z"                                         │
│  }                                                                              │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Azure AI Search Index Schema

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                        AZURE AI SEARCH INDEX SCHEMA                               │
│                         Index: genai-copilot-documents                            │
└──────────────────────────────────────────────────────────────────────────────────┘

{
  "name": "genai-copilot-documents",
  "fields": [
    {
      "name": "id",
      "type": "Edm.String",
      "key": true,
      "searchable": false,
      "filterable": true,
      "sortable": false,
      "facetable": false,
      "retrievable": true
    },
    {
      "name": "documentId",
      "type": "Edm.String",
      "searchable": false,
      "filterable": true,
      "sortable": false,
      "facetable": true,
      "retrievable": true
    },
    {
      "name": "title",
      "type": "Edm.String",
      "searchable": true,
      "filterable": true,
      "sortable": true,
      "facetable": false,
      "retrievable": true,
      "analyzer": "en.microsoft"
    },
    {
      "name": "content",
      "type": "Edm.String",
      "searchable": true,
      "filterable": false,
      "sortable": false,
      "facetable": false,
      "retrievable": true,
      "analyzer": "en.microsoft"
    },
    {
      "name": "contentVector",
      "type": "Collection(Edm.Single)",
      "searchable": true,
      "retrievable": false,
      "dimensions": 1536,
      "vectorSearchProfile": "vector-profile"
    },
    {
      "name": "category",
      "type": "Edm.String",
      "searchable": true,
      "filterable": true,
      "sortable": false,
      "facetable": true,
      "retrievable": true
    },
    {
      "name": "pageNumber",
      "type": "Edm.Int32",
      "searchable": false,
      "filterable": true,
      "sortable": true,
      "facetable": false,
      "retrievable": true
    },
    {
      "name": "chunkIndex",
      "type": "Edm.Int32",
      "searchable": false,
      "filterable": true,
      "sortable": true,
      "facetable": false,
      "retrievable": true
    },
    {
      "name": "uploadedAt",
      "type": "Edm.DateTimeOffset",
      "searchable": false,
      "filterable": true,
      "sortable": true,
      "facetable": false,
      "retrievable": true
    },
    {
      "name": "permissions",
      "type": "Collection(Edm.String)",
      "searchable": false,
      "filterable": true,
      "sortable": false,
      "facetable": true,
      "retrievable": true
    }
  ],
  "vectorSearch": {
    "algorithms": [
      {
        "name": "hnsw-algorithm",
        "kind": "hnsw",
        "hnswParameters": {
          "m": 4,
          "efConstruction": 400,
          "efSearch": 500,
          "metric": "cosine"
        }
      }
    ],
    "profiles": [
      {
        "name": "vector-profile",
        "algorithm": "hnsw-algorithm"
      }
    ]
  },
  "semantic": {
    "configurations": [
      {
        "name": "semantic-config",
        "prioritizedFields": {
          "titleField": { "fieldName": "title" },
          "contentFields": [{ "fieldName": "content" }],
          "keywordsFields": [{ "fieldName": "category" }]
        }
      }
    ]
  }
}
```

---

## 3. API Specifications

### 3.1 REST API Design

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              API ENDPOINT DESIGN                                  │
└──────────────────────────────────────────────────────────────────────────────────┘

BASE URL: https://func-api-genai-copilot-{suffix}.azurewebsites.net/api

┌─────────────────────────────────────────────────────────────────────────────────┐
│  CHAT ENDPOINTS                                                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  POST /api/chat                                                                 │
│  ─────────────────                                                              │
│  Description: Submit a question and get AI-generated response                   │
│  Auth: Bearer Token (Azure AD)                                                  │
│                                                                                 │
│  Request:                                                                       │
│  {                                                                              │
│    "conversationId": "conv-uuid-1234",        // Optional, creates new if null │
│    "message": "What was our Q3 revenue?",                                      │
│    "options": {                                                                 │
│      "searchScope": ["financial-reports"],    // Optional category filter      │
│      "maxSources": 5,                         // Max documents to cite         │
│      "temperature": 0.7,                      // LLM temperature              │
│      "streamResponse": false                  // Enable streaming              │
│    }                                                                            │
│  }                                                                              │
│                                                                                 │
│  Response (200 OK):                                                             │
│  {                                                                              │
│    "conversationId": "conv-uuid-1234",                                         │
│    "messageId": "msg-uuid-002",                                                │
│    "response": "Based on the Q3 Financial Report, the revenue was $45.2M...", │
│    "sources": [                                                                 │
│      {                                                                          │
│        "documentId": "doc-uuid-789",                                           │
│        "title": "Q3 Financial Report.pdf",                                     │
│        "page": 5,                                                              │
│        "snippet": "...Q3 2024 revenue reached $45.2M, representing a 12%...", │
│        "relevanceScore": 0.95                                                  │
│      }                                                                          │
│    ],                                                                           │
│    "metadata": {                                                                │
│      "tokensUsed": 450,                                                        │
│      "processingTimeMs": 2500,                                                 │
│      "modelUsed": "gpt-4o-mini"                                                │
│    }                                                                            │
│  }                                                                              │
│                                                                                 │
│  Error Responses:                                                               │
│  • 400 Bad Request - Invalid input                                             │
│  • 401 Unauthorized - Missing/invalid token                                    │
│  • 429 Too Many Requests - Rate limit exceeded                                 │
│  • 500 Internal Server Error - Processing error                                │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  SEARCH ENDPOINTS                                                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  GET /api/search                                                                │
│  ───────────────                                                                │
│  Description: Search documents using hybrid search                              │
│  Auth: Bearer Token (Azure AD)                                                  │
│                                                                                 │
│  Query Parameters:                                                              │
│  • q (required): Search query string                                           │
│  • category (optional): Filter by category                                     │
│  • top (optional): Number of results (default: 10, max: 50)                   │
│  • skip (optional): Pagination offset                                          │
│  • searchMode (optional): "hybrid" | "vector" | "keyword" (default: hybrid)   │
│                                                                                 │
│  Response (200 OK):                                                             │
│  {                                                                              │
│    "results": [                                                                 │
│      {                                                                          │
│        "documentId": "doc-uuid-789",                                           │
│        "title": "Q3 Financial Report.pdf",                                     │
│        "category": "financial-reports",                                        │
│        "snippet": "...Q3 2024 revenue reached $45.2M...",                      │
│        "score": 0.95,                                                          │
│        "highlights": ["<em>revenue</em>", "<em>Q3</em>"]                       │
│      }                                                                          │
│    ],                                                                           │
│    "totalCount": 25,                                                           │
│    "facets": {                                                                  │
│      "category": [                                                              │
│        { "value": "financial-reports", "count": 15 },                          │
│        { "value": "policies", "count": 10 }                                    │
│      ]                                                                          │
│    }                                                                            │
│  }                                                                              │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  DOCUMENT ENDPOINTS                                                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  POST /api/documents                                                            │
│  ───────────────────                                                            │
│  Description: Upload a document for processing                                  │
│  Auth: Bearer Token (Azure AD)                                                  │
│  Content-Type: multipart/form-data                                             │
│                                                                                 │
│  Form Fields:                                                                   │
│  • file (required): Document file (max 100MB)                                  │
│  • category (required): Document category                                      │
│  • title (optional): Custom title (defaults to filename)                       │
│  • permissions (optional): JSON array of group names                           │
│                                                                                 │
│  Response (202 Accepted):                                                       │
│  {                                                                              │
│    "documentId": "doc-uuid-new",                                               │
│    "status": "processing",                                                     │
│    "statusUrl": "/api/documents/doc-uuid-new/status",                          │
│    "estimatedProcessingTime": "5 minutes"                                      │
│  }                                                                              │
│                                                                                 │
│  ─────────────────────────────────────────────────────────────────────────────│
│                                                                                 │
│  GET /api/documents/{documentId}                                                │
│  ───────────────────────────────                                                │
│  Description: Get document details                                              │
│                                                                                 │
│  Response (200 OK):                                                             │
│  {                                                                              │
│    "id": "doc-uuid-789",                                                       │
│    "title": "Q3 Financial Report.pdf",                                         │
│    "category": "financial-reports",                                            │
│    "status": "indexed",                                                        │
│    "uploadedAt": "2024-10-15T09:00:00Z",                                       │
│    "processedAt": "2024-10-15T09:05:30Z",                                      │
│    "pageCount": 45,                                                            │
│    "downloadUrl": "https://storage.../documents/..."  // SAS URL, 1hr expiry  │
│  }                                                                              │
│                                                                                 │
│  ─────────────────────────────────────────────────────────────────────────────│
│                                                                                 │
│  DELETE /api/documents/{documentId}                                             │
│  ──────────────────────────────────                                             │
│  Description: Delete a document and its embeddings                              │
│  Auth: Bearer Token (Azure AD) + Admin role                                    │
│                                                                                 │
│  Response (204 No Content)                                                      │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  CONVERSATION ENDPOINTS                                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  GET /api/conversations                                                         │
│  ──────────────────────                                                         │
│  Description: Get user's conversation history                                   │
│                                                                                 │
│  Query Parameters:                                                              │
│  • top (optional): Number of results (default: 20)                             │
│  • skip (optional): Pagination offset                                          │
│  • search (optional): Search in conversation titles                            │
│                                                                                 │
│  Response (200 OK):                                                             │
│  {                                                                              │
│    "conversations": [                                                           │
│      {                                                                          │
│        "id": "conv-uuid-1234",                                                 │
│        "title": "Q3 Revenue Discussion",                                       │
│        "createdAt": "2024-11-24T10:30:00Z",                                    │
│        "messageCount": 8,                                                      │
│        "lastMessage": "Based on the Q3 report..."                              │
│      }                                                                          │
│    ],                                                                           │
│    "totalCount": 45                                                            │
│  }                                                                              │
│                                                                                 │
│  ─────────────────────────────────────────────────────────────────────────────│
│                                                                                 │
│  GET /api/conversations/{conversationId}                                        │
│  ───────────────────────────────────────                                        │
│  Description: Get full conversation with all messages                           │
│                                                                                 │
│  Response (200 OK):                                                             │
│  {                                                                              │
│    "id": "conv-uuid-1234",                                                     │
│    "title": "Q3 Revenue Discussion",                                           │
│    "messages": [ ... ],                                                        │
│    "metadata": { ... }                                                         │
│  }                                                                              │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": [
      {
        "field": "message",
        "issue": "Message cannot be empty"
      }
    ],
    "requestId": "req-uuid-12345",
    "timestamp": "2024-11-24T10:30:00Z"
  }
}
```

---

## 4. Module/Class Design

### 4.1 Backend Module Structure

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                            BACKEND MODULE STRUCTURE                               │
└──────────────────────────────────────────────────────────────────────────────────┘

backend/
├── shared/                              # Shared utilities across functions
│   ├── __init__.py
│   ├── config.py                        # Configuration management
│   ├── auth.py                          # Authentication utilities
│   ├── exceptions.py                    # Custom exceptions
│   └── models/                          # Data models
│       ├── __init__.py
│       ├── conversation.py
│       ├── document.py
│       └── search.py
│
├── api-gateway/                         # API Gateway Function App
│   ├── function_app.py                  # Main entry point
│   ├── chat/
│   │   ├── __init__.py
│   │   └── function.json
│   ├── search/
│   │   ├── __init__.py
│   │   └── function.json
│   ├── documents/
│   │   ├── __init__.py
│   │   └── function.json
│   └── requirements.txt
│
├── orchestrator/                        # Orchestrator Function App
│   ├── function_app.py
│   ├── workflows/
│   │   ├── __init__.py
│   │   ├── chat_workflow.py
│   │   └── ingestion_workflow.py
│   └── requirements.txt
│
├── ingestion/                           # Document Ingestion Function App
│   ├── function_app.py
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── pdf_processor.py
│   │   ├── docx_processor.py
│   │   └── chunker.py
│   ├── blob_trigger/
│   │   ├── __init__.py
│   │   └── function.json
│   └── requirements.txt
│
└── rag-processor/                       # RAG Processing Function App
    ├── function_app.py
    ├── services/
    │   ├── __init__.py
    │   ├── embedding_service.py
    │   ├── search_service.py
    │   └── llm_service.py
    ├── rag/
    │   ├── __init__.py
    │   ├── context_builder.py
    │   ├── prompt_templates.py
    │   └── response_generator.py
    └── requirements.txt
```

### 4.2 Class Diagrams

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                               CLASS DIAGRAM                                       │
│                            RAG Processing Module                                  │
└──────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────┐
│          <<interface>>              │
│           LLMService                │
├─────────────────────────────────────┤
│ + generate(prompt: str): str        │
│ + embed(text: str): List[float]     │
│ + get_token_count(text: str): int   │
└─────────────────────────────────────┘
                    △
                    │
        ┌───────────┴───────────┐
        │                       │
┌───────────────────┐   ┌───────────────────┐
│ AzureOpenAIService│   │   OllamaService   │
├───────────────────┤   ├───────────────────┤
│ - endpoint: str   │   │ - base_url: str   │
│ - api_key: str    │   │ - model: str      │
│ - deployment: str │   │                   │
├───────────────────┤   ├───────────────────┤
│ + generate()      │   │ + generate()      │
│ + embed()         │   │ + embed()         │
│ + get_token_count()   │ + get_token_count()
└───────────────────┘   └───────────────────┘

┌─────────────────────────────────────┐
│          <<interface>>              │
│          SearchService              │
├─────────────────────────────────────┤
│ + search(query: str,                │
│          options: SearchOptions)    │
│   : SearchResults                   │
│ + index(document: Document): bool   │
│ + delete(doc_id: str): bool         │
└─────────────────────────────────────┘
                    △
                    │
┌─────────────────────────────────────┐
│       AzureAISearchService          │
├─────────────────────────────────────┤
│ - endpoint: str                     │
│ - index_name: str                   │
│ - api_key: str                      │
├─────────────────────────────────────┤
│ + search()                          │
│ + hybrid_search()                   │
│ + vector_search()                   │
│ + keyword_search()                  │
│ + index()                           │
│ + delete()                          │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐        ┌─────────────────────────────────┐
│         ContextBuilder              │        │        PromptTemplate           │
├─────────────────────────────────────┤        ├─────────────────────────────────┤
│ - search_service: SearchService     │───────▶│ - template: str                 │
│ - max_context_tokens: int           │        │ - variables: Dict               │
├─────────────────────────────────────┤        ├─────────────────────────────────┤
│ + build_context(query: str,         │        │ + render(context: Dict): str    │
│                 results: List)      │        │ + validate(): bool              │
│   : str                             │        └─────────────────────────────────┘
│ + rank_chunks(chunks: List): List   │
│ + truncate_to_limit(text: str): str │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│        ResponseGenerator            │
├─────────────────────────────────────┤
│ - llm_service: LLMService           │
│ - context_builder: ContextBuilder   │
│ - prompt_template: PromptTemplate   │
├─────────────────────────────────────┤
│ + generate_response(                │
│     query: str,                     │
│     conversation: Conversation      │
│   ): ChatResponse                   │
│ + format_citations(sources): List   │
│ + validate_response(response): bool │
└─────────────────────────────────────┘
```

### 4.3 Data Models

```python
# models/conversation.py

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
from enum import Enum

class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

@dataclass
class Source:
    document_id: str
    title: str
    page: int
    snippet: str
    relevance_score: float

@dataclass
class Message:
    id: str
    role: MessageRole
    content: str
    timestamp: datetime
    sources: Optional[List[Source]] = None
    tokens_used: Optional[int] = None

@dataclass
class Conversation:
    id: str
    user_id: str
    title: str
    messages: List[Message]
    created_at: datetime
    updated_at: datetime
    metadata: dict

@dataclass
class ChatRequest:
    conversation_id: Optional[str]
    message: str
    options: Optional[dict] = None

@dataclass
class ChatResponse:
    conversation_id: str
    message_id: str
    response: str
    sources: List[Source]
    metadata: dict
```

---

## 5. Sequence Diagrams

### 5.1 Chat Query Flow

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                         CHAT QUERY SEQUENCE DIAGRAM                               │
└──────────────────────────────────────────────────────────────────────────────────┘

┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
│ Client │  │  API   │  │  Auth  │  │  RAG   │  │ Search │  │ OpenAI │  │CosmosDB│
│        │  │Gateway │  │Service │  │Process │  │Service │  │        │  │        │
└───┬────┘  └───┬────┘  └───┬────┘  └───┬────┘  └───┬────┘  └───┬────┘  └───┬────┘
    │           │           │           │           │           │           │
    │ POST /api/chat        │           │           │           │           │
    │ + Bearer Token        │           │           │           │           │
    │──────────────────────▶│           │           │           │           │
    │           │           │           │           │           │           │
    │           │ Validate Token        │           │           │           │
    │           │──────────────────────▶│           │           │           │
    │           │           │           │           │           │           │
    │           │           │ Token Valid           │           │           │
    │           │◀──────────────────────│           │           │           │
    │           │           │           │           │           │           │
    │           │ Process Query         │           │           │           │
    │           │──────────────────────────────────▶│           │           │
    │           │           │           │           │           │           │
    │           │           │           │ Generate Query Embedding          │
    │           │           │           │──────────────────────────────────▶│
    │           │           │           │           │           │           │
    │           │           │           │           │ Embedding Vector      │
    │           │           │           │◀──────────────────────────────────│
    │           │           │           │           │           │           │
    │           │           │           │ Hybrid Search         │           │
    │           │           │           │──────────────────────▶│           │
    │           │           │           │           │           │           │
    │           │           │           │  Ranked Results       │           │
    │           │           │           │◀──────────────────────│           │
    │           │           │           │           │           │           │
    │           │           │           │ Build Context + Prompt            │
    │           │           │           │───────────────────────────────────│
    │           │           │           │           │           │           │
    │           │           │           │ Generate Response     │           │
    │           │           │           │──────────────────────────────────▶│
    │           │           │           │           │           │           │
    │           │           │           │           │     AI Response       │
    │           │           │           │◀──────────────────────────────────│
    │           │           │           │           │           │           │
    │           │           │           │ Store Conversation    │           │
    │           │           │           │──────────────────────────────────────────▶│
    │           │           │           │           │           │           │
    │           │           │           │           │           │  Stored   │
    │           │           │           │◀──────────────────────────────────────────│
    │           │           │           │           │           │           │
    │           │  ChatResponse         │           │           │           │
    │           │◀──────────────────────────────────│           │           │
    │           │           │           │           │           │           │
    │  JSON Response        │           │           │           │           │
    │◀──────────────────────│           │           │           │           │
    │           │           │           │           │           │           │
```

### 5.2 Document Ingestion Flow

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                     DOCUMENT INGESTION SEQUENCE DIAGRAM                           │
└──────────────────────────────────────────────────────────────────────────────────┘

┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
│ Client │  │  API   │  │  Blob  │  │Ingest  │  │Doc     │  │ OpenAI │  │ Search │
│        │  │Gateway │  │Storage │  │Function│  │Intel.  │  │        │  │        │
└───┬────┘  └───┬────┘  └───┬────┘  └───┬────┘  └───┬────┘  └───┬────┘  └───┬────┘
    │           │           │           │           │           │           │
    │ POST /api/documents   │           │           │           │           │
    │ (multipart/form-data) │           │           │           │           │
    │──────────────────────▶│           │           │           │           │
    │           │           │           │           │           │           │
    │           │ Upload to Blob        │           │           │           │
    │           │──────────────────────▶│           │           │           │
    │           │           │           │           │           │           │
    │           │           │ Blob Created          │           │           │
    │           │◀──────────────────────│           │           │           │
    │           │           │           │           │           │           │
    │  202 Accepted         │           │           │           │           │
    │  (documentId, status) │           │           │           │           │
    │◀──────────────────────│           │           │           │           │
    │           │           │           │           │           │           │
    │           │           │ Blob Trigger          │           │           │
    │           │           │──────────────────────▶│           │           │
    │           │           │           │           │           │           │
    │           │           │           │ Extract Text (OCR)    │           │
    │           │           │           │──────────────────────▶│           │
    │           │           │           │           │           │           │
    │           │           │           │           │ Extracted Text        │
    │           │           │           │◀──────────────────────│           │
    │           │           │           │           │           │           │
    │           │           │           │ Chunk Text            │           │
    │           │           │           │───────────────────────│           │
    │           │           │           │           │           │           │
    │           │           │           │ for each chunk:       │           │
    │           │           │           │ ┌─────────────────────────────────┤
    │           │           │           │ │ Generate Embedding  │           │
    │           │           │           │ │─────────────────────────────────▶
    │           │           │           │ │         │           │           │
    │           │           │           │ │         │  Embedding Vector     │
    │           │           │           │ │◀────────────────────────────────│
    │           │           │           │ │         │           │           │
    │           │           │           │ │ Index in Search     │           │
    │           │           │           │ │──────────────────────────────────────▶
    │           │           │           │ │         │           │           │
    │           │           │           │ │         │           │  Indexed  │
    │           │           │           │ │◀──────────────────────────────────────│
    │           │           │           │ └─────────────────────────────────┤
    │           │           │           │           │           │           │
    │           │           │           │ Update Status: "indexed"          │
    │           │           │           │───────────────────────────────────│
    │           │           │           │           │           │           │
```

---

## 6. Error Handling Strategy

### 6.1 Error Categories

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           ERROR HANDLING STRATEGY                                 │
└──────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  ERROR CATEGORIES                                                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  CLIENT ERRORS (4xx)                                                    │   │
│  ├─────────────────────────────────────────────────────────────────────────┤   │
│  │  Code    │ Name                │ Description                │ Retry?   │   │
│  │  ────────┼─────────────────────┼────────────────────────────┼──────────│   │
│  │  400     │ Bad Request         │ Invalid input parameters   │ No       │   │
│  │  401     │ Unauthorized        │ Missing/invalid auth token │ No       │   │
│  │  403     │ Forbidden           │ Insufficient permissions   │ No       │   │
│  │  404     │ Not Found           │ Resource doesn't exist     │ No       │   │
│  │  413     │ Payload Too Large   │ File exceeds size limit    │ No       │   │
│  │  429     │ Too Many Requests   │ Rate limit exceeded        │ Yes*     │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  SERVER ERRORS (5xx)                                                    │   │
│  ├─────────────────────────────────────────────────────────────────────────┤   │
│  │  Code    │ Name                │ Description                │ Retry?   │   │
│  │  ────────┼─────────────────────┼────────────────────────────┼──────────│   │
│  │  500     │ Internal Error      │ Unexpected server error    │ Yes      │   │
│  │  502     │ Bad Gateway         │ Upstream service error     │ Yes      │   │
│  │  503     │ Service Unavailable │ Service temporarily down   │ Yes      │   │
│  │  504     │ Gateway Timeout     │ Upstream service timeout   │ Yes      │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  * Retry with exponential backoff after Retry-After header duration            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Retry Strategy

```python
# shared/retry.py

import asyncio
from functools import wraps
from typing import Type, Tuple

def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """Decorator for retry with exponential backoff."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = min(
                            base_delay * (exponential_base ** attempt),
                            max_delay
                        )
                        await asyncio.sleep(delay)
            raise last_exception
        return wrapper
    return decorator
```

---

## 7. Configuration Management

### 7.1 Environment Variables

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                          CONFIGURATION VARIABLES                                  │
└──────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  AZURE SERVICES                                                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│  Variable                          │ Source        │ Example                    │
│  ──────────────────────────────────┼───────────────┼────────────────────────────│
│  AZURE_OPENAI_ENDPOINT             │ Key Vault     │ https://oai-xxx.openai...  │
│  AZURE_OPENAI_API_KEY              │ Key Vault     │ sk-xxx...                  │
│  AZURE_OPENAI_DEPLOYMENT_NAME      │ App Settings  │ gpt-4o-mini                │
│  AZURE_OPENAI_EMBEDDING_DEPLOYMENT │ App Settings  │ text-embedding-3-small     │
│  AZURE_SEARCH_ENDPOINT             │ Key Vault     │ https://search-xxx...      │
│  AZURE_SEARCH_API_KEY              │ Key Vault     │ xxx...                     │
│  AZURE_SEARCH_INDEX_NAME           │ App Settings  │ genai-copilot-documents    │
│  COSMOS_DB_ENDPOINT                │ Key Vault     │ https://cosmos-xxx...      │
│  COSMOS_DB_KEY                     │ Key Vault     │ xxx...                     │
│  COSMOS_DB_DATABASE                │ App Settings  │ copilot-db                 │
│  STORAGE_ACCOUNT_CONNECTION        │ Key Vault     │ DefaultEndpointsProtocol...│
│  DOCUMENT_INTELLIGENCE_ENDPOINT    │ Key Vault     │ https://di-xxx...          │
│  DOCUMENT_INTELLIGENCE_KEY         │ Key Vault     │ xxx...                     │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  APPLICATION SETTINGS                                                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│  Variable                          │ Default       │ Description                │
│  ──────────────────────────────────┼───────────────┼────────────────────────────│
│  ENVIRONMENT                       │ dev           │ dev / staging / prod       │
│  LOG_LEVEL                         │ INFO          │ DEBUG / INFO / WARNING     │
│  MAX_TOKENS_RESPONSE               │ 4096          │ Max tokens in LLM response │
│  MAX_CONTEXT_TOKENS                │ 8000          │ Max tokens for context     │
│  SEARCH_TOP_K                      │ 10            │ Number of search results   │
│  CHUNK_SIZE                        │ 512           │ Document chunk size        │
│  CHUNK_OVERLAP                     │ 50            │ Overlap between chunks     │
│  RATE_LIMIT_REQUESTS               │ 100           │ Requests per minute        │
│  RATE_LIMIT_TOKENS                 │ 100000        │ Tokens per minute          │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Feature Flags

```python
# shared/config.py

from dataclasses import dataclass
from typing import Dict

@dataclass
class FeatureFlags:
    """Feature flags for gradual rollout."""

    enable_streaming: bool = False
    enable_hybrid_search: bool = True
    enable_semantic_ranking: bool = True
    enable_content_safety: bool = True
    enable_conversation_history: bool = True
    enable_document_permissions: bool = False
    max_file_size_mb: int = 100
    supported_file_types: list = None

    def __post_init__(self):
        if self.supported_file_types is None:
            self.supported_file_types = [
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                "text/plain",
                "text/markdown"
            ]
```

---

## 8. Testing Strategy

### 8.1 Test Structure

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              TEST STRUCTURE                                       │
└──────────────────────────────────────────────────────────────────────────────────┘

tests/
├── unit/                            # Unit tests (mocked dependencies)
│   ├── test_context_builder.py
│   ├── test_prompt_templates.py
│   ├── test_chunker.py
│   └── test_validators.py
│
├── integration/                     # Integration tests (real services)
│   ├── test_search_service.py
│   ├── test_llm_service.py
│   ├── test_cosmos_repository.py
│   └── test_blob_storage.py
│
├── e2e/                            # End-to-end tests
│   ├── test_chat_flow.py
│   ├── test_document_ingestion.py
│   └── test_search_flow.py
│
├── performance/                     # Performance/load tests
│   ├── test_concurrent_queries.py
│   └── test_large_document_processing.py
│
└── fixtures/                        # Test data
    ├── sample_documents/
    └── mock_responses/
```

### 8.2 Test Coverage Requirements

| Component | Minimum Coverage | Critical Paths |
|-----------|------------------|----------------|
| API Gateway | 80% | Auth, validation |
| RAG Processor | 90% | Query flow, LLM calls |
| Ingestion | 85% | Parsing, chunking |
| Shared Utils | 95% | All utilities |

---

## 9. Deployment Specifications

### 9.1 Azure Function Configuration

```json
// host.json (API Gateway)
{
  "version": "2.0",
  "functionTimeout": "00:05:00",
  "extensions": {
    "http": {
      "routePrefix": "api",
      "maxConcurrentRequests": 100,
      "maxOutstandingRequests": 200
    }
  },
  "logging": {
    "applicationInsights": {
      "samplingSettings": {
        "isEnabled": true,
        "maxTelemetryItemsPerSecond": 5
      }
    },
    "logLevel": {
      "default": "Information",
      "Host.Results": "Error",
      "Function": "Information"
    }
  }
}
```

### 9.2 Terraform Module Configuration

```hcl
# modules/compute/main.tf - Function App Configuration

resource "azurerm_linux_function_app" "rag_processor" {
  name                       = "func-rag-${var.project_name}-${var.resource_suffix}"
  resource_group_name        = var.resource_group_name
  location                   = var.location
  storage_account_name       = var.storage_account_name
  storage_account_access_key = var.storage_account_access_key
  service_plan_id            = azurerm_service_plan.functions_premium.id

  site_config {
    always_on                = true
    ftps_state               = "Disabled"
    minimum_tls_version      = "1.2"

    application_stack {
      python_version = "3.11"
    }

    app_service_logs {
      disk_quota_mb         = 35
      retention_period_days = 7
    }
  }

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME"       = "python"
    "PYTHON_ISOLATE_WORKER_DEPENDENCIES" = "1"
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = var.app_insights_connection_string
    "AZURE_OPENAI_ENDPOINT"          = "@Microsoft.KeyVault(SecretUri=${var.key_vault_uri}/secrets/openai-endpoint/)"
    "AZURE_SEARCH_ENDPOINT"          = "@Microsoft.KeyVault(SecretUri=${var.key_vault_uri}/secrets/search-endpoint/)"
  }

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}
```

---

## 10. Appendices

### 10.1 Prompt Templates

```python
# rag/prompt_templates.py

SYSTEM_PROMPT = """You are an AI assistant for enterprise knowledge management.
Your role is to answer questions based ONLY on the provided context documents.

Rules:
1. Only use information from the provided context
2. If the answer is not in the context, say "I don't have information about that"
3. Always cite your sources using [Source: document_title, page X] format
4. Be concise but thorough
5. If asked about something outside your knowledge, politely decline

Context documents will be provided between <context> tags."""

RAG_PROMPT_TEMPLATE = """<context>
{context}
</context>

User Question: {query}

Please provide a helpful answer based on the context above. Remember to cite your sources."""
```

### 10.2 Document Processing Rules

| File Type | Max Size | Processing Method | Chunk Size |
|-----------|----------|-------------------|------------|
| PDF | 100 MB | Document Intelligence OCR | 512 tokens |
| DOCX | 50 MB | python-docx + OCR | 512 tokens |
| XLSX | 50 MB | openpyxl (sheet by sheet) | 256 tokens |
| PPTX | 100 MB | python-pptx + OCR | 512 tokens |
| TXT/MD | 10 MB | Direct text processing | 512 tokens |

---

*Document End*
