/**
 * References panel: chunk cards, optional query highlighting, clear control.
 */

import { getBookChunks } from "../api.js";

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
function highlightText(text, query) {
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
 * @param {HTMLElement} container
 * @param {number} ordinal
 * @param {object} chunk
 */
function renderReferenceChunk(container, ordinal, chunk) {
  const id = chunk.id != null ? chunk.id : "?";
  const chapter = chunk.chapter_title ?? chunk.chapter ?? "";
  const idx = chunk.chunk_index ?? chunk.chunkIndex;
  const strategy = chunk.strategy ?? "";
  const text = typeof chunk.text === "string" ? chunk.text : String(chunk.text ?? "");

  const article = document.createElement("article");
  article.className = "reference-chunk";
  article.dataset.chunkId = String(id);

  const head = document.createElement("header");
  head.className = "reference-chunk__head";

  const label = document.createElement("span");
  label.className = "reference-chunk__label";
  label.textContent = `[${ordinal}]`;

  const meta = document.createElement("span");
  meta.className = "reference-chunk__meta";
  const metaBits = [];
  if (chapter) metaBits.push(`Chapter: ${chapter}`);
  if (idx !== undefined && idx !== null && idx !== "") metaBits.push(`Chunk index: ${idx}`);
  if (strategy) metaBits.push(String(strategy));
  meta.textContent = metaBits.join(" · ");

  head.appendChild(label);
  if (metaBits.length) head.appendChild(meta);

  const body = document.createElement("div");
  body.className = "reference-chunk__body";
  body.appendChild(highlightText(text, _highlightQuery));

  article.appendChild(head);
  article.appendChild(body);
  container.appendChild(article);
  container.scrollTop = container.scrollHeight;
}

/** @type {string} */
let _highlightQuery = "";

/**
 * @param {object} [options]
 * @param {string} [options.listId]
 * @param {string} [options.clearButtonId]
 * @returns {{ clear: () => void, setHighlightQuery: (q: string) => void, appendReferencedChunkIds: (bookId: number|string, chunkIds: number[]) => Promise<void>, appendReferenceEntry: (entry: object) => void }}
 */
export function initReferences(options = {}) {
  const listEl = document.getElementById(options.listId ?? "references-list");
  const clearBtn = document.getElementById(options.clearButtonId ?? "clear-references");
  if (!listEl || !clearBtn) {
    throw new Error("initReferences: #references-list and #clear-references required");
  }

  function clear() {
    listEl.innerHTML = "";
  }

  clearBtn.addEventListener("click", () => {
    clear();
  });

  /**
   * @param {string} q
   */
  function setHighlightQuery(q) {
    _highlightQuery = typeof q === "string" ? q : "";
  }

  /**
   * @param {number|string} bookId
   * @param {number[]} chunkIds
   */
  async function appendReferencedChunkIds(bookId, chunkIds) {
    if (bookId == null || !chunkIds?.length) return;

    let rows = [];
    try {
      const raw = await getBookChunks(bookId);
      if (Array.isArray(raw)) {
        rows = raw;
      } else if (raw && typeof raw === "object") {
        rows = /** @type {any} */ (raw).chunks ?? /** @type {any} */ (raw).items ?? [];
      }
    } catch {
      rows = [];
    }

    const byId = new Map();
    for (const r of rows) {
      if (r && r.id != null) byId.set(String(r.id), r);
    }

    const existing = listEl.querySelectorAll(".reference-chunk").length;
    chunkIds.forEach((cid, j) => {
      const row = byId.get(String(cid));
      const ordinal = existing + j + 1;
      renderReferenceChunk(
        listEl,
        ordinal,
        row ?? {
          id: cid,
          text: "(Chunk text unavailable — check API or book index.)",
        },
      );
    });
  }

  /**
   * @param {object} entry
   */
  function appendReferenceEntry(entry) {
    const n = listEl.querySelectorAll(".reference-chunk").length + 1;
    renderReferenceChunk(listEl, n, entry);
  }

  return {
    clear,
    setHighlightQuery,
    appendReferencedChunkIds,
    appendReferenceEntry,
  };
}
