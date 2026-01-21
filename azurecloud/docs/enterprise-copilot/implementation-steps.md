# Enterprise Copilot — Implementation Steps

## Master Implementation Table

| Step | Module | Implementation Step | Azure Service/Tool | Output |
|------|--------|--------------------|--------------------|--------|
| 1 | Project Setup | Create dev/test/prod resource groups | Azure Portal / ARM/Bicep | Isolated environments |
| 2 | Project Setup | Setup networking (VNet, subnets, private DNS) | Azure VNet | Secure network foundation |
| 3 | Project Setup | Enable Managed Identity + Key Vault keys | Entra ID, Key Vault | Secure auth + CMK ready |
| 4 | Data Discovery | Identify all doc sources + access owners | Internal process | Source inventory sheet |
| 5 | Data Discovery | Define metadata fields (docType, dept, ACL, tags) | Design doc | Metadata schema |
| 6 | Ingestion | Create raw data storage containers | Azure Blob Storage | Landing zone ready |
| 7 | Ingestion | Build connectors for SharePoint/Wiki/Git/Blob | Data Factory / Logic Apps / Functions | Automated ingestion |
| 8 | Ingestion | Implement incremental sync (delta updates) | Data Factory / Functions | No duplicate ingestion |
| 9 | Parsing | Extract text + structure from docs | Azure Document Intelligence / custom parsers | Normalized text |
| 10 | Parsing | Convert to canonical JSON format | Functions / Databricks | Clean "gold" corpus |
| 11 | Chunking | Implement structure-aware chunking | Functions / Databricks | Document chunks |
| 12 | Chunking | Attach lineage metadata (docId, page, section) | Custom logic | Citation-ready chunks |
| 13 | Embeddings | Generate embeddings per chunk | Azure OpenAI embeddings | Vector embeddings |
| 14 | Embeddings | Cache embeddings for unchanged chunks | Blob + hash logic | Cost efficiency |
| 15 | AI Search Setup | Create Azure AI Search service | Azure AI Search | Search resource ready |
| 16 | AI Search Index | Define index schema (text + vector + ACL fields) | AI Search Index JSON | Hybrid index schema |
| 17 | AI Search Index | Push chunks + embeddings into index | Indexer / SDK pipeline | Fully populated index |
| 18 | Hybrid Search | Implement hybrid retrieval query | AI Search hybrid API | Top-k relevant chunks |
| 19 | Hybrid Search | Add fusion (RRF) + diversity (MMR) | Retrieval logic | High recall & no redundancy |
| 20 | Security | Add ACL/RBAC metadata at chunk level | Index-time tagging | Security trimming ready |
| 21 | Security | Apply search filters per user | Query-time filters | No unauthorized retrieval |
| 22 | Agent Design | Define intents, skills, tools list | Foundry / Studio design | Agent blueprint |
| 23 | Agent Flow | Build "User Query Receiver" node | Copilot Studio | Input + auth capture |
| 24 | Agent Flow | Add intent detection & routing | LLM classifier / rules | Correct tool routing |
| 25 | Agent Flow | Build retrieval tool call (hybrid search) | Foundry tool / Function | Context fetch tool |
| 26 | Agent Flow | Add tool relevance step (planner) | GPT-4o planning prompt | Smart tool selection |
| 27 | Agent Flow | Connect Logic Apps/Functions as tools | Logic Apps / Functions + Foundry tool registry | Backend tool system |
| 28 | Prompting | Write system prompt enforcing grounding + citations | Azure OpenAI prompt | Safe grounded generation |
| 29 | Response Gen | Inject retrieved chunks into GPT call | Azure OpenAI (GPT-4o) | Draft grounded answer |
| 30 | Post-Processing | Format citations + apply safety masks | Functions | Final user response |
| 31 | Tracing | Enable prompt/tool/retrieval tracing | Azure AI Foundry + App Insights | Full observability |
| 32 | Monitoring | Add latency/cost/hallucination dashboards | Azure Monitor | Live KPIs |
| 33 | Offline Eval | Create golden Q&A dataset | Manual + scripts | Eval benchmark |
| 34 | Offline Eval | Run Precision@K, groundedness, nDCG | Foundry evaluation | Baseline scores |
| 35 | Online Eval | Deploy shadow/A-B test configs | App Config / Foundry | Best config chosen |
| 36 | Copilot UI | Build Copilot Studio UI + file/image upload | Copilot Studio | User-facing bot |
| 37 | Copilot UI | Add feedback buttons + source toggle | Copilot Studio | Feedback telemetry |
| 38 | Testing | Load test concurrency & search latency | Azure Load Testing | Perf validation |
| 39 | Testing | Security validation (RBAC bypass tests) | Manual + scripts | Secure go-live proof |
| 40 | Production | Enable private endpoints for OpenAI/Search/Storage | Private Link | Locked-down prod |
| 41 | Production | Deploy production pipelines + indexers | CI/CD / DevOps | Prod system running |
| 42 | Launch | Pilot rollout to one department | Teams / Web | Real usage starts |
| 43 | Refinement | Weekly tuning of chunks, ranking, prompts | Refinement loop | Continuous quality gain |
| 44 | Org Rollout | Expand access org-wide | Entra groups | Full enterprise Copilot |

