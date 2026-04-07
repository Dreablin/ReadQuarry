# ReadQuarry — Product Requirements Document

> A local-first book discussion application that lets users upload books, index them for semantic and exact search, and have intelligent conversations about their content with an LLM.

---

## 1. Overview

### 1.1 Problem Statement

Readers want to discuss, analyze, and explore books interactively — ask questions about characters, themes, events, and get precise answers grounded in the actual text. Existing tools either require cloud-only infrastructure, lack privacy, or don't provide transparent references to source material.

### 1.2 Solution

**ReadQuarry** is a local desktop application that:

- Runs entirely on the user's machine via a single startup script.
- Provides a web-based UI at `localhost` in the browser.
- Allows users to upload books (starting with EPUB), chunk and vectorize them, and store everything locally.
- Supports intelligent LLM-powered book discussions with hybrid search (semantic + exact match).
- Shows transparent source references for every AI answer.
- Works with both local LLMs (Ollama) and cloud LLM providers.

### 1.3 Target User

Individual readers, researchers, and students who want private, local-first book analysis with AI assistance.

---

## 2. Technology Stack

### 2.1 Backend

| Component | Technology | Rationale |
|---|---|---|
| **Language** | Python 3.11+ | Rich NLP/ML ecosystem, fast prototyping |
| **Web Framework** | FastAPI | Async, fast, built-in OpenAPI docs, WebSocket support |
| **Task Runner** | Background tasks via FastAPI / asyncio | No need for Celery for local single-user app |

### 2.2 Frontend

| Component | Technology | Rationale |
|---|---|---|
| **Framework** | Vanilla HTML + CSS + JavaScript | Lightweight, no build step, served by FastAPI |
| **Styling** | Modern CSS with CSS variables | Premium dark theme, glassmorphism, micro-animations |
| **Communication** | Fetch API + Server-Sent Events (SSE) | Real-time streaming of LLM responses |

### 2.3 Data & AI

| Component | Technology | Rationale |
|---|---|---|
| **Vector Store** | ChromaDB (persistent mode) | Embedded, SQLite-like simplicity, zero server setup, `pip install` only, excellent Python API, ideal for local RAG |
| **Relational DB** | SQLite via SQLAlchemy | Metadata, book records, settings, chat history |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` | Fast, lightweight (80MB), 384-dim vectors, runs on CPU, high quality for semantic search |
| **Exact Search** | `tantivy-py` (Tantivy via Python bindings) | High-performance Rust-based full-text search engine with BM25, phrase queries, and exact match. Modern, actively maintained replacement for Whoosh |
| **EPUB Parsing** | `EbookLib` + `BeautifulSoup4` | Standard EPUB parsing with clean HTML-to-text conversion |
| **LLM Integration** | `openai` Python SDK (compatible with Ollama and cloud APIs) | Unified interface for both local (Ollama) and cloud (OpenAI, Anthropic, etc.) |

### 2.4 Project Structure

```
readquarry/
├── main.py                     # Entry point — starts FastAPI server
├── requirements.txt            # Python dependencies
├── start.sh / start.bat        # One-click startup scripts
├── config.py                   # App configuration & defaults
├── src/
│   ├── __init__.py
│   ├── api/                    # FastAPI route modules
│   │   ├── __init__.py
│   │   ├── books.py            # Book upload & management endpoints
│   │   ├── chat.py             # Chat / discussion endpoints (SSE)
│   │   ├── search.py           # Search endpoints (semantic + exact)
│   │   └── settings.py         # Settings CRUD endpoints
│   ├── core/                   # Core business logic
│   │   ├── __init__.py
│   │   ├── book_processor.py   # Orchestrates ingestion pipeline
│   │   ├── chunking.py         # Chunking strategies (pluggable)
│   │   ├── embeddings.py       # Embedding generation service
│   │   ├── vector_store.py     # ChromaDB wrapper
│   │   ├── search_engine.py    # Tantivy exact/phrase search wrapper
│   │   ├── llm_client.py       # Unified LLM client (Ollama / cloud)
│   │   └── hybrid_search.py    # Combines semantic + exact search
│   ├── parsers/                # Book format parsers (pluggable)
│   │   ├── __init__.py
│   │   ├── base.py             # Abstract parser interface
│   │   └── epub_parser.py      # EPUB implementation
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── book.py             # Book, Chapter, Paragraph models
│   │   ├── chunk.py            # Chunk model
│   │   ├── chat.py             # ChatSession, ChatMessage models
│   │   └── settings.py         # Settings model
│   └── db/                     # Database setup & session
│       ├── __init__.py
│       └── database.py         # SQLAlchemy engine, session factory
├── static/                     # Frontend assets served by FastAPI
│   ├── index.html              # Main SPA entry point
│   ├── css/
│   │   └── style.css           # Complete design system
│   └── js/
│       ├── app.js              # Main application controller
│       ├── api.js              # API client wrapper
│       ├── components/         # UI components
│       │   ├── book-upload.js  # Upload dialog with chunking options
│       │   ├── book-list.js    # Book selector dropdown
│       │   ├── chat.js         # Chat panel with message history
│       │   ├── references.js   # Right panel — source fragments
│       │   └── settings.js     # Settings modal
│       └── utils.js            # Shared utilities
├── data/                       # Runtime data directory (gitignored)
│   ├── readquarry.db           # SQLite database
│   ├── chroma/                 # ChromaDB persistent storage
│   └── tantivy_index/          # Tantivy search indices
└── tests/                      # Test suite
    ├── __init__.py
    ├── conftest.py             # Shared fixtures
    ├── test_parsers/
    │   ├── __init__.py
    │   └── test_epub_parser.py
    ├── test_core/
    │   ├── __init__.py
    │   ├── test_chunking.py
    │   ├── test_embeddings.py
    │   ├── test_vector_store.py
    │   ├── test_search_engine.py
    │   ├── test_hybrid_search.py
    │   └── test_book_processor.py
    ├── test_api/
    │   ├── __init__.py
    │   ├── test_books_api.py
    │   ├── test_chat_api.py
    │   ├── test_search_api.py
    │   └── test_settings_api.py
    └── test_models/
        ├── __init__.py
        └── test_models.py
