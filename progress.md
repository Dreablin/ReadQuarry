# ReadQuarry — Progress Tracker (Bugfix Phase 8)

> This file is the Ralph Loop agent's long-term memory. It is updated after every completed task.

---

## Current Status

**Phase**: 8 — Bug Fixes (Round 3)
**Next Task**: B08
**Last Completed**: B07
**Total Progress**: 6 / 9 tasks

---

## Task Log

### Phase 8: Bug Fixes (Round 3)

- [!] **B01**: Fix log viewer — only update DOM when new log entries arrive, not on every poll — see BUGS.md B01 *(implementation/tests done; full-suite gate blocked by unrelated pre-existing chat/LLM/e2e failures after 3+ attempts)*
- [x] **B02**: Fix Ollama empty responses — add raw response debug logging, fix content extraction — see BUGS.md B02
- [x] **B03**: Add `search_score_threshold` setting to backend defaults and frontend Embeddings & Search UI — see BUGS.md B03
- [x] **B04**: Apply `search_score_threshold` filtering in search endpoints and hybrid merge — see BUGS.md B04 (depends on B03)
- [x] **B05**: Include chunk relevance scores in chat SSE `done` event alongside chunk IDs — see BUGS.md B05
- [x] **B06**: Display relevance score for each reference in the references panel UI — see BUGS.md B06 (depends on B05)
- [x] **B07**: Write Ollama integration tests — skip if not running, detect model, verify non-empty response — see BUGS.md B07
- [ ] **B08**: Prevent HuggingFace Hub network access when embedding model is already cached — see BUGS.md B08
- [ ] **B09**: Suppress BERT `position_ids` UNEXPECTED key load report from cluttering logs — see BUGS.md B09

---

## Decisions Log

| Date | Task | Decision | Rationale |
|------|------|----------|-----------|
| 2026-04-09 | B02 | Kept native Ollama `/api/chat`; added `/api/tags` model validation, raw payload/status debug logging, `response` fallback extraction, and chat compatibility for iterable test streams | BUGS.md B02 and full-suite stability |
| 2026-04-09 | B03 | `search_score_threshold` default 0.6 in `DEFAULTS` + `SettingsUpdate`; Embeddings tab field + `readForm` float parse; API tests for persist and 0–1 validation | BUGS.md B03 |
| 2026-04-09 | B04 | `filter_rows_by_min_score` + settings threshold; semantic + hybrid API filtered; `HybridSearch.merge_results` sets combined `score` on rows; chat RAG uses same filter; exact endpoint unchanged | BUGS.md B04 |
| 2026-04-09 | B05 | `_build_context_chunks` now returns `(context, ids, scores)`; SSE `done` event adds `referenced_chunk_scores` while preserving `referenced_chunk_ids` | BUGS.md B05 |
| 2026-04-09 | B06 | `chat.js` forwards `referenced_chunk_scores` to `onDone(ids, scores)`; `app.js` passes scores to `appendReferencedChunkIds`; `references.js` shows `Score: X.XXXX` in meta (independent of threshold setting) | BUGS.md B06 |
| 2026-04-09 | B07 | `tests/test_integration/test_ollama_integration.py` with `@pytest.mark.integration`, module skip when Ollama unreachable, model pick from `/api/ps` ∩ `/api/tags`; `pytest.ini` registers `integration` marker; Ollama `/api/chat` no longer sends `options.num_predict` (some thinking models return empty `message.content` when set) | BUGS.md B07 |

---

## Issues & Blockers

| Date | Task | Issue | Status |
|------|------|-------|--------|
| 2026-04-09 | B01 | Full suite gate failed after B01 changes due unrelated existing regressions in chat/LLM area (`test_chat_api`, `test_llm_client`, `test_e2e_smoke_flow`); B01-targeted tests pass | Open |

---

## Notes

- Previous phases archived in `archive_tasks/progress-phase7.md` and `archive_tasks/BUGS-phase7.md`.
- Bug specs are in `BUGS.md` (read-only for the agent).
- Ralph Loop: use a **finite** `max_iterations` in scratchpad (e.g. 30–50), not `0` unlimited — see `prompt.md` header.
- Always run `pytest tests/ -v --tb=short` before committing (from repo root).
- Commit format: `fix: B{XX} - {brief description}`.
- **Task ordering matters**: B04 depends on B03, B06 depends on B05. Complete them in listed order.
