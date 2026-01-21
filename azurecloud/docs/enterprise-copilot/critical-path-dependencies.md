# Enterprise Copilot — Critical Path & Dependencies

## Step Dependencies Matrix

| Step # | Step Name | Dependencies | Critical Path? | Parallel With |
|--------|-----------|--------------|----------------|---------------|
| 1 | Create resource groups | None | ✅ YES | - |
| 2 | Configure VNet + private DNS | Step 1 | ✅ YES | Step 3 |
| 3 | Enable Managed Identity + Key Vault | Step 1 | ✅ YES | Step 2 |
| 4 | Identify document sources | None | ✅ YES | Steps 1-3 |
| 5 | Define metadata + ACL schema | Step 4 | ✅ YES | Steps 2-3 |
| 6 | Create raw storage containers | Step 1 | ✅ YES | Steps 2-5 |
| 7 | Build ingestion connectors | Steps 4, 6 | ✅ YES | - |
| 8 | Implement incremental sync | Step 7 | ✅ YES | - |
| 9 | Parse documents (text extraction) | Step 7 | ✅ YES | Step 8 |
| 10 | Normalize into canonical JSON | Step 9 | ✅ YES | - |
| 11 | Chunking (structure-aware) | Step 10 | ✅ YES | - |
| 12 | Add lineage metadata | Step 11 | ✅ YES | - |
| 13 | Generate embeddings | Step 12 | ✅ YES | - |
| 14 | Embedding caching | Step 13 | ❌ NO | - |
| 15 | Create AI Search service | Step 1 | ✅ YES | Steps 7-14 |
| 16 | Define index schema (text + vector) | Steps 5, 15 | ✅ YES | Step 13 |
| 17 | Push chunks + embeddings to index | Steps 13, 16 | ✅ YES | - |
| 18 | Implement hybrid search | Step 17 | ✅ YES | - |
| 19 | Apply RRF + MMR tuning | Step 18 | ✅ YES | - |
| 20 | Add ACL labels to chunks | Steps 12, 16 | ✅ YES | Step 17 |
| 21 | Apply RBAC/ABAC filtering | Step 20 | ✅ YES | - |
| 22 | Define agent intents & tools | None | ✅ YES | Steps 1-21 |
| 23 | Build query receiver node | Step 22 | ✅ YES | - |
| 24 | Intent detection + routing | Step 23 | ✅ YES | - |
| 25 | Build retrieval tool (search wrapper) | Steps 18, 24 | ✅ YES | - |
| 26 | Tool relevance planner (LLM routing) | Step 24 | ✅ YES | Step 25 |
| 27 | Logic Apps/Functions tool integration | Step 24 | ❌ NO | Steps 25-26 |
| 28 | Grounding system prompts | Step 26 | ✅ YES | - |
| 29 | RAG context injection in GPT call | Steps 25, 28 | ✅ YES | - |
| 30 | Post-processing + citation formatting | Step 29 | ❌ NO | - |
| 31 | Tracing & telemetry | Steps 23-30 | ❌ NO | Step 30 |
| 32 | Monitoring dashboards | Step 31 | ❌ NO | - |
| 33 | Golden Q&A benchmark creation | Steps 9-10 | ❌ NO | Steps 11-29 |
| 34 | Offline evaluation | Steps 29, 33 | ✅ YES | - |
| 35 | Online A/B testing | Step 34 | ❌ NO | - |
| 36 | Copilot Studio UI | Step 23 | ✅ YES | Steps 24-29 |
| 37 | Add feedback + source toggle | Step 36 | ❌ NO | - |
| 38 | Load testing | Steps 29, 36 | ✅ YES | - |
| 39 | Security validation (RBAC bypass tests) | Steps 20, 21 | ✅ YES | Step 38 |
| 40 | Enable private endpoints (prod) | Steps 2, 3 | ✅ YES | Steps 38-39 |
| 41 | CI/CD deployment | Steps 20-30 | ❌ NO | Steps 38-40 |
| 42 | Pilot rollout | Steps 29, 36, 39 | ✅ YES | - |
| 43 | Weekly refinement loop | Step 42 | ❌ NO | - |
| 44 | Org-wide rollout | Step 42 | ✅ YES | - |

