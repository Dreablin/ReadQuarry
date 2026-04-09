# ReadQuarry — Progress Tracker (Bugfixes)

> This file is the Ralph Loop agent's long-term memory.
> Updated after every completed task.

---

## Current Status

**Phase**: Bugfixes
**Next Task**: —
**Last Completed**: B08
**Total Progress**: 8 / 8 tasks

---

## Task Log

### Phase 6: Critical Bugfixes (Data Integrity & Ingestion)

- [x] **B01**: SearchEngine exact result scoring bug — Modify `SearchEngine.search()` in `src/core/search_engine.py` to include `"score"` inside each document so `HybridSearch` ranks exact hits properly.
- [x] **B02**: EmbeddingService random vectors bug — In `src/core/embeddings.py`, remove silent `_fallback_embed` random noise fallback in production to ensure proper ImportError when models are missing.
- [x] **B03**: Missing Chunk rows in SQLite breaking RAG context — In `BookProcessor.process_book`, bulk insert SQLAlchemy `Chunk` models into the database so they can be joined and checked during chat completion.
- [x] **B04**: Empty SSE LLM streams — Add detailed debugging in `chat.py` and ensure the frontend renders empty streams with an explicit "[Empty]" log to trace Ollama empty response bugs.
- [x] **B06**: EpubParser destroying paragraph chunking — Update `src/parsers/epub_parser.py`'s `clean_html` to use `separator="\n\n"` instead of `" "`, preserving line breaks so `ParagraphChunking` can find paragraphs.

### Phase 7: UI & Path Fixes

- [x] **B05**: Hardcoded search results limit — Expose `max_results` in the UI and allow retrieving more than 7 matches (e.g. increasing defaults to 20-50).
- [x] **B07**: Model caching location — In `src/core/embeddings.py`, configure `SentenceTransformer` with `cache_folder` pointing to `data/models` so models stay localized to the project.
- [x] **B08**: Clear Model Cache action — Add a `DELETE /api/settings/models_cache` endpoint and a UI button in Settings to purge the `data/models` folder.

---

## Decisions Log

| Date | Task | Decision | Rationale |
|---|---|---|---|
| 2026-04-08 | B01 | Word and phrase `search()` return `{**doc, "score": float(...)}`; phrase uses occurrence count (min 1) | BUGS.md B01 — HybridSearch no longer sees 0.0 for exact hits |
| 2026-04-08 | B02 | Default path loads `SentenceTransformer` without swallowing errors; `allow_fallback=True` enables old deterministic stub for tests only | BUGS.md B02 |
| 2026-04-08 | B03 | `process_book(..., db=)` inserts `Chunk` rows + flush; Chroma/SearchEngine ids = `str(chunk.id)` for `chat.py` lookup | BUGS.md B03 |
| 2026-04-08 | B04 | `logger.debug` per chunk/delta; empty/whitespace-only stream → placeholder delta + `warning`; `chat.js` `console.warn` on bad SSE JSON; `typeof ev.content === "string"` | BUGS.md B04 |
| 2026-04-08 | B05 | Hybrid defaults: semantic 15, exact 15, final 20; `le=50` on search k fields; Search panel `#search-max-results` drives `semantic_k`/`exact_k`/`final_n` | BUGS.md B05 |
| 2026-04-08 | B06 | `clean_html`: extract `p`/headings/`li` with spaced inline text, join with `\n\n`; fallback `get_text(\n\n)` + merge | BUGS.md B06 — ParagraphChunking |
| 2026-04-08 | B07 | `EmbeddingService(cache_folder=)` defaults to `str(settings.data_dir / "models")`; passed to `SentenceTransformer` | BUGS.md B07 |
| 2026-04-08 | B08 | `DELETE /api/settings/models_cache` removes `data_dir/models`; `clearModelsCache()` + Embeddings tab button + hint; idempotent when missing | BUGS.md B08 |

---

## Issues & Blockers

| Date | Task | Issue | Status |
|---|---|---|---|
| (none yet) | | | |

---

## Notes

- Check `BUGS.md` for detailed context on all issues.
- Always run tests (`pytest tests/ -v --tb=short`) before committing.
- Commit format: `fix: B{XX} - {brief description}`.
