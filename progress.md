# ReadQuarry — Progress Tracker (Bugfix Phase)

> This file is the Ralph Loop agent's long-term memory. It is updated after every completed task.

---

## Current Status

**Phase**: 6 — Bug Fixes
**Next Task**: B05
**Last Completed**: B04
**Total Progress**: 4 / 12 tasks

---

## Task Log

### Phase 6: Bug Fixes

- [x] **B01**: Unify book storage — move from in-memory dict to SQLAlchemy DB so chat sessions can find uploaded books — see BUGS.md B01
- [x] **B02**: Wire semantic search to real EmbeddingService + VectorStore instead of placeholder — see BUGS.md B02
- [x] **B03**: Persist settings to JSON file on disk so they survive restarts — see BUGS.md B03
- [x] **B04**: Fix GPU idle load caused by infinite CSS header-shimmer animation — see BUGS.md B04
- [ ] **B05**: Add multi-language support (Russian + English) for embeddings, search, and chunking — see BUGS.md B05
- [ ] **B06**: Split LLM settings into Ollama/Cloud groups with dropdown selector and conditional field visibility — see BUGS.md B06
- [ ] **B07**: Reorganize settings dialog into tabbed layout (LLM / Embeddings & Search) — see BUGS.md B07
- [ ] **B08**: Show API key security warning when Cloud LLM mode is selected — see BUGS.md B08
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