---

## Critical Path Visualization

```
CRITICAL PATH (Must complete in sequence - any delay impacts project)
═══════════════════════════════════════════════════════════════════════

Week 1
┌───────────────────────────────────────────────────────────────────────┐
│  [1] Resource Groups ─┬─► [2] VNet + DNS                             │
│                       │                                               │
│                       └─► [3] Identity + KV                          │
│                                                                       │
│  [4] Doc Sources ────────► [5] Metadata Schema                       │
│                                                                       │
│  [6] Storage Containers                                              │
└───────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
Week 2-3
┌───────────────────────────────────────────────────────────────────────┐
│  [7] Ingestion Connectors ──► [8] Incremental Sync                   │
│           │                                                           │
│           └──────────────────► [9] Document Parsing                  │
│                                        │                              │
│                                        ▼                              │
│                                [10] JSON Normalization               │
│                                        │                              │
│                                        ▼                              │
│                                [11] Chunking                         │
│                                        │                              │
│                                        ▼                              │
│                                [12] Lineage Metadata                 │
│                                        │                              │
│                                        ▼                              │
│                                [13] Embeddings                       │
└───────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
Week 3-4
┌───────────────────────────────────────────────────────────────────────┐
│  [15] AI Search Service ──► [16] Index Schema                        │
│                                      │                                │
│                                      ▼                                │
│         [13] Embeddings ────► [17] Index Population                  │
│                                      │                                │
│                                      ▼                                │
│                              [18] Hybrid Search                      │
│                                      │                                │
│                                      ▼                                │
│                              [19] RRF + MMR Tuning                   │
└───────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
Week 4-5
┌───────────────────────────────────────────────────────────────────────┐
│  [20] ACL Labels ────────────► [21] RBAC Filtering                   │
│                                                                       │
│  [22] Agent Design ──► [23] Query Receiver ──► [24] Intent Routing   │
│                                                        │              │
│                                                        ▼              │
│                        [18] ─────────────────► [25] Retrieval Tool   │
│                                                        │              │
│                                                        ▼              │
│                                                [26] Tool Planner     │
└───────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
Week 5-6
┌───────────────────────────────────────────────────────────────────────┐
│  [26] Tool Planner ──► [28] Grounding Prompts                        │
│                                   │                                   │
│                                   ▼                                   │
│  [25] Retrieval Tool ────► [29] RAG Generation                       │
│                                   │                                   │
│  [23] Query Receiver ────► [36] Copilot UI                           │
└───────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
Week 7-8
┌───────────────────────────────────────────────────────────────────────┐
│  [29] RAG ──┬──► [34] Offline Evaluation                             │
│             │                                                         │
│  [36] UI ───┼──► [38] Load Testing                                   │
│             │                                                         │
│  [21] RBAC ─┴──► [39] Security Validation                            │
│                                                                       │
│  [2,3] ────────► [40] Private Endpoints (Prod)                       │
└───────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
Week 9-10
┌───────────────────────────────────────────────────────────────────────┐
│  [29,36,39] ──────────────► [42] Pilot Rollout                       │
│                                      │                                │
│                                      ▼                                │
│                              [44] Org-wide Rollout                   │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Critical Path Summary

### The Minimum Timeline Chain

```
1 → 2 → 4 → 5 → 7 → 9 → 10 → 11 → 12 → 13 → 16 → 17 → 18 → 19
→ 20 → 21 → 22 → 23 → 24 → 25 → 26 → 28 → 29 → 34 → 36 → 38 → 39 → 42 → 44
```

**Total Critical Path Steps**: 30 steps
**Estimated Critical Path Duration**: ~50 working days (10 weeks)

---

## Parallelization Opportunities

### Phase 1: Infrastructure (Can run in parallel)
```
[1] Resource Groups
    ├── [2] VNet + DNS      ─┐
    ├── [3] Identity + KV    ├─► All complete before Step 7
    └── [6] Storage          ─┘

[4] Doc Discovery ──► [5] Schema   (Independent track)
```

### Phase 2: Data Pipeline (Sequential but some parallel)
```
[7] Connectors ──► [9] Parsing  ──► [10] Normalize ──► [11] Chunk
                        │
                        └──► [8] Incremental Sync (parallel)
