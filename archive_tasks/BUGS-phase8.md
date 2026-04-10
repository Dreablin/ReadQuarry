# ReadQuarry — Bug Reports (Phase 8)

> This file is the bug specification reference for the Ralph Loop bugfix phase.
> **Do NOT modify this file from the loop** — it is read-only for the agent.

---

## B01 — Log viewer resets text selection every 2 seconds — impossible to copy log entries

**Severity**: major
**Where**: `static/js/components/log-viewer.js`, `src/api/logs.py`
**Steps to reproduce**:
1. Open the app, switch to the Logs tab.
2. Try to select text in the log viewer to copy it.
3. Every 2 seconds the selection disappears because the DOM is fully replaced.

**Expected behavior**: The log viewer updates only when new log entries arrive. Text selection should remain stable between polls.
**Actual behavior**: `log-viewer.js` calls `fetchLogs()` every 2 seconds via `setInterval` and **unconditionally** replaces `pre.textContent = lines.join("\n")`, destroying any text selection.

**Root cause** (in `static/js/components/log-viewer.js`):
```javascript
async function refresh() {
  const data = await fetchLogs();
  const entries = Array.isArray(data?.entries) ? data.entries : [];
  const lines = entries.map((e) => ...);
  pre.textContent = lines.join("\n");     // ← always replaces, even if nothing changed
  pre.scrollTop = pre.scrollHeight;
}
```
No comparison is done between old and new content.

**Fix requirements**:
1. **Backend** (`src/api/logs.py`): Add a `count` field to the `GET /api/logs` response: `{"entries": [...], "count": len(_LOG_BUFFER)}`. The count is the total number of entries ever appended (or simply `len(_LOG_BUFFER)` if that is sufficient for change detection). Alternatively, return a monotonic `seq` or timestamp of the latest entry.
2. **Frontend** (`static/js/components/log-viewer.js`):
   - Track the last known entry count (e.g. `let lastCount = -1`).
   - In `refresh()`, compare `data.count` (or `entries.length`) to `lastCount`. **Only update DOM if count changed.**
   - When updating, set `lastCount = data.count`.
   - Auto-scroll only on update, not on no-op polls.
3. Tests: verify the log viewer component tracks `lastCount` and skips DOM writes when count is unchanged.

---

## B02 — Ollama always returns "[Empty block returned from LLM]" — chat responses are blank

**Severity**: critical
**Where**: `src/core/llm_client.py`, `src/api/chat.py`
**Steps to reproduce**:
1. Have Ollama running locally with any model loaded.
2. Upload a book, select it, send any chat message.
3. The assistant always responds with "[Empty block returned from LLM]".

**Expected behavior**: The assistant returns a meaningful text response from the Ollama model.
**Actual behavior**: `chat.py` line ~162 fires `logger.warning("LLM returned empty response")` and substitutes the placeholder because `content` is empty string.

**Investigation path**:
The `_ollama_chat` method in `llm_client.py` sends a request to `{ollama_base}/api/chat` and parses `data.get("message").get("content", "")`. Possible causes of empty content:

1. **Model mismatch**: settings have `ollama_model_id: "llama3.2"` but the user has a different model loaded (e.g. `qwen2.5:7b`). Ollama may auto-pull and timeout, or return an empty response for a missing model.
2. **Response parsing**: the raw Ollama JSON response may have a different structure than expected (e.g. `response` field instead of `message.content` for certain API versions).
3. **Content lost in wrapper**: the `_OllamaResponse`/`_OllamaChoice`/`_OllamaMessage` wrappers may silently swallow content.

**Fix requirements**:
1. **Add raw response logging** in `_ollama_chat` (in `src/core/llm_client.py`):
   - After `data = resp.json()`, add `logger.debug("Ollama raw response body: %s", json.dumps(data, ensure_ascii=False)[:2000])` (truncate to avoid flooding).
   - Log `resp.status_code` explicitly.
