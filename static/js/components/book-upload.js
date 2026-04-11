/**
 * Book upload dialog: drag-and-drop, chunking strategy, progress UI, `uploadBook` API.
 */

import { uploadBook } from "../api.js";

/** @type {Record<string, string>} */
const DEFAULT_IDS = {
  dialog: "upload-dialog",
  openButton: "upload-open",
  dropzone: "upload-dropzone",
  fileInput: "upload-file",
  chunkSelect: "chunking-strategy",
  feedback: "upload-feedback",
  progress: "upload-progress",
  form: "upload-form",
  cancelButton: "upload-cancel",
  submitButton: "upload-submit",
};

/**
 * @param {string} name
 * @param {HTMLElement | null | undefined} el
 * @returns {HTMLElement}
 */
function requireEl(name, el) {
  if (!el) {
    throw new Error(`initBookUpload: missing element for ${name}`);
  }
  return el;
}

/**
 * @param {HTMLElement} root
 * @returns {HTMLElement | null}
 */
function findProgressBar(root) {
  return root.querySelector(".upload-progress__bar");
}

/**
 * @param {number} value
 * @param {HTMLElement} bar
 * @param {HTMLElement} container
 */
function setProgress(value, bar, container) {
  const clamped = Math.max(0, Math.min(100, value));
  bar.style.width = `${clamped}%`;
  bar.setAttribute("aria-valuenow", String(Math.round(clamped)));
  container.setAttribute("aria-hidden", clamped <= 0 ? "true" : "false");
}

/**
 * @param {{ stage: string, progress: number, detail?: string }} ev
 * @returns {string}
 */
function formatUploadStageLine(ev) {
  if (ev.detail) return ev.detail;
  const map = {
    parsing: "Parsing book…",
    chunking: "Chunking text…",
    embedding: "Embedding chunks…",
    indexing: "Indexing search…",
    done: "Finishing…",
  };
  return map[ev.stage] || ev.stage || "";
}

/**
 * @param {object} [options]
 * @param {Record<string, string>} [options.ids] element id overrides
 * @param {(result: unknown) => void} [options.onSuccess]
 * @param {(err: Error) => void} [options.onError]
 * @returns {{ open: () => void, close: () => void }}
 */
