# Glossary — Azure OpenAI Enterprise RAG Platform

> Authoritative terminology reference for the Enterprise RAG Copilot platform, aligned with **CMMI Level 3 | ISO/IEC 42001 | NIST AI RMF** standards for consistent communication across engineering, security, compliance, and executive stakeholders.

---

## Table of Contents

1. [AI/ML Core Concepts](#1-aiml-core-concepts)
2. [Search & Retrieval](#2-search--retrieval)
3. [Azure Services](#3-azure-services)
4. [Security & Compliance](#4-security--compliance)
5. [Enterprise & Governance](#5-enterprise--governance)
6. [Domain-Specific Terms](#6-domain-specific-terms)
7. [Platform-Specific Terms](#7-platform-specific-terms)
8. [Acronym Quick Reference](#8-acronym-quick-reference)
9. [Consistent Usage Guide](#9-consistent-usage-guide)

---

## 1. AI/ML Core Concepts

### 1.1 Models & Architectures

**Artificial Intelligence (AI)** — The broad discipline of creating systems capable of performing tasks that typically require human intelligence, including reasoning, learning, perception, and natural language understanding.

**Machine Learning (ML)** — A subset of AI in which systems learn patterns from data rather than being explicitly programmed, using statistical methods to improve performance on tasks over time.

**Deep Learning** — A subset of machine learning that uses multi-layered neural networks (deep neural networks) to learn hierarchical representations of data, enabling breakthroughs in vision, language, and speech.

**Neural Network** — A computational model inspired by biological neurons, consisting of layers of interconnected nodes that process inputs through weighted connections and activation functions.

**Transformer** — A neural network architecture introduced in "Attention Is All You Need" (2017) that relies entirely on self-attention mechanisms rather than recurrence, enabling parallelized training and superior performance on sequence tasks.

**Attention Mechanism** — A technique that allows a model to dynamically focus on different parts of the input sequence when producing each element of the output, computing relevance scores between all pairs of positions.

**Self-Attention** — A specific form of attention where the query, key, and value vectors are all derived from the same input sequence, enabling the model to relate different positions within a single sequence to compute a representation.

**Multi-Head Attention** — An extension of attention that runs multiple attention operations in parallel with different learned linear projections, allowing the model to jointly attend to information from different representation subspaces.

**Large Language Model (LLM)** — A transformer-based model trained on massive text corpora (hundreds of billions of tokens) that exhibits emergent capabilities in language understanding, generation, reasoning, and in-context learning.

**GPT (Generative Pre-trained Transformer)** — A family of autoregressive language models developed by OpenAI that generate text by predicting the next token in a sequence, pre-trained on large corpora and fine-tuned for specific tasks.

**Foundation Model** — A large-scale model trained on broad data that can be adapted to a wide range of downstream tasks through fine-tuning, prompt engineering, or in-context learning, serving as a base for specialized applications.

**Generative AI** — AI systems capable of creating new content (text, images, code, audio) by learning patterns from training data and generating novel outputs that reflect those patterns.

**Model** — In the ML context, a mathematical function with learned parameters that maps inputs to outputs; in this platform, typically refers to a specific GPT deployment (e.g., GPT-4o, GPT-4o-mini).

### 1.2 Training & Optimization

**Pre-training** — The initial training phase where a model learns general language understanding from large-scale unsupervised data, forming the foundation for downstream task adaptation.

**Fine-tuning** — The process of continuing the training of a pre-trained model on a smaller, task-specific dataset to adapt its behavior for particular use cases such as domain-specific Q&A or classification.

**RLHF (Reinforcement Learning from Human Feedback)** — A training technique where human preferences are used to train a reward model, which then guides the language model via reinforcement learning to produce outputs aligned with human values and expectations.

**Transfer Learning** — The practice of applying knowledge learned from one task or domain to a different but related task, enabling effective performance with less task-specific training data.

**Supervised Learning** — A training paradigm where models learn from labeled input-output pairs, mapping inputs to known correct outputs through optimization of a loss function.

**Unsupervised Learning** — A training paradigm where models learn patterns and structure from unlabeled data without explicit target outputs, commonly used for clustering, dimensionality reduction, and representation learning.

### 1.3 Inference & Generation

**Inference** — The process of using a trained model to generate predictions or outputs from new input data at runtime, as opposed to training the model on data.

**Token** — The basic unit of text processed by language models, typically representing a word, subword, or character depending on the tokenizer; GPT-4o averages approximately 0.75 tokens per word in English.

**Tokenizer** — The component that converts raw text into a sequence of tokens (integers) that the model can process, and converts model output tokens back into human-readable text.

**Context Window** — The maximum number of tokens a model can process in a single request, including both the input prompt and generated output; GPT-4o supports 128K tokens.

**Temperature** — A parameter (0.0–2.0) controlling the randomness of token selection during generation; lower values (e.g., 0.1 for RAG) produce more deterministic outputs, while higher values increase diversity and creativity.

**Top-p (Nucleus Sampling)** — A sampling strategy that selects from the smallest set of tokens whose cumulative probability exceeds a threshold p, providing an alternative to temperature for controlling output diversity.

**Top-k Sampling** — A decoding strategy that restricts token selection to the k most probable tokens at each generation step, limiting the vocabulary considered during sampling.

**Beam Search** — A decoding strategy that maintains multiple candidate sequences (beams) at each generation step, selecting the highest-scoring complete sequence, often producing more coherent but less diverse outputs.

**Logits** — The raw, unnormalized output scores from the model's final layer before applying softmax, representing the model's confidence for each possible next token in the vocabulary.

**Softmax** — A function that converts logits into a probability distribution over the vocabulary, ensuring all values are between 0 and 1 and sum to 1.

**Hallucination** — A phenomenon where the model generates plausible-sounding but factually incorrect or fabricated information not supported by the input context or training data. This platform targets a hallucination rate of 5% or less.

**Grounding / Groundedness** — The degree to which a model's generated response is supported by and attributable to the provided source documents or context. This platform enforces a groundedness threshold of 0.80 or higher.

**Latency** — The time elapsed between sending a request to the model and receiving the complete response, measured at P50, P95, and P99 percentiles; this platform targets P95 latency of 3 seconds or less.

**Throughput** — The number of requests or tokens a model deployment can process per unit of time, typically measured in tokens per minute (TPM) or requests per minute (RPM).

### 1.4 Prompt Engineering

**Prompt Engineering** — The practice of designing and optimizing input prompts to elicit desired outputs from language models, encompassing techniques such as few-shot examples, chain-of-thought reasoning, and structured instructions.

**System Prompt** — The initial instruction set provided to the model that establishes its behavior, persona, constraints, and response format; in this platform, it enforces citation requirements and context-only answering.

**User Prompt** — The end-user's natural language query or instruction submitted to the model for processing within a conversation turn.

**Assistant Prompt** — The model's generated response to a user prompt, which may include cited content, structured formatting, and follow-up suggestions.

**Few-Shot Learning** — A prompting technique that provides a small number of input-output examples within the prompt to guide the model's behavior on a new task without fine-tuning.

**Zero-Shot Learning** — A prompting technique where the model performs a task based solely on instructions without any examples, relying on its pre-trained knowledge to understand the task.

**One-Shot Learning** — A prompting technique providing exactly one example to guide the model's response format and behavior for a given task.

**Chain-of-Thought (CoT)** — A prompting technique that encourages the model to produce intermediate reasoning steps before arriving at a final answer, improving performance on complex multi-step problems.

**Prompt Template** — A parameterized prompt structure with placeholders for dynamic content (e.g., retrieved context, user query, conversation history) that ensures consistent model interaction across requests.

**Prompt Injection** — An adversarial technique where malicious instructions are embedded in user input to manipulate the model into ignoring its system prompt or performing unintended actions; mitigated through input validation and content filtering.

### 1.5 NLP Tasks

**Retrieval-Augmented Generation (RAG)** — An architecture that enhances LLM responses by first retrieving relevant documents from an external knowledge base, then providing those documents as context for the model to generate grounded, accurate answers.

**Classification** — The NLP task of assigning predefined category labels to text, such as intent detection, topic categorization, or document routing.

**Named Entity Recognition (NER)** — The task of identifying and classifying named entities in text into predefined categories such as person names, organizations, locations, dates, and monetary values.

**Sentiment Analysis** — The task of determining the emotional tone or opinion expressed in text, typically categorized as positive, negative, or neutral, with optional fine-grained scoring.

**Summarization** — The task of condensing longer text into a shorter version that preserves key information, available in extractive (selecting key sentences) and abstractive (generating new text) forms.

**Semantic Similarity** — A measure of how closely two pieces of text share meaning, independent of lexical overlap, typically computed as the distance or angle between their embedding vectors.

**Cosine Similarity** — A metric that measures the cosine of the angle between two vectors in embedding space, ranging from -1 (opposite) to 1 (identical), commonly used to compare document and query embeddings.

**Embedding** — A dense, fixed-dimensional vector representation of text (or other data) in a continuous vector space where semantically similar items are positioned close together; this platform uses text-embedding-3-large producing 3072-dimensional vectors.

**Vector** — A mathematical array of numbers representing a point in multi-dimensional space; in AI search, vectors encode the semantic meaning of text chunks for similarity comparison.

### 1.6 Evaluation Metrics

**Precision** — The proportion of retrieved or generated items that are relevant, calculated as true positives divided by the sum of true positives and false positives.

**Recall** — The proportion of all relevant items that are successfully retrieved or identified, calculated as true positives divided by the sum of true positives and false negatives.

**F1 Score** — The harmonic mean of precision and recall, providing a single metric that balances both measures, calculated as 2 * (precision * recall) / (precision + recall).

**BLEU (Bilingual Evaluation Understudy)** — An automated metric that evaluates generated text quality by measuring n-gram overlap between the generated output and reference text.

**ROUGE (Recall-Oriented Understudy for Gisting Evaluation)** — A set of metrics for evaluating text summarization quality by comparing n-gram overlap, longest common subsequence, and skip-bigrams against reference summaries.

**Perplexity** — A metric measuring how well a language model predicts a sample of text; lower perplexity indicates better predictive performance and more confident token predictions.

**LLM-as-Judge** — An evaluation technique where a language model is used to assess the quality of another model's output across dimensions such as groundedness, relevance, coherence, and fluency.

**Human Evaluation** — The process of having human annotators assess model output quality across defined rubrics, providing ground truth for calibrating automated metrics and identifying failure modes.

**Inter-Annotator Agreement** — A statistical measure of the degree to which independent human evaluators produce the same quality judgments, commonly measured using Cohen's Kappa or Fleiss' Kappa.

**Confusion Matrix** — A table that summarizes the performance of a classification model by showing the counts of true positives, true negatives, false positives, and false negatives for each class.

**AUC-ROC (Area Under the Receiver Operating Characteristic Curve)** — A metric that evaluates binary classification performance across all discrimination thresholds, where 1.0 represents perfect classification and 0.5 represents random chance.

---

## 2. Search & Retrieval

### 2.1 Search Paradigms

**Vector Search** — A search method that converts queries and documents into embedding vectors and retrieves results by computing similarity (e.g., cosine similarity) in the vector space, excelling at capturing semantic meaning.

**Keyword Search** — A traditional search method that matches documents based on exact or stemmed term overlap with the query, effective for precise term matching but unable to capture synonyms or paraphrases.

**Hybrid Search** — A search strategy that combines vector search and keyword search (BM25) to leverage both semantic understanding and exact term matching, delivering approximately 40% better recall than vector-only search in this platform.

**Semantic Search** — A search approach that understands the intent and contextual meaning of a query rather than relying solely on keyword matching, typically powered by neural embeddings and/or transformer-based models.

**Semantic Ranking (Semantic Ranker)** — An Azure AI Search feature that uses a cross-encoder transformer model to rerank initial search results based on deep semantic understanding of query-document relevance, applied as a second-pass ranking stage.

**Full-Text Search** — Search that examines every word in a document corpus against query terms, typically using an inverted index structure for efficient retrieval.

### 2.2 Scoring & Ranking

**BM25 (Best Matching 25)** — A probabilistic ranking function that scores documents based on term frequency, inverse document frequency, and document length normalization; the default keyword scoring algorithm in Azure AI Search.

**TF-IDF (Term Frequency-Inverse Document Frequency)** — A statistical measure that evaluates how important a word is to a document within a corpus, assigning higher weight to terms that are frequent in the document but rare across the corpus.

**Reranking** — A second-pass ranking process that takes initial search results and reorders them using a more sophisticated model (e.g., cross-encoder) to improve the quality and relevance of the final result set.

**Reciprocal Rank Fusion (RRF)** — A score combination method that merges ranked result lists from multiple retrieval strategies (e.g., vector and BM25) by summing the reciprocal of each result's rank position across lists, used in Azure AI Search hybrid mode.

**Scoring Profile** — A configurable component in Azure AI Search that adjusts the relevance score of search results based on custom rules such as field weighting, freshness boosting, distance calculations, or tag matching.

**Cross-Encoder** — A neural model architecture that jointly encodes the query and document together to produce a relevance score, offering higher accuracy than bi-encoder approaches but at greater computational cost, used in reranking.

**Bi-Encoder** — A neural model architecture that independently encodes the query and document into separate embeddings, enabling efficient pre-computation and approximate nearest neighbor search at the cost of less precise relevance estimation.

### 2.3 Index Structures & Algorithms

**HNSW (Hierarchical Navigable Small World)** — A graph-based approximate nearest neighbor algorithm that builds a multi-layer navigable graph structure for efficient vector search; this platform uses m=4, efConstruction=400, efSearch=500.

**IVF (Inverted File Index)** — A vector indexing method that partitions the embedding space into clusters (Voronoi cells) and searches only the nearest clusters at query time, trading recall for speed.

**Approximate Nearest Neighbor (ANN)** — A family of algorithms (including HNSW, IVF, LSH) that find vectors close to a query vector without exhaustive comparison, sacrificing perfect accuracy for dramatically improved search speed.

**k-Nearest Neighbors (k-NN)** — A retrieval method that returns the k most similar items to a query vector based on a distance metric; in Azure AI Search, this refers to the exact or approximate nearest neighbor search over vector fields.

**Inverted Index** — A data structure that maps each unique term to the list of documents containing that term, enabling fast full-text keyword search by avoiding scanning every document.

**Index** — A structured data store optimized for search operations; in Azure AI Search, an index contains fields (searchable, filterable, sortable, facetable) with documents organized for efficient retrieval.

**Index Alias** — A pointer or reference name that maps to a specific index version, enabling blue-green index swaps without changing application configuration or experiencing downtime.

### 2.4 Data Processing

**Chunking** — The process of dividing large documents into smaller, semantically coherent segments (chunks) suitable for embedding and retrieval; this platform uses 512-token chunks as the default size.

**Overlap** — The number of tokens shared between adjacent chunks during the chunking process, ensuring contextual continuity across chunk boundaries; this platform uses 128-token overlap.

**Analyzer** — A component in the search indexing pipeline that processes text through character filters, tokenization, and token filters to produce the terms stored in the inverted index.

**Tokenizer (Search Context)** — The component within a search analyzer that splits text into individual tokens based on rules such as whitespace, punctuation, or language-specific patterns; distinct from the ML tokenizer used by language models.

**Metadata Filtering** — The application of structured field-based filters (e.g., department, date range, document type) to narrow search results before or after relevance scoring, improving precision for targeted queries.

**Faceting** — A search feature that groups results by field values (e.g., department, document type, date) and returns counts per group, enabling guided navigation and drill-down refinement of search results.

**Skillset** — In Azure AI Search, a collection of AI enrichment skills (OCR, entity extraction, key phrase extraction) applied during indexing to extract structured data from unstructured content.

**Indexer** — An Azure AI Search component that automates data ingestion from supported data sources (Blob Storage, Cosmos DB, SQL) into a search index, supporting incremental updates via change tracking.

**Synonym Map** — A search resource that defines equivalent terms (e.g., "HR" maps to "Human Resources") so that queries using either form return matching results, improving recall without reindexing.

**Suggester** — An Azure AI Search feature that provides type-ahead autocomplete and search suggestions based on partial query input, improving the user search experience with real-time recommendations.

**Knowledge Store** — A feature of Azure AI Search skillsets that persists enrichment outputs (entities, key phrases, tables) to Azure Storage for downstream analytics, reporting, or secondary indexing.

**Document Scoring** — The process of computing a numerical relevance score for each document in the result set based on term frequency, field weights, scoring profiles, and optional boosting functions.

**Filter Expression** — An OData-syntax expression applied to search queries to include or exclude documents based on structured field values (e.g., `department eq 'Legal' and effectiveDate ge 2024-01-01`).

---

## 3. Azure Services

### 3.1 AI & Cognitive Services

**Azure OpenAI Service** — A managed Azure service providing REST API access to OpenAI models (GPT-4o, GPT-4o-mini, text-embedding-3-large) with enterprise features including VNet integration, managed identity, content filtering, and regional deployment.

**Azure AI Search (formerly Azure Cognitive Search)** — A fully managed cloud search service providing vector search, full-text search, semantic ranking, and hybrid search capabilities with built-in AI enrichment, used as the primary retrieval engine in this platform.

**Azure AI Document Intelligence (formerly Form Recognizer)** — A cloud-based AI service that extracts text, key-value pairs, tables, and structure from documents using OCR and deep learning models, supporting prebuilt (invoice, receipt, ID) and custom models.

**Azure AI Content Safety** — A service providing AI-powered content moderation that detects harmful content (violence, hate, sexual, self-harm) in text and images, integrated into the platform's content filtering pipeline.

### 3.2 Compute & Containers

**Azure Kubernetes Service (AKS)** — A managed Kubernetes container orchestration service used to host the platform's microservices with features including HPA, KEDA-based scaling, Workload Identity, and private API server endpoints.

**Azure Functions** — A serverless compute platform for event-driven code execution, used in this platform for document ingestion orchestration, embedding generation, and asynchronous processing pipelines with fan-out/fan-in patterns.

**Azure Container Registry (ACR)** — A managed Docker container registry for storing and managing container images used by AKS deployments, integrated with vulnerability scanning and geo-replication.

### 3.3 Data & Storage

**Azure Cosmos DB** — A globally distributed, multi-model NoSQL database service used for conversation history, session state, user preferences, and evaluation results with guaranteed single-digit millisecond latency.

**Azure Blob Storage** — Massively scalable object storage for unstructured data, used as the primary document store for source documents (PDFs, Word, HTML) and the data source for search indexer ingestion.

**Azure Data Lake Storage Gen2** — A hierarchical file system layered on Blob Storage optimized for analytics workloads, used for storing processed documents, evaluation datasets, and telemetry exports.

**Azure Cache for Redis** — A managed in-memory data store used for semantic caching of query results (15-30 min TTL), retrieval results (30-60 min TTL), and embedding vectors (30-day TTL) to reduce latency and API costs.

### 3.4 Networking & Security

**Azure API Management (APIM)** — A hybrid, multi-cloud management platform for APIs that provides rate limiting, authentication, request/response transformation, and developer portal capabilities; serves as the platform's API gateway.

**Azure Application Gateway** — A layer-7 load balancer with Web Application Firewall (WAF) capabilities that provides SSL termination, URL-based routing, and protection against OWASP top-10 vulnerabilities.

**Azure Front Door** — A global, scalable entry point for web applications providing CDN, SSL offloading, WAF, and intelligent traffic routing across regions for high availability and low latency.

**Azure Traffic Manager** — A DNS-based traffic load balancer that distributes traffic across global Azure regions based on routing methods such as priority, weighted, performance, or geographic.

**Azure Firewall** — A managed, cloud-based network security service that provides threat intelligence-based filtering, FQDN filtering, and network/application rule processing for VNet traffic control.

**Network Security Group (NSG)** — A set of inbound and outbound security rules applied to subnets or network interfaces to filter network traffic based on source/destination IP, port, and protocol.

**Private Endpoint** — A network interface that assigns a private IP address from your VNet to an Azure service, enabling access over a private connection rather than the public internet.

**Private Link** — An Azure networking feature that enables private connectivity from a VNet to Azure services, partner services, or customer-owned services, ensuring traffic stays on the Microsoft backbone network.

**Virtual Network (VNet)** — A logically isolated network in Azure that enables secure communication between Azure resources, on-premises networks, and the internet with configurable subnets, routing, and security.

**Azure Key Vault** — A cloud service for securely storing and managing secrets, encryption keys, and certificates used by the platform for API keys, connection strings, and customer-managed encryption keys.

### 3.5 Identity & Access

**Microsoft Entra ID (formerly Azure Active Directory)** — Microsoft's cloud-based identity and access management service providing authentication, single sign-on, conditional access, and Managed Identity for Azure resource authorization.

**Managed Identity** — An Azure feature that provides automatically managed credentials for services to authenticate to other Azure resources without storing secrets in code or configuration.

**Workload Identity** — A Kubernetes-native mechanism that federates AKS pod identity with Microsoft Entra ID, replacing the deprecated AAD Pod Identity for secure, secretless authentication from pods to Azure services.

### 3.6 Monitoring & Observability

**Azure Monitor** — A comprehensive monitoring platform that collects, analyzes, and acts on telemetry from Azure resources and applications, providing metrics, logs, alerts, and autoscale capabilities.

**Application Insights** — An Application Performance Management (APM) service within Azure Monitor that provides distributed tracing, live metrics, request tracking, dependency mapping, and custom event telemetry.

**Log Analytics** — A tool within Azure Monitor for querying and analyzing log data using Kusto Query Language (KQL), serving as the central log aggregation point for platform diagnostics and audit trails.

**Azure Workbooks** — An interactive reporting tool within Azure Monitor that combines text, KQL queries, metrics, and visualizations into shared dashboards for operational and executive reporting.

**Azure Cost Management** — A suite of tools for monitoring, allocating, and optimizing Azure cloud spending, providing cost analysis, budgets, alerts, and recommendations for resource rightsizing.

**Azure Policy** — A governance service that creates, assigns, and manages policies enforcing rules and effects over Azure resources, ensuring compliance with organizational standards (e.g., require tags, deny public endpoints).

**Azure Resource Manager (ARM)** — The deployment and management layer for Azure that provides a consistent management API for creating, updating, and deleting resources through templates, Bicep, or Terraform.

**Azure Service Bus** — A fully managed enterprise message broker supporting queues and publish-subscribe topics, used for decoupling application components and asynchronous processing of document ingestion events.

**Azure Event Grid** — A serverless event routing service that enables reactive programming by delivering events from Azure services and custom sources to event handlers with at-least-once delivery guarantees.

---

## 4. Security & Compliance

### 4.1 Access Control

**Role-Based Access Control (RBAC)** — An authorization model that assigns permissions based on predefined roles (e.g., Reader, Contributor, Owner) rather than individual user identities, simplifying access management at scale.

**Attribute-Based Access Control (ABAC)** — An authorization model that evaluates access decisions based on attributes of the user, resource, action, and environment (e.g., department, classification level, time of day), providing finer-grained control than RBAC.

**Least Privilege** — A security principle requiring that users, services, and processes are granted only the minimum permissions necessary to perform their intended functions, reducing the blast radius of compromised identities.

**Zero Trust** — A security model that assumes no implicit trust for any user, device, or network, requiring continuous verification of identity, device health, and authorization for every access request regardless of location.

**Defense in Depth** — A layered security strategy that deploys multiple independent security controls (network, identity, application, data) so that the failure of any single layer does not compromise the overall system.

### 4.2 Authentication & Authorization

**OAuth 2.0** — An industry-standard authorization framework that enables third-party applications to obtain limited access to resources on behalf of a user through access tokens issued by an authorization server.

**OpenID Connect (OIDC)** — An identity layer built on top of OAuth 2.0 that provides authentication by allowing clients to verify the identity of an end-user and obtain basic profile information via ID tokens.

**JSON Web Token (JWT)** — A compact, URL-safe token format used to securely transmit claims between parties, consisting of a header, payload, and signature; used in this platform for bearer authentication and user group extraction.

**Mutual TLS (mTLS)** — A security protocol where both the client and server authenticate each other using X.509 certificates during the TLS handshake, ensuring bidirectional identity verification for service-to-service communication.

**Service Principal** — An identity created for applications, hosted services, or automated tools to access Azure resources, configured with specific role assignments and credential management policies.

### 4.3 Encryption & Key Management

**Customer-Managed Key (CMK)** — An encryption key owned and controlled by the customer (stored in Azure Key Vault or HSM) used to encrypt data at rest, providing full control over key lifecycle, rotation, and revocation.

**Hardware Security Module (HSM)** — A dedicated, tamper-resistant hardware device for secure cryptographic key generation, storage, and operations, providing FIPS 140-2 Level 3 certified protection for encryption keys.

**Encryption at Rest** — The protection of stored data using encryption algorithms (AES-256) so that data remains unreadable without the corresponding decryption key, applied to all platform data stores.

**Encryption in Transit** — The protection of data during transmission using TLS 1.2+ to prevent interception or tampering, enforced for all platform API calls and inter-service communication.

### 4.4 Data Protection

**PII (Personally Identifiable Information)** — Any data that can be used to identify a specific individual, including name, email, SSN, phone number, and IP address; detected, classified, and optionally redacted during document ingestion.

**PHI (Protected Health Information)** — Health-related data that is individually identifiable and subject to HIPAA privacy and security rules, including diagnoses, treatment records, and insurance information.

**Data Loss Prevention (DLP)** — A set of tools and policies that detect and prevent unauthorized transmission, sharing, or exposure of sensitive data, enforced at network, endpoint, and application layers.

**Data Classification** — The process of categorizing data by sensitivity level (Public, Internal, Confidential, Restricted) to apply appropriate security controls, retention policies, and access restrictions.

**Data Residency** — The requirement that data be stored and processed within specified geographic boundaries (e.g., country or region) to comply with regulatory requirements such as GDPR or data sovereignty laws.

### 4.5 Compliance Frameworks

**SOC 2 (System and Organization Controls 2)** — An auditing standard developed by AICPA that evaluates an organization's controls related to security, availability, processing integrity, confidentiality, and privacy of customer data.

**ISO 27001** — An international standard for information security management systems (ISMS) that specifies requirements for establishing, implementing, maintaining, and continually improving information security controls.

**ISO/IEC 42001** — An international standard for Artificial Intelligence Management Systems (AIMS) that provides a framework for organizations to manage risks and opportunities associated with AI systems responsibly.

**NIST AI RMF (AI Risk Management Framework)** — A voluntary framework from the National Institute of Standards and Technology that provides guidance for managing risks associated with AI systems across the lifecycle, organized around Govern, Map, Measure, and Manage functions.

**NIST SP 800-53** — A catalog of security and privacy controls published by NIST for federal information systems, widely adopted as a baseline for enterprise security programs.

**GDPR (General Data Protection Regulation)** — The European Union regulation governing the collection, processing, and storage of personal data of EU residents, requiring explicit consent, data minimization, and the right to erasure.

**CCPA (California Consumer Privacy Act)** — A California state law granting consumers rights over their personal information, including the right to know, delete, opt-out of sale, and non-discrimination for exercising privacy rights.

---

## 5. Enterprise & Governance

### 5.1 Maturity & Process

**CMMI (Capability Maturity Model Integration)** — A process improvement framework that defines five maturity levels (Initial, Managed, Defined, Quantitatively Managed, Optimizing) for assessing and improving organizational processes.

**Change Advisory Board (CAB)** — A cross-functional governance body that reviews, evaluates, and approves or rejects proposed changes to production systems, ensuring risk assessment and stakeholder alignment.

**Change Management** — The disciplined process of planning, reviewing, approving, implementing, and documenting changes to production systems to minimize risk and ensure traceability.

**Incident Management** — The process of detecting, responding to, resolving, and learning from production incidents, governed by severity levels, escalation paths, and post-incident review procedures.

**Problem Management** — The process of identifying and resolving the root causes of recurring incidents to prevent future occurrences and improve overall system reliability.

**Post-Incident Review (PIR)** — A structured analysis conducted after incident resolution to identify root causes, contributing factors, timeline of events, and actionable improvement items; also known as a blameless postmortem.

### 5.2 Reliability & SLAs

**SLA (Service Level Agreement)** — A contractual commitment defining the expected level of service (e.g., 99.9% uptime, P95 latency under 3s) between the platform team and its consumers, with defined consequences for breaches.

**SLO (Service Level Objective)** — An internal target for a specific service metric (e.g., 99.95% availability) that is typically stricter than the SLA, providing a buffer before contractual obligations are breached.

**SLI (Service Level Indicator)** — A quantitative measure of a specific aspect of service quality (e.g., request latency, error rate, throughput) used to evaluate whether SLOs and SLAs are being met.

**Error Budget** — The permissible amount of unreliability (1 minus the SLO target) that a service can consume before further changes are frozen; for a 99.9% SLO, the monthly error budget is approximately 43.2 minutes.

**RTO (Recovery Time Objective)** — The maximum acceptable duration from a disruption to service restoration; this platform targets RTO of 4 hours for regional failover and 1 hour for component-level recovery.

**RPO (Recovery Point Objective)** — The maximum acceptable amount of data loss measured in time; this platform targets RPO of 1 hour for transactional data and 24 hours for analytics data.

**MTTR (Mean Time to Recover)** — The average time from incident detection to full service restoration, used as a key reliability metric; this platform targets MTTR under 60 minutes.

**MTTD (Mean Time to Detect)** — The average time from incident occurrence to detection, reflecting the effectiveness of monitoring and alerting; this platform targets MTTD under 5 minutes.

**MTBF (Mean Time Between Failures)** — The average time between consecutive system failures, used to measure overall system reliability and predict maintenance needs.

### 5.3 Deployment & Operations

**Infrastructure as Code (IaC)** — The practice of managing and provisioning infrastructure through machine-readable configuration files (e.g., Terraform, Bicep) rather than manual processes, enabling version control, peer review, and reproducibility.

**CI/CD (Continuous Integration / Continuous Deployment)** — An automated software delivery practice where code changes are continuously built, tested, and deployed through a pipeline, reducing time-to-production and human error.

**GitOps** — An operational framework that uses Git repositories as the single source of truth for declarative infrastructure and application configuration, with automated reconciliation ensuring the live state matches the desired state.

**Blue-Green Deployment** — A release strategy that maintains two identical production environments (blue and green), routing traffic to one while deploying and testing on the other, then switching traffic for zero-downtime releases.

**Canary Deployment** — A release strategy that gradually routes a small percentage of traffic (e.g., 5-10%) to the new version while monitoring key metrics, allowing rollback before full deployment if issues are detected.

**Feature Flag** — A mechanism that enables or disables functionality at runtime without code deployment, allowing controlled rollout, A/B testing, and instant rollback of features across user segments.

**Rolling Deployment** — A release strategy that incrementally updates instances in a service one or a few at a time, maintaining availability throughout the deployment process.

### 5.4 Financial Operations

**FinOps (Financial Operations)** — A practice that brings financial accountability to cloud spending by combining engineering, finance, and business teams to optimize cost efficiency, forecast spending, and allocate costs accurately.

**Cost Allocation** — The process of attributing cloud resource costs to specific teams, projects, or business units through tagging, resource groups, or chargeback models.

**Reserved Instances** — A pricing model offering significant discounts (up to 72%) for committing to a specific resource configuration for a 1- or 3-year term, used for predictable baseline workloads.

**Consumption-Based Pricing** — A pay-per-use pricing model where costs are directly proportional to resource consumption (e.g., tokens processed, queries executed), used for variable workloads.

---

## 6. Domain-Specific Terms

### 6.1 Financial Services

**KYC (Know Your Customer)** — A regulatory process requiring financial institutions to verify the identity, suitability, and risk profile of their customers before and during the business relationship.

**AML (Anti-Money Laundering)** — A set of laws, regulations, and procedures designed to prevent criminals from disguising illegally obtained funds as legitimate income through the financial system.

**CTR (Currency Transaction Report)** — A report filed by financial institutions for cash transactions exceeding $10,000, required under the Bank Secrecy Act to detect and deter money laundering.

**SAR (Suspicious Activity Report)** — A report filed by financial institutions when they detect potentially suspicious transactions that may involve money laundering, fraud, or terrorist financing.

**Basel III** — An international regulatory framework developed by the Basel Committee on Banking Supervision that sets requirements for bank capital adequacy, stress testing, and market liquidity risk.

**PCI-DSS (Payment Card Industry Data Security Standard)** — A set of security requirements for organizations that handle credit card information, covering network security, access control, encryption, and monitoring.

### 6.2 Healthcare & Education

**HIPAA (Health Insurance Portability and Accountability Act)** — A US federal law establishing national standards for the protection of electronic health information, requiring administrative, physical, and technical safeguards.

**FERPA (Family Educational Rights and Privacy Act)** — A US federal law protecting the privacy of student education records, granting parents and eligible students rights to access and control the disclosure of their records.

**HL7 FHIR (Fast Healthcare Interoperability Resources)** — A standard for exchanging healthcare information electronically, providing RESTful APIs and standardized data formats for interoperable health data systems.

### 6.3 Legal & Audit

**SOX (Sarbanes-Oxley Act)** — A US federal law mandating strict financial reporting and internal control requirements for publicly traded companies, requiring audit trails and executive certification of financial statements.

**eDiscovery** — The process of identifying, collecting, preserving, reviewing, and producing electronically stored information (ESI) in response to legal proceedings, regulatory investigations, or litigation.

**Legal Hold** — A directive requiring an organization to preserve all potentially relevant documents and data when litigation or investigation is reasonably anticipated, overriding normal retention and deletion policies.

**Chain of Custody** — The documented chronological record of the seizure, custody, control, transfer, analysis, and disposition of evidence, ensuring its integrity and admissibility in legal proceedings.

**Audit Trail** — A chronological record of system activities that provides evidence of the sequence of events, user actions, and system changes, enabling reconstruction and review for compliance and forensic purposes.

**Data Retention Policy** — A set of rules governing how long different categories of data must be preserved and when they should be disposed of, balancing legal requirements, business needs, and storage costs.

### 6.4 Document Processing

**Document Intelligence** — The AI-powered capability to extract structured data (text, tables, key-value pairs, entities) from unstructured documents such as PDFs, images, and scanned forms.

**OCR (Optical Character Recognition)** — The technology that converts images of text (scanned documents, photos, handwritten notes) into machine-readable text data for processing and indexing.

**Form Recognizer** — The previous name for Azure AI Document Intelligence; a service that uses ML models to extract information from forms, invoices, receipts, and identity documents.

**Document Cracking** — The process of extracting raw text and metadata from various file formats (PDF, DOCX, PPTX, HTML) during the document ingestion pipeline, prior to chunking and embedding.

---

## 7. Platform-Specific Terms

### 7.1 Data Quality & Evaluation

**Golden Dataset** — A curated, human-validated set of question-answer pairs with verified source citations used as the ground truth for evaluating RAG pipeline accuracy, groundedness, and relevance.

**Evaluation Pipeline** — An automated CI/CD-integrated process that runs the golden dataset through the RAG system and computes quality metrics (groundedness >= 0.80, hallucination <= 0.10, relevance >= 0.75) as release gates.

**Groundedness Score** — A metric (0.0-1.0) measuring the degree to which a generated answer is supported by the retrieved source documents, computed via LLM-as-judge evaluation; this platform requires >= 0.80 for production release.

**Relevance Score** — A metric (0.0-1.0) measuring how well the generated response addresses the user's query, considering completeness, specificity, and topic alignment.

**Coherence Score** — A metric (0.0-1.0) measuring the logical consistency, readability, and structural quality of the generated response.

**Fluency Score** — A metric (0.0-1.0) measuring the grammatical correctness, naturalness, and readability of the generated text.

### 7.2 Routing & Optimization

**Model Routing** — The platform's strategy of directing different types of requests to different model deployments based on task complexity (e.g., GPT-4o for RAG generation at temperature 0.1, GPT-4o-mini for query rewriting at temperature 0.3) to optimize cost and quality.

**Semantic Cache** — A caching layer that stores previous query-response pairs and returns cached responses for semantically similar (not just identical) future queries, reducing API calls and latency by checking embedding similarity above a configurable threshold.

**Token Budget** — The maximum number of tokens allocated for a specific scope (platform: 5M/day, per-tenant: variable, per-user: 50K/day, per-session: 10K/day) to control API consumption and costs.

**Context Window Management** — The strategy of allocating the available context window across system prompt, conversation history, retrieved documents, and generation space to maximize response quality within token limits.

**Query Rewriting** — An intermediate processing step where the user's raw query is reformulated by a lightweight model (GPT-4o-mini) to improve retrieval effectiveness by expanding abbreviations, resolving pronouns, and clarifying intent.

### 7.3 Response & Safety

**Citation** — An explicit reference in the generated response to the specific source document and passage from which the information was derived, enabling users to verify the answer against authoritative sources.

**Source Attribution** — The practice of identifying and displaying the origin document, page, section, and confidence level for each claim in a generated response, supporting transparency and trust.

**Content Filter** — A configurable safety layer that screens both input prompts and generated outputs for harmful content categories (hate, violence, sexual, self-harm) and blocks or flags content exceeding severity thresholds.

**System Prompt** — See [Prompt Engineering > System Prompt](#14-prompt-engineering). In this platform context, the system prompt enforces context-only answering, mandatory citations, graceful out-of-scope handling, and PII redaction rules.

**Conversation History** — The sequence of prior user-assistant message pairs maintained within a session, stored in Cosmos DB, and included in subsequent prompts to enable multi-turn contextual dialogue.

**Feedback Loop** — The mechanism by which end-user feedback (thumbs up/down, corrections) is collected, stored, and used to improve retrieval quality, prompt templates, and golden dataset coverage over time.

---

## 8. Acronym Quick Reference

| Acronym | Full Form | Category |
|---------|-----------|----------|
| ABAC | Attribute-Based Access Control | Security |
| ACL | Access Control List | Security |
| ACR | Azure Container Registry | Azure Services |
| AI | Artificial Intelligence | AI/ML |
| AKS | Azure Kubernetes Service | Azure Services |
| AML | Anti-Money Laundering | Domain |
| ANN | Approximate Nearest Neighbor | Search |
| APM | Application Performance Management | Enterprise |
| APIM | Azure API Management | Azure Services |
| BM25 | Best Matching 25 | Search |
| BLEU | Bilingual Evaluation Understudy | AI/ML |
| CAB | Change Advisory Board | Enterprise |
| CCPA | California Consumer Privacy Act | Compliance |
| CDN | Content Delivery Network | Azure Services |
| CI/CD | Continuous Integration / Continuous Deployment | Enterprise |
| CMK | Customer-Managed Key | Security |
| CMMI | Capability Maturity Model Integration | Enterprise |
| CNI | Container Network Interface | Azure Services |
| CoT | Chain-of-Thought | AI/ML |
| CTR | Currency Transaction Report | Domain |
| DLP | Data Loss Prevention | Security |
| DNS | Domain Name System | Networking |
| ESI | Electronically Stored Information | Domain |
| FERPA | Family Educational Rights and Privacy Act | Domain |
| FHIR | Fast Healthcare Interoperability Resources | Domain |
| FIPS | Federal Information Processing Standards | Security |
| FinOps | Financial Operations | Enterprise |
| FQDN | Fully Qualified Domain Name | Networking |
| F1 | F1 Score (Harmonic Mean of Precision & Recall) | AI/ML |
| GDPR | General Data Protection Regulation | Compliance |
| GPT | Generative Pre-trained Transformer | AI/ML |
| HIPAA | Health Insurance Portability and Accountability Act | Domain |
| HL7 | Health Level Seven International | Domain |
| HNSW | Hierarchical Navigable Small World | Search |
| HPA | Horizontal Pod Autoscaler | Azure Services |
| HSM | Hardware Security Module | Security |
| IaC | Infrastructure as Code | Enterprise |
| ISMS | Information Security Management System | Compliance |
| ISO | International Organization for Standardization | Compliance |
| IVF | Inverted File Index | Search |
| JWT | JSON Web Token | Security |
| KEDA | Kubernetes Event-Driven Autoscaling | Azure Services |
| k-NN | k-Nearest Neighbors | Search |
| KQL | Kusto Query Language | Azure Services |
| KYC | Know Your Customer | Domain |
| LLM | Large Language Model | AI/ML |
| LSH | Locality-Sensitive Hashing | Search |
| ML | Machine Learning | AI/ML |
| mTLS | Mutual Transport Layer Security | Security |
| MTBF | Mean Time Between Failures | Enterprise |
| MTTD | Mean Time to Detect | Enterprise |
| MTTR | Mean Time to Recover | Enterprise |
| NER | Named Entity Recognition | AI/ML |
| NIST | National Institute of Standards and Technology | Compliance |
| NLP | Natural Language Processing | AI/ML |
| NSG | Network Security Group | Azure Services |
| OAuth | Open Authorization | Security |
| OCR | Optical Character Recognition | Domain |
| OIDC | OpenID Connect | Security |
| OWASP | Open Web Application Security Project | Security |
| PCI-DSS | Payment Card Industry Data Security Standard | Domain |
| PHI | Protected Health Information | Security |
| PII | Personally Identifiable Information | Security |
| PIR | Post-Incident Review | Enterprise |
| RAG | Retrieval-Augmented Generation | AI/ML |
| RBAC | Role-Based Access Control | Security |
| RLHF | Reinforcement Learning from Human Feedback | AI/ML |
| RPM | Requests Per Minute | Enterprise |
| RPO | Recovery Point Objective | Enterprise |
| RRF | Reciprocal Rank Fusion | Search |
| RTO | Recovery Time Objective | Enterprise |
| ROUGE | Recall-Oriented Understudy for Gisting Evaluation | AI/ML |
| SAR | Suspicious Activity Report | Domain |
| SLA | Service Level Agreement | Enterprise |
| SLI | Service Level Indicator | Enterprise |
| SLO | Service Level Objective | Enterprise |
| SOC | System and Organization Controls | Compliance |
| SOX | Sarbanes-Oxley Act | Domain |
| SSL | Secure Sockets Layer | Security |
| TF-IDF | Term Frequency-Inverse Document Frequency | Search |
| TLS | Transport Layer Security | Security |
| TPM | Tokens Per Minute | AI/ML |
| TTL | Time to Live | Platform |
| VNet | Virtual Network | Azure Services |
| WAF | Web Application Firewall | Azure Services |
| ARM | Azure Resource Manager | Azure Services |
| AUC | Area Under the Curve | AI/ML |
| ROC | Receiver Operating Characteristic | AI/ML |
| AIMS | AI Management System | Compliance |
| RMF | Risk Management Framework | Compliance |
| SPN | Service Principal Name | Security |
| IAM | Identity and Access Management | Security |
| MFA | Multi-Factor Authentication | Security |
| SSO | Single Sign-On | Security |
| SIEM | Security Information and Event Management | Security |
| SOAR | Security Orchestration, Automation and Response | Security |
| ETL | Extract, Transform, Load | Enterprise |
| SRE | Site Reliability Engineering | Enterprise |
| OKR | Objectives and Key Results | Enterprise |
| KPI | Key Performance Indicator | Enterprise |

---

## 9. Consistent Usage Guide

The following table defines the preferred terminology for this platform's documentation. All contributors must use the preferred term in documentation, code comments, API responses, and user-facing content.

| Preferred Term | Deprecated / Incorrect Term(s) | Rationale |
|---------------|-------------------------------|-----------|
| **Azure AI Search** | Cognitive Search, Azure Search, Azure Cognitive Search | Rebranded by Microsoft in November 2023 |
| **Microsoft Entra ID** | Azure AD, Azure Active Directory, AAD | Rebranded by Microsoft in July 2023 |
| **Azure AI Document Intelligence** | Form Recognizer, Azure Form Recognizer | Rebranded by Microsoft in July 2023 |
| **Groundedness** | Grounding score, grounding metric, faithfulness | Platform-standard evaluation term |
| **Hallucination rate** | Fabrication rate, confabulation rate | Industry-standard term for unsupported generation |
| **Embedding** | Vector representation, dense encoding | Preferred short form for documentation |
| **Chunking** | Segmentation, splitting, partitioning | Platform-standard ingestion term |
| **Token budget** | Token limit, token cap, token quota | Platform-standard resource governance term |
| **Model routing** | Model selection, model switching, model dispatch | Platform-standard traffic management term |
| **Semantic cache** | AI cache, embedding cache, smart cache | Platform-standard caching layer term |
| **Golden dataset** | Test dataset, benchmark set, evaluation set | Platform-standard quality assurance term |
| **Content filter** | Safety filter, moderation filter, content moderation | Azure OpenAI standard term |
| **Private endpoint** | Private connection, private access, VNet injection | Azure networking standard term |
| **Managed identity** | Service identity, system identity | Azure identity standard term |
| **Workload Identity** | AAD Pod Identity, Pod Identity, Pod Managed Identity | Successor mechanism for AKS pod authentication |
| **System prompt** | System message, system instruction, preamble | OpenAI API standard term |
| **Context window** | Context length, context size, max tokens | Industry-standard model capacity term |
| **Hybrid search** | Combined search, multi-modal search, fusion search | Azure AI Search standard term |
| **Semantic ranking** | Semantic reranking, L2 ranking, neural ranking | Azure AI Search standard feature name |
| **Evaluation pipeline** | Test pipeline, quality pipeline, validation pipeline | Platform-standard CI/CD quality term |
| **Infrastructure as Code** | Scripted infra, automated provisioning | Industry-standard DevOps term |
| **Blue-green deployment** | A/B deployment, swap deployment | Industry-standard release pattern name |

---

## Document Control

| Field | Value |
|-------|-------|
| **Document Title** | Glossary — Azure OpenAI Enterprise RAG Platform |
| **Version** | 1.0 |
| **Classification** | Internal |
| **Owner** | Platform Team |
| **Last Updated** | 2024-01 |
| **Review Cadence** | Quarterly |
| **Approved By** | Platform Architecture Board |
| **Change Log** | v1.0 — Initial release with 120+ terms across 7 categories |

---

*This glossary is a living document. To propose additions or corrections, submit a pull request to `docs/reference/GLOSSARY.md` with the term, definition, and category. All changes require Platform Team review.*
