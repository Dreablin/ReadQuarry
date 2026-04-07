# ReadQuarry — Progress Tracker

> This file is the Ralph Loop agent's long-term memory. It is updated after every completed task.

---

## Current Status

**Phase**: 3 — API Layer  
**Next Task**: T27  
**Last Completed**: T26  
**Total Progress**: 26 / 41 tasks  

---

## Task Log

### Phase 1: Foundation

- [x] **T01**: Project scaffolding — Create directory structure, `requirements.txt`, `main.py`, `config.py`, `.gitignore`
- [x] **T02**: Database models — Implement SQLAlchemy models (Book, Paragraph, Chunk, ChatSession, ChatMessage, AppSettings) with `database.py` setup
- [x] **T03**: Database model tests — Write and pass tests for all CRUD operations, cascade deletes, constraints

### Phase 2: Book Ingestion Pipeline

- [x] **T04**: Parser base class — Implement `BaseParser` ABC and `ParserRegistry`
- [x] **T05**: EPUB parser — Implement `EpubParser` with chapter extraction and HTML cleaning
- [x] **T06**: EPUB parser tests — Test with valid EPUB, chapter extraction, malformed files, HTML stripping
- [x] **T07**: Chunking strategies — Implement `ChunkingStrategy` interface and all 4 strategies (paragraph, sentence, fixed-size, chapter-aware recursive)
- [x] **T08**: Chunking tests — Test each strategy: correct chunk count, overlap behavior, boundary respect, metadata preservation
- [x] **T09**: Embedding service — Implement `EmbeddingService` wrapping sentence-transformers
- [x] **T10**: Embedding tests — Test embedding generation, dimensionality, batch processing
- [x] **T11**: Vector store service — Implement ChromaDB wrapper (create/query/delete collections)
- [x] **T12**: Vector store tests — Test CRUD operations, similarity queries, collection management
- [x] **T13**: Search engine service — Implement Tantivy wrapper (index/search/delete)
- [x] **T14**: Search engine tests — Test indexing, word search, phrase search, case-insensitive matching
- [x] **T15**: Hybrid search — Implement `HybridSearch` combining semantic + exact results with deduplication and ranking
- [x] **T16**: Hybrid search tests — Test merging, deduplication, ranking with various combinations
- [x] **T17**: Book processor — Implement `BookProcessor` orchestrating the full pipeline (parse → split → chunk → embed → index)
- [x] **T18**: Book processor tests — Integration test of full ingestion pipeline

### Phase 3: API Layer

- [x] **T19**: Books API — Implement upload, list, get, delete endpoints
- [x] **T20**: Books API tests — Test all endpoints with valid/invalid inputs
- [x] **T21**: Search API — Implement semantic, exact, and hybrid search endpoints
- [x] **T22**: Search API tests — Test all search endpoints
- [x] **T23**: Settings API — Implement get, update, reset, test-llm endpoints
- [x] **T24**: Settings API tests — Test settings CRUD and validation
- [x] **T25**: LLM client — Implement unified LLM client (Ollama + OpenAI-compatible cloud)
- [x] **T26**: LLM client tests — Test client initialization, request formatting, error handling (use mocks)
- [ ] **T27**: Chat API — Implement session management and message endpoint with SSE streaming
- [ ] **T28**: Chat API tests — Test session creation, message sending, history retrieval

### Phase 4: Frontend

- [ ] **T29**: HTML shell — Create `index.html` with split-panel layout, all sections, semantic HTML
- [ ] **T30**: CSS design system — Create `style.css` with full dark theme, glassmorphism, variables, animations, responsive layout
- [ ] **T31**: API client module — Create `api.js` with all API call wrappers
- [ ] **T32**: Book upload component — Create `book-upload.js` with drag-drop, chunking selector, progress bar
- [ ] **T33**: Book list component — Create `book-list.js` with dropdown selector
- [ ] **T34**: Chat component — Create `chat.js` with message rendering, SSE streaming, typing indicator
- [ ] **T35**: References panel component — Create `references.js` with chunk display, highlighting, clear button
- [ ] **T36**: Settings component — Create `settings.js` with the settings modal/form
- [ ] **T37**: App controller — Create `app.js` wiring all components together, routing between views
- [ ] **T38**: Static file serving — Configure FastAPI to serve static files and the SPA

### Phase 5: Polish & Startup

- [ ] **T39**: Startup scripts — Create `start.bat` and `start.sh` with venv, deps, and browser launch
- [ ] **T40**: Error handling — Add global error handlers, user-friendly error messages throughout
- [ ] **T41**: End-to-end manual verification — Upload an EPUB, discuss it, verify references, test search, test settings

---

## Decisions Log