```

---

## 3. Functional Requirements

### 3.1 Book Upload (F-UPLOAD)

#### F-UPLOAD-01: File Upload

- The user MUST be able to upload a book file through the web interface via an "Upload Book" button.
- The system MUST accept EPUB files.
- The system MUST validate the file format before processing and show a clear error if the format is unsupported.
- The system MUST show upload progress and processing status.

#### F-UPLOAD-02: Text Extraction

- The system MUST extract clean, readable text from the uploaded book.
- The system MUST preserve chapter/section structure as metadata.
- The system MUST strip all HTML/XML markup, scripts, styles, and formatting artifacts.
- The parser layer MUST follow the `BaseParser` abstract interface so new formats (PDF, FB2, MOBI, TXT, DOCX) can be added by implementing a single class without modifying existing code.

#### F-UPLOAD-03: Paragraph Splitting

- The system MUST split the extracted text into paragraphs (separated by double newlines or equivalent structural boundaries from the source format).
- Each paragraph MUST retain metadata: book ID, chapter title/number, paragraph index within the chapter, and the raw text.

#### F-UPLOAD-04: Chunking Strategies

The user MUST choose a chunking strategy at upload time from the following options:

| Strategy | Description |
|---|---|
| **Paragraph** (default) | Each chunk = 1 paragraph. Overlap = 1 paragraph (the last paragraph of the previous chunk is repeated as the first paragraph of the next). |
| **Sentence** | Each chunk = 1 sentence. Overlap = 1 sentence. |
| **Fixed-size (token-based)** | Each chunk = N tokens (default 256). Overlap = 10–20% of chunk size. Splits respect sentence boundaries. |
| **Chapter-aware recursive** | Uses `RecursiveCharacterTextSplitter` logic: splits by `\n\n` → `\n` → `. ` → ` `, with configurable chunk size (default 512 tokens) and overlap (default 64 tokens). Each chunk is tagged with its source chapter. |

- Each chunk MUST store: chunk text, book ID, chapter reference, position index, chunking strategy used.
- The chunking module MUST be extensible — new strategies can be added by implementing a `ChunkingStrategy` interface.

#### F-UPLOAD-05: Vectorization & Storage

- The system MUST generate embeddings for all chunks using `sentence-transformers/all-MiniLM-L6-v2`.
- Embeddings MUST be stored in ChromaDB in a collection named per book (e.g., `book_{book_id}`).
- Each vector entry MUST include metadata: `book_id`, `chapter`, `paragraph_index`, `chunk_index`, `strategy`.

#### F-UPLOAD-06: Exact Search Index

- The system MUST build a Tantivy full-text search index for the uploaded book.
- The index MUST support: exact word search, phrase search (quoted strings), and case-insensitive matching.
- The index MUST be scoped per book (separate index directory per book).

#### F-UPLOAD-07: Book Persistence

- The system MUST save book metadata (title, author, file name, upload date, chunking strategy, total chunks, total paragraphs) to SQLite.
- The system MUST save all paragraphs and chunks to SQLite for retrieval and display.
- After successful processing, the book MUST appear in the book selector for discussions.

#### F-UPLOAD-08: Parser Plugin Architecture

- All parsers MUST implement the `BaseParser` abstract class:
  ```python
  class BaseParser(ABC):
      @abstractmethod
      def can_parse(self, file_path: str) -> bool:
          """Return True if this parser can handle the given file."""
          pass

      @abstractmethod
      def parse(self, file_path: str) -> ParsedBook:
          """Extract text and metadata from the file."""
          pass

      @abstractmethod
      def supported_extensions(self) -> list[str]:
          """Return list of supported file extensions."""
          pass
  ```
- A `ParserRegistry` MUST auto-discover and register all parser implementations.
- When a file is uploaded, the registry MUST select the correct parser based on file extension.
- If no parser matches, the system MUST return a clear error.

---

### 3.2 Book Discussion (F-DISCUSS)

#### F-DISCUSS-01: Book Selection

- The user MUST be able to click a "Discuss Book" button.
- The system MUST show a dropdown list of all previously uploaded books.
- Each entry MUST display: book title, author (if available), upload date.
- After selecting a book, the user MUST see the discussion interface.

#### F-DISCUSS-02: Chat Interface

- The left panel MUST display a scrollable chat history with alternating user/AI messages.
- The user MUST have a text input field and a send button at the bottom.
- User messages MUST appear immediately in the chat.
- AI responses MUST stream in real-time via SSE (Server-Sent Events) with a typing indicator.

#### F-DISCUSS-03: Hybrid Search on Query

When the user sends a message, the system MUST:

1. **Semantic search**: Embed the user's query and search ChromaDB for the top-K (default K=5) most similar chunks from the selected book.
2. **Exact search**: Run the query through Tantivy to find chunks containing exact word/phrase matches. This is especially important for character names, specific terms, and quoted phrases.
3. **Merge & deduplicate**: Combine results from both searches, remove duplicates, and rank by a combined relevance score.
4. **Build context**: Assemble the top N (default N=7) unique chunks as context for the LLM prompt.
5. **Generate response**: Send the context + user query to the configured LLM with a system prompt instructing it to answer based only on the provided book fragments, citing chunk references.
6. **Stream response**: Stream the LLM response back to the user via SSE.
7. **Save history**: Save the user message, AI response, and referenced chunks to SQLite.

#### F-DISCUSS-04: Source References

- The AI response MUST indicate which chunks were used (e.g., numbered references like `[1]`, `[2]`).
- The right panel MUST display the actual text of all referenced chunks.
- Each displayed chunk MUST show: the chunk text, chapter name, and position metadata.
- New referenced chunks MUST be appended to the right panel list as the conversation progresses.

#### F-DISCUSS-05: In-Book Search

- The user MUST be able to perform explicit search within the selected book (separate from chat).
- Search MUST support:
  - Free text search (BM25 via Tantivy).
  - Exact phrase search (user wraps query in quotes).
- Search results MUST appear in the right panel.
- Each result MUST show the matching chunk with the search term highlighted.

#### F-DISCUSS-06: Clear References

- There MUST be a "Clear" button on the right panel to remove all displayed chunks/references.
- Clearing references MUST NOT affect chat history.

---

### 3.3 Discussion Interface Layout (F-UI)

#### F-UI-01: Split-Panel Layout

```
┌─────────────────────────────────────────────────────┐
│                    Header Bar                       │
│  [Book: <dropdown>]        [Search] [Settings] [⚙]  │
├────────────────────────┬────────────────────────────┤
│                        │                            │
│      Chat Panel        │    References Panel        │
│                        │                            │
│  ┌──────────────────┐  │  ┌──────────────────────┐  │
│  │ AI: Based on     │  │  │ [1] Chapter 3, ¶12   │  │
│  │ chapter 3 [1]... │  │  │ "The actual text..." │  │
│  │                  │  │  │                      │  │
│  │ User: Who is...  │  │  │ [2] Chapter 7, ¶4    │  │
│  │                  │  │  │ "Another fragment..." │  │
│  │ AI: According    │  │  │                      │  │
│  │ to [2]...        │  │  │         ...           │  │
│  └──────────────────┘  │  │                      │  │
│                        │  │        [Clear]        │  │
│  ┌──────────────────┐  │  └──────────────────────┘  │
│  │ Type a message...│  │                            │
│  │            [Send]│  │                            │
│  └──────────────────┘  │                            │
├────────────────────────┴────────────────────────────┤
│                    Status Bar                       │
└─────────────────────────────────────────────────────┘
```

#### F-UI-02: Visual Design Requirements

- Dark theme with rich, premium aesthetics (not plain/flat).
- Glassmorphism effects on panels.
- Smooth gradient accents (e.g., deep purple → teal for headers/buttons).
- Modern typography via Google Fonts (Inter or Outfit).
- Micro-animations: message fade-in, button hover glow, typing indicator pulse.
- Responsive layout: panels stack vertically on narrow viewports.

#### F-UI-03: Upload Dialog

- Modal dialog with:
  - File drop zone (drag & drop + click to browse).
  - Chunking strategy dropdown with descriptions.
  - Progress bar during processing.
  - Success/error notification.

---

### 3.4 Settings (F-SETTINGS)

#### F-SETTINGS-01: LLM Mode Selection

The user MUST choose between two modes:

**Mode A — Local LLM (Ollama)**

| Setting | Description | Default |
|---|---|---|
| Ollama Base URL | URL of the running Ollama instance | `http://localhost:11434` |
| Model ID | The model to use (e.g., `llama3.2`, `mistral`) | `llama3.2` |

