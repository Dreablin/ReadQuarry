/**
 * ReadQuarry API client — fetch wrappers for all backend routes (PRD §6).
 * Uses same-origin relative URLs; call from `type="module"` scripts.
 */

const JSON_HEADERS = { "Content-Type": "application/json" };

/**
 * @param {Response} res
 * @returns {Promise<unknown>}
 */
async function _parseBody(res) {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

/**
 * @param {Response} res
 * @returns {Promise<unknown>}
 */
async function _jsonOrThrow(res) {
  const data = await _parseBody(res);
  if (!res.ok) {
    let msg = res.statusText;
    if (data && typeof data === "object" && "detail" in data) {
      msg = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    } else if (typeof data === "string") {
      msg = data;
    }
    throw new Error(`HTTP ${res.status}: ${msg}`);
  }
  return data;
}

/**
 * Read B01 upload SSE (`text/event-stream`) until `done` or `error`.
 *
 * @param {Response} res
 * @param {(e: { stage: string, progress: number, detail?: string }) => void} [onProgress]
 * @returns {Promise<unknown>}
 */
async function _consumeBookUploadSse(res, onProgress) {
  const ct = res.headers.get("content-type") || "";
  if (!ct.includes("text/event-stream")) {
    throw new Error("Expected upload response to be text/event-stream");
  }
  const reader = res.body?.getReader();
  if (!reader) {
    throw new Error("Upload response has no readable body");
  }
  const decoder = new TextDecoder();
  let buffer = "";
  /** @type {unknown} */
  let book = null;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n");
    buffer = parts.pop() ?? "";
    for (const rawLine of parts) {
      const line = rawLine.trim();
      if (!line.startsWith("data:")) continue;
      const jsonText = line.startsWith("data: ") ? line.slice(6) : line.slice(5).trimStart();
      if (!jsonText) continue;
      let obj;
      try {
        obj = JSON.parse(jsonText);
      } catch {
        continue;
      }
      if (!obj || typeof obj !== "object") continue;
      if (obj.stage === "error") {
        const m = typeof obj.message === "string" ? obj.message : "Upload failed";
        throw new Error(m);
      }
      if (obj.stage === "done") {
        book = obj.book;
        if (typeof onProgress === "function") {
          onProgress({ stage: "done", progress: 100 });
        }
        continue;
      }
      if (typeof onProgress === "function" && typeof obj.progress === "number") {
        onProgress({
          stage: typeof obj.stage === "string" ? obj.stage : "",
          progress: obj.progress,
          detail: typeof obj.detail === "string" ? obj.detail : undefined,
        });
      }
    }
  }
  if (book == null) {
    throw new Error("Upload stream ended without a book payload");
  }
  return book;
}

// ——— Books ———

/**
 * @param {File} file
 * @param {string} [chunkingStrategy]
 * @param {{ chunkSize?: number, overlapRatio?: number }} [extras] fixed-size upload options
 * @param {{ onProgress?: (e: { stage: string, progress: number, detail?: string }) => void }} [streamOptions] B01 SSE progress
 * @returns {Promise<unknown>}
 */
export async function uploadBook(file, chunkingStrategy = "paragraph", extras = {}, streamOptions = {}) {
  const onProgress = typeof streamOptions.onProgress === "function" ? streamOptions.onProgress : undefined;
  const body = new FormData();
  body.append("file", file);
  body.append("chunking_strategy", chunkingStrategy);
  if (extras.chunkSize != null && Number.isFinite(Number(extras.chunkSize))) {
    body.append("chunk_size", String(Math.round(Number(extras.chunkSize))));
  }
  if (extras.overlapRatio != null && Number.isFinite(Number(extras.overlapRatio))) {
    body.append("overlap_ratio", String(Number(extras.overlapRatio)));
  }
  const res = await fetch("/api/books/upload", { method: "POST", body });
  const ct = res.headers.get("content-type") || "";
  if (!res.ok) {
    return _jsonOrThrow(res);
  }
  if (ct.includes("text/event-stream")) {
    return _consumeBookUploadSse(res, onProgress);
  }
  return _jsonOrThrow(res);
}

/** @returns {Promise<unknown>} */
export async function listBooks() {
  const res = await fetch("/api/books");
  return _jsonOrThrow(res);
}

/**
 * @param {number|string} bookId
 * @returns {Promise<unknown>}
 */
