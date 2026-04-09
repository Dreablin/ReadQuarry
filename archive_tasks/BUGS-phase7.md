# ReadQuarry — Bug Reports

> This file is the bug specification reference for the Ralph Loop bugfix phase.
> **Do NOT modify this file from the loop** — it is read-only for the agent.

---

## B01 — Books stored in-memory, chat requires DB row — session creation always fails

**Severity**: critical
**Where**: `src/api/books.py`, `src/api/chat.py`, `src/models/`
**Steps to reproduce**:
1. Start the app, upload an EPUB via the UI
2. Select the uploaded book in the dropdown
3. Try to send a chat message

**Expected behavior**: A chat session is created for the selected book and the message is sent.
**Actual behavior**: Error "Choose a book and open a chat session first." — because `ensureSession` in `app.js` calls `createChatSession({ book_id })`, which hits `POST /api/chat/sessions`, which does `db.get(Book, payload.book_id)` and returns 404 since the book was only added to the in-memory `_BOOKS` dict, not the SQLAlchemy `Book` table.
**Notes**: The fix must unify book storage. The upload endpoint in `books.py` should create a `Book` row in the SQLAlchemy DB (same DB used by chat). Remove the in-memory `_BOOKS` dict entirely and use the DB for list/get/delete too. The `BookProcessor` pipeline (parse, chunk, embed, index) should also run during upload so the book is fully searchable. Consider running the processor as a background task if it's slow.

---

## B02 — Semantic search endpoint is a hardcoded placeholder

**Severity**: critical
**Where**: `src/api/search.py`, `src/core/embeddings.py`, `src/core/vector_store.py`
**Steps to reproduce**:
1. Upload a book
2. Go to Search view
3. Search for any term

**Expected behavior**: Real semantic search results from the book's vectorized chunks.
**Actual behavior**: Returns a single fake result like `{chunk_id: "1_sem_1", text: "Semantic match for 'query'", score: 0.9}` — hardcoded in the endpoint.
**Notes**: The `POST /api/search/semantic` endpoint must use `EmbeddingService` to embed the query, then `VectorStore` to query the book's ChromaDB collection. The collection name should match what `BookProcessor` uses during ingestion (likely `book_{id}`). The exact search via Tantivy appears to be wired correctly. The hybrid endpoint calls both, so fixing semantic fixes hybrid too.

---

## B03 — Settings don't persist between restarts

**Severity**: critical
**Where**: `src/api/settings.py`, `config.py`
**Steps to reproduce**:
1. Open Settings, change LLM mode or Ollama URL
2. Save settings
3. Restart the app
4. Open Settings again

**Expected behavior**: Previously saved settings are loaded.
**Actual behavior**: All settings reset to defaults because they live in an in-memory `_SETTINGS` dict.
**Notes**: Save settings to a JSON file at `{config.data_dir}/settings.json`. On startup, load from the file if it exists, otherwise use defaults. The `GET`, `PUT`, and `POST /reset` endpoints should read/write this file. Keep the in-memory dict as a cache but sync to disk on every write.

---

## B04 — GPU loaded 25-30% when idle due to infinite CSS animation

**Severity**: major
**Where**: `static/css/style.css`
**Steps to reproduce**:
1. Open the web interface
2. Do nothing
3. Check GPU usage in Task Manager

**Expected behavior**: Near-zero GPU usage when idle.
**Actual behavior**: GPU at 25-30% continuously.
**Notes**: The `.app-header` has `animation: header-shimmer 8s ease-in-out infinite` which animates `filter: saturate()`. This forces continuous GPU compositing. Either remove this animation entirely, make it a one-shot on page load, or replace `filter` with a less expensive property (e.g. opacity on a pseudo-element). Also check if `backdrop-filter: blur()` on glass panels contributes — if so, consider reducing or removing it.

---

## B05 — Multi-language support (Russian and English)

**Severity**: major
**Where**: `src/core/embeddings.py`, `src/core/search_engine.py`, `src/core/chunking.py`
**Steps to reproduce**:
1. Upload a Russian-language EPUB
2. Search for a Russian word or phrase
3. Try to discuss the book in Russian

