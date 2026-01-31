# Data Pipeline by Type — Azure OpenAI Enterprise RAG Platform

> Per-data-type processing pipelines: architecture, Azure service selection, open-source libraries, challenges, and enterprise use cases.

---

## Table of Contents

1. [Text (Plain Text)](#1-text-plain-text)
2. [CSV (Tabular Data)](#2-csv-tabular-data)
3. [PDF Documents](#3-pdf-documents)
4. [Images](#4-images)
5. [Video](#5-video)
6. [Audio](#6-audio)
7. [Log Files](#7-log-files)
8. [Web / HTML](#8-web--html)
9. [Library Comparison Tables](#9-library-comparison-tables)
10. [Enterprise Use Cases by Type](#10-enterprise-use-cases-by-type)

---

## 1. Text (Plain Text)

### Pipeline Flow

```
Plain Text → Tokenize → Chunk → Embed → Index
```

### Architecture Diagram

```
[Text File Upload]
     │
     ▼
[Azure Storage (Data Lake Gen2)]  ← raw/ container
     │
     ▼
[Azure Functions - Ingestion]
     ├── Tokenize (tiktoken / sentence-transformers)
     ├── Chunk (section-aware, 700-1200 tokens)
     ├── Metadata extraction (title, headers, keywords)
     └── PII scan (Presidio)
     │
     ▼
[Azure OpenAI - Embedding]  ← text-embedding-3-large (3072d)
     │
     ▼
[Azure AI Search - Index]  ← HNSW + BM25 hybrid index
```

### Azure Service Selection

| Stage | Service | SKU | Purpose |
|-------|---------|-----|---------|
| Storage | Data Lake Gen2 | Standard | Raw file storage |
| Processing | Azure Functions | Premium EP1 | Tokenization, chunking |
| Embedding | Azure OpenAI | Standard S0 | text-embedding-3-large |
| Indexing | Azure AI Search | Standard S2 | HNSW vector + BM25 |

### Open-Source Libraries

| Library | Purpose | Version |
|---------|---------|---------|
| tiktoken | Token counting | 0.5+ |
| langchain.text_splitter | Chunking strategies | 0.1+ |
| spaCy | NLP preprocessing (sentence segmentation) | 3.6+ |
| presidio-analyzer | PII detection | 2.2+ |
| nltk | Tokenization fallback | 3.8+ |

### Chunking Strategy

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,        # ~700-1200 tokens
    chunk_overlap=100,      # 100 token overlap
    separators=["\n\n", "\n", ". ", " ", ""],
    length_function=tiktoken_len,  # Token-based length
)
chunks = splitter.split_text(document_text)
```

### Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| Encoding detection (UTF-8, Latin-1, etc.) | `chardet` library for auto-detection, fallback to UTF-8 |
| Very long documents (>1MB text) | Stream processing, chunk in batches |
| No structure (no headings) | Sentence-based chunking with overlap |
| Mixed languages | Language detection per chunk, multi-language embeddings |

### Limitations

- No structural hierarchy in plain text — rely on paragraph breaks
- Token counting varies by model — use tiktoken with correct encoding
- Large overlap increases storage cost — balance quality vs cost

---

## 2. CSV (Tabular Data)

### Pipeline Flow

```
CSV → Parse → Validate → Tabular-to-Text → Chunk → Embed → Index
```

### Architecture Diagram

```
[CSV File Upload]
     │
     ▼
[Azure Storage (Data Lake Gen2)]
     │
     ▼
[Azure Functions - Ingestion]
     ├── Parse (pandas / csv module)
     ├── Schema validation (data types, required columns)
     ├── Data quality checks (nulls, duplicates, outliers)
     ├── Tabular-to-text conversion
     │     ├── Row-level: "Column1: Value1, Column2: Value2"
     │     ├── Group-level: Aggregate rows by key column
     │     └── Summary-level: Statistical summary per column
     ├── Chunk (row-groups, 300-600 tokens)
     └── Metadata (column names, row count, source)
     │
     ▼
[Azure OpenAI - Embedding]
     │
     ▼
[Azure AI Search - Index]
```

### Open-Source Libraries

| Library | Purpose | Version |
|---------|---------|---------|
| pandas | CSV parsing, validation, transformation | 2.0+ |
| csvkit | Advanced CSV operations | 1.1+ |
| great_expectations | Data quality validation | 0.17+ |
| tabulate | Table formatting for text conversion | 0.9+ |

### Tabular-to-Text Conversion

```python
def csv_to_text_chunks(df, key_column=None, chunk_rows=20):
    """Convert CSV rows to searchable text chunks."""
    chunks = []

    if key_column:
        # Group by key column for contextual chunks
        for key, group in df.groupby(key_column):
            text = f"{key_column}: {key}\n"
            for _, row in group.iterrows():
                text += " | ".join(f"{col}: {val}" for col, val in row.items()) + "\n"
            chunks.append(text)
    else:
        # Fixed-size row groups
        for i in range(0, len(df), chunk_rows):
            batch = df.iloc[i:i+chunk_rows]
            header = " | ".join(batch.columns)
            rows = "\n".join(
                " | ".join(str(val) for val in row)
                for _, row in batch.iterrows()
            )
            chunks.append(f"{header}\n{rows}")

    return chunks
```

### Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| Large CSV files (>100MB) | Streaming read with `chunksize` parameter in pandas |
| Inconsistent schemas | Schema validation before processing, reject malformed |
| Numeric data loses context | Include column headers in every chunk |
| Multi-sheet Excel masquerading as CSV | Detect and reject, prompt re-upload as XLSX |
| Special characters in values | UTF-8 normalization, escape handling |

### Limitations

- Tabular-to-text conversion increases token count ~3x
- Row relationships (foreign keys) are lost in chunking
- Very wide tables (50+ columns) produce verbose text chunks
- Workaround: Select key columns, summarize others

---

## 3. PDF Documents

### Pipeline Flow

```
PDF → OCR → Layout → Structure → Heading-Aware Chunk → Embed → Index
```

### Architecture Diagram

```
[PDF File Upload]
     │
     ▼
[Azure Storage (Data Lake Gen2)]
     │
     ▼
[Azure Functions - Ingestion]
     ├── File analysis (native vs scanned, encrypted check)
     │
     ├── [Native PDF]                    [Scanned PDF]
     │     │                                │
     │     ▼                                ▼
     │   [PyPDF2 / pdfplumber]    [Azure Document Intelligence]
     │   Text extraction            ├── Prebuilt-read (OCR)
     │                              └── Layout model (tables, structure)
     │
     ├── Layout analysis (headings, paragraphs, tables, images)
     ├── Structure extraction (TOC, sections, page numbers)
     ├── Heading-aware chunking
     │     ├── Policies/SOPs: 700-1200 tokens
     │     ├── Contracts: 400-800 tokens
     │     ├── Manuals: 800-1500 tokens
     │     └── Scanned: 500-900 tokens
     ├── Table extraction → tabular-to-text
     ├── Image extraction → Azure Vision API
     └── PII scan (Presidio)
     │
     ▼
[Azure OpenAI - Embedding]
     │
     ▼
[Azure AI Search - Index]
```

### Azure Service Selection

| Stage | Service | Purpose |
|-------|---------|---------|
| OCR | Azure Document Intelligence (prebuilt-read) | Scanned PDF text extraction |
| Layout | Azure Document Intelligence (layout model) | Table, heading, structure detection |
| Image extraction | Azure Computer Vision | Describe embedded images |
| Processing | Azure Functions (Durable) | Long-running PDF processing |

### Open-Source Libraries

| Library | Purpose | When to Use |
|---------|---------|------------|
| PyPDF2 | Native PDF text extraction | Digital PDFs (fast, free) |
| pdfplumber | Table extraction, layout | Digital PDFs with tables |
| pdf2image | PDF to image conversion | Pre-OCR conversion |
| Tesseract (pytesseract) | Open-source OCR | Fallback for Doc Intelligence |
| camelot | Table extraction | Complex table structures |
| fitz (PyMuPDF) | Advanced PDF manipulation | Multi-column, embedded objects |

### Chunking by Document Type

| Document Type | Chunk Size | Overlap | Strategy |
|---------------|-----------|---------|----------|
| HR Policies & SOPs | 700–1200 tokens | 100 | Section/heading-aware |
| Legal Contracts | 400–800 tokens | 50 | Clause-level splitting |
| Technical Manuals | 800–1500 tokens | 150 | Heading-hierarchy aware |
| Scanned PDFs | 500–900 tokens | 75 | OCR + layout-aware |
| Financial Reports | 600–1000 tokens | 100 | Table-aware + narrative |

### Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| Scanned PDF quality varies | Confidence threshold (0.70), manual review queue |
| Multi-column layouts | Document Intelligence layout model with reading-order detection |
| Encrypted PDFs | Detect via header analysis, reject with instructions |
| Large PDFs (>100 pages) | Fan-out: 20-page batches in parallel Azure Functions |
| Embedded images with text | Extract images → Computer Vision → add as text chunks |
| Watermarks interfere with OCR | Pre-processing: image filtering before OCR |
| Mixed orientation pages | Auto-detect orientation via Document Intelligence |
| PDF forms (fillable) | Extract form field values + labels as key-value text |

### Limitations

- Document Intelligence OCR: $0.01/page (cost at scale)
- Handwritten text: lower accuracy (~70% vs 95% for printed)
- Complex mathematical formulas: OCR may fail — use LaTeX extraction
- Workaround: Flag complex pages for manual review

---

## 4. Images

### Pipeline Flow

```
Image → OCR/Vision → Description → Text → Embed → Index
```

### Architecture Diagram

```
[Image File Upload] (JPG, PNG, TIFF, BMP)
     │
     ▼
[Azure Storage (Data Lake Gen2)]
     │
     ▼
[Azure Functions - Ingestion]
     ├── Image classification (photo vs diagram vs screenshot vs document)
     │
     ├── [Document Image]           [Photo/Diagram]
     │     │                             │
     │     ▼                             ▼
     │   [Azure Document Intelligence] [Azure Computer Vision]
     │   OCR text extraction            ├── Image analysis (tags, objects)
     │                                  ├── Dense captions
     │                                  └── Description generation
     │
     ├── [GPT-4o Vision] (optional)
     │     └── Detailed image understanding for complex diagrams
     │
     ├── Text output assembly
     ├── Chunk (if text is long)
     └── Metadata (image dimensions, format, EXIF)
     │
     ▼
[Azure OpenAI - Embedding]
     │
     ▼
[Azure AI Search - Index]
```

### Azure Service Selection

| Stage | Service | Purpose |
|-------|---------|---------|
| OCR | Azure Document Intelligence | Text from document images |
| Vision | Azure Computer Vision 4.0 | Image analysis, captions, tags |
| Advanced understanding | Azure OpenAI GPT-4o (vision) | Complex diagram interpretation |

### Open-Source Libraries

| Library | Purpose | When to Use |
|---------|---------|------------|
| Pillow (PIL) | Image preprocessing | Resize, format conversion |
| pytesseract | Open-source OCR | Fallback for Document Intelligence |
| OpenCV | Image preprocessing | Denoising, deskewing, contrast |
| CLIP (openai/clip) | Image-text similarity | Image search without OCR |

### Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| Low-resolution images | Upscale with Pillow before OCR |
| Handwritten text in images | Document Intelligence with handwriting mode |
| Complex diagrams (architecture, flowcharts) | GPT-4o Vision for semantic description |
| Screenshots with UI elements | Combine OCR + layout analysis |
| EXIF metadata with PII (GPS, camera info) | Strip EXIF before storage |
| Large image files (>20MB) | Resize to max 4096px before processing |

### Limitations

- GPT-4o Vision: higher cost per image (~$0.01-$0.05 per image)
- OCR accuracy drops with handwriting, unusual fonts
- Diagrams require semantic interpretation, not just text extraction
- Color-coded information lost in text conversion

---

## 5. Video

### Pipeline Flow

```
Video → Speech-to-Text → Diarization → Caption → Chunk → Embed → Index
```

### Architecture Diagram

```
[Video File Upload] (MP4, AVI, MOV, WebM)
     │
     ▼
[Azure Storage (Data Lake Gen2)]
     │
     ▼
[Azure Functions - Ingestion (Durable)]
     ├── Audio extraction (ffmpeg)
     ├── Frame extraction (key frames for visual content)
     │
     ├── [Audio Track]                    [Key Frames]
     │     │                                │
     │     ▼                                ▼
     │   [Azure Speech Service]    [Azure Computer Vision]
     │   ├── Speech-to-text             ├── Frame analysis
     │   ├── Speaker diarization        └── Description per frame
     │   └── Timestamp alignment
     │
     ├── Caption generation (merge audio + visual descriptions)
     ├── Transcript assembly with timestamps and speakers
     ├── Chunk (by topic segment, 2-5 minute chunks)
     └── Metadata (duration, speakers, language)
     │
     ▼
[Azure OpenAI - Embedding]
     │
     ▼
[Azure AI Search - Index]
```

### Azure Service Selection

| Stage | Service | Purpose |
|-------|---------|---------|
| Audio extraction | Azure Functions + ffmpeg | Extract audio track from video |
| Speech-to-text | Azure Speech Service (batch) | Transcription with timestamps |
| Diarization | Azure Speech Service | Speaker identification |
| Visual analysis | Azure Computer Vision | Key frame descriptions |
| Caption merge | Azure Functions | Combine audio + visual |

### Open-Source Libraries

| Library | Purpose | When to Use |
|---------|---------|------------|
| ffmpeg (ffmpeg-python) | Audio/video processing | Audio extraction, format conversion |
| moviepy | Video editing | Key frame extraction |
| Whisper (OpenAI) | Open-source speech-to-text | Fallback / development |
| pyannote.audio | Speaker diarization | Open-source alternative |
| webvtt-py | Caption file parsing | Process existing subtitle files |

### Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| Large video files (>1GB) | Streaming processing, extract audio only if visual not needed |
| Multiple speakers | Azure Speech Service diarization, label speakers |
| Background noise | Audio preprocessing with noise reduction |
| Non-English speech | Multi-language Speech Service models |
| Long videos (>1 hour) | Segment into 5-minute chunks for parallel processing |
| Visual-only content (no speech) | Key frame extraction + Computer Vision descriptions |

### Limitations

- Speech-to-text accuracy: ~85-95% depending on audio quality
- Diarization: max 36 speakers, accuracy ~90% for 2-4 speakers
- Video processing is compute-intensive — use Durable Functions
- Real-time processing not supported — batch only
- Cost: $1/hour of audio (Speech Service) + compute

---

## 6. Audio

### Pipeline Flow

```
Audio → Speech-to-Text → Transcript → Chunk → Embed → Index
```

### Architecture Diagram

```
[Audio File Upload] (WAV, MP3, FLAC, OGG, M4A)
     │
     ▼
[Azure Storage (Data Lake Gen2)]
     │
     ▼
[Azure Functions - Ingestion]
     ├── Format detection and conversion (to WAV if needed)
     ├── Audio quality assessment
     │
     ▼
[Azure Speech Service]
     ├── Batch transcription API
     ├── Language detection (auto)
     ├── Speaker diarization (optional)
     ├── Punctuation restoration
     └── Timestamp alignment
     │
     ▼
[Azure Functions - Post-processing]
     ├── Transcript cleanup
     ├── Speaker labeling
     ├── Topic segmentation
     ├── Chunk (by topic or time segment, 2-5 min)
     ├── PII scan (names, account numbers in speech)
     └── Metadata (duration, language, speakers, quality score)
     │
     ▼
[Azure OpenAI - Embedding]
     │
     ▼
[Azure AI Search - Index]
```

### Open-Source Libraries

| Library | Purpose | When to Use |
|---------|---------|------------|
| pydub | Audio format conversion | Pre-processing |
| Whisper (OpenAI) | Open-source transcription | Development, offline |
| librosa | Audio analysis | Quality assessment, features |
| noisereduce | Noise reduction | Pre-processing noisy audio |
| soundfile | Audio I/O | Read/write audio files |

### Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| Poor audio quality (phone recordings) | Noise reduction + lower confidence threshold |
| Accents and dialects | Custom speech models (Azure Custom Speech) |
| Technical jargon | Custom vocabulary list for Speech Service |
| Overlapping speakers | Diarization + channel separation if stereo |
| Very long recordings (>4 hours) | Batch API with segmentation |

### Limitations

- Batch transcription: 5-minute SLA for short files, proportional for longer
- Custom Speech models require training data (50+ hours)
- Real-time transcription available but at higher cost
- Accuracy drops below 80% for very noisy environments

---

## 7. Log Files

### Pipeline Flow

```
Log File → Parse → Structure → Filter → Chunk → Embed → Index
```

### Architecture Diagram

```
[Log File Upload / Stream] (txt, json, csv, syslog)
     │
     ▼
[Azure Storage (Data Lake Gen2)] or [Azure Event Hub] (streaming)
     │
     ▼
[Azure Functions - Ingestion]
     ├── Format detection (JSON, CSV, syslog, custom)
     ├── Parse (regex for unstructured, JSON parser for structured)
     ├── Structure extraction
     │     ├── Timestamp
     │     ├── Log level (ERROR, WARN, INFO, DEBUG)
     │     ├── Source (service, host, function)
     │     └── Message
     ├── Filter (exclude DEBUG/TRACE, keep ERROR/WARN/INFO)
     ├── Pattern recognition (group related entries)
     ├── Chunk (by time window or error group, 50-200 entries)
     └── Metadata (time range, severity distribution, source)
     │
     ▼
[Azure OpenAI - Embedding]
     │
     ▼
[Azure AI Search - Index]
```

### Open-Source Libraries

| Library | Purpose | When to Use |
|---------|---------|------------|
| loguru | Structured logging | Application-side |
| python-dateutil | Timestamp parsing | Multi-format timestamps |
| grok (pygrok) | Log pattern matching | Unstructured log parsing |
| regex | Advanced pattern matching | Custom log formats |
| drain3 | Log template mining | Auto-discover log patterns |

### Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| Unknown log format | Auto-detect with drain3, fall back to line-by-line |
| Multi-line log entries (stack traces) | Regex pattern for continuation lines |
| High volume (millions of entries) | Filter by severity, sample, aggregate |
| Timestamps in various formats | python-dateutil with auto-detection |
| PII in log messages | Presidio scan on message field |

### Limitations

- Log files can be very large — filter and sample before processing
- Context between log entries (causation) is hard to capture in chunks
- Debug/trace logs add noise without search value
- Time-series nature doesn't map well to embedding search

---

## 8. Web / HTML

### Pipeline Flow

```
Web Page → Crawl → Clean → Extract → Chunk → Embed → Index
```

### Architecture Diagram

```
[URL / HTML File]
     │
     ▼
[Azure Functions - Ingestion]
     ├── Fetch / crawl (httpx + robots.txt compliance)
     ├── HTML parsing (BeautifulSoup)
     ├── Clean (remove nav, footer, ads, scripts, styles)
     ├── Content extraction
     │     ├── Main content identification (readability algorithm)
     │     ├── Heading structure (h1-h6)
     │     ├── Table extraction
     │     ├── Link extraction
     │     └── Image alt text extraction
     ├── Markdown conversion (html2text)
     ├── Chunk (heading-aware, 700-1200 tokens)
     └── Metadata (URL, title, last-modified, author)
     │
     ▼
[Azure Storage (Data Lake Gen2)]  ← processed/ container
     │
     ▼
[Azure OpenAI - Embedding]
     │
     ▼
[Azure AI Search - Index]
```

### Open-Source Libraries

| Library | Purpose | When to Use |
|---------|---------|------------|
| BeautifulSoup4 | HTML parsing | All HTML processing |
| html2text | HTML to Markdown | Content cleanup |
| readability-lxml | Main content extraction | Noisy web pages |
| httpx | HTTP client | URL fetching |
| Scrapy | Web crawling framework | Large-scale crawling |
| trafilatura | Web content extraction | Article/blog extraction |

### Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| JavaScript-rendered content | Playwright/Selenium for dynamic pages |
| Rate limiting by source site | Respectful crawling, delays, robots.txt |
| Content behind authentication | Use API or authenticated session |
| Duplicate content across pages | Content hash deduplication |
| Navigation/boilerplate text | Readability algorithm, DOM analysis |
| Dynamic content (SPA) | Headless browser rendering |

### Limitations

- JavaScript rendering requires headless browser (heavy compute)
- Copyright/licensing issues with web content
- Frequent content changes require re-crawling schedule
- Deeply nested content may lose structural context

---

## 9. Library Comparison Tables

### 9.1 OCR / Document Processing

| Feature | Azure Document Intelligence | Tesseract (Open Source) | Google Document AI |
|---------|---------------------------|----------------------|-------------------|
| Accuracy (printed) | 95–99% | 85–95% | 95–99% |
| Accuracy (handwritten) | 70–85% | 50–70% | 75–90% |
| Layout detection | ✅ Excellent | ⚠️ Basic | ✅ Excellent |
| Table extraction | ✅ Native | ❌ Limited | ✅ Native |
| Language support | 300+ | 100+ | 200+ |
| Cost | $0.01/page | Free | $0.01/page |
| Latency | 2–5s/page | 1–3s/page | 2–5s/page |
| **Recommendation** | **Production** | **Dev/Fallback** | Alternative cloud |

### 9.2 Speech-to-Text

| Feature | Azure Speech Service | OpenAI Whisper | Google Speech-to-Text |
|---------|---------------------|---------------|---------------------|
| Accuracy | 90–95% | 85–95% | 90–95% |
| Diarization | ✅ Up to 36 speakers | ❌ External needed | ✅ Up to 6 speakers |
| Real-time | ✅ Streaming | ❌ Batch only | ✅ Streaming |
| Custom vocabulary | ✅ Custom Speech | ❌ | ✅ Custom models |
| Languages | 100+ | 97+ | 125+ |
| Cost | $1/hour | Free (self-hosted) | $0.96/hour |
| **Recommendation** | **Production** | **Dev/Offline** | Alternative cloud |

### 9.3 Text Chunking

| Feature | LangChain Splitters | LlamaIndex | Custom (tiktoken) |
|---------|-------------------|------------|-------------------|
| Token-aware | ✅ | ✅ | ✅ |
| Heading-aware | ✅ MarkdownSplitter | ✅ NodeParser | Manual implementation |
| Semantic chunking | ⚠️ Experimental | ✅ | Manual implementation |
| Table handling | ❌ | ⚠️ Basic | Manual implementation |
| Customizability | Medium | High | Full control |
| **Recommendation** | **Primary** | Alternative | **Custom edge cases** |

### 9.4 PII Detection

| Feature | Presidio | spaCy NER | Azure Content Safety | Regex |
|---------|----------|-----------|---------------------|-------|
| SSN detection | ✅ | ❌ | ⚠️ Limited | ✅ |
| Name detection | ✅ | ✅ | ❌ | ❌ |
| Email detection | ✅ | ⚠️ | ❌ | ✅ |
| Credit card | ✅ | ❌ | ⚠️ | ✅ |
| Custom entities | ✅ | ✅ | ❌ | ✅ |
| Context-aware | ✅ | ✅ | ❌ | ❌ |
| **Recommendation** | **Primary** | **Supplement** | **Harmful content** | **Structured PII** |

### 9.5 Embedding Generation

| Feature | Azure OpenAI (text-embedding-3-large) | Sentence-Transformers | Cohere Embed |
|---------|---------------------------------------|---------------------|-------------|
| Dimensions | 3072 | 384–1024 | 1024 |
| Quality (MTEB) | Top tier | Good (model-dependent) | Top tier |
| Latency | 50ms | 10–30ms (local) | 50ms |
| Cost | $0.00013/1K tokens | Free (self-hosted) | $0.0001/1K tokens |
| Azure integration | ✅ Native | Manual | Manual |
| **Recommendation** | **Production** | **Dev/Offline** | Alternative |

---

## 10. Enterprise Use Cases by Type

### 10.1 Text Use Cases

| Use Case | Industry | Example |
|----------|----------|---------|
| Policy search | All | Employee handbook, compliance policies |
| Knowledge base | All | FAQ, internal wiki, troubleshooting guides |
| Email archival | Financial | Regulatory email retention and search |
| Code documentation | Technology | API docs, README files, design docs |

### 10.2 CSV Use Cases

| Use Case | Industry | Example |
|----------|----------|---------|
| Financial reporting | Banking | Transaction summaries, P&L data |
| Employee data | HR | Headcount reports, benefits enrollment |
| Inventory management | Retail | Stock levels, supplier data |
| Survey analysis | All | Employee satisfaction, customer feedback |

### 10.3 PDF Use Cases

| Use Case | Industry | Example |
|----------|----------|---------|
| Contract analysis | Legal | NDA review, clause extraction |
| Invoice processing | Finance | Automated invoice data extraction |
| Regulatory filings | Banking | Basel III reports, audit documents |
| Medical records | Healthcare | Patient reports, lab results |
| Insurance claims | Insurance | Claim forms, policy documents |
| Engineering specs | Manufacturing | Technical drawings, specifications |

### 10.4 Image Use Cases

| Use Case | Industry | Example |
|----------|----------|---------|
| Architecture diagrams | Technology | System design, network topology |
| ID verification | Banking | KYC document verification |
| Damage assessment | Insurance | Photo evidence for claims |
| Medical imaging | Healthcare | X-ray reports, pathology slides |
| Whiteboard capture | All | Meeting notes, brainstorming |

### 10.5 Video Use Cases

| Use Case | Industry | Example |
|----------|----------|---------|
| Training recordings | All | Onboarding videos, compliance training |
| Meeting recordings | All | Teams/Zoom meeting search |
| Security footage | Retail/Banking | Incident review, compliance |
| Product demos | Technology | Customer-facing demo library |
| Depositions | Legal | Legal testimony search |

### 10.6 Audio Use Cases

| Use Case | Industry | Example |
|----------|----------|---------|
| Call center recordings | All | Customer service quality, compliance |
| Earnings calls | Finance | Investor relations, analysis |
| Podcast/webinar | All | Internal knowledge sharing |
| Voicemail | All | Searchable voicemail archive |
| Dictation | Healthcare/Legal | Doctor notes, legal dictation |

### 10.7 Log File Use Cases

| Use Case | Industry | Example |
|----------|----------|---------|
| Incident investigation | Technology | Root cause analysis from logs |
| Compliance audit | Banking | Transaction log review |
| Security analysis | All | Threat detection, forensics |
| Performance analysis | Technology | Bottleneck identification |
| System monitoring | All | Proactive issue detection |

### 10.8 Web/HTML Use Cases

| Use Case | Industry | Example |
|----------|----------|---------|
| Competitive intelligence | All | Competitor website monitoring |
| Regulatory updates | Banking/Legal | Government regulation changes |
| Product documentation | Technology | External API docs, release notes |
| News monitoring | All | Industry news, press releases |
| Internal portals | All | SharePoint, Confluence, wiki |

---

## Cross-References

- [EDGE-CASES-DATA-TYPES.md](./EDGE-CASES-DATA-TYPES.md) — Edge cases per data type
- [TECH-STACK-SERVICES.md](./TECH-STACK-SERVICES.md) — Azure services inventory
- [AZURE-SERVICE-DEEP-DIVE.md](./AZURE-SERVICE-DEEP-DIVE.md) — Service operational guide
- [TESTING-STRATEGY.md](../testing/TESTING-STRATEGY.md) — Testing per pipeline stage
- [SECURITY-LAYERS.md](../security/SECURITY-LAYERS.md) — PII handling in pipelines
- [LLD-ARCHITECTURE.md](../../azurecloud/docs/LLD-ARCHITECTURE.md) — Chunking strategy details
