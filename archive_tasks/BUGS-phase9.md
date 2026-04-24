# ReadQuarry — Bug Reports (Phase 9)

> This file is the bug specification reference for the Ralph Loop bugfix phase.
> **Do NOT modify this file from the loop** — it is read-only for the agent.

---

## B01 — Upload progress bar is fake — does not reflect real ingestion progress

**Severity**: major
**Where**: `src/api/books.py`, `static/js/components/book-upload.js`, `static/js/api.js`
**Steps to reproduce**:
1. Upload an EPUB file.
2. Watch the progress bar — it animates randomly from 5% to 92%, then jumps to 100%.

**Expected behavior**: The progress bar reflects actual ingestion phases: parsing, chunking, embedding, indexing.
**Actual behavior**: `book-upload.js` `startProgressAnimation()` runs a fake `setInterval` that adds `Math.random() * 12` every 220ms, capped at 92%. The backend upload endpoint (`POST /api/books/upload`) is a single HTTP request that blocks until the entire pipeline completes — there is no progress feedback from server to client.

**Fix requirements**:
1. **Backend** (`src/api/books.py`): Convert the upload endpoint to use **SSE** (Server-Sent Events) to stream progress updates during ingestion. The endpoint should:
   - Accept the file and return `StreamingResponse(media_type="text/event-stream")`.
   - Send SSE events at each stage: `{"stage": "parsing", "progress": 10}`, `{"stage": "chunking", "progress": 30}`, `{"stage": "embedding", "progress": 50, "detail": "Embedding 140 chunks..."}`, `{"stage": "indexing", "progress": 80}`, `{"stage": "done", "progress": 100, "book": {...}}`.
   - Use percentage ranges: parsing 0–20%, chunking 20–40%, embedding 40–80%, indexing 80–95%, done 100%.
2. **BookProcessor** (`src/core/book_processor.py`): Add an optional `on_progress` callback parameter to `process_book()`. Call it at each pipeline stage with `(stage_name, percentage)`. The upload endpoint passes a callback that yields SSE events.
3. **Frontend API** (`static/js/api.js`): Modify `uploadBook()` to handle SSE response instead of plain JSON. Read the event stream, parse each `data: {...}` line, and call a progress callback.
4. **Frontend UI** (`static/js/components/book-upload.js`):
   - Remove `startProgressAnimation()` fake timer.
   - Use real progress from SSE events to update the progress bar and show the current stage text (e.g. "Embedding 140 chunks...").
   - On `stage: "done"`, set progress to 100% and close the dialog.
   - On error, show the error in the feedback element.
5. Tests: verify that the upload endpoint yields SSE events with increasing progress values.

---

## B02 — Chat history persists across book switches — should start fresh

**Severity**: major
**Where**: `static/js/app.js`, `src/api/chat.py`
**Steps to reproduce**:
1. Select Book A, have a conversation.
2. Select Book B — the old chat history from Book B's previous session is loaded.
3. The user expects a fresh start when activating a book for discussion.

**Expected behavior**: When the user selects a book, a **new** chat session is created and the chat panel starts empty. Previous sessions are not lost (they remain in the DB) but the user begins with a clean conversation context.
**Actual behavior**: `ensureSession(bookId)` in `app.js` calls `listChatSessions(bookId)` and picks the **newest** existing session, then `loadHistory(sessionId)` fills the chat panel with old messages. The user sees stale conversation from before the restart.

**Fix requirements**:
1. **Frontend** (`static/js/app.js`): In the `onChange` handler for book selection, always create a **new** session instead of reusing the existing one. Replace the `ensureSession(bookId)` logic:
   - Instead of picking the first existing session, call `createChatSession({ book_id: bookId })` directly.
   - The chat panel will be empty since the new session has no messages.
   - This way, each time the user selects (or re-selects) a book, they get a fresh conversation.
2. **Backend**: No changes needed — `POST /api/chat/sessions` already creates new sessions. The old sessions remain in the DB (no data loss).
3. Tests: verify that selecting a book creates a new session and does not load old messages.

---

## B03 — Add "Prompts" tab to settings for viewing and editing system prompts

**Severity**: major
**Where**: `static/index.html`, `static/js/components/settings.js`, `src/api/settings.py`, `src/api/chat.py`
**Steps to reproduce**:
1. Open Settings — only "LLM" and "Embeddings & Search" tabs exist.
2. The system prompt for the LLM is hardcoded in `_system_prompt()` in `chat.py` — the user cannot see or change it.

**Expected behavior**: A third tab "Prompts" in the Settings dialog. It shows each system prompt used by the application as a labeled `<textarea>`, pre-filled with the current value. The user can edit and save. Prompts persist across restarts.
**Actual behavior**: `_system_prompt()` in `chat.py` returns a hardcoded string. There is no UI to view or edit it.

**This task is split into sub-tasks B03a, B03b, B03c for atomicity.**

---

## B03a — Backend: store system prompts in settings with defaults

**Severity**: major
**Where**: `src/api/settings.py`, `src/api/chat.py`
**Depends on**: nothing