---

## Detailed Implementation Table with Techniques, Algorithms & Effort

| Step | Module | Implementation Step | Technique Used | Algorithm/Model | Owner | Effort (Days) |
|------|--------|--------------------|-----------------|--------------------|-------|---------------|
| 1 | Project Setup | Create dev/test/prod resource groups | IaC deployment | Terraform/Bicep modules | DevOps Engineer | 0.5 |
| 2 | Project Setup | Setup networking (VNet, subnets, private DNS) | Zero-trust architecture | Hub-spoke topology | Network Engineer | 2 |
| 3 | Project Setup | Enable Managed Identity + Key Vault keys | Identity federation | System-assigned MI + RBAC | Security Engineer | 1 |
| 4 | Data Discovery | Identify all doc sources + access owners | Requirements gathering | Stakeholder interviews | Product Owner | 3 |
| 5 | Data Discovery | Define metadata fields (docType, dept, ACL, tags) | Schema design | Entity-relationship modeling | Data Architect | 2 |
| 6 | Ingestion | Create raw data storage containers | Data lake design | Bronze/Silver/Gold layers | Data Engineer | 0.5 |
| 7 | Ingestion | Build connectors for SharePoint/Wiki/Git/Blob | ETL pipeline | Graph API, REST connectors | Data Engineer | 5 |
| 8 | Ingestion | Implement incremental sync (delta updates) | Change data capture | Delta tokens, watermarks | Data Engineer | 2 |
| 9 | Parsing | Extract text + structure from docs | Document understanding | Azure DI Layout model | ML Engineer | 3 |
| 10 | Parsing | Convert to canonical JSON format | Data normalization | JSON schema validation | Data Engineer | 2 |
| 11 | Chunking | Implement structure-aware chunking | Text segmentation | Heading-aware recursive split | ML Engineer | 3 |
| 12 | Chunking | Attach lineage metadata (docId, page, section) | Provenance tracking | UUID + path mapping | ML Engineer | 1 |
| 13 | Embeddings | Generate embeddings per chunk | Vectorization | text-embedding-3-large (3072d) | ML Engineer | 2 |
| 14 | Embeddings | Cache embeddings for unchanged chunks | Content-addressed storage | SHA256 hash keying | ML Engineer | 1 |
| 15 | AI Search Setup | Create Azure AI Search service | Search provisioning | Standard tier + replicas | Search Engineer | 0.5 |
| 16 | AI Search Index | Define index schema (text + vector + ACL fields) | Index design | HNSW (m=4, ef=400) | Search Engineer | 2 |
| 17 | AI Search Index | Push chunks + embeddings into index | Bulk indexing | Push API batching (1000/batch) | Data Engineer | 2 |
| 18 | Hybrid Search | Implement hybrid retrieval query | Hybrid search | Vector + BM25 fusion | Search Engineer | 2 |
| 19 | Hybrid Search | Add fusion (RRF) + diversity (MMR) | Result merging | RRF (k=60) + MMR (λ=0.5) | Search Engineer | 2 |
| 20 | Security | Add ACL/RBAC metadata at chunk level | Access control | ABAC tagging | Security Engineer | 2 |
| 21 | Security | Apply search filters per user | Security trimming | OData filter expressions | Search Engineer | 1 |
| 22 | Agent Design | Define intents, skills, tools list | Conversation design | Intent taxonomy | Product Owner | 2 |
| 23 | Agent Flow | Build "User Query Receiver" node | Dialog management | Copilot Studio trigger | Frontend Engineer | 1 |
| 24 | Agent Flow | Add intent detection & routing | Intent classification | GPT-4o zero-shot classify | ML Engineer | 2 |
| 25 | Agent Flow | Build retrieval tool call (hybrid search) | Tool integration | HTTP action + JSON parse | Backend Engineer | 2 |
| 26 | Agent Flow | Add tool relevance step (planner) | Agentic planning | ReAct pattern prompting | ML Engineer | 2 |
| 27 | Agent Flow | Connect Logic Apps/Functions as tools | Workflow automation | OpenAPI tool registration | Integration Engineer | 2 |
| 28 | Prompting | Write system prompt enforcing grounding + citations | Prompt engineering | Chain-of-citation prompting | Prompt Engineer | 3 |
| 29 | Response Gen | Inject retrieved chunks into GPT call | RAG generation | Context window optimization | Backend Engineer | 2 |
| 30 | Post-Processing | Format citations + apply safety masks | Output formatting | Regex + Content Safety API | Backend Engineer | 2 |
| 31 | Tracing | Enable prompt/tool/retrieval tracing | Distributed tracing | OpenTelemetry spans | DevOps Engineer | 2 |
| 32 | Monitoring | Add latency/cost/hallucination dashboards | Observability | KQL queries + Grafana | DevOps Engineer | 2 |
| 33 | Offline Eval | Create golden Q&A dataset | Benchmark creation | SME curation + labeling | Product Owner + SMEs | 3 |
| 34 | Offline Eval | Run Precision@K, groundedness, nDCG | Retrieval evaluation | LLM-as-judge scoring | QA Engineer | 2 |
| 35 | Online Eval | Deploy shadow/A-B test configs | Experimentation | Feature flags + traffic split | ML Engineer | 2 |
| 36 | Copilot UI | Build Copilot Studio UI + file/image upload | UX design | Adaptive cards + file picker | Frontend Engineer | 3 |
| 37 | Copilot UI | Add feedback buttons + source toggle | Telemetry capture | Custom events + ratings | Frontend Engineer | 1 |
| 38 | Testing | Load test concurrency & search latency | Performance testing | Locust / JMeter scripts | Performance Engineer | 2 |
| 39 | Testing | Security validation (RBAC bypass tests) | Penetration testing | OWASP test cases | Security Engineer | 3 |
| 40 | Production | Enable private endpoints for OpenAI/Search/Storage | Network isolation | Private Link + DNS zones | Network Engineer | 2 |
| 41 | Production | Deploy production pipelines + indexers | CI/CD deployment | Azure Pipelines YAML | DevOps Engineer | 2 |
| 42 | Launch | Pilot rollout to one department | Staged rollout | Entra group targeting | Product Owner | 2 |
| 43 | Refinement | Weekly tuning of chunks, ranking, prompts | Continuous improvement | A/B test analysis | ML Engineer | Ongoing |
| 44 | Org Rollout | Expand access org-wide | Feature graduation | Progressive rollout | Product Owner | 2 |