**Mode B — Cloud LLM**

| Setting | Description | Default |
|---|---|---|
| Provider | `openai`, `anthropic`, or `custom` | `openai` |
| API Key | The provider's API key | (empty) |
| API Base URL | Custom endpoint URL (for proxies or compatible APIs) | (provider default) |
| Model ID | The model to use (e.g., `gpt-4o`, `claude-sonnet-4-20250514`) | `gpt-4o` |
| Max Tokens | Maximum response length | `2048` |
| Temperature | Creativity parameter (0.0 – 2.0) | `0.3` |

#### F-SETTINGS-02: Embedding Settings

| Setting | Description | Default |
|---|---|---|
| Embedding Model | HuggingFace model ID | `all-MiniLM-L6-v2` |
| Device | `cpu` or `cuda` | `cpu` |

#### F-SETTINGS-03: Search Settings

| Setting | Description | Default |
|---|---|---|
| Semantic top-K | Number of semantic search results | `5` |
| Exact search results | Number of exact search results | `5` |
| Final context chunks | Max chunks sent to LLM | `7` |

#### F-SETTINGS-04: Persistence

- All settings MUST be saved to SQLite and persist across application restarts.
- Settings MUST load on application startup.
- The settings page MUST have a "Save" button and a "Reset to Defaults" button.
- The system MUST validate settings before saving (e.g., URL format, non-empty API key when cloud mode is selected).