**Fix requirements**:
1. **Settings defaults** (`src/api/settings.py`):
   - Add a new key `"system_prompt"` to `DEFAULTS` with the current hardcoded value from `_system_prompt()`:
     ```
     "You are ReadQuarry, a book discussion assistant. Answer using only the excerpts below. When you use information from an excerpt, cite it with the matching bracket label like [1] or [2]. If the excerpts do not contain enough information, say so clearly."
     ```
   - Add `system_prompt: str | None = None` to `SettingsUpdate` (no special validation needed, just a string).
2. **Chat** (`src/api/chat.py`):
   - Modify `_system_prompt()` to accept `app_settings` dict and read `app_settings.get("system_prompt", <default>)`.
   - Update `_stream_chat` to pass `app_settings` to `_system_prompt(app_settings)`.
3. Tests: verify that `system_prompt` appears in defaults, can be updated via PUT, and that `_system_prompt()` returns the custom value when set.

---

## B03b — Frontend: add "Prompts" tab to settings dialog

**Severity**: major
**Where**: `static/index.html`, `static/js/components/settings.js`
**Depends on**: B03a

**Fix requirements**:
1. **HTML** (`static/index.html`):
   - Add a third tab button in `.settings-tabs`: `<button type="button" id="settings-tab-prompts" class="settings-tab" role="tab" aria-selected="false" aria-controls="settings-panel-prompts">Prompts</button>`.
   - Add a third tab panel `<div id="settings-panel-prompts" class="settings-tab-panel settings-tab-panel--hidden" role="tabpanel" aria-labelledby="settings-tab-prompts">` containing a `<fieldset>` with:
     - `<label for="settings-system_prompt">System prompt (Discussion)</label>`
     - `<textarea id="settings-system_prompt" name="system_prompt" rows="6"></textarea>`
2. **JS** (`static/js/components/settings.js`):
   - Add `"system_prompt"` to `FIELD_KEYS`.
   - Register the new tab button click handler in `initSettings` (same pattern as LLM/Embeddings tabs).
   - Update `activateSettingsTab` to handle three tabs: `"llm"`, `"embeddings"`, `"prompts"`.
3. Tests: verify the Prompts tab is present, the textarea is populated from settings, and saving persists the value.

---

## B04 — Paragraph chunking misses paragraphs — `clean_html` extracts only `<p>` and heading tags

**Severity**: critical
**Where**: `src/parsers/epub_parser.py`
**Steps to reproduce**:
1. Upload an EPUB with paragraph chunking strategy.
2. The ingestion log shows ~140 chunks, but the book has far more paragraphs.

**Expected behavior**: All text content from the EPUB is extracted, producing a chunk count proportional to the actual paragraph count in the book.
**Actual behavior**: `clean_html()` in `epub_parser.py` only extracts text from `<p>`, `<h1>`–`<h6>`, and `<li>` tags (line 26). Text that lives in other block-level elements — `<div>`, `<blockquote>`, `<td>`, `<dd>`, `<figcaption>`, `<section>`, `<article>`, bare text nodes — is **silently dropped** when any `<p>` tag exists in the document. The fallback path (lines 32–38) only activates when **zero** matching tags are found.

**Root cause** (line 26–31):
```python
for tag in soup.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "li"]):
    piece = " ".join(tag.get_text(separator=" ", strip=True).split())
    if piece:
        blocks.append(piece)
if blocks:
    return "\n\n".join(blocks)   # ← returns early, text in <div>/<blockquote>/etc. lost
```

Many EPUBs wrap content in `<div>` with sub-`<div>` paragraphs instead of `<p>` tags. If even one `<p>` exists (e.g. a footer), the early return triggers and all `<div>`-based content is lost.

**Fix requirements**:
1. **Expand the tag list** in `clean_html()` to include more block-level elements:
   `["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "dd", "dt", "figcaption", "td", "th", "pre"]`.
2. **Also handle `<div>` leaves**: After the primary tag extraction, find all `<div>` elements that have **no** child block elements (leaf `<div>`s) and extract their text too. This catches EPUB patterns where `<div class="para">...</div>` is used instead of `<p>`.
3. **Deduplication**: Since `find_all` is recursive, a `<p>` inside a `<blockquote>` would be found by both. Use a set to track seen text or process only leaf nodes.
4. **Preserve order**: Blocks must remain in document order.
5. Tests: create an EPUB-like HTML with `<div>`-wrapped paragraphs and verify they are all extracted.

---

## B05 — Sentence chunking misses sentences — same `clean_html` root cause plus regex limitations

**Severity**: critical
**Where**: `src/parsers/epub_parser.py`, `src/core/chunking.py`
**Depends on**: B04 (the parser fix provides more text to chunk)
**Steps to reproduce**:
1. Upload an EPUB with sentence chunking strategy.
2. The ingestion log shows far fewer sentence chunks than expected.