---

## Technique Deep-Dive Reference

### Chunking Techniques (Step 11)

| Technique | Algorithm | Best For | Parameters |
|-----------|-----------|----------|------------|
| Fixed-size | Token split | Generic text | `size=512, overlap=64` |
| Sentence-based | NLTK punkt | Conversational | Sentence boundaries |
| Paragraph-based | `\n\n` split | Structured docs | Merge small paras |
| **Heading-aware** | Markdown H1-H6 parse | **Technical docs** | **Preserve hierarchy** |
| Semantic | Embedding clustering | Mixed content | Similarity threshold |

**Recommended**: Heading-aware chunking with `max_tokens=512`, `overlap=64`

### Embedding Models (Step 13)

| Model | Dimensions | Cost/1M tokens | Quality | Latency |
|-------|------------|----------------|---------|---------|
| text-embedding-3-small | 1536 | $0.02 | Good | Fast |
| **text-embedding-3-large** | **3072** | **$0.13** | **Best** | **Medium** |
| text-embedding-ada-002 | 1536 | $0.10 | Legacy | Fast |

**Recommended**: text-embedding-3-large for highest quality retrieval

### Hybrid Search Configuration (Steps 18-19)

```json
{
  "search": "{query_text}",
  "vectorQueries": [{
    "kind": "vector",
    "vector": "{query_embedding}",
    "fields": "chunk_vector",
    "k": 50,
    "exhaustive": false
  }],
  "queryType": "semantic",
  "semanticConfiguration": "semantic-config",
  "top": 10,
  "select": "chunk_id,chunk_text,title,heading_path,score"
}
```

**Fusion**: RRF with k=60 (default)
**Diversity**: MMR with λ=0.5 (balance relevance/diversity)

