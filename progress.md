# ReadQuarry — Progress Tracker (Bugfix Phase 9)

> This file is the Ralph Loop agent's long-term memory. It is updated after every completed task.

---

## Current Status

**Phase**: 9 — Bug Fixes (Round 4)
**Next Task**: B01-TEST
**Last Completed**: B01-FE
**Total Progress**: 9 / 10 tasks

---

## Task Log

### Phase 9: Bug Fixes (Round 4)

- [x] **B02**: Clear chat on book switch — create new session instead of reusing old one — see BUGS.md B02
- [x] **B07**: Add "Clear Chat" button — clear messages and create new session — see BUGS.md B07
- [x] **B04**: Fix paragraph chunking — expand `clean_html` tag list to capture all block-level content — see BUGS.md B04
- [x] **B05**: Fix sentence chunking — handle paragraph boundaries in sentence splitting regex — see BUGS.md B05 (depends on B04)
- [x] **B06**: Fixed-size chunking UI — show chunk_size/overlap fields when "Fixed size" strategy selected — see BUGS.md B06
- [x] **B03a**: Backend: add `system_prompt` to settings defaults and wire into `_system_prompt()` — see BUGS.md B03a
- [x] **B03b**: Frontend: add "Prompts" tab to settings dialog with system prompt textarea — see BUGS.md B03b (depends on B03a)
- [x] **B01**: Real upload progress bar via SSE — replace fake animation with server-streamed progress events — see BUGS.md B01
- [x] **B01-FE**: Frontend: consume upload SSE stream and update progress bar with real stage data — see BUGS.md B01 (frontend part)
- [ ] **B01-TEST**: Integration test for upload SSE progress events — see BUGS.md B01 (test part)

---

## Decisions Log

| Date | Task | Decision | Rationale |
|------|------|----------|-----------|
| 2026-04-10 | B02 | Removed `ensureSession` / `listChatSessions`; book `onChange` always `createChatSession({ book_id })` then `loadHistory` (empty for new session) | BUGS.md B02 |
| 2026-04-10 | — | Ollama integration tests `pytest.skip` on `httpx.HTTPStatusError` from `/api/chat` when Ollama is up but model errors (e.g. 500) | Stable full-suite gate |
| 2026-04-10 | B07 | `#clear-chat` in `index.html`; `app.js` click → `createChatSession`, `sessionId`, `chatApi.clearMessages()`, `refs.clear()`, status "New conversation started"; no-op if no book | BUGS.md B07 |
| 2026-04-10 | B04 | `_EXTRACT_BLOCK_TAGS` adds blockquote, dd, dt, figcaption, td, th, pre, div; emit only tags with no inner extractable descendant (dedupe + leaf divs); `find_all` order preserves document order | BUGS.md B04 |
| 2026-04-10 | B05 | `SentenceChunking.chunk` splits on `\n\s*\n` first, then `(?<=[.!?…])\s+` per paragraph so `\n\n` separates units without terminal punctuation | BUGS.md B05 |
| 2026-04-10 | B06 | Upload: `#upload-fixed-size-options` + `uploadBook(..., { chunkSize, overlapRatio })` → Form `chunk_size`/`overlap_ratio`; API validates 50–2000 / 0–0.5; `BookProcessor.process_book` forwards to `FixedSizeChunking` (defaults 256/0.15 when omitted) | BUGS.md B06 |
| 2026-04-10 | B03a | `SYSTEM_PROMPT_DEFAULT` + `DEFAULTS["system_prompt"]`; `SettingsUpdate.system_prompt`; `_system_prompt(app_settings)` uses `get` + None guard; `_stream_chat` passes `app_settings` | BUGS.md B03a |
| 2026-04-10 | B03b | Settings: third tab `#settings-tab-prompts` / `#settings-panel-prompts` + `#settings-system_prompt`; `FIELD_KEYS` + `activateSettingsTab("llm"|"embeddings"|"prompts")`; load/save via existing `fillForm`/`readForm` | BUGS.md B03b |
| 2026-04-10 | B01 | `POST /upload` → `StreamingResponse` SSE (`stage`/`progress`/`detail`); `BookProcessor.iter_ingestion` yields progress bands B01; `done` carries `book`; failures → SSE `error` + cleanup (HTTP 200). `process_book` drains `iter_ingestion`; optional `on_progress` | BUGS.md B01 |
| 2026-04-10 | B01-FE | `uploadBook` fourth arg `onProgress`; `_consumeBookUploadSse` + `getReader`/`text/event-stream`; `#upload-stage` + `.upload-stage` CSS; `book-upload.js` removes fake `setInterval`, drives bar + label from SSE | BUGS.md B01 |

---

## Issues & Blockers

| Date | Task | Issue | Status |
|------|------|-------|--------|

---

## Notes

- Previous phases archived in `archive_tasks/`.
- Bug specs are in `BUGS.md` (read-only for the agent).
- Ralph Loop: use a **finite** `max_iterations` in scratchpad (e.g. 30–50), not `0` unlimited — see `prompt.md` header.
- Always run `pytest tests/ -v --tb=short` before committing (from repo root).
- Commit format: `fix: B{XX} - {brief description}`.
- **Task ordering matters**: B05 depends on B04, B03b depends on B03a. B01 is split into three sub-tasks.
- B01 is placed last because it is the most complex (SSE refactor of upload). Quick wins (B02, B07, B04) come first.