```

### Phase 3: Indexing (Some parallel)
```
[15] AI Search Service ──► [16] Index Schema
                                   │
[13] Embeddings ───────────────────┴──► [17] Index Population

[20] ACL Labels (can start with Step 12)
```

### Phase 4: Agent (Multiple parallel tracks)
```
[22] Agent Design ──► [23] Query Receiver
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
            [24] Intent             [36] Copilot UI
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
    [25] Search Tool    [26] Planner
```

### Phase 5: Testing (Parallel tracks)
```
         ┌──► [38] Load Testing
[29] RAG─┼──► [34] Offline Eval
         └──► [33] Golden Dataset (earlier start)

[21] RBAC ──► [39] Security Testing
```

---

## Risk Points on Critical Path

| Step | Risk | Impact if Delayed | Mitigation |
|------|------|-------------------|------------|
| **7** | SharePoint API limits | 2-3 days | Early rate limit testing |
| **9** | OCR quality issues | 2-5 days | Parallel manual review |
| **11** | Poor chunk quality | 3-5 days | Early retrieval testing |
| **13** | Embedding API throttling | 1-2 days | Batch + retry logic |
| **17** | Index population failures | 1-2 days | Incremental indexing |
| **18** | Low retrieval quality | 3-5 days | Extensive tuning time |
| **21** | RBAC bypass discovered | 2-3 days | Early security review |
| **29** | Hallucination issues | 3-5 days | Strong grounding prompts |
| **38** | Performance bottleneck | 2-3 days | Early load testing |
| **39** | Security findings | 3-5 days | Continuous security review |

---

## Timeline Compression Strategies

### Strategy 1: Start Agent Design Early
- Begin Step 22 (Agent Design) in Week 1 while infrastructure is being built
- Saves 2-3 days

### Strategy 2: Parallel Ingestion Tracks
- Split document sources across multiple engineers
- Each source type (SharePoint, Confluence, etc.) in parallel
- Saves 3-5 days

### Strategy 3: Early Security Review
- Start Step 20 (ACL Labels) alongside Step 12
- Begin security testing (Step 39) before full RAG completion
- Saves 2-3 days

### Strategy 4: Golden Dataset Creation
- Start Step 33 in Week 2 with SMEs
- Don't wait for full pipeline completion
- Saves 2-3 days

### Strategy 5: Copilot UI Development
- Start Step 36 immediately after Step 23
- Build UI while RAG pipeline is being completed
- Saves 2-3 days

---

## Effort Distribution by Role

| Role | Critical Path Steps | Total Effort (Days) | Peak Week |
|------|---------------------|---------------------|-----------|
| **Data Engineer** | 7, 8, 9, 10, 17 | 13 | Week 2-3 |
| **ML/Search Engineer** | 11, 12, 13, 16, 18, 19 | 12 | Week 3-4 |
| **AI Engineer** | 24, 25, 26, 28, 29 | 9 | Week 5-6 |
| **Security Engineer** | 3, 20, 21, 39, 40 | 10 | Week 4-5, 8 |
| **DevOps Engineer** | 1, 2, 15, 38 | 6 | Week 1, 7 |
| **Frontend Engineer** | 23, 36 | 4 | Week 5, 7 |
| **Product Owner** | 4, 5, 22, 33, 42 | 11 | Week 1, 7-9 |

---

## Weekly Milestone Targets

| Week | Milestone | Success Criteria |
|------|-----------|------------------|
| 1 | Infrastructure Ready | RGs, VNet, KV deployed; Sources identified |
| 2 | Ingestion Started | First connector working; Storage populated |
| 3 | Parsing Complete | 80% documents parsed successfully |
| 4 | Index Populated | Full index with embeddings searchable |
| 5 | Hybrid Search Working | Retrieval precision > 70% |
| 6 | RAG MVP | End-to-end query works with citations |
| 7 | Security Complete | RBAC enforced; Security tests passed |
| 8 | Evaluation Done | Baseline metrics established |
| 9 | UI Ready | Copilot Studio functional in Teams |
| 10 | Launch | Pilot users active; No P1 issues |

---

*Document Version: 1.0*
*Last Updated: 2025-01-15*