export function initBookUpload(options = {}) {
  const ids = { ...DEFAULT_IDS, ...options.ids };

  const dialog = /** @type {HTMLDialogElement} */ (requireEl("dialog", document.getElementById(ids.dialog)));
  const openButton = requireEl("openButton", document.getElementById(ids.openButton));
  const dropzone = requireEl("dropzone", document.getElementById(ids.dropzone));
  const fileInput = /** @type {HTMLInputElement} */ (requireEl("fileInput", document.getElementById(ids.fileInput)));
  const chunkSelect = /** @type {HTMLSelectElement} */ (requireEl("chunkSelect", document.getElementById(ids.chunkSelect)));
  const fixedSizeOptions = document.getElementById("upload-fixed-size-options");
  const chunkSizeInput = /** @type {HTMLInputElement | null} */ (document.getElementById("upload-chunk-size"));
  const overlapRatioInput = /** @type {HTMLInputElement | null} */ (document.getElementById("upload-overlap-ratio"));
  const stageEl = /** @type {HTMLParagraphElement | null} */ (document.getElementById("upload-stage"));
  const feedbackEl = /** @type {HTMLParagraphElement} */ (
    requireEl("feedback", document.getElementById(ids.feedback))
  );
  const progressContainer = requireEl("progress", document.getElementById(ids.progress));
  const progressBar = findProgressBar(progressContainer);
  if (!progressBar) {
    throw new Error("initBookUpload: .upload-progress__bar not found inside progress container");
  }
  const form = /** @type {HTMLFormElement} */ (requireEl("form", document.getElementById(ids.form)));
  const cancelButton = requireEl("cancelButton", document.getElementById(ids.cancelButton));
  const submitButton = /** @type {HTMLButtonElement} */ (requireEl("submitButton", document.getElementById(ids.submitButton)));

  /** @type {File | null} */
  let selectedFile = null;

  function resetProgress() {
    setProgress(0, progressBar, progressContainer);
    if (stageEl) {
      stageEl.textContent = "";
      stageEl.hidden = true;
    }
  }

  function clearUploadFeedback() {
    feedbackEl.textContent = "";
    feedbackEl.classList.remove("upload-feedback--error");
    feedbackEl.hidden = true;
  }

  /**
   * @param {string} message
   */
  function showUploadError(message) {
    feedbackEl.textContent = message;
    feedbackEl.classList.add("upload-feedback--error");
    feedbackEl.hidden = false;
  }

  function setBusy(busy) {
    submitButton.disabled = busy;
    cancelButton.disabled = busy;
    openButton.disabled = busy;
    form.setAttribute("aria-busy", busy ? "true" : "false");
  }

  function pickFile(file) {
    if (!file) return;
    const name = file.name.toLowerCase();
    if (!name.endsWith(".epub")) {
      const err = new Error("Only EPUB files are supported.");
      if (options.onError) options.onError(err);
      else console.error(err);
      return;
    }
    selectedFile = file;
    clearUploadFeedback();
    const p = dropzone.querySelector("p");
    if (p) {
      p.textContent = `Selected: ${file.name}`;
    }
  }

  openButton.addEventListener("click", () => {
    clearUploadFeedback();
    if (typeof dialog.showModal === "function") {
      dialog.showModal();
    }
  });

  cancelButton.addEventListener("click", () => {
    dialog.close("cancel");
    resetProgress();
    clearUploadFeedback();
    selectedFile = null;
  });

  dropzone.addEventListener("click", () => {
    fileInput.click();
  });

  dropzone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      fileInput.click();
    }
  });

  fileInput.addEventListener("change", () => {
    const f = fileInput.files?.[0];
    if (f) pickFile(f);
  });

  function syncFixedSizeOptionsVisibility() {
    if (!fixedSizeOptions) return;
    const show = chunkSelect.value === "fixed-size";
    fixedSizeOptions.hidden = !show;
  }

  chunkSelect.addEventListener("change", syncFixedSizeOptionsVisibility);
  syncFixedSizeOptionsVisibility();

  dropzone.addEventListener("dragenter", (e) => {
    e.preventDefault();
    dropzone.classList.add("upload-dropzone--active");
  });

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
    dropzone.classList.add("upload-dropzone--active");
  });

  dropzone.addEventListener("dragleave", (e) => {
    e.preventDefault();
    if (!dropzone.contains(e.relatedTarget)) {
      dropzone.classList.remove("upload-dropzone--active");
    }
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("upload-dropzone--active");
    const f = e.dataTransfer?.files?.[0];
    if (f) pickFile(f);
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!selectedFile) {
      const err = new Error("Choose an EPUB file first.");
      if (options.onError) options.onError(err);
      else console.error(err);
      return;
    }

    const strategy = chunkSelect.value;
    clearUploadFeedback();
    setBusy(true);
    resetProgress();
    setProgress(0, progressBar, progressContainer);

    try {
      /** B06: extras.chunkSize / extras.overlapRatio → FormData chunk_size / overlap_ratio in api.js */
      /** @type {{ chunkSize?: number, overlapRatio?: number }} */
      const extras = {};
      if (strategy === "fixed-size" && chunkSizeInput && overlapRatioInput) {
        const cs = parseInt(String(chunkSizeInput.value), 10);
        const orv = parseFloat(String(overlapRatioInput.value));
        if (Number.isFinite(cs)) extras.chunkSize = cs;
        if (Number.isFinite(orv)) extras.overlapRatio = orv;
      }
      const result = await uploadBook(selectedFile, strategy, extras, {
        onProgress: (ev) => {
          setProgress(ev.progress, progressBar, progressContainer);
          if (stageEl) {
            const line = formatUploadStageLine(ev);
            stageEl.textContent = line;
            stageEl.hidden = !line;
          }
        },
      });
      setProgress(100, progressBar, progressContainer);
      clearUploadFeedback();
      if (options.onSuccess) options.onSuccess(result);
      dialog.close("ok");
      selectedFile = null;
      fileInput.value = "";
      const p = dropzone.querySelector("p");
      if (p) {
        p.textContent = "Drag and drop an EPUB here, or click to browse.";
      }
    } catch (err) {
      resetProgress();
      const error = err instanceof Error ? err : new Error(String(err));
      showUploadError(error.message);
      if (options.onError) options.onError(error);
      else console.error(error);
    } finally {
      setBusy(false);
      resetProgress();
    }
  });

  return {
    open: () => {
      if (typeof dialog.showModal === "function") dialog.showModal();
    },
    close: () => dialog.close(),
  };
}