**Expected behavior**: The sentence count should approximate the total sentences across all extracted text.
**Actual behavior**: Two compounding issues:
1. **Parser drops text** (same as B04): `clean_html()` misses content in `<div>`, `<blockquote>`, etc.
2. **Sentence regex misses splits**: The regex `(?<=[.!?…])\s+` in `SentenceChunking.chunk()` (line 41 of `chunking.py`) requires **whitespace after** the punctuation. Sentences ending at the very end of a block (followed by `\n\n` from paragraph joining) may not split correctly.

**Fix requirements**:
1. **Parser fix from B04** addresses the primary data loss.
2. **Sentence splitting** (`src/core/chunking.py` `SentenceChunking`):
   - Before splitting by sentence regex, first split by `\n\s*\n` (paragraph boundaries) to handle multi-paragraph text blocks. Then split each paragraph into sentences.
   - Alternatively, normalize the text by replacing `\n\n` with `. ` or a space before sentence splitting, so the regex can work across paragraph boundaries.
   - Consider using a more robust sentence boundary regex that also splits on `\n\n` as a sentence boundary.
3. Tests: verify sentence chunking produces the correct number of sentences from multi-paragraph text with various punctuation patterns.

---

## B06 — Fixed-size chunking has no UI for chunk size — user cannot see or configure the size

**Severity**: major
**Where**: `static/index.html`, `static/js/components/book-upload.js`, `static/js/api.js`, `src/api/books.py`, `src/core/book_processor.py`
**Steps to reproduce**:
1. Open the upload dialog, select "Fixed size" chunking strategy.
2. No additional fields appear — the user has no idea what size will be used.

**Expected behavior**: When "Fixed size" is selected, additional input fields appear: "Chunk size (words)" defaulting to 256, and "Overlap ratio" defaulting to 0.15. These values are sent to the backend and used by `FixedSizeChunking`.
**Actual behavior**: `FixedSizeChunking()` always uses its default constructor values (256 words, 0.15 overlap). The upload dialog shows only the strategy dropdown — no conditional fields.

**Fix requirements**:
1. **HTML** (`static/index.html`): Add a conditional group inside the upload dialog, after the strategy `<select>`:
   ```html
   <div id="upload-fixed-size-options" class="upload-strategy-options" hidden>
     <label for="upload-chunk-size">Chunk size (words)</label>
     <input type="number" id="upload-chunk-size" name="chunk_size" value="256" min="50" max="2000" step="1" />
     <label for="upload-overlap-ratio">Overlap ratio</label>
     <input type="number" id="upload-overlap-ratio" name="overlap_ratio" value="0.15" min="0" max="0.5" step="0.05" />
   </div>
   ```
2. **Frontend JS** (`static/js/components/book-upload.js`):
   - Add a `change` listener on the `chunkSelect` (`#chunking-strategy`). When value is `"fixed-size"`, show `#upload-fixed-size-options` (`hidden = false`); otherwise hide it.
   - When submitting, if strategy is `"fixed-size"`, read `chunk_size` and `overlap_ratio` from the inputs and pass them to `uploadBook()`.
3. **Frontend API** (`static/js/api.js`): Update `uploadBook()` to accept optional `chunk_size` and `overlap_ratio` parameters and append them to `FormData` when provided.
4. **Backend** (`src/api/books.py`): Accept optional `chunk_size: int = Form(256)` and `overlap_ratio: float = Form(0.15)` parameters in `upload_book()`. Pass them through to `BookProcessor`.
5. **BookProcessor** (`src/core/book_processor.py`): Update `_get_chunker()` to accept and forward `chunk_size` and `overlap_ratio` to `FixedSizeChunking(chunk_size=..., overlap_ratio=...)`.
6. Tests: verify that custom chunk_size/overlap_ratio values are used when provided, and defaults apply when omitted.

---

## B07 — No "Clear Chat" button — user cannot start a fresh conversation without switching books

**Severity**: major
**Where**: `static/index.html`, `static/js/app.js`, `static/js/components/chat.js`
**Steps to reproduce**:
1. Select a book, have a conversation.
2. Want to start over with a clean chat for the same book — no way to do it.

**Expected behavior**: A "Clear Chat" button in the chat panel that clears the current messages and creates a new session, giving the user a fresh LLM context.
**Actual behavior**: No such button exists. The only way to get a new session is to switch to another book and back (and with B02 fix, each book switch creates a new session).

**Fix requirements**:
1. **HTML** (`static/index.html`): Add a "Clear Chat" button in `#chat-panel`, near the chat form:
   ```html
   <button type="button" id="clear-chat" class="btn-clear">Clear Chat</button>
   ```
   Place it in the panel header area or as a toolbar button above the chat messages.
2. **Frontend** (`static/js/app.js`):
   - Get the `#clear-chat` button.
   - On click:
     a. Get the currently selected `bookId`.
     b. If no book selected, do nothing.
     c. Call `createChatSession({ book_id: bookId })` to create a **new** session.
     d. Set `sessionId` to the new session's id.
     e. Call `chatApi.clearMessages()` to empty the chat panel.
     f. Call `refs.clear()` to clear references.
     g. Set status to "New conversation started".
3. **No backend changes needed** — creating a new session is already supported. The old session stays in the DB.
4. Tests: verify the clear chat button exists and creates a new session.