**Expected behavior**: Search and discussion work equally well in Russian and English.
**Actual behavior**: Unknown — but the embedding model `all-MiniLM-L6-v2` is English-focused and may produce poor vectors for Russian text. Tantivy's default analyzer may not tokenize Russian well.
**Notes**: For embeddings, consider switching to `paraphrase-multilingual-MiniLM-L12-v2` (also from sentence-transformers, ~470MB, 384-dim, supports 50+ languages including Russian). For Tantivy exact search, ensure the index uses a language-aware or simple tokenizer that handles Cyrillic. For chunking, sentence splitting must handle Russian punctuation correctly. Update `requirements.txt` if the model name changes. The model name should be configurable in settings so users can choose.

---

## B06 — LLM settings: split into Ollama/Cloud groups with dropdown selector

**Severity**: major
**Where**: `static/index.html`, `static/js/components/settings.js`, `static/css/style.css`
**Steps to reproduce**:
1. Open Settings dialog

**Expected behavior**: A dropdown at the top selects "Ollama" or "Cloud LLM". Only the fields relevant to the selected mode are visible. Switching modes preserves previously entered values for both modes.
**Actual behavior**: All LLM fields are shown at once in a flat list with no grouping.
**Notes**: Group fields into two `<fieldset>` or `<div>` containers: one for Ollama (base URL, model name) and one for Cloud (API key, base URL, model name). The `settings-llm_mode` select toggles visibility. All field values must be saved to settings regardless of which mode is active, so switching back restores previous values. Use CSS `display: none`/`block` for toggling, not DOM removal.

---

## B07 — Settings dialog: tabbed layout (LLM vs Embeddings & Search)

**Severity**: major
**Where**: `static/index.html`, `static/js/components/settings.js`, `static/css/style.css`
**Steps to reproduce**:
1. Open Settings dialog

**Expected behavior**: Settings are organized in two tabs: "LLM" and "Embeddings & Search". Clicking a tab shows only that section.
**Actual behavior**: All settings fields are stacked vertically in one scrollable form.
**Notes**: Add tab buttons inside the settings dialog. Each tab shows/hides a `<div>` containing the relevant fields. The LLM tab contains the Ollama/Cloud mode selector and LLM fields (from B06). The Embeddings & Search tab contains embedding model, device, semantic top-k, and other search parameters. Tab state does not need to persist — default to the LLM tab on open.

---

## B08 — Cloud LLM mode: show API key security warning

**Severity**: minor
**Where**: `static/index.html`, `static/js/components/settings.js`
**Steps to reproduce**:
1. Open Settings
2. Select "Cloud" in the LLM mode dropdown

**Expected behavior**: A warning message appears: "All settings, including API keys, are stored in a local file at data/settings.json. Keep this file secure!"
**Actual behavior**: No warning shown.
**Notes**: Add a `<p>` or `<div>` with a warning class inside the Cloud fields group. Show it only when Cloud mode is selected (same visibility toggle as B06). The file path shown should match the actual settings file path from B03. Style it with a distinct warning color (e.g. amber/yellow text or border).

---

## B09 — Discussion and Search should be on separate screens with navigation buttons

**Severity**: major
**Where**: `static/index.html`, `static/js/app.js`, `static/css/style.css`
**Steps to reproduce**:
1. Open the app

**Expected behavior**: Two clearly labeled buttons at the top of the main area: "Discussion" and "Search". Clicking each shows the corresponding full-screen view. The current view is visually highlighted.
**Actual behavior**: Discussion is the default view with a small "Search" link; switching back requires a "Back" button inside the search panel. The UX is not symmetric.
**Notes**: Replace the current `#search-open` / `#search-back` links with two equal buttons in a tab-bar or button-group in the header or top of `#app-main`. Both views should be full-width. The active button should have a distinct style (e.g. accent color, underline). Keep the `data-view` attribute approach on `#app-main` for CSS-driven layout switching.

---

## B10 — Debug log viewer screen (third navigation button)

**Severity**: major
**Where**: `static/index.html`, `static/js/app.js`, `static/css/style.css`, `main.py`, new file `static/js/components/log-viewer.js`, new file `src/api/logs.py`
**Steps to reproduce**:
1. Open the app

