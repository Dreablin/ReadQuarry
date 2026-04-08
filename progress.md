# ReadQuarry — Progress Tracker (Bugfix Phase)

> This file is the Ralph Loop agent's long-term memory. It is updated after every completed task.

---

## Current Status

**Phase**: 7 — Bug Fixes (Round 2)
**Next Task**: B14
**Last Completed**: B13
**Total Progress**: 14 / 17 tasks

---

## Task Log

### Phase 6: Bug Fixes (Round 1)

- [x] **B01**: Unify book storage — move from in-memory dict to SQLAlchemy DB so chat sessions can find uploaded books — see BUGS.md B01
- [x] **B02**: Wire semantic search to real EmbeddingService + VectorStore instead of placeholder — see BUGS.md B02
- [x] **B03**: Persist settings to JSON file on disk so they survive restarts — see BUGS.md B03
- [x] **B04**: Fix GPU idle load caused by infinite CSS header-shimmer animation — see BUGS.md B04
- [x] **B05**: Add multi-language support (Russian + English) for embeddings, search, and chunking — see BUGS.md B05
- [x] **B06**: Split LLM settings into Ollama/Cloud groups with dropdown selector and conditional field visibility — see BUGS.md B06
- [x] **B07**: Reorganize settings dialog into tabbed layout (LLM / Embeddings & Search) — see BUGS.md B07
- [x] **B08**: Show API key security warning when Cloud LLM mode is selected — see BUGS.md B08
- [x] **B09**: Put Discussion and Search on separate screens with symmetric navigation buttons — see BUGS.md B09
- [x] **B10**: Add debug log viewer as third navigation screen — see BUGS.md B10
- [x] **B11**: Add detailed logging during book ingestion pipeline — see BUGS.md B11
- [x] **B12**: Document Ralph Loop scratchpad safety cap requirement — see BUGS.md B12

### Phase 7: Bug Fixes (Round 2)

- [x] **B17**: Fix navigation tabs — CSS `display: flex` on `.panel--logs`/`.panel--search` overrides HTML `hidden` attribute, making Logs always visible — see BUGS.md B17
- [x] **B13**: Duplicate book upload fails silently — add backend logging and show error inside upload dialog — see BUGS.md B13
- [ ] **B14**: "Test LLM" button is a stub — wire to real LLMClient connectivity check — see BUGS.md B14
- [ ] **B15**: Settings dialog action buttons unreadable — add themed CSS for `.dialog__actions button` — see BUGS.md B15
- [ ] **B16**: Add "Clear All Data" button to delete all books and reset databases — see BUGS.md B16

---

## Decisions Log

| Date | Task | Decision | Rationale |
|------|------|----------|-----------|
| 2026-04-07 | B01 | Persist `SearchEngine` docs to `documents.json` under per-book index dir; align search API with `settings.data_dir` | Exact search must see chunks after upload when a new `SearchEngine` instance is constructed per request |
| 2026-04-07 | B02 | Map Chroma distances to `score = 1/(1+dist)` for hybrid merge (higher is better) | Aligns with `HybridSearch.merge_results` summing scores |
| 2026-04-07 | B03 | Persist to `{data_dir}/settings.json`; load known keys on import; `PUT`/`reset` sync disk | Matches BUGS.md; corrupt JSON logs warning and keeps defaults |
| 2026-04-07 | B04 | Remove `header-shimmer` animation and `@keyframes`; regression test forbids the string in `style.css` | Infinite filter animation on `.app-header` caused continuous GPU compositing when idle |
| 2026-04-07 | B05 | Default `embedding_model` = `paraphrase-multilingual-MiniLM-L12-v2`; wire upload/search/chat to settings; exact search uses `casefold` + Unicode `\w` tokens; sentence chunking adds `…` | Matches BUGS.md; English-only MiniLM poor for Russian; JSON-backed exact search is not Tantivy but needed Cyrillic-aware tokenization |
| 2026-04-07 | B06 | `#settings-llm-group-ollama` / `-cloud`; `applyLlmModeVisibility` + class `settings-llm-group--hidden`; max tokens & temperature in always-visible `settings-llm-shared`; `readForm` unchanged so hidden fields still save | BUGS.md: toggle with CSS only; all keys remain in DOM for preserve-on-switch |
| 2026-04-07 | B07 | Tab bar `settings-tabs` + panels `settings-panel-llm` / `settings-panel-embeddings`; `activateSettingsTab`; ARIA tablist/tab/tabpanel; LLM tab on each open and after reset | Matches BUGS.md; inactive panel `settings-tab-panel--hidden` |
| 2026-04-07 | B08 | `#settings-cloud-security-warning` in cloud group; copy cites `data/settings.json` (B03 path); `.settings-warning` amber styling; `hidden` toggled in `applyLlmModeVisibility` with cloud mode | Aligns with BUGS.md; `hidden` keeps notice out of accessibility tree when Ollama |
| 2026-04-07 | B09 | `app-main__view-switch` with `#main-nav-discussion` / `#main-nav-search`; removed header Search and `#search-back`; grid row for toolbar + `data-view` on `#app-main`; `.main-nav-btn--active` for current view | Matches BUGS.md symmetric nav; search panel stays full-width via existing `data-view="search"` CSS |
| 2026-04-07 | B10 | `RingBufferHandler` + deque(500) in `src/api/logs.py`; `GET /api/logs`; `install_memory_log_handler()` from `main.py`; `#main-nav-logs`, `data-view="logs"`, `log-viewer.js` polls and scrolls `<pre>` | BUGS.md option (b); polling while Logs tab active only |
| 2026-04-07 | B11 | `logger.info` in `BookProcessor.process_book` (parser, chapters, chunker, embeddings, ChromaDB collection+count, SearchEngine `index_path`+doc count, elapsed); upload logs save path, dirs, success | BUGS mentions Tantivy; app uses `SearchEngine` JSON index — logged as SearchEngine path |
| 2026-04-07 | B12 | Document finite `max_iterations` in `prompt.md` + `.cursor/rules/ralph-loop.mdc`; regression test `test_prompt_documents_ralph_loop_finite_max_iterations_safety` | BUGS.md B12: avoid unlimited loop when completion promise does not stop the scheduler |
| 2026-04-07 | B17 | `.view--hidden { display: none !important }`; `setView` uses `classList.toggle` on chat/refs/search/logs; HTML uses `view--hidden` on `#view-search`/`#view-logs` (no boolean `hidden`) | BUGS.md B17 approach (a): author `display:flex` overrides `[hidden]` |
| 2026-04-07 | B13 | `logger.warning` on duplicate hash before 409; `#upload-feedback` + `.upload-feedback--error` in dialog; `book-upload.js` shows `error.message` in-dialog; still calls `onError` for status bar | BUGS.md B13 |

---

## Issues & Blockers

| Date | Task | Issue | Status |
|------|------|-------|--------|

---

## Notes

- Bug specs are in `BUGS.md` (read-only for the agent).
- Build history is archived in `progress-v1-build.md`.
- Ralph Loop: use a **finite** `max_iterations` in scratchpad (e.g. 15–100), not `0` unlimited — see `prompt.md` header.
- Always run `pytest tests/ -v --tb=short` before committing (from repo root with `PYTHONPATH` set to the project root if imports fail).
- Commit format: `fix: B{XX} - {brief description}`.
