/**
 * Application controller: wires book list, upload, chat, references, settings, and search view.
 */

import {
  createChatSession,
  listChatSessions,
  searchHybrid,
} from "./api.js";
import { initBookList } from "./components/book-list.js";
import { initBookUpload } from "./components/book-upload.js";
import { initChat } from "./components/chat.js";
import { initLogViewer } from "./components/log-viewer.js";
import { initReferences } from "./components/references.js";
import { initSettings } from "./components/settings.js";

/**
 * @param {string} text
 * @returns {string}
 */
function escapeRegExp(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * @param {string} text
 * @param {string} query
 * @returns {DocumentFragment}
 */
function highlightFragment(text, query) {
  const frag = document.createDocumentFragment();
  const q = typeof query === "string" ? query.trim() : "";
  if (!q) {
    frag.appendChild(document.createTextNode(text));
    return frag;
  }
  const parts = text.split(new RegExp(`(${escapeRegExp(q)})`, "gi"));
  for (const part of parts) {
    if (part.toLowerCase() === q.toLowerCase()) {
      const mark = document.createElement("mark");
      mark.className = "ref-highlight";
      mark.textContent = part;
      frag.appendChild(mark);
    } else {
      frag.appendChild(document.createTextNode(part));
    }
  }
  return frag;
}

/**
 * @param {number} bookId
 * @returns {Promise<number>}
 */
async function ensureSession(bookId) {
  const raw = await listChatSessions(bookId);
  const list = Array.isArray(raw) ? raw : [];
  if (list.length > 0 && list[0].id != null) {
    return Number(list[0].id);
  }
  const s = await createChatSession({ book_id: bookId });
  return Number(s.id);
}

/**
 * @param {{ getSelectedBookId: () => number | null }} bookList
 * @param {ReturnType<typeof initReferences>} refs
 * @param {(msg: string) => void} setStatus
 * @param {ReturnType<typeof initLogViewer>} logViewer
 */
function wireMainViews(bookList, refs, setStatus, logViewer) {
  const navDiscuss = document.getElementById("main-nav-discussion");
  const navSearch = document.getElementById("main-nav-search");
  const navLogs = document.getElementById("main-nav-logs");
  const viewSearch = document.getElementById("view-search");
  const viewLogs = document.getElementById("view-logs");
  const chatPanel = document.getElementById("chat-panel");
  const refsPanel = document.getElementById("references-panel");
  const mainEl = document.getElementById("app-main");
  const form = document.getElementById("search-form");
  const queryInput = document.getElementById("search-query");
  const maxResultsInput = document.getElementById("search-max-results");
  const resultsEl = document.getElementById("search-results");

  /**
   * @param {"discuss" | "search" | "logs"} mode
   */
  function setView(mode) {
    const showSearch = mode === "search";
    const showLogs = mode === "logs";
    if (chatPanel) chatPanel.classList.toggle("view--hidden", showSearch || showLogs);
    if (refsPanel) refsPanel.classList.toggle("view--hidden", showSearch || showLogs);
    if (viewSearch) viewSearch.classList.toggle("view--hidden", !showSearch);
    if (viewLogs) viewLogs.classList.toggle("view--hidden", !showLogs);
    if (mainEl) {
      if (showLogs) mainEl.dataset.view = "logs";
      else if (showSearch) mainEl.dataset.view = "search";
      else mainEl.dataset.view = "discuss";
    }
    if (navDiscuss) {
      navDiscuss.classList.toggle("main-nav-btn--active", mode === "discuss");
      navDiscuss.setAttribute("aria-selected", String(mode === "discuss"));
    }
    if (navSearch) {
      navSearch.classList.toggle("main-nav-btn--active", mode === "search");
      navSearch.setAttribute("aria-selected", String(mode === "search"));
    }
    if (navLogs) {
      navLogs.classList.toggle("main-nav-btn--active", mode === "logs");
      navLogs.setAttribute("aria-selected", String(mode === "logs"));
    }
    if (mode === "logs") logViewer.start();
    else logViewer.stop();
  }

  navDiscuss?.addEventListener("click", () => setView("discuss"));
  navSearch?.addEventListener("click", () => setView("search"));
  navLogs?.addEventListener("click", () => setView("logs"));

  form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const bookId = bookList.getSelectedBookId();
    if (bookId == null) {
      setStatus("Select a book first");
      return;
    }
    const q = queryInput?.value?.trim() ?? "";
    if (!q) return;
    setStatus("Searching…");
    if (resultsEl) resultsEl.innerHTML = "";
    try {
      const rawLimit =
        maxResultsInput && maxResultsInput.value != null && String(maxResultsInput.value).trim() !== ""
          ? parseInt(String(maxResultsInput.value), 10)
          : 20;
      const limit = Number.isFinite(rawLimit) ? Math.min(50, Math.max(1, rawLimit)) : 20;
      const data = await searchHybrid({
        book_id: bookId,
        query: q,
        semantic_k: limit,
        exact_k: limit,
        final_n: limit,
      });
      const rows = Array.isArray(data?.results) ? data.results : [];
      refs.setHighlightQuery(q);
      if (resultsEl) {
        for (const row of rows) {
          const chunkId = row.chunk_id ?? row.chunkId;
          const text = typeof row.text === "string" ? row.text : "";
          const article = document.createElement("article");
          article.className = "reference-chunk";
          article.dataset.chunkId = String(chunkId ?? "");
          const head = document.createElement("header");
          head.className = "reference-chunk__head";
          const label = document.createElement("span");
          label.className = "reference-chunk__label";
          label.textContent = String(chunkId ?? "");
          const meta = document.createElement("span");
          meta.className = "reference-chunk__meta";
          if (row.score != null) meta.textContent = `Score: ${Number(row.score).toFixed(4)}`;
          head.appendChild(label);
          if (meta.textContent) head.appendChild(meta);
          const body = document.createElement("div");
          body.className = "reference-chunk__body";
          body.appendChild(highlightFragment(text, q));
          article.appendChild(head);
          article.appendChild(body);
          resultsEl.appendChild(article);
        }
      }
      setStatus(`Found ${rows.length} result(s)`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setStatus(msg);
    }
  });
}