export async function getBook(bookId) {
  const res = await fetch(`/api/books/${bookId}`);
  return _jsonOrThrow(res);
}

/**
 * @param {number|string} bookId
 * @returns {Promise<unknown>}
 */
export async function deleteBook(bookId) {
  const res = await fetch(`/api/books/${bookId}`, { method: "DELETE" });
  return _jsonOrThrow(res);
}

/** Deletes all books and associated stored data (Chroma, indices, uploads). */
export async function clearAllBooks() {
  const res = await fetch("/api/books", { method: "DELETE" });
  return _jsonOrThrow(res);
}

/**
 * @param {number|string} bookId
 * @param {Record<string, string|number|boolean>} [query]
 * @returns {Promise<unknown>}
 */
export async function getBookChunks(bookId, query = {}) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (v !== undefined && v !== null) qs.set(k, String(v));
  }
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  const res = await fetch(`/api/books/${bookId}/chunks${suffix}`);
  return _jsonOrThrow(res);
}

// ——— Search ———

/**
 * @param {{ book_id: number, query: string, top_k?: number }} payload
 * @returns {Promise<unknown>}
 */
export async function searchSemantic(payload) {
  const res = await fetch("/api/search/semantic", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(payload),
  });
  return _jsonOrThrow(res);
}

/**
 * @param {{ book_id: number, query: string, max_results?: number }} payload
 * @returns {Promise<unknown>}
 */
export async function searchExact(payload) {
  const res = await fetch("/api/search/exact", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(payload),
  });
  return _jsonOrThrow(res);
}

/**
 * @param {{ book_id: number, query: string, semantic_k?: number, exact_k?: number, final_n?: number }} payload
 * @returns {Promise<unknown>}
 */
export async function searchHybrid(payload) {
  const res = await fetch("/api/search/hybrid", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(payload),
  });
  return _jsonOrThrow(res);
}

// ——— Settings ———

/** @returns {Promise<unknown>} */
export async function getSettings() {
  const res = await fetch("/api/settings");
  return _jsonOrThrow(res);
}

/**
 * @param {Record<string, unknown>} partial
 * @returns {Promise<unknown>}
 */
export async function updateSettings(partial) {
  const res = await fetch("/api/settings", {
    method: "PUT",
    headers: JSON_HEADERS,
    body: JSON.stringify(partial),
  });
  return _jsonOrThrow(res);
}

/** @returns {Promise<unknown>} */
export async function resetSettings() {
  const res = await fetch("/api/settings/reset", { method: "POST" });
  return _jsonOrThrow(res);
}

/** @returns {Promise<unknown>} */
export async function testLlm() {
  const res = await fetch("/api/settings/test-llm", { method: "POST" });
  return _jsonOrThrow(res);
}

/** @returns {Promise<unknown>} */
export async function clearModelsCache() {
  const res = await fetch("/api/settings/models_cache", { method: "DELETE" });
  return _jsonOrThrow(res);
}

// ——— Logs (debug viewer) ———

/** @returns {Promise<unknown>} */
export async function fetchLogs() {
  const res = await fetch("/api/logs");
  return _jsonOrThrow(res);
}

// ——— Chat ———

/**
 * @param {{ book_id: number, title?: string|null }} payload
 * @returns {Promise<unknown>}
 */
export async function createChatSession(payload) {
  const res = await fetch("/api/chat/sessions", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(payload),
  });
  return _jsonOrThrow(res);
}

/**
 * @param {number|string} bookId
 * @returns {Promise<unknown>}
 */
export async function listChatSessions(bookId) {
  const res = await fetch(`/api/chat/sessions?book_id=${encodeURIComponent(bookId)}`);
  return _jsonOrThrow(res);
}

/**
 * @param {number|string} sessionId
 * @returns {Promise<unknown>}
 */
export async function getChatMessages(sessionId) {
  const res = await fetch(`/api/chat/sessions/${sessionId}/messages`);
  return _jsonOrThrow(res);
}

/**
 * Streamed reply; caller reads `response.body` as SSE text.
 * @param {number|string} sessionId
 * @param {string} content
 * @returns {Promise<Response>}
 */
export async function sendChatMessage(sessionId, content) {
  const res = await fetch(`/api/chat/sessions/${sessionId}/message`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ content }),
  });
  if (!res.ok) {
    await _jsonOrThrow(res);
  }
  return res;
}
