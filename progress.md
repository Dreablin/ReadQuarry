# ReadQuarry — Progress Tracker (Bugfix Phase 10)

> This file is the Ralph Loop agent's long-term memory. It is updated after every completed task.

---

## Current Status

**Phase**: 10 — Bug Fixes (Round 5)
**Next Task**: B02
**Last Completed**: B01
**Total Progress**: 1 / 9 tasks

---

## Task Log

### Phase 10: Bug Fixes (Round 5)

- [x] **B01**: Clear references before each new AI response — call `refs.clear()` before `appendReferencedChunkIds` — see BUGS.md B01
- [ ] **B02**: Save chunks to `data/book_load_chunks.txt` during ingestion — see BUGS.md B02
- [ ] **B03**: Add `llm_timeout` setting (default 300s) and wire to LLMClient — see BUGS.md B03
- [ ] **B04**: Add tag system to log entries (INFO, TIME, LLM) — update `RingBufferHandler` and API — see BUGS.md B04
- [ ] **B05**: Add duration logging with TIME tag for search, chat, embedding operations — see BUGS.md B05 (depends on B04)
- [ ] **B06**: Log full LLM prompt and response with LLM tag — see BUGS.md B06 (depends on B04)
- [ ] **B07**: Add tag filter dropdown to Logs viewer — see BUGS.md B07 (depends on B04)
- [ ] **B03-FE**: Add `llm_timeout` input to Settings LLM tab and wire in `settings.js` — see BUGS.md B03 (frontend part)
- [ ] **B07-CSS**: Style the log filter bar to match the app theme — see BUGS.md B07 (CSS part, depends on B07)

---

## Decisions Log

| Date | Task | Decision | Rationale |
|------|------|----------|-----------|
| 2026-04-10 | B01 | Structural test parses `onDone` arrow callback body and asserts `refs.clear()` before `appendReferencedChunkIds`. | Keeps B01 covered without a browser harness; matches BUGS.md ordering requirement. |

---

## Issues & Blockers

| Date | Task | Issue | Status |
|------|------|-------|--------|

---

## Notes

- Previous phases archived in `archive_tasks/`.
- Bug specs are in `BUGS.md` (read-only for the agent).
- Ralph Loop: use a **finite** `max_iterations` in scratchpad (e.g. 30–50), not `0` unlimited.
- Always run `pytest tests/ -v --tb=short` before committing (from repo root).
- Commit format: `fix: B{XX} - {brief description}`.
- **Task ordering matters**: B05, B06, and B07 depend on B04. B03-FE follows B03. B07-CSS follows B07.
- Independent tasks (B01, B02, B03) come first as quick wins before the tag infrastructure (B04).