| Date | Task | Decision | Rationale |
|---|---|---|---|
| 2026-04-07 | T01 | Added minimal scaffold test and initial app/config/requirements structure | Establishes a runnable baseline and validates required directories/files exist |
| 2026-04-07 | T02 | Added SQLAlchemy declarative models and session setup in modular files | Matches PRD schema and prepares explicit CRUD/cascade testing in T03 |
| 2026-04-07 | T03 | Added isolated in-memory SQLite model tests with FK enforcement for CRUD, cascade, and unique constraints | Locks database behavior before API/core layers build on it |
| 2026-04-07 | T04 | Added parser contracts (`BaseParser`, `ParsedBook`, `ParsedChapter`) and registry resolution logic with extension introspection | Establishes pluggable parser architecture required for EPUB and future formats |
| 2026-04-07 | T05 | Implemented `EpubParser` with extension detection, HTML cleaning, metadata extraction, and chapter document parsing | Provides working EPUB ingestion primitive for upcoming detailed parser tests |
| 2026-04-07 | T06 | Expanded EPUB parser tests to cover generated valid EPUBs, chapter extraction, malformed files, and HTML stripping behavior | Validates parser reliability before chunking and ingestion pipeline work |
| 2026-04-07 | T07 | Implemented chunking strategy interface and all four strategies with overlap-aware metadata-rich chunk outputs | Unblocks strategy-level behavioral testing and downstream ingestion orchestration |
| 2026-04-07 | T08 | Added detailed chunking tests validating counts, overlap windows, boundaries, and metadata propagation across all strategies | Guards chunking behavior needed for deterministic indexing and retrieval |
| 2026-04-07 | T09 | Implemented `EmbeddingService` with sentence-transformers integration and deterministic fallback vectors for offline/local test stability | Enables semantic embedding pipeline without blocking on heavyweight runtime model availability |
| 2026-04-07 | T10 | Expanded embedding tests for generation shape, batch behavior, determinism, empty batch handling, and input validation | Hardens embedding API contract before vector store integration |
| 2026-04-07 | T11 | Implemented `VectorStore` ChromaDB wrapper with collection lifecycle, add, and query APIs | Establishes persistence and similarity retrieval foundation for hybrid search |
| 2026-04-07 | T12 | Expanded vector store tests for CRUD, similarity query behavior, custom persistence paths, and idempotent missing-collection deletion | Verifies robust collection management semantics before search integration |
| 2026-04-07 | T13 | Added `SearchEngine` wrapper with index/add/search/delete behavior and case-insensitive exact matching | Establishes full-text retrieval interface needed before dedicated search behavior tests |
| 2026-04-07 | T14 | Added dedicated search-engine tests for indexing, case-insensitive terms, quoted phrase matching, and simple relevance ranking | Validates full-text behavior expectations before hybrid search composition |
| 2026-04-07 | T15 | Implemented `HybridSearch` merge pipeline combining semantic and exact scores with chunk-level deduplication and final-N truncation | Enables unified retrieval ranking for downstream chat context assembly |
| 2026-04-07 | T16 | Expanded hybrid-search tests for empty inputs, tie-break ordering, and repeated exact-hit aggregation | Strengthens result-merging guarantees before book-processor integration |
| 2026-04-07 | T17 | Implemented `BookProcessor` orchestration flow connecting parser selection, chunking, embedding generation, vector persistence, and exact index population | Provides the core end-to-end ingestion execution path |
| 2026-04-07 | T18 | Added book-processor integration coverage with real service components and empty-content guard behavior | Validates full ingestion pipeline wiring and stabilizes no-chunk edge handling |
| 2026-04-07 | T19 | Implemented Books API endpoints (upload/list/get/delete) and integrated router into app startup | Establishes core book-management HTTP surface for upcoming API test expansion |
| 2026-04-07 | T20 | Expanded Books API tests for invalid formats, missing IDs, and unsupported chunking strategies; enforced strategy validation in upload endpoint | Improves endpoint input safety and error semantics before search/chat API work |
| 2026-04-07 | T21 | Implemented Search API endpoints for semantic, exact, and hybrid flows and wired router into app | Enables end-to-end query entry points for retrieval features |
| 2026-04-07 | T22 | Expanded Search API tests for empty query and non-positive limit validation; enforced strict numeric bounds via request schemas | Hardens search endpoint contracts and prevents invalid retrieval parameters |
| 2026-04-07 | T23 | Implemented Settings API endpoints (get/update/reset/test-llm) with validation for cloud mode API key requirement | Provides settings management surface for LLM/search configuration |
| 2026-04-07 | T24 | Expanded Settings API tests for enum/range validation, partial updates, and http(s) URL checks on Ollama/cloud base URLs | Aligns API behavior with PRD validation expectations |
| 2026-04-07 | T25 | Implemented `LLMClient` with OpenAI SDK: Ollama mode uses `{base}/v1` and dummy `api_key`; cloud mode uses optional `api_base_url`; `chat_completion` applies settings defaults for model, max_tokens, temperature | Matches PRD unified openai-compatible integration for local and cloud providers |
| 2026-04-07 | T26 | Expanded `test_llm_client` with mocked OpenAI: default models, trailing-slash base URL, stream and sampling kwargs passthrough, explicit overrides, and propagated provider errors | Locks LLM client contract without network calls |

---

## Issues & Blockers

| Date | Task | Issue | Status |
|---|---|---|---|
| (none yet) | | | |

---

## Notes

- Technology stack is defined in `PRD.md` section 2.
- Always run `pytest tests/ -v --tb=short` before committing.
- Commit format: `feat: T{XX} - {brief description}`.
