# Edge Cases by Data Type & Use Case

> **Comprehensive Edge Case Analysis for Azure OpenAI Enterprise Platform**
>
> Document Types | Output Relevancy | PII | Security | B2C | B2B

---

## Table of Contents

1. [PDF Edge Cases](#pdf-edge-cases)
2. [Word Document Edge Cases](#word-document-edge-cases)
3. [Excel Edge Cases](#excel-edge-cases)
4. [Image Edge Cases](#image-edge-cases)
5. [Video Edge Cases](#video-edge-cases)
6. [CSV Edge Cases](#csv-edge-cases)
7. [Log File Edge Cases](#log-file-edge-cases)
8. [Web Page Edge Cases](#web-page-edge-cases)
9. [Output Text Relevancy Controls](#output-text-relevancy-controls)
10. [PII Edge Cases](#pii-edge-cases)
11. [Security & Compliance Edge Cases](#security--compliance-edge-cases)
12. [B2C-Specific Edge Cases](#b2c-specific-edge-cases)
13. [B2B-Specific Edge Cases](#b2b-specific-edge-cases)

---

## PDF Edge Cases

| Edge Case | Problem | Detection | Solution | Fallback |
|-----------|---------|-----------|----------|----------|
| **Scanned PDF (image-only)** | No extractable text | Page text length = 0 | Azure Document Intelligence OCR | Flag as "OCR-processed" with confidence score |
| **Encrypted/password-protected** | Cannot read content | Parse error: encrypted | Reject with message "Password-protected PDF not supported" | Queue for manual processing |
| **Multi-column layout** | Text extraction in wrong order | Layout analysis detects columns | Document Intelligence layout model | Fall back to read model with column reordering |
| **Large PDF (>100 pages)** | Processing timeout, memory | Page count check on upload | Split into 50-page batches, process in parallel | Process first 100 pages, warn user |
| **PDF forms (AcroForms)** | Form fields not in text layer | Form field detection | Extract form fields separately, merge with text | Treat as image-based PDF |
| **PDF with embedded fonts** | Character encoding issues | Garbled text detection (entropy check) | OCR fallback on garbled pages | Flag for manual review |
| **PDF/A (archival)** | Different structure than standard | MIME type detection | Standard processing (compatible) | N/A |
| **Rotated pages** | OCR misalignment | Orientation detection | Auto-rotate before OCR | Manual rotation flag |
| **Mixed text + image pages** | Partial text extraction | Compare OCR vs text layer | Hybrid: text layer + OCR for image areas | OCR entire page |
| **Corrupted PDF** | Parse failure | Try-catch on open | Reject with error message | Queue for manual recovery |

### PDF Processing Pipeline

```
PDF Upload
    │
    ├── Check: File valid? → No → Reject (corrupted)
    ├── Check: Encrypted? → Yes → Reject (manual queue)
    ├── Check: Page count > 100? → Yes → Split into batches
    │
    ▼
Document Intelligence
    │
    ├── Layout model (structure extraction)
    ├── OCR (scanned pages)
    ├── Table extraction
    └── Form field extraction
    │
    ▼
Quality Check
    │
    ├── Text length > min threshold?
    ├── OCR confidence > 0.70?
    ├── Encoding valid (UTF-8)?
    └── No garbled text?
    │
    ▼
Chunk + Index (or flag for manual review)
```

---

## Word Document Edge Cases

| Edge Case | Problem | Detection | Solution | Fallback |
|-----------|---------|-----------|----------|----------|
| **Macros (VBA)** | Security risk, not extractable text | File extension .docm, VBA project detected | Strip macros, extract text only | Reject .docm files |
| **Tracked changes** | Multiple versions of text | Revision marks detected | Accept all changes, extract final text | Process both original and revised |
| **Embedded objects (OLE)** | Charts, Excel sheets, images in doc | Object detection in OOXML | Extract embedded objects separately | Skip embedded objects, process text only |
| **Templates (.dotx)** | Placeholder text, merge fields | Template markers detected | Skip template placeholders | Reject templates |
| **Legacy format (.doc)** | Binary format, harder to parse | File extension check | Convert to .docx first (LibreOffice) | Document Intelligence extraction |
| **Headers/footers** | Repeated across pages, pollute chunks | Repeated text pattern detection | Remove headers/footers before chunking | Include but de-duplicate |
| **Table of contents** | Auto-generated, not useful for RAG | TOC markers in OOXML | Skip TOC sections | Include but lower relevance weight |
| **Comments/annotations** | May contain sensitive review notes | Comment nodes in OOXML | Strip comments (configurable: include for B2E) | Always strip |
| **Large images in doc** | Processing timeout | Image size check | Extract and OCR images separately | Skip images over 10MB |
| **Corrupted OOXML** | Parse failure | XML parse error | Try Document Intelligence as fallback | Reject with error |

---

## Excel Edge Cases

| Edge Case | Problem | Detection | Solution | Fallback |
|-----------|---------|-----------|----------|----------|
| **Formulas (not values)** | Extract formulas instead of results | Cell type detection | Extract calculated values, not formula text | Flag cells with formulas |
| **Pivot tables** | Complex aggregated views | Pivot table detection in XML | Flatten pivot data to tabular format | Extract source data instead |
| **Charts** | Visual data not in text | Chart objects in OOXML | Extract chart data series as text/table | Skip charts, note "chart present" |
| **Multi-sheet workbooks** | Which sheets to process? | Sheet count > 1 | Process all sheets, tag chunks by sheet name | Process only first sheet |
| **Large files (>1M rows)** | Memory overflow | Row count check | Stream processing (chunked reads) | Process first 100K rows, warn |
| **Merged cells** | Broken table structure | Merged cell detection | Unmerge and duplicate values | Process as-is with warnings |
| **Hidden sheets/columns** | May contain sensitive data | Hidden attribute check | Include hidden data (B2E) or skip (B2C) | Always skip hidden |
| **Named ranges** | Structured references | Name manager analysis | Include named range context | Ignore, process raw cells |
| **Data validation lists** | Dropdown values not visible | Data validation detection | Extract validation lists as metadata | Skip |
| **Conditional formatting** | Visual meaning lost in text | Format rule detection | Add textual description of rules | Skip formatting context |
| **External links** | Broken references | External ref detection | Resolve or flag broken links | Skip external references |

---

## Image Edge Cases

| Edge Case | Problem | Detection | Solution | Fallback |
|-----------|---------|-----------|----------|----------|
| **Low resolution (<150 DPI)** | Poor OCR accuracy | DPI metadata check | Upscale with interpolation before OCR | Flag low-confidence result |
| **Handwritten text** | Standard OCR fails | Handwriting detection model | Azure Document Intelligence handwriting model | Flag for manual transcription |
| **Multi-language text** | Wrong language model used | Language detection on image | Multi-language OCR pipeline | Default to English, flag |
| **Rotated/skewed** | Misaligned OCR | Orientation detection | Auto-deskew before OCR | Manual rotation flag |
| **Photographs of documents** | Perspective distortion, shadows | Image quality analysis | Perspective correction, contrast enhancement | Document Intelligence with prebuilt-read |
| **Diagrams/flowcharts** | Visual meaning not in text | Image classification | Describe diagram with GPT-4o Vision | Tag as "diagram" with alt-text |
| **Screenshots** | Mixed UI elements + text | UI element detection | OCR with layout analysis | Standard OCR |
| **Watermarked** | Watermark interferes with OCR | Watermark pattern detection | Image preprocessing to remove watermark | OCR with lower confidence |
| **Transparent backgrounds** | OCR issues with PNG transparency | Alpha channel detection | Flatten to white background | Standard processing |
| **Very large images (>50MP)** | Memory overflow | Resolution check | Downsample to 10MP before processing | Reject with size warning |

---

## Video Edge Cases

| Edge Case | Problem | Detection | Solution | Fallback |
|-----------|---------|-----------|----------|----------|
| **No captions/subtitles** | No text to extract | Subtitle track check | Azure Speech-to-Text transcription | Reject or flag for manual transcription |
| **Multiple speakers** | Unclear attribution | Speaker count detection | Speaker diarization (Azure Speech) | Transcribe without attribution |
| **Background noise** | Poor transcription quality | Audio SNR analysis | Noise reduction preprocessing | Lower confidence flag |
| **Non-English audio** | Wrong language model | Language identification | Multi-language Speech-to-Text | Default English, flag |
| **Long videos (>2 hours)** | Processing time, cost | Duration check | Segment into 30-min chunks | Process first 30 min, warn |
| **Multiple audio tracks** | Which track to process | Audio track enumeration | Process primary audio track | Process all tracks separately |
| **Screen recordings** | Text in video frames | Frame analysis | OCR key frames at intervals | Speech-to-Text only |
| **Music/jingles** | Non-speech audio segments | Audio classification | Skip non-speech segments | Include with "non-speech" label |

---

## CSV Edge Cases

| Edge Case | Problem | Detection | Solution | Fallback |
|-----------|---------|-----------|----------|----------|
| **Encoding issues (non-UTF-8)** | Garbled characters | chardet encoding detection | Auto-detect and convert to UTF-8 | Try common encodings (Latin-1, CP1252) |
| **Malformed CSV** | Inconsistent column count | Row length validation | Best-effort parsing, skip bad rows | Reject with row-level error report |
| **Large files (>1GB)** | Memory overflow | File size check | Stream processing (pandas chunked) | Process first 100MB, warn |
| **Mixed data types in columns** | Type inference failures | Column type analysis | Keep as string, infer per-cell | All strings |
| **No header row** | Cannot determine column meaning | Heuristic: first row analysis | Auto-generate column names (col_0, col_1) | Require user to specify headers |
| **Multi-line values** | Broken row parsing | Quoted field detection | RFC 4180 compliant parser | Simple split with warning |
| **Embedded commas/quotes** | Field boundary confusion | Quote handling check | Proper CSV dialect detection | Reject or manual review |
| **BOM (Byte Order Mark)** | Extra characters at start | BOM detection | Strip BOM before parsing | Auto-handle in reader |
| **Duplicate headers** | Ambiguous column references | Header uniqueness check | Append suffix (_1, _2) to duplicates | Reject with error |

---

## Log File Edge Cases

| Edge Case | Problem | Detection | Solution | Fallback |
|-----------|---------|-----------|----------|----------|
| **Unstructured logs** | No consistent format | Pattern matching failure | Multi-format parser (Grok patterns) | Treat as raw text chunks |
| **Multi-line entries** | Log entry spans multiple lines | Timestamp-based boundary detection | Group lines between timestamps | Fixed-line chunking |
| **Binary mixed content** | Non-text data intermixed | Binary byte detection | Skip binary sections, extract text only | Reject binary files |
| **Very large log files** | Memory/time overflow | File size check | Tail-based processing (last N lines) | Sample processing |
| **Compressed logs (.gz)** | Need decompression | File extension check | Stream decompress before processing | Reject with instruction |
| **Interleaved sources** | Multiple log sources merged | Source identifier detection | Split by source, process separately | Process as single stream |
| **Timestamps in various formats** | Parsing inconsistency | Regex pattern library | dateutil flexible parser | ISO 8601 fallback |

---

## Web Page Edge Cases

| Edge Case | Problem | Detection | Solution | Fallback |
|-----------|---------|-----------|----------|----------|
| **Dynamic content (SPA)** | No content in static HTML | Content length after parsing | Headless browser rendering (Playwright) | API-based content fetch |
| **Auth-required pages** | Cannot access content | HTTP 401/403 response | Authenticated crawler with service account | Skip with warning |
| **Rate-limited sites** | Blocked after N requests | HTTP 429 response | Respect rate limits, exponential backoff | Queue for delayed processing |
| **JavaScript-rendered content** | Content not in initial HTML | Script tag analysis | Headless browser with wait-for-content | Extract server-side rendered content |
| **Cookie consent walls** | Content blocked by overlay | Cookie banner detection | Auto-accept or bypass | Skip blocked content |
| **Infinite scroll** | Content loaded dynamically | Scroll-based loading detection | Scroll automation with page limit | Capture initial viewport only |
| **Paywall content** | Partial content visible | Paywall pattern detection | Skip paywalled content | Index available excerpt only |

---

## Output Text Relevancy Controls

### Relevancy Scoring

| Check | Method | Threshold | Action |
|-------|--------|-----------|--------|
| **Query-Answer Relevance** | LLM-as-judge (GPT-4o) | ≥ 0.70 | Below threshold → "I couldn't find a relevant answer" |
| **Groundedness** | Context-answer comparison | ≥ 0.80 | Below threshold → Add disclaimer |
| **Factual Consistency** | Cross-reference citations | ≥ 0.90 | Below threshold → Flag for review |
| **Topic Relevance** | Intent match check | Exact or close match | Mismatch → "Your question seems to be about X, but I found Y" |
| **Freshness** | Document date check | Within policy period | Outdated → "Note: This information is from [date]" |
| **Completeness** | Coverage analysis | All aspects addressed | Partial → "I found information about X but not Y" |

### Relevancy Fallback Chain

```
Score ≥ 0.85: Direct answer with high confidence
Score 0.70–0.84: Answer with "Based on available information..." qualifier
Score 0.50–0.69: "I found some related information, but I'm not fully confident..."
Score < 0.50: "I don't have enough information to answer this accurately."
```

### Context Window Management

| Scenario | Strategy | Implementation |
|----------|----------|----------------|
| Too many results | Select top-K by relevance | Sort by score, take top 8 |
| Results too large | Compress context | Summarize long chunks |
| Conflicting results | Highlight conflict | Present both views with dates |
| Outdated + current results | Prefer current | Sort by effectiveDate, note versions |
| No results | Graceful decline | "I don't have information about..." |

---

## PII Edge Cases

### PII Detection by Data Type

| Data Type | Common PII | Detection Challenge | Solution |
|-----------|-----------|---------------------|----------|
| **PDF** | Names in headers, SSN in forms | OCR quality affects detection | Run PII on OCR output, lower confidence threshold |
| **Excel** | PII in cell values, hidden sheets | Structured + unstructured mix | Scan all cells, including hidden sheets |
| **Images** | PII in photos, badges, screenshots | OCR required first | OCR → PII scan pipeline |
| **CSV** | PII in column values, headers may hint | Column name heuristics | Header-aware PII detection |
| **Logs** | IP addresses, user IDs, emails | Unstructured format | Regex + NER combined |
| **Email** | Sender, recipient, signature blocks | Semi-structured | Parse email structure, scan body + headers |

### PII False Positive Cases

| Scenario | Example | Why False Positive | Mitigation |
|----------|---------|-------------------|------------|
| Company name similar to person | "John Deere" in agriculture doc | NER tags as person | Org entity whitelist |
| Product codes look like SSN | "123-45-6789" as part number | Regex match | Context-aware scoring (Presidio) |
| Dates misidentified as DOB | "Born in 1985" in history doc | Context-dependent | Require "DOB" or "birth" context |
| Account IDs look like phone numbers | "1234567890" as internal ID | Regex match | Column header context |
| City names match person names | "Jackson" as a city | NER ambiguity | Cross-reference with location entities |

### PII in LLM Output

| Scenario | Risk | Control |
|----------|------|---------|
| Model halluccinates real PII | Leaks training data | Output PII scan + block |
| Model copies PII from context | Passes through retrieval PII | Pre-retrieval masking |
| User asks for someone's contact info | Directly requests PII | Intent classifier blocks |
| PII in citations | Source document contains PII | Mask PII in citations |

---

## Security & Compliance Edge Cases

| Edge Case | Risk | Detection | Mitigation |
|-----------|------|-----------|------------|
| **JWT token expired mid-request** | Auth bypass | Token validation timestamp | Reject and force re-auth |
| **Tenant filter removed by code bug** | Cross-tenant data leak | Integration tests, code review | Mandatory middleware enforcement |
| **Prompt injection via uploaded document** | Indirect injection | Document content scanning | Strip instruction-like text from docs |
| **Rate limit bypass via distributed clients** | DoS / cost spike | Per-tenant aggregate rate tracking | Tenant-level rate limit (not just per-IP) |
| **Malicious file upload** | Malware, code execution | File type validation + antivirus scan | Reject non-allowed types, scan with Defender |
| **Token budget exhaustion** | Service unavailable | Token counter near limit | Reserve 10% buffer, alert at 80% |
| **Model returns system prompt** | Leaks instructions | Output regex for system prompt patterns | Block responses containing system prompt |
| **Concurrent session limit bypass** | Resource exhaustion | Session counter per user | Hard limit (10 concurrent sessions) |
| **Data residency violation** | Regulatory breach | Geo-check on data storage | Enforce region policy at ingestion |
| **Audit log tampering** | Compliance failure | Immutable storage check | WORM storage for audit logs |

---

## B2C-Specific Edge Cases

| Edge Case | Context | Risk | Solution |
|-----------|---------|------|----------|
| **Multilingual input** | Customer types in non-English | Wrong language processing | Auto-detect language, route to appropriate pipeline |
| **Accessibility (screen reader)** | Visually impaired users | Non-accessible responses | WCAG 2.1 AA compliant responses, alt-text for visuals |
| **GDPR consent withdrawal** | User revokes consent mid-session | Continued data processing | Immediate session termination, data deletion within 24h |
| **Minor user detection** | Under-13 user accessing chat | COPPA/GDPR children | Age gate, no PII collection from minors |
| **Abusive user** | Sends harmful/abusive content | Safety risk, legal | Content filters + rate limit + ban after repeated violations |
| **Session timeout** | User inactive for extended period | Stale context, security | Auto-expire session after 30 min inactivity |
| **Cross-site scripting via chat** | User injects HTML/JS | XSS attack | Sanitize all input/output, CSP headers |
| **Customer data in public context** | User shares PII in query | Privacy violation | PII detection on input, warn user before processing |
| **Bot traffic** | Automated queries | Cost spike, abuse | CAPTCHA after suspicious patterns, bot detection |
| **Mobile browser compatibility** | Varied device capabilities | Broken UI | Responsive design, progressive enhancement |

---

## B2B-Specific Edge Cases

| Edge Case | Context | Risk | Solution |
|-----------|---------|------|----------|
| **SLA enforcement** | Partner expects guaranteed latency | Breach of contract | Real-time SLA monitoring, credit system |
| **Tenant isolation failure** | Code bug exposes another tenant's data | Data breach | Defense-in-depth, pen testing, audit |
| **API rate limit dispute** | Partner claims limits are too strict | Business relationship | Transparent usage dashboard, burst allowance |
| **Partner API key compromise** | Stolen OAuth credentials | Unauthorized access | Token rotation, anomaly detection, IP allowlist |
| **Large batch ingestion** | Partner uploads 10,000 docs at once | System overload | Queue-based ingestion with concurrency limits |
| **Schema version mismatch** | Partner uses old API version | Integration failure | API versioning, backward compatibility, deprecation notices |
| **Geo-compliance conflict** | Partner requires EU data residency | Regulatory | Configurable data residency per tenant |
| **Multi-region latency** | Partner in different region | High latency | Regional endpoints, edge caching |
| **Billing dispute** | Usage tracking discrepancy | Financial | Metered billing with detailed logs, transparent dashboard |
| **Partner offboarding** | Tenant data deletion requirements | Data retention conflict | Automated tenant data purge workflow |

---

## Edge Case Response Matrix

### Priority-Based Handling

| Priority | Response | Example |
|----------|----------|---------|
| **P0 — Block** | Reject input, return error | Malicious file upload, prompt injection detected |
| **P1 — Warn** | Process with warning to user | Low OCR confidence, outdated document |
| **P2 — Flag** | Process normally, flag for review | PII false positive, edge case format |
| **P3 — Log** | Process normally, log for analytics | Unusual query pattern, new file format |

---

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Classification | Internal |
| Owner | Platform Team |
| Review | Quarterly |
| Related | [Tech Stack](TECH-STACK-SERVICES.md), [Security Layers](../security/SECURITY-LAYERS.md) |