### Intent Classification (Step 24)

| Method | Model | Accuracy | Latency | Cost |
|--------|-------|----------|---------|------|
| Rule-based | Regex/Keywords | 70-80% | <10ms | Free |
| **Zero-shot** | **GPT-4o-mini** | **85-90%** | **200ms** | **Low** |
| Few-shot | GPT-4o | 90-95% | 500ms | Medium |
| Fine-tuned | BERT/RoBERTa | 95%+ | 50ms | Training cost |

**Recommended**: GPT-4o-mini zero-shot for flexibility

### Prompt Engineering (Step 28)

```
SYSTEM PROMPT TEMPLATE:
───────────────────────
You are an enterprise knowledge assistant. Follow these rules:

1. ONLY answer using the provided context
2. If context doesn't contain the answer, say "I don't have information about that topic in my knowledge base"
3. ALWAYS cite sources using [Source N] format
4. Be concise and professional
5. Never fabricate information

Context:
{context_chunks}

───────────────────────
USER: {query}
───────────────────────
```

### Evaluation Metrics (Step 34)

| Metric | Formula | Target | Tool |
|--------|---------|--------|------|
| Precision@5 | relevant_in_5 / 5 | ≥ 0.70 | Custom script |
| nDCG@10 | Normalized DCG | ≥ 0.75 | scikit-learn |
| Groundedness | LLM judge (0-1) | ≥ 0.85 | GPT-4o eval |
| Hallucination | Claims not in context | ≤ 0.05 | GPT-4o detect |
| Latency P95 | 95th percentile | ≤ 3000ms | App Insights |

### Security Filter Expression (Step 21)

```python
# Build OData filter from user's Entra groups
user_groups = ["HR-Team", "All-Employees", "US-Region"]
filter_expr = f"acl_groups/any(g: search.in(g, '{','.join(user_groups)}'))"

# Full query with security filter
search_request = {
    "search": query,
    "filter": filter_expr,
    "vectorQueries": [...]
}
```

---

## Effort Summary by Module

| Module | Total Steps | Total Effort (Days) | Primary Owner |
|--------|-------------|---------------------|---------------|
| Project Setup | 3 | 3.5 | DevOps + Security |
| Data Discovery | 2 | 5 | Product Owner |
| Ingestion | 3 | 7.5 | Data Engineer |
| Parsing | 2 | 5 | ML Engineer |
| Chunking | 2 | 4 | ML Engineer |
| Embeddings | 2 | 3 | ML Engineer |
| AI Search | 5 | 8.5 | Search Engineer |
| Security | 2 | 3 | Security Engineer |
| Agent Flow | 6 | 11 | Backend + ML |
| Prompting & Generation | 3 | 7 | Prompt Engineer |
| Tracing & Monitoring | 2 | 4 | DevOps |
| Evaluation | 3 | 7 | QA + ML |
| Copilot UI | 2 | 4 | Frontend |
| Testing | 2 | 5 | QA + Security |
| Production | 2 | 4 | DevOps + Network |
| Launch & Rollout | 3 | 4+ | Product Owner |

**Total Estimated Effort**: ~85 person-days (not including ongoing refinement)

---

## Critical Path Items

The following steps are on the critical path and should be prioritized:

1. **Steps 7-8**: Ingestion connectors (blocks all downstream)
2. **Steps 11-13**: Chunking + embeddings (blocks indexing)
3. **Steps 16-17**: Index schema + population (blocks retrieval)
4. **Steps 18-19**: Hybrid search implementation (blocks agent)
5. **Steps 28-29**: Prompting + RAG generation (blocks MVP)
6. **Steps 20-21**: Security trimming (blocks production)

---

## Risk Mitigation by Step

| Step | Risk | Mitigation |
|------|------|------------|
| 7 | SharePoint API rate limits | Implement exponential backoff, batch requests |
| 9 | OCR quality issues | Use Document Intelligence prebuilt-layout, add validation |
| 11 | Poor chunk boundaries | Test multiple strategies, validate with retrieval metrics |
| 13 | Embedding API throttling | Batch processing, retry logic, caching |
| 18 | Low retrieval quality | Tune RRF k value, add semantic ranker |
| 21 | RBAC bypass | Extensive security testing, audit logging |
| 28 | Hallucination | Strong grounding prompts, citation requirements |
| 38 | Performance bottleneck | Early load testing, horizontal scaling |

---

*Document Version: 1.0*
*Last Updated: 2025-01-15*