**Expected behavior**: A third button "Logs" in the top navigation opens a scrollable log viewer. New log entries appear at the bottom. The list scrolls to show the latest entry.
**Actual behavior**: No log viewer exists.
**Notes**: Backend: create a new API endpoint that streams or returns recent log entries. Options: (a) SSE endpoint that pushes log lines in real-time, or (b) a simple `GET /api/logs` returning the last N lines from a ring buffer. Use Python's `logging` module with a custom handler that captures log records into a deque. Frontend: new `log-viewer.js` component renders log entries in a `<pre>` or `<ul>` inside a new `#view-logs` panel. Auto-scroll to bottom on new entries. Add "Logs" as a third view in the navigation alongside Discussion and Search.

---

## B11 — Detailed logging on book ingestion

**Severity**: major
**Where**: `src/api/books.py`, `src/core/book_processor.py`
**Steps to reproduce**:
1. Upload a book

**Expected behavior**: Detailed log messages during ingestion: file saved where, parser used, number of chapters found, chunking strategy, number of chunks created, embeddings generated, vectors stored in ChromaDB (collection name, count), Tantivy index updated (index path, document count), total processing time.
**Actual behavior**: Minimal or no logging during book upload and processing.
**Notes**: Add `logger.info(...)` calls at each stage of `BookProcessor.process()` and in the books upload endpoint. These logs will be visible in the log viewer (B10). Include counts and paths so the user can verify what happened. Log both success and any partial failures.

---

## B12 — Fix Ralph Loop scratchpad safety cap

**Severity**: minor
**Where**: `.cursor/ralph/scratchpad.md`
**Steps to reproduce**:
1. Start a Ralph Loop with `max_iterations: 0` (unlimited)
2. All tasks are already complete or no tasks exist
3. The loop outputs ALL_TASKS_COMPLETE but keeps cycling

**Expected behavior**: The loop stops after outputting the completion promise.
**Actual behavior**: The loop continues indefinitely, burning iterations.
**Notes**: This is an infrastructure issue. When starting the next Ralph Loop, always set `max_iterations` to a reasonable finite number (e.g. 50 or 100) as a safety net. The completion promise should still be the primary stop mechanism, but `max_iterations` acts as a hard cap. This bug is "fixed" by deleting the stale scratchpad (already done) and ensuring the next loop start uses a finite cap.

---

## B13 — Duplicate book upload fails silently — no visible error in UI or backend logs

**Severity**: major
**Where**: `src/api/books.py`, `static/js/components/book-upload.js`
**Steps to reproduce**:
1. Upload an EPUB file successfully.
2. Try to upload the exact same EPUB file again.
3. Observe: nothing happens — no error message visible, no log entry in the Logs tab.

**Expected behavior**: A clear, visible error message tells the user the book already exists. The backend logs record the duplicate attempt.
**Actual behavior**: The backend correctly returns HTTP 409 with `{"detail": "Book with this content already exists"}`, but:
- **Backend**: There is no `logger.warning(...)` call on the duplicate-detection path (line ~64 of `books.py`), so the Logs viewer shows nothing.
- **Frontend**: The error is sent to `options.onError(error)` which calls `setStatus(err.message)` — this updates the **status bar** at the very bottom of the page. However, the **upload dialog is still open on top**, hiding the status bar. The user never sees the message.

**Fix requirements**:
1. **Backend** (`src/api/books.py`): Add `logger.warning("Duplicate book upload rejected: file_hash=%s filename=%r", file_hash, file.filename)` before raising the 409, so the attempt appears in the Logs tab.
2. **Frontend** (`static/js/components/book-upload.js`): In the `catch` block of the form submit handler, display the error **inside the upload dialog** (e.g. in a dedicated `<p id="upload-feedback">` element) rather than only in the status bar. The dialog should remain open so the user can see the error message and try a different file. Make the error text clearly visible (e.g. red/warning color).

---

## B14 — "Test LLM" button always shows success — endpoint is a stub

**Severity**: major
**Where**: `src/api/settings.py` (endpoint `POST /api/settings/test-llm`), `src/core/llm_client.py`, `static/js/components/settings.js`
**Steps to reproduce**:
1. Open Settings.
2. Set LLM mode to Ollama with a URL pointing to a non-running Ollama instance (e.g. `http://localhost:99999`).
3. Click "Test LLM".
4. Observe: feedback says `{"status":"ok"}`.