2. **Robust content extraction**: After extracting `content` from `data["message"]["content"]`, also check `data.get("response", "")` as a fallback (Ollama's `/api/generate` format). Log which field was used.
3. **Model validation**: Before making the completion call, log the model name from settings and consider calling `GET {ollama_base}/api/tags` to verify the model exists. If it doesn't, return a clear error message instead of an empty response.
4. **Empty response detail**: In `chat.py`, when content is empty, include the raw response length and model name in the warning log: `logger.warning("LLM returned empty response session_id=%s model=%s raw_len=%d", session_id, model_name, len(raw_body))`.
5. Tests: mock Ollama response with real JSON shape and verify non-empty content is passed through.

---

## B03 — Add `search_score_threshold` setting to backend and frontend

**Severity**: major
**Where**: `src/api/settings.py`, `static/index.html`, `static/js/components/settings.js`
**Steps to reproduce**:
1. Open Settings → Embeddings & Search tab.
2. There is no option to set a minimum score threshold for search results.

**Expected behavior**: A new "Search score threshold" field in the Embeddings & Search settings tab with default value `0.6`. The value is persisted like other settings.
**Actual behavior**: No such setting exists. Search always returns exactly `top_k` / `max_results` results regardless of how relevant they are.

**Fix requirements**:
1. **Backend** (`src/api/settings.py`):
   - Add `"search_score_threshold": 0.6` to `DEFAULTS` dict.
   - Add `search_score_threshold: float | None = Field(default=None, ge=0.0, le=1.0)` to `SettingsUpdate` model.
2. **Frontend** (`static/index.html`):
   - Add a new field in `#settings-panel-embeddings` fieldset:
     ```html
     <label for="settings-search_score_threshold">Search score threshold</label>
     <input type="number" id="settings-search_score_threshold" name="search_score_threshold" min="0" max="1" step="0.05" />
     ```
3. **Frontend** (`static/js/components/settings.js`):
   - Add `"search_score_threshold"` to the `FIELD_KEYS` array.
   - In `readForm()`, parse it as a float (same as `temperature`).
4. Tests: verify the new setting appears in defaults, can be updated via PUT, and persists in JSON file.

---

## B04 — Apply search score threshold filtering to search results

**Severity**: major
**Where**: `src/api/search.py`, `src/core/hybrid_search.py`, `src/api/chat.py`
**Depends on**: B03 (the setting must exist first)
**Steps to reproduce**:
1. Upload a book, go to Search, search for something generic.
2. All `top_k` results are returned even if most have very low scores (e.g. 0.2).

**Expected behavior**: Results with score below `search_score_threshold` (default 0.6) are excluded. If all results are below threshold, return an empty list (not artificially padded results).
**Actual behavior**: No score filtering — all `top_k` results from ChromaDB and all `max_results` from exact search are returned regardless of score.

**Fix requirements**:
1. **Semantic search** (`src/api/search.py` → `semantic_search` and `_chroma_query_to_results`):
   - Read `search_score_threshold` from `get_settings()`.
   - After computing score for each result, filter out results where `score < threshold`.
2. **Exact search** (`src/api/search.py` → `exact_search`):
   - The exact search scores from `SearchEngine` are occurrence counts (1, 2, ...), not 0–1. These should NOT be filtered by the same threshold (they use a different scale). Leave exact search unfiltered, or normalize exact scores to 0–1 range before filtering.
   - Recommended: only apply threshold to semantic results and hybrid merge output, leave exact search as-is.
3. **Hybrid search** (`src/api/search.py` → `hybrid_search` or `src/core/hybrid_search.py`):
   - After `HybridSearch().merge_results(...)`, filter the merged list by threshold before returning.
   - The hybrid score is a sum of semantic + exact scores, which can exceed 1.0. Apply the threshold to the **semantic component** during merge, OR apply a normalized threshold after merge. Simplest: filter the final merged results by checking `row["score"] >= threshold` (since merged scores are additive, a combined score ≥ 0.6 means at least moderate relevance).
4. **Chat context** (`src/api/chat.py` → `_build_context_chunks`):
   - Also apply the threshold when building RAG context to avoid feeding low-relevance chunks to the LLM.
5. Tests: verify that results below threshold are excluded, and that an empty result set is returned when all scores are below threshold.

---

## B05 — Include chunk relevance scores in chat SSE done event

**Severity**: major
**Where**: `src/api/chat.py`
**Steps to reproduce**:
1. Send a chat message in Discussion.
2. The `done` SSE event contains only `referenced_chunk_ids` — no scores.

**Expected behavior**: The `done` SSE event includes both chunk IDs and their relevance scores, so the frontend can display how confident the model was about each reference.
**Actual behavior**: `_build_context_chunks` calculates scores internally (via `HybridSearch.merge_results`) but discards them — only returns `chunk_ids_ordered`.

**Fix requirements**:
1. **`_build_context_chunks`** in `src/api/chat.py`:
   - Change return type to `tuple[str, list[int], list[float]]` — add a list of scores parallel to `chunk_ids_ordered`.
   - When building `chunk_ids_ordered`, also collect `float(row.get("score", 0.0))` for each merged result.
2. **`_stream_chat`** in `src/api/chat.py`:
   - Unpack the third element: `context_text, ref_chunk_ids, ref_chunk_scores = _build_context_chunks(...)`.
   - In the `done` SSE event, include scores: `{"type": "done", "referenced_chunk_ids": ref_chunk_ids, "referenced_chunk_scores": ref_chunk_scores}`.
3. **`ChatMessage` storage** (optional): optionally persist scores alongside `referenced_chunks` in the DB. This can be a JSON dict mapping chunk_id to score, or a separate JSON array. If not stored, scores are only available for the current message (acceptable for now).
4. Tests: verify the `done` SSE payload contains `referenced_chunk_scores` as a list of floats with the same length as `referenced_chunk_ids`.

**Important**: This change must NOT break the existing `referenced_chunk_ids` field — it is additive.

---

## B06 — Display relevance score for each reference in the references panel

**Severity**: minor
**Where**: `static/js/components/references.js`, `static/js/components/chat.js`, `static/js/app.js`
**Depends on**: B05 (scores must be available in the SSE event)
**Steps to reproduce**:
1. Send a chat message in Discussion.
2. Look at the References panel — chunks are shown with [ordinal], chapter, chunk index, and text.
3. No indication of how relevant each reference is.

**Expected behavior**: Each reference card shows a relevance score (e.g. "Score: 0.8421") after the chunk index metadata. This helps the user judge quality of the references.
**Actual behavior**: No score is displayed. The score data is not passed from the chat component to the references component.

**Important note from the user**: The score display must NOT depend on or be limited by the search_score_threshold setting from B03/B04. It is purely informational — always display the score for every reference shown, regardless of threshold value.

**Fix requirements**:
1. **`chat.js`**: In the `done` event handler, pass `ev.referenced_chunk_scores` alongside `ev.referenced_chunk_ids` to `options.onDone(...)`. Update the `onDone` callback signature.
2. **`app.js`**: Update the `onDone` handler in `initChat` options to pass scores through to `refs.appendReferencedChunkIds(bid, ids, scores)`.
3. **`references.js`**:
   - Update `appendReferencedChunkIds(bookId, chunkIds, scores)` to accept an optional `scores` array.
   - When rendering each reference chunk, pass `score` to `renderReferenceChunk`.
   - In `renderReferenceChunk`, if a score is provided, add it to the meta line: after "Chunk index: N" add "· Score: 0.XXXX" (formatted to 4 decimal places).
4. Tests: verify the score is included in the rendered reference card metadata.

---

## B07 — Write Ollama integration tests — verify LLM interaction produces non-empty responses

**Severity**: major
**Where**: new file `tests/test_integration/test_ollama_integration.py`
**Steps to reproduce**: N/A — tests don't exist yet.

**Expected behavior**: Integration tests validate that the `LLMClient` → Ollama pipeline returns non-empty responses when Ollama is available.
**Actual behavior**: No integration tests for Ollama exist.

**Fix requirements**:
1. Create `tests/test_integration/__init__.py` and `tests/test_integration/test_ollama_integration.py`.
2. **Skip logic**: At the start of the test module or in a fixture, check if Ollama is running by attempting `GET http://localhost:11434/api/tags` (or `httpx.get("http://localhost:11434/api/tags", timeout=5)`). If the connection fails (refused, timeout), **skip the entire module** with `pytest.skip("Ollama is not running")`.
3. **Detect loaded model**: If Ollama is running, call `ollama ps` via `subprocess.run(["ollama", "ps"], capture_output=True, text=True)` or query `GET http://localhost:11434/api/ps` to find which model is currently loaded/running. Extract the model name from the output. If no model is loaded, try `GET http://localhost:11434/api/tags` to get the list of available models and pick the first one. If no models at all, skip with `pytest.skip("No Ollama models available")`.
4. **Test: non-empty response**: Instantiate `LLMClient` with settings `{"llm_mode": "ollama", "ollama_base_url": "http://localhost:11434", "ollama_model_id": detected_model, "max_tokens": 64, "temperature": 0.3}`. Call `client.chat_completion([{"role": "user", "content": "What can you do?"}])`. Assert that `response.choices[0].message.content` is a non-empty string (`.strip()` is not empty).
5. **Test: response structure**: Verify that the response has `choices` attribute, `choices[0].message` exists, `choices[0].message.content` is a `str`.
6. Use `pytest` markers: `@pytest.mark.integration` so these can be run selectively.
7. All tests must pass when Ollama is not running (they skip cleanly).

---

## B08 — HuggingFace Hub network access on first search after restart despite local cache

**Severity**: major
**Where**: `src/core/embeddings.py`
**Steps to reproduce**:
1. Upload a book (model downloads to `data/models/`).
2. Restart the application.
3. Perform a search — logs show:
   ```
   Warning: You are sending unauthenticated requests to the HF Hub.
   Loading weights: 100%|███| 199/199 [00:00<00:00, 9576.59it/s]
   ```

**Expected behavior**: After the model is cached in `data/models/`, subsequent loads should be fully offline — no HuggingFace Hub access at all.
**Actual behavior**: `SentenceTransformer(model_name, cache_folder=...)` still contacts HuggingFace Hub to check for model updates, even when the model files exist locally.

**Root cause**: The `sentence-transformers` library by default checks for newer versions of the model on HuggingFace Hub. The `SentenceTransformer` constructor does NOT use `local_files_only=True` by default.

**Fix requirements**:
1. **In `EmbeddingService._load_model()`** (`src/core/embeddings.py`):
   - Before constructing `SentenceTransformer`, check if the model already exists in the cache folder. The cache stores models under `{cache_folder}/sentence-transformers/{model_name}/` (or `{cache_folder}/{model_name}/` depending on version). Check if this directory exists and contains files.
   - If the model directory exists (cache hit), pass `local_files_only=True` to `SentenceTransformer(...)`. This prevents any network access.
   - If the model directory does NOT exist (first download), load normally without `local_files_only` (so it can download).
   - This way, first use downloads the model, subsequent uses are fully offline.
2. **Environment variable approach (complementary)**: Set `HF_HUB_OFFLINE=1` environment variable when the cache directory exists. This is a belt-and-suspenders approach alongside `local_files_only`.
3. Tests: verify that `SentenceTransformer` is called with `local_files_only=True` when the cache directory exists.

---

## B09 — BERT "UNEXPECTED: embeddings.position_ids" load report clutters logs every search

**Severity**: minor
**Where**: `src/core/embeddings.py`
**Steps to reproduce**:
1. Perform any search or chat that triggers embedding.
2. In logs:
   ```
   BertModel LOAD REPORT from: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
   Key                     | Status     |
   ------------------------+------------+
   embeddings.position_ids | UNEXPECTED |
   Notes: - UNEXPECTED: can be ignored when loading from different task/architecture
   ```

**Expected behavior**: This harmless model-loading diagnostic should not appear in the application logs.
**Actual behavior**: Every time `SentenceTransformer` loads the model (which happens on each new `EmbeddingService` instance), this report is printed to stderr or via Python logging, appearing in the Logs tab.

**Root cause**: The `paraphrase-multilingual-MiniLM-L12-v2` checkpoint includes `embeddings.position_ids` in its state dict, but the `BertModel` class does not define this parameter (it computes `position_ids` on-the-fly). The `transformers` library logs this mismatch as a diagnostic. It is completely harmless.

**Fix requirements**:
1. **Suppress the load report** in `_load_model()`:
   - Wrap the `SentenceTransformer(...)` call in a context that temporarily suppresses the specific `transformers` logger or redirects it:
     ```python
     import logging
     logging.getLogger("transformers.modeling_utils").setLevel(logging.ERROR)
     # ... load model ...
     logging.getLogger("transformers.modeling_utils").setLevel(logging.WARNING)
     ```
   - Alternatively, use `transformers.logging.set_verbosity_error()` before loading and restore after.
2. **Do NOT suppress all warnings globally** — only suppress during model loading, then restore. Other `transformers` warnings may be legitimate.
3. Tests: verify that after loading the model, the `transformers.modeling_utils` logger is restored to its previous level (not permanently silenced).
