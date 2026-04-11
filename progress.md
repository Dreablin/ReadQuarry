# ReadQuarry — Progress Tracker (Bugfix Phase 10)

> This file is the Ralph Loop agent's long-term memory. It is updated after every completed task.

---

## Current Status

**Phase**: 10 — Bug Fixes (Round 5)
**Next Task**: B07
**Last Completed**: B06
**Total Progress**: 6 / 9 tasks

---

## Task Log

### Phase 10: Bug Fixes (Round 5)

- [x] **B01**: Clear references before each new AI response — call `refs.clear()` before `appendReferencedChunkIds` — see BUGS.md B01
- [x] **B02**: Save chunks to `data/book_load_chunks.txt` during ingestion — see BUGS.md B02
- [x] **B03**: Add `llm_timeout` setting (default 300s) and wire to LLMClient — see BUGS.md B03
- [x] **B04**: Add tag system to log entries (INFO, TIME, LLM) — update `RingBufferHandler` and API — see BUGS.md B04
- [x] **B05**: Add duration logging with TIME tag for search, chat, embedding operations — see BUGS.md B05 (depends on B04)
- [x] **B06**: Log full LLM prompt and response with LLM tag — see BUGS.md B06 (depends on B04)
- [ ] **B07**: Add tag filter dropdown to Logs viewer — see BUGS.md B07 (depends on B04)
- [ ] **B03-FE**: Add `llm_timeout` input to Settings LLM tab and wire in `settings.js` — see BUGS.md B03 (frontend part)
- [ ] **B07-CSS**: Style the log filter bar to match the app theme — see BUGS.md B07 (CSS part, depends on B07)

---

## Decisions Log

| Date | Task | Decision | Rationale |
|------|------|----------|-----------|
| 2026-04-10 | B01 | Structural test parses `onDone` arrow callback body and asserts `refs.clear()` before `appendReferencedChunkIds`. | Keeps B01 covered without a browser harness; matches BUGS.md ordering requirement. |
| 2026-04-10 | B02 | `GET`/`SSE` book payloads include `total_chunks`; B06 API test compares upload `done` book counts instead of `GET /chunks` length. | Chunk rows can accumulate in the dev SQLite DB across runs; `total_chunks` reflects the current ingestion. |
| 2026-04-10 | B03 | Cloud `OpenAI` client always receives `timeout=self._timeout` (resolved from settings or kwarg). | Aligns cloud chat with configurable `llm_timeout`; `/test-llm` still passes `timeout=10.0` explicitly. |
| 2026-04-10 | B04 | `get_logs()` normalizes legacy buffer rows with `setdefault("tag", "INFO")` when building the response. | Ring buffer may contain pre-B04 dicts without `tag` during long-lived test processes. |
| 2026-04-10 | B05 | Chat RAG sub-steps (embed, Chroma, exact, merge) log only when the book has chunks; `_stream_chat` always logs context build + LLM + pipeline totals. | Matches BUGS: skip heavy steps when `n_chunks == 0`; pipeline timing still useful. |
| 2026-04-10 | B06 | Prompt log capped at 5000 chars; response body log capped at 2000 chars (BUGS examples). | Keeps ring buffer usable; metadata `LLM request … context_chars` retained. |

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