**Expected behavior**: The test actually connects to the configured LLM endpoint. On failure (connection refused, invalid API key, model not found, timeout) the UI shows a descriptive error. On success, it shows confirmation (e.g. "Connected to llama3.2 on Ollama").
**Actual behavior**: The endpoint (`src/api/settings.py` line 131) is a placeholder that always returns `{"status": "ok"}` without making any network call.

**Fix requirements**:
1. **Backend** (`src/api/settings.py`): Replace the stub `test_llm` endpoint with real logic:
   - Read current `_SETTINGS` (or accept an optional request body to test before saving).
   - Instantiate `LLMClient` from `src/core/llm_client.py` with those settings.
   - For **Ollama mode**: call `llm_client.chat_completion(messages=[{"role":"user","content":"ping"}], max_tokens=1)` inside a try/except. Catch `openai.APIConnectionError`, `openai.AuthenticationError`, timeouts, and any other `Exception`. Return `{"status": "ok", "model": "<model>", "mode": "<mode>"}` on success, or `{"status": "error", "detail": "<error description>"}` on failure. Set HTTP status to 200 on success and **200 on failure too** (so the frontend JS can always parse the JSON body — the `_jsonOrThrow` helper throws on non-2xx).
   - For **Cloud mode**: same approach — attempt a minimal completion to validate API key + base URL.
   - Add a timeout (e.g. 10 seconds) so the test doesn't hang forever.
   - Log the result with `logger.info(...)` on success and `logger.warning(...)` on failure.
2. **Frontend** (`static/js/components/settings.js`): Update the Test LLM click handler to interpret the response. If `res.status === "error"`, display the error clearly in red. If `res.status === "ok"`, display a green success message (e.g. "Connected to {model} via {mode}").

---

## B15 — Settings dialog action buttons have poor contrast — unreadable on dark theme

**Severity**: minor
**Where**: `static/css/style.css`, `static/index.html`
**Steps to reproduce**:
1. Open Settings dialog.
2. Look at the bottom row of buttons: Close, Reset defaults, Test LLM, Save.

**Expected behavior**: All buttons are clearly readable with good contrast against the dark background.
**Actual behavior**: The buttons in `.dialog__actions` have **no custom CSS styling** — they use browser-default `<button>` appearance, which renders as light gray buttons with dark text on some browsers, or as nearly invisible gray-on-gray on others. On a dark theme with `background: #12141f`, they look washed out and hard to read.

**Fix requirements** (in `static/css/style.css`):
1. Add explicit styling for `.dialog__actions button` with:
   - Readable text color (e.g. `var(--color-text)` or `#fff`).
   - Visible background (e.g. `var(--color-surface-strong)` or a subtle gradient).
   - Border matching the theme (e.g. `1px solid var(--color-border)`).
   - Rounded corners matching the design system (e.g. `var(--radius-sm)`).
   - Hover state with lighter background or glow.
   - Cursor pointer.
2. Optionally give the "Save" button (primary action) a distinct accent style (e.g. gradient from `--color-accent-start` to `--color-accent-end`, white text) to make it stand out from secondary buttons (Close, Reset, Test).
3. Apply the same fix to `.dialog--upload .dialog__actions button` as well (the upload dialog has the same issue).

---

## B16 — No "Clear All" button to delete all books and reset databases

**Severity**: major
**Where**: `src/api/books.py`, `static/index.html`, `static/js/components/settings.js`, `static/js/api.js`
**Steps to reproduce**:
1. Upload several books.
2. Want to start fresh / clear all data.
3. No way to do this without manually deleting files in `data/`.

**Expected behavior**: A "Clear All Data" button in the Settings dialog (or a dedicated section) that deletes all books and associated data (SQLite rows, ChromaDB collections, search indices, uploaded files).
**Actual behavior**: Only individual book deletion exists (`DELETE /api/books/{book_id}`) — and it's only exposed in the API, not in the frontend UI.

