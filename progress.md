# ReadQuarry — Progress Tracker (Bugfix Phase)

> This file is the Ralph Loop agent's long-term memory. It is updated after every completed task.

---

## Current Status

**Phase**: 6 — Bug Fixes
**Next Task**: B09
**Last Completed**: B08
**Total Progress**: 8 / 12 tasks

---

## Task Log

### Phase 6: Bug Fixes

- [x] **B01**: Unify book storage — move from in-memory dict to SQLAlchemy DB so chat sessions can find uploaded books — see BUGS.md B01
- [x] **B02**: Wire semantic search to real EmbeddingService + VectorStore instead of placeholder — see BUGS.md B02
- [x] **B03**: Persist settings to JSON file on disk so they survive restarts — see BUGS.md B03
- [x] **B04**: Fix GPU idle load caused by infinite CSS header-shimmer animation — see BUGS.md B04
- [x] **B05**: Add multi-language support (Russian + English) for embeddings, search, and chunking — see BUGS.md B05
- [x] **B06**: Split LLM settings into Ollama/Cloud groups with dropdown selector and conditional field visibility — see BUGS.md B06
- [x] **B07**: Reorganize settings dialog into tabbed layout (LLM / Embeddings & Search) — see BUGS.md B07
- [x] **B08**: Show API key security warning when Cloud LLM mode is selected — see BUGS.md B08
- [ ] **B09**: Put Discussion and Search on separate screens with symmetric navigation buttons — see BUGS.md B09
- [ ] **B10**: Add debug log viewer as third navigation screen — see BUGS.md B10
- [ ] **B11**: Add detailed logging during book ingestion pipeline — see BUGS.md B11
- [ ] **B12**: Document Ralph Loop scratchpad safety cap requirement — see BUGS.md B12

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

---

## Issues & Blockers

| Date | Task | Issue | Status |
|------|------|-------|--------|

---

## Notes

- Bug specs are in `BUGS.md` (read-only for the agent).
- Build history is archived in `progress-v1-build.md`.
- Always run `pytest tests/ -v --tb=short` before committing.
- Commit format: `fix: B{XX} - {brief description}`.