---

### 3.5 Data Storage (F-DATA)

#### F-DATA-01: SQLite Database

Schema overview:

```sql
-- Books table
books (
    id              INTEGER PRIMARY KEY,
    title           TEXT NOT NULL,
    author          TEXT,
    file_name       TEXT NOT NULL,
    file_hash       TEXT NOT NULL UNIQUE,  -- prevent duplicate uploads
    chunking_strategy TEXT NOT NULL,
    total_paragraphs INTEGER,
    total_chunks    INTEGER,
    upload_date     DATETIME DEFAULT CURRENT_TIMESTAMP
)

-- Paragraphs table
paragraphs (
    id              INTEGER PRIMARY KEY,
    book_id         INTEGER REFERENCES books(id) ON DELETE CASCADE,
    chapter_title   TEXT,
    chapter_index   INTEGER,
    paragraph_index INTEGER,
    text            TEXT NOT NULL
)

-- Chunks table
chunks (
    id              INTEGER PRIMARY KEY,
    book_id         INTEGER REFERENCES books(id) ON DELETE CASCADE,
    chapter_title   TEXT,
    chunk_index     INTEGER,
    strategy        TEXT NOT NULL,
    text            TEXT NOT NULL,
    paragraph_ids   TEXT  -- JSON array of source paragraph IDs
)

-- Chat sessions
chat_sessions (
    id              INTEGER PRIMARY KEY,
    book_id         INTEGER REFERENCES books(id) ON DELETE CASCADE,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    title           TEXT
)

-- Chat messages
chat_messages (
    id              INTEGER PRIMARY KEY,
    session_id      INTEGER REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role            TEXT NOT NULL,  -- 'user' or 'assistant'
    content         TEXT NOT NULL,
    referenced_chunks TEXT,  -- JSON array of chunk IDs used
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
)

-- App settings
app_settings (
    key             TEXT PRIMARY KEY,
    value           TEXT NOT NULL
)
```