/**
 * @returns {Promise<void>}
 */
export async function initApp() {
  const statusEl = document.getElementById("status-bar");

  /**
   * @param {string} msg
   */
  function setStatus(msg) {
    if (statusEl) statusEl.textContent = msg;
  }

  const refs = initReferences();

  /** @type {{ getSelectedBookId: () => number | null } | null} */
  let bookListRef = null;

  let sessionId = null;

  const chatApi = await initChat({
    getSessionId: () => sessionId,
    onError: setStatus,
    onDone: (ids, scores) => {
      const bid = bookListRef?.getSelectedBookId() ?? null;
      if (bid != null) void refs.appendReferencedChunkIds(bid, ids, scores);
    },
  });

  const bookList = await initBookList({
    onChange: async (bookId) => {
      if (bookId == null) {
        sessionId = null;
        chatApi.clearMessages();
        setStatus("Select a book");
        return;
      }
      try {
        setStatus("Loading…");
        sessionId = await ensureSession(bookId);
        await chatApi.loadHistory(sessionId);
        setStatus("Ready");
      } catch (e) {
        sessionId = null;
        chatApi.clearMessages();
        setStatus(e instanceof Error ? e.message : "Session error");
      }
    },
  });

  bookListRef = bookList;

  initSettings({
    onAfterClearAllBooks: async () => {
      await bookList.refresh();
      const sel = document.getElementById("book-select");
      if (sel instanceof HTMLSelectElement) sel.value = "";
      sessionId = null;
      chatApi.clearMessages();
      setStatus("All books and conversations cleared.");
    },
  });

  initBookUpload({
    onSuccess: async () => {
      await bookList.refresh();
      setStatus("Upload complete");
    },
    onError: (err) => setStatus(err.message),
  });

  const logViewer = initLogViewer({ pollMs: 2000, containerId: "log-viewer-output" });
  wireMainViews(bookList, refs, setStatus, logViewer);
  setStatus("Ready");
}

void initApp();
