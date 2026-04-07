/**
 * Book selector dropdown: loads `/api/books` and fills `#book-select`.
 */

import { listBooks } from "../api.js";

/**
 * @param {object} [options]
 * @param {string} [options.selectId]
 * @param {(bookId: number | null) => void} [options.onChange]
 * @returns {Promise<{ refresh: () => Promise<void>, getSelectedBookId: () => number | null }>}
 */
export async function initBookList(options = {}) {
  const selectId = options.selectId ?? "book-select";
  const select = document.getElementById(selectId);
  if (!select || !(select instanceof HTMLSelectElement)) {
    throw new Error(`initBookList: #${selectId} not found or not a <select>`);
  }

  /** @type {HTMLOptionElement | null} */
  let placeholder = select.options[0] ?? null;

  function rebuildPlaceholder() {
    if (!placeholder) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "Select a book…";
      placeholder = opt;
    }
  }

  async function refresh() {
    rebuildPlaceholder();
    const raw = await listBooks();
    const books = Array.isArray(raw) ? raw : [];

    select.innerHTML = "";
    select.appendChild(placeholder);

    for (const b of books) {
      if (!b || typeof b !== "object") continue;
      const id = b.id;
      if (id === undefined || id === null) continue;
      const opt = document.createElement("option");
      opt.value = String(id);
      const title = (typeof b.title === "string" && b.title.trim()) ? b.title.trim() : "";
      const file =
        typeof b.file_name === "string" && b.file_name.trim() ? b.file_name.trim() : "";
      opt.textContent = title || file || `Book ${id}`;
      select.appendChild(opt);
    }
  }

  function getSelectedBookId() {
    const v = select.value;
    if (v === "") return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }

  select.addEventListener("change", () => {
    if (typeof options.onChange === "function") {
      options.onChange(getSelectedBookId());
    }
  });

  await refresh();

  return {
    refresh,
    getSelectedBookId,
  };
}