#### F-DATA-02: ChromaDB Vector Store

- Persistent storage in `data/chroma/`.
- One collection per book: `book_{book_id}`.
- Each document in the collection stores:
  - `id`: chunk ID (matching SQLite chunk ID).
  - `embedding`: 384-dimensional vector.
  - `document`: chunk text.
  - `metadata`: `{ book_id, chapter, chunk_index, strategy }`.

#### F-DATA-03: Tantivy Search Index

- Persistent storage in `data/tantivy_index/book_{book_id}/`.
- One index directory per book.
- Each indexed document includes:
  - `chunk_id` (stored, indexed).
  - `text` (full-text indexed with BM25 scoring).
  - `chapter` (stored, indexed).
  - `chunk_index` (stored).

#### F-DATA-04: Book Deletion

- The user SHOULD be able to delete a book from the system.
- Deletion MUST remove: SQLite records (book, paragraphs, chunks, related chat sessions/messages), ChromaDB collection, and Tantivy index directory.

---

## 4. Non-Functional Requirements

### 4.1 Installation & Startup

- The system MUST run after `pip install -r requirements.txt` and `python main.py`.
- NO external services or databases should need manual installation.
- ChromaDB, Tantivy, and SQLite MUST be embedded and require zero setup.
- Startup script (`start.bat` / `start.sh`) MUST:
  1. Check Python version.
  2. Create virtualenv if not exists.
  3. Install dependencies.
  4. Start the application.
  5. Open the browser to `http://localhost:8000`.

### 4.2 Performance

- Book upload (EPUB, ~300 pages): SHOULD complete in under 60 seconds.
- Semantic search: SHOULD return results in under 2 seconds.
- Exact search: SHOULD return results in under 500ms.
- LLM response streaming SHOULD begin within 3 seconds of query submission (latency depends on LLM provider).

### 4.3 Reliability

