# ReadQuarry 📚

A local-first book discussion application powered by RAG (Retrieval-Augmented Generation).

Upload books, index them for semantic and exact search, and have intelligent AI-powered conversations about their content — all running privately on your machine.

## Features

- **Book Upload**: Upload EPUB books with configurable chunking strategies
- **Smart Discussion**: Chat with an LLM about your books with context from the actual text
- **Hybrid Search**: Semantic search (by meaning) + exact search (by words/phrases)
- **Source References**: See exactly which book fragments the AI uses for answers
- **Local & Private**: Everything runs on your machine — no data leaves your computer
- **Flexible LLM**: Works with local models (Ollama) or cloud APIs (OpenAI, etc.)

## Quick Start

```bash
# Windows
start.bat

# Linux / macOS
./start.sh
```

Then open `http://localhost:8000` in your browser.

## Manual Setup

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python main.py
```

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy
- **Vector Store**: ChromaDB (embedded)
- **Full-Text Search**: Tantivy
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **Frontend**: Vanilla HTML/CSS/JS
- **Database**: SQLite

## License

This project is licensed under the MIT License.