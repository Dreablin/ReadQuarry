# ReadQuarry — Bug Reports (Phase 10)

> This file is the bug specification reference for the Ralph Loop bugfix phase.
> **Do NOT modify this file from the loop** — it is read-only for the agent.

---

## B01 — References panel accumulates chunks from all responses — should show only current response's references

**Severity**: major
**Where**: `static/js/app.js`, `static/js/components/references.js`
**Steps to reproduce**:
1. Select a book, send a chat message — references appear in the right panel.
2. Send a second chat message — new references are **appended** below the old ones.
3. The panel now shows references from both messages, making it unclear which chunks belong to the latest response.

**Expected behavior**: Before adding new references from each AI response, the references panel should be cleared so it always shows only the references relevant to the latest response.
**Actual behavior**: `app.js` `onDone` callback calls `refs.appendReferencedChunkIds(bid, ids, scores)` without clearing first. `appendReferencedChunkIds` counts existing `.reference-chunk` nodes and continues ordinal numbering.

**Root cause** (`static/js/app.js` lines ~195-198):
```javascript
onDone: (ids, scores) => {
  const bid = bookListRef?.getSelectedBookId() ?? null;
  if (bid != null) void refs.appendReferencedChunkIds(bid, ids, scores);
},
```
No `refs.clear()` call before appending.

**Fix requirements**:
1. **`app.js`**: In the `onDone` callback, add `refs.clear()` **before** calling `refs.appendReferencedChunkIds(...)`:
   ```javascript
   onDone: (ids, scores) => {
     const bid = bookListRef?.getSelectedBookId() ?? null;
     if (bid != null) {
       refs.clear();
       void refs.appendReferencedChunkIds(bid, ids, scores);
     }
   },
   ```
2. No backend changes needed.
3. Tests: verify references panel is cleared before each new set of references is displayed.

---

## B02 — Save chunks to a debug file during book ingestion

**Severity**: minor
**Where**: `src/core/book_processor.py`, `config.py`
**Steps to reproduce**: N/A — feature does not exist yet.

**Expected behavior**: When a book is uploaded and chunked, all resulting chunks are also written to `data/book_load_chunks.txt` for debugging. Each chunk is separated by a line of dashes `"--------------"`. If the file already exists, it is deleted before writing new chunks.
**Actual behavior**: Chunks are only stored in SQLite and ChromaDB — no human-readable debug file.

**Fix requirements**:
1. **`src/core/book_processor.py`** in `iter_ingestion()`, after the chunking loop builds the `chunks` list (after the `logger.info("Chunking ...")` call):
   - Compute path: `chunks_file = Path(settings.data_dir) / "book_load_chunks.txt"` (import `settings` from `config`).
   - If the file exists, delete it.
   - Write all chunks to the file: for each chunk in `chunks`, write `chunk["text"]` followed by a separator line `"--------------"`. Use UTF-8 encoding.
   - Log: `logger.info("Saved %d chunks to %s", len(chunks), chunks_file)`.
2. This file is in `data/` which is already gitignored.
3. Tests: verify the file is created with correct content and separator, and that it is deleted and recreated on subsequent uploads.

---

## B03 — Add `llm_timeout` setting (default 300 seconds) to LLM configuration

**Severity**: major
**Where**: `src/api/settings.py`, `src/core/llm_client.py`, `src/api/chat.py`
**Steps to reproduce**:
1. Send a complex question to an LLM that takes >120 seconds to respond.
2. The request times out because `llm_client.py` uses `timeout = self._timeout or 120.0`.

**Expected behavior**: The timeout is configurable in Settings and defaults to 300 seconds.
**Actual behavior**: Hardcoded to 120 seconds in `_ollama_chat()` at line `timeout = self._timeout or 120.0`. The `LLMClient` constructor accepts an optional `timeout` parameter, but `chat.py` never passes it — `LLMClient(dict(app_settings))` uses no timeout kwarg.

**Fix requirements**:
1. **Settings** (`src/api/settings.py`):
   - Add `"llm_timeout": 300` to `DEFAULTS`.
   - Add `llm_timeout: int | None = Field(default=None, gt=0, le=600)` to `SettingsUpdate`.
2. **LLM Client** (`src/core/llm_client.py`):
   - In `__init__`, if `timeout` is `None`, read `settings.get("llm_timeout", 300)` and use that.
   - Update the Ollama path: `timeout = self._timeout or float(self._settings.get("llm_timeout", 300))`.
3. **Chat** (`src/api/chat.py`): No explicit change needed if `LLMClient` reads timeout from settings dict. But if not already passing, ensure `LLMClient(dict(app_settings))` includes the `llm_timeout` key (it does since it passes the full settings dict).
4. **Frontend**: Add the field to the LLM tab in `index.html` (shared section, visible for both Ollama and Cloud):
   ```html
   <label for="settings-llm_timeout">LLM timeout (seconds)</label>
   <input type="number" id="settings-llm_timeout" name="llm_timeout" min="10" max="600" step="10" />
   ```
   Add `"llm_timeout"` to `FIELD_KEYS` in `settings.js` and parse as int in `readForm()`.
5. Tests: verify the setting persists, the LLMClient uses it, and the default is 300.

---

## B04 — Add tag system to log entries (INFO, TIME, LLM)

**Severity**: major
**Where**: `src/api/logs.py`
**Steps to reproduce**: N/A — feature does not exist. Logs currently have no tag/category system.

**Expected behavior**: Each log entry has a `tag` field. Standard informational logs are tagged `INFO`. Duration/timing logs are tagged `TIME`. LLM communication logs are tagged `LLM`. The API returns the tag with each entry, and also returns a list of all distinct tags seen.
**Actual behavior**: Log entries have `time`, `level`, `logger`, `message` — no tag field.

**Fix requirements**:
1. **`src/api/logs.py`** — `RingBufferHandler.emit()`:
   - Read `tag` from the log record's `extra` dict: `tag = getattr(record, "tag", "INFO")`.
   - Include it in the entry dict: `"tag": tag`.
2. **`src/api/logs.py`** — `get_logs()` endpoint:
   - In addition to `entries` and `count`, return `"tags"`: a sorted list of all unique tags seen across all entries in the buffer. Example: `{"entries": [...], "count": 42, "tags": ["INFO", "LLM", "TIME"]}`.
3. **Helper function**: Create a module-level helper in a common location (or in `logs.py` itself) so other modules can easily log with a tag:
   ```python
   def log_with_tag(lgr: logging.Logger, level: int, tag: str, msg: str, *args: Any) -> None:
       lgr.log(level, msg, *args, extra={"tag": tag})
   ```
   Or simpler: just document that `logger.info("msg", extra={"tag": "TIME"})` works.
4. Tests: verify entries have a `tag` field defaulting to `"INFO"`, and that custom tags propagate correctly.

---

## B05 — Add duration logging with TIME tag for all long operations

**Severity**: major
**Where**: `src/api/chat.py`, `src/api/search.py`, `src/core/book_processor.py`
**Depends on**: B04 (tag system must exist first)
**Steps to reproduce**:
1. Open Logs tab.
2. Perform a search or chat — no timing information is shown for individual operations.

**Expected behavior**: Every long operation logs its duration with the `TIME` tag:
- Query vectorization (embedding the search query)
- Semantic search (ChromaDB query)
- Exact search (SearchEngine query)
- Hybrid merge
- LLM response generation time
- Total chat response pipeline time

**Actual behavior**: Only book ingestion logs total elapsed time. Search and chat operations have no duration logging.

**Fix requirements**:
1. **`src/api/search.py`**:
   - `semantic_search`: wrap in `time.perf_counter()`, log: `logger.info("[TIME] Semantic search book_id=%s elapsed=%.3fs", ..., extra={"tag": "TIME"})`.
   - `exact_search`: same pattern.
   - `hybrid_search`: log total time.
2. **`src/api/chat.py`** in `_build_context_chunks`:
   - Time the embedding step: `embedder.embed_text(query)`.
   - Time the ChromaDB query.
   - Time the exact search.
   - Time the hybrid merge.
   - Log each with `extra={"tag": "TIME"}`.
3. **`src/api/chat.py`** in `_stream_chat`:
   - Time `_build_context_chunks(...)` total.
   - Time `llm.chat_completion(...)`.
   - Time total pipeline (from user message receipt to assistant message commit).
   - Log each with `extra={"tag": "TIME"}`.
4. **`src/core/book_processor.py`**: The existing `elapsed_seconds` log at the end of ingestion should use `extra={"tag": "TIME"}`.
5. Tests: verify TIME-tagged entries appear after search and chat operations.

---

## B06 — Log full LLM prompt with LLM tag

**Severity**: major
**Where**: `src/api/chat.py`
**Depends on**: B04 (tag system must exist first)
**Steps to reproduce**:
1. Send a chat message.
2. Check Logs — the LLM request is logged with `messages` count and `context_chars`, but the actual prompt content is not visible.

**Expected behavior**: The full prompt (system message + user message with RAG context) is logged with the `LLM` tag so the user can inspect exactly what was sent to the model.
**Actual behavior**: Only metadata is logged: `"LLM request session_id=%s messages=%d context_chars=%d"`.

**Fix requirements**:
1. **`src/api/chat.py`** in `_stream_chat`, after building the `messages` list and before calling `llm.chat_completion(...)`:
   - Log the full prompt with the `LLM` tag:
     ```python
     prompt_text = "\n---\n".join(f"[{m['role']}]\n{m['content']}" for m in messages)
     logger.info(
         "[LLM] Full prompt for session_id=%s:\n%s",
         session_id, prompt_text,
         extra={"tag": "LLM"},
     )
     ```
   - Also log the LLM response content with the `LLM` tag:
     ```python
     logger.info(
         "[LLM] Response for session_id=%s (%d chars):\n%s",
         session_id, len(content), content[:2000],
         extra={"tag": "LLM"},
     )
     ```
2. Truncate very long prompts in the log to prevent the ring buffer from filling with a single entry (e.g. first 5000 chars).
3. Tests: verify LLM-tagged entries appear containing the prompt content.

---

## B07 — Add tag filter dropdown to the Logs viewer

**Severity**: major
**Where**: `static/index.html`, `static/js/components/log-viewer.js`, `static/js/api.js`
**Depends on**: B04 (backend must return `tag` field and `tags` list)
**Steps to reproduce**:
1. Open the Logs tab — all log entries are shown with no way to filter.

**Expected behavior**: A dropdown below the log viewer with options: "ALL" (default) plus every tag that exists in the system (e.g. INFO, TIME, LLM). Selecting a tag shows only entries with that tag. Selecting ALL shows everything.
**Actual behavior**: No filter UI exists.

**Fix requirements**:
1. **HTML** (`static/index.html`): Add a filter bar below `#log-viewer-output` inside `#view-logs`:
   ```html
   <div class="log-filter">
     <label for="log-filter-tag">Filter by tag:</label>
     <select id="log-filter-tag">
       <option value="ALL">ALL</option>
     </select>
   </div>
   ```
2. **`log-viewer.js`**:
   - Get the `#log-filter-tag` select element.
   - In `refresh()`, after fetching `data`:
     a. Read `data.tags` (array of strings). Update the dropdown options: keep "ALL" as first, then add an `<option>` for each tag not already present. Do not remove options that disappeared (tags are additive).
     b. Read the current filter value from the select.
     c. If filter is not "ALL", filter `entries` to only those where `entry.tag === filterValue`.
     d. Render only the filtered entries.
   - When the user changes the filter dropdown, trigger a refresh immediately (or just re-render from cached data).
3. **API** (`static/js/api.js`): No changes needed — `fetchLogs()` already returns the full response which will now include `tags`.
4. Tests: verify the filter dropdown renders tags and filters entries correctly.