- The application MUST handle malformed EPUB files gracefully with clear error messages.
- The application MUST handle LLM connection failures gracefully (show error, don't crash).
- All database operations MUST use transactions to prevent data corruption.

### 4.4 Extensibility

- New book formats MUST be addable by creating a single parser class implementing `BaseParser`.
- New chunking strategies MUST be addable by implementing `ChunkingStrategy` interface.
- New LLM providers MUST be supportable through the `openai`-compatible interface or by extending the LLM client.

---

## 5. Testing Requirements (TDD)

The Ralph Loop agent MUST write and run tests for each component before or alongside the implementation.

### 5.1 Unit Tests

| Test File | Covers | Key Test Cases |
|---|---|---|
| `test_epub_parser.py` | EPUB parsing | Parse valid EPUB, extract chapters, handle malformed files, clean HTML |
| `test_chunking.py` | All chunking strategies | Paragraph chunking with overlap, sentence chunking with overlap, fixed-size with sentence boundary respect, recursive chapter-aware splitting |
| `test_embeddings.py` | Embedding generation | Generate embeddings, correct dimensionality (384), batch processing |
| `test_vector_store.py` | ChromaDB operations | Create collection, add documents, query by similarity, delete collection |
| `test_search_engine.py` | Tantivy operations | Index documents, exact word search, phrase search, case-insensitive, delete index |
| `test_hybrid_search.py` | Combined search | Merge semantic+exact results, deduplication, ranking |
| `test_book_processor.py` | Full ingestion pipeline | End-to-end upload, processing, indexing |
| `test_models.py` | SQLAlchemy models | CRUD operations for all models, cascade deletion, constraints |

### 5.2 API Tests

| Test File | Covers | Key Test Cases |
|---|---|---|
| `test_books_api.py` | `/api/books/*` | Upload file, list books, get book details, delete book |
| `test_chat_api.py` | `/api/chat/*` | Send message, stream response, get history, create session |
| `test_search_api.py` | `/api/search/*` | Semantic search, exact search, phrase search |
| `test_settings_api.py` | `/api/settings/*` | Get settings, update settings, validate settings, reset defaults |

### 5.3 Test Infrastructure

- Use `pytest` as the test runner.
- Use `pytest-asyncio` for async test support.
- Use `httpx` with `ASGITransport` for testing FastAPI endpoints.
- Use temporary directories and in-memory databases for test isolation.
- Every test MUST clean up after itself (no leftover files or database entries).
- Tests MUST be runnable with `pytest tests/ -v`.

---

## 6. API Specification

### 6.1 Books API

```
POST   /api/books/upload          # Upload and process a book
GET    /api/books                  # List all books
GET    /api/books/{book_id}        # Get book details
DELETE /api/books/{book_id}        # Delete a book and all its data
GET    /api/books/{book_id}/chunks # Get chunks for a book (paginated)
```

### 6.2 Chat API

```
POST   /api/chat/sessions                      # Create a new chat session for a book
GET    /api/chat/sessions?book_id={book_id}     # List sessions for a book
GET    /api/chat/sessions/{session_id}/messages  # Get message history
POST   /api/chat/sessions/{session_id}/message   # Send a message (returns SSE stream)
```

### 6.3 Search API

```
POST   /api/search/semantic    # { book_id, query, top_k }
POST   /api/search/exact       # { book_id, query, max_results }
POST   /api/search/hybrid      # { book_id, query, semantic_k, exact_k, final_n }
```

### 6.4 Settings API

```
GET    /api/settings            # Get all settings
PUT    /api/settings            # Update settings
POST   /api/settings/reset      # Reset to defaults
POST   /api/settings/test-llm   # Test LLM connection with current settings
```

---

## 7. Implementation Tasks

> **Task tracking is maintained in `progress.md`** — that file is the single source of truth for task status.

The project is broken into **41 atomic tasks** across 5 phases:

| Phase | Tasks | Description |
|---|---|---|
| **1. Foundation** | T01–T03 | Project scaffolding, database models, model tests |
| **2. Book Ingestion** | T04–T18 | Parsers, chunking, embeddings, vector store, search engine, hybrid search, book processor |
| **3. API Layer** | T19–T28 | Books API, search API, settings API, LLM client, chat API |
| **4. Frontend** | T29–T38 | HTML, CSS, JS components, static file serving |
| **5. Polish & Startup** | T39–T41 | Startup scripts, error handling, end-to-end verification |

Each task is atomic, testable, and builds on previous tasks. The agent completes them in order using TDD.

---

## 8. Dependencies (requirements.txt)

```
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
sqlalchemy>=2.0.0
aiosqlite>=0.20.0
python-multipart>=0.0.18
ebooklib>=0.18
beautifulsoup4>=4.12.0
lxml>=5.0.0
sentence-transformers>=3.0.0
chromadb>=0.5.0
tantivy>=0.22.0
openai>=1.50.0
pydantic>=2.0.0
pydantic-settings>=2.0.0

# Testing
pytest>=8.0.0
pytest-asyncio>=0.24.0
httpx>=0.27.0
```

---

## 9. Out of Scope (v1)

- Multi-user support / authentication.
- Cloud deployment.
- Mobile-specific responsive optimization.
- Concurrent book discussion (only one book at a time per session).
- Book highlight/annotation features.
- Export of conversations.
- PDF, FB2, MOBI, TXT, DOCX parsers (designed for, but not implemented in v1).
- Custom embedding model training.
- GPU-required models.

---

## 10. Open Questions

- **Q1**: Should the system support discussing multiple books simultaneously in one chat session (cross-book analysis)?
  - **Current decision**: No, v1 supports one book per chat session.
- **Q2**: Should there be a "book library" view with covers and detailed metadata?
  - **Current decision**: Simple dropdown list is sufficient for v1.
- **Q3**: Should chat history persist across application restarts?
  - **Current decision**: Yes, chat sessions/messages are stored in SQLite.

---

## 11. Glossary

| Term | Definition |
|---|---|
| **Chunk** | A piece of text derived from a book, sized according to the chosen chunking strategy, used as the unit of retrieval |
| **Paragraph** | A natural text block separated by double newlines in the source text |
| **Semantic search** | Finding chunks by meaning similarity using vector embeddings |
| **Exact search** | Finding chunks by literal word/phrase matching using full-text indexing |
| **Hybrid search** | Combining semantic and exact search results |
| **RAG** | Retrieval-Augmented Generation — using retrieved text as context for LLM answers |
| **SSE** | Server-Sent Events — one-way streaming from server to client |
| **ChromaDB** | Embedded vector database, used for storing and searching chunk embeddings |
| **Tantivy** | High-performance Rust-based full-text search engine with Python bindings |
