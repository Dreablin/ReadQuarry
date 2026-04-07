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

// ——— Books ———

/**
 * @param {File} file
 * @param {string} [chunkingStrategy]
 * @returns {Promise<unknown>}
 */
export async function uploadBook(file, chunkingStrategy = "paragraph") {
  const body = new FormData();
  body.append("file", file);
  body.append("chunking_strategy", chunkingStrategy);
  const res = await fetch("/api/books/upload", { method: "POST", body });
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