**Fix requirements**:
1. **Backend** (`src/api/books.py`): Add a `DELETE /api/books` (or `POST /api/books/clear-all`) endpoint that:
   - Queries all `Book` rows from the database.
   - For each book: deletes its ChromaDB collection (`book_{id}`), removes its search index directory (`tantivy_index/book_{id}`), and removes its uploaded file from `data/uploads/`.
   - Deletes all `Book` rows from the SQLite DB (which cascades to paragraphs, chunks, chat sessions, chat messages).
   - Logs the operation with `logger.info("Cleared all books: count=%d", count)`.
   - Returns `{"status": "cleared", "deleted_count": N}`.
2. **Frontend API** (`static/js/api.js`): Add `clearAllBooks()` function that calls the new endpoint.
3. **Frontend UI** (`static/index.html`, `static/js/components/settings.js` or `static/js/app.js`): Add a "Clear All Data" button in the Settings dialog (in the actions area or as a separate danger zone section). On click:
   - Show a confirmation prompt (`confirm("Delete all books and conversations? This cannot be undone.")` or a custom confirmation dialog).
   - If confirmed, call `clearAllBooks()`.
   - On success, refresh the book list dropdown, clear current chat, and show feedback.
   - Style the button with a warning/danger color (e.g. red tint) to signal destructiveness.

---

## B17 — Navigation tabs always show Logs panel — CSS `display: flex` overrides HTML `hidden` attribute

**Severity**: critical
**Where**: `static/css/style.css`, `static/js/app.js`
**Steps to reproduce**:
1. Open the app.
2. Click "Discussion" — Logs panel is visible.
3. Click "Search" — Logs panel is visible.
4. Click "Logs" — Logs panel is visible.
5. Discussion and Search content are never accessible.

**Expected behavior** (per PRD §3.2, §3.3 and B09):
- **Discussion** tab shows the chat panel (left) + references panel (right) in split layout.
- **Search** tab shows the search form + results in a single-column layout.
- **Logs** tab shows the log viewer in a single-column layout.
- Only the active view's panels are visible.

**Actual behavior**: Both `#view-search` (`.panel--search`) and `#view-logs` (`.panel--logs`) are **always visible** despite having the HTML `hidden` attribute. The Logs panel appears on top because it comes later in the DOM and shares the same grid cell.

**Root cause**: CSS rules override the `hidden` attribute. In `style.css`:
```css
.panel--logs {
  display: flex;           /* ← overrides [hidden] { display: none } */
  flex-direction: column;
  min-height: 0;
}
.panel--search {
  display: flex;           /* ← same problem */
  flex-direction: column;
  min-height: 0;
}
```
The HTML `hidden` attribute works by setting `display: none` via the browser's user-agent stylesheet, but **any author CSS rule setting `display` overrides it** because author styles have higher priority than UA styles. The `.panel--logs` and `.panel--search` rules set `display: flex`, so `hidden` has no effect.

**Fix requirements** — choose ONE approach:

**(a) Class-based visibility (preferred)**: Instead of using the HTML `hidden` attribute, toggle a CSS class (e.g. `view--hidden`) that uses `display: none !important`. In `app.js` `setView()`, replace `viewSearch.hidden = ...` / `viewLogs.hidden = ...` with `viewSearch.classList.toggle("view--hidden", !showSearch)` / `viewLogs.classList.toggle("view--hidden", !showLogs)`. Do the same for `chatPanel` and `refsPanel`. Add `.view--hidden { display: none !important; }` to `style.css`. Remove the `hidden` attribute from the initial HTML for `#view-search` and `#view-logs` and add the `view--hidden` class instead.

**(b) Targeted `[hidden]` override**: Add rules in `style.css`:
```css
.panel--search[hidden],
.panel--logs[hidden] {
  display: none;
}
```
This ensures `hidden` wins when the attribute is present. Less invasive but more fragile.

**(c)** Fix the existing `.panel--search` / `.panel--logs` rules to not set `display` unconditionally — move `display: flex` into a `:not([hidden])` selector:
```css
.panel--logs:not([hidden]) {
  display: flex;
  ...
}
```

Approach **(a)** is recommended because it is robust, explicit, and consistent with how the nav tab styling already works (class-based toggling).
