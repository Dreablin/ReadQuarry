/**
 * Settings modal: load/save app settings via `/api/settings`.
 */

import { getSettings, resetSettings, testLlm, updateSettings } from "../api.js";

/** @type {readonly string[]} */
const FIELD_KEYS = [
  "llm_mode",
  "ollama_base_url",
  "ollama_model_id",
  "provider",
  "api_key",
  "api_base_url",
  "model_id",
  "max_tokens",
  "temperature",
  "embedding_model",
  "embedding_device",
  "semantic_top_k",
  "exact_results",
  "final_context_chunks",
];

/**
 * @param {string} key
 * @returns {string}
 */
function fieldId(key) {
  return `settings-${key}`;
}

/**
 * @param {Record<string, unknown>} data
 */
function fillForm(data) {
  for (const key of FIELD_KEYS) {
    const el = document.getElementById(fieldId(key));
    if (!el || !("value" in el)) continue;
    const v = data[key];
    if (v === undefined || v === null) continue;
    el.value = String(v);
  }
}

/**
 * @returns {Record<string, unknown>}
 */
function readForm() {
  /** @type {Record<string, unknown>} */
  const out = {};
  for (const key of FIELD_KEYS) {
    const el = document.getElementById(fieldId(key));
    if (!el || !("value" in el)) continue;
    const raw = el.value;
    if (
      key === "max_tokens" ||
      key === "semantic_top_k" ||
      key === "exact_results" ||
      key === "final_context_chunks"
    ) {
      const n = parseInt(String(raw), 10);
      if (!Number.isNaN(n)) out[key] = n;
    } else if (key === "temperature") {
      const n = parseFloat(String(raw));
      if (!Number.isNaN(n)) out[key] = n;
    } else {
      out[key] = raw;
    }
  }
  return out;
}

/**
 * @param {object} options
 * @param {string} [options.dialogId]
 * @param {string} [options.formId]
 * @param {string} [options.openButtonId]
 * @param {string} [options.feedbackId]
 */
export function initSettings(options = {}) {
  const dialogId = options.dialogId ?? "settings-dialog";
  const formId = options.formId ?? "settings-form";
  const openButtonId = options.openButtonId ?? "settings-open";
  const feedbackId = options.feedbackId ?? "settings-feedback";

  const dialog = document.getElementById(dialogId);
  const form = document.getElementById(formId);
  const openBtn = document.getElementById(openButtonId);
  const feedback = document.getElementById(feedbackId);

  if (!(dialog instanceof HTMLDialogElement)) {
    throw new Error(`initSettings: #${dialogId} not found or not a <dialog>`);
  }
  if (!(form instanceof HTMLFormElement)) {
    throw new Error(`initSettings: #${formId} not found or not a <form>`);
  }

  function setFeedback(text) {
    if (feedback) feedback.textContent = text;
  }

  async function loadAndShow() {
    setFeedback("");
    try {
      const data = await getSettings();
      if (data && typeof data === "object") {
        fillForm(/** @type {Record<string, unknown>} */ (data));
      }
    } catch (e) {
      setFeedback(e instanceof Error ? e.message : "Failed to load settings");
    }
    dialog.showModal();
  }

  if (openBtn) {
    openBtn.addEventListener("click", () => {
      void loadAndShow();
    });
  }

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    setFeedback("Saving…");
    try {
      const payload = readForm();
      await updateSettings(payload);
      setFeedback("Saved.");
    } catch (e) {
      setFeedback(e instanceof Error ? e.message : "Save failed");
    }
  });

  const closeBtn = document.getElementById("settings-close");
  if (closeBtn) {
    closeBtn.addEventListener("click", () => {
      dialog.close();
    });
  }

  const resetBtn = document.getElementById("settings-reset");
  if (resetBtn) {
    resetBtn.addEventListener("click", async () => {
      setFeedback("Resetting…");
      try {
        const data = await resetSettings();
        if (data && typeof data === "object") {
          fillForm(/** @type {Record<string, unknown>} */ (data));
        }
        setFeedback("Defaults restored.");
      } catch (e) {
        setFeedback(e instanceof Error ? e.message : "Reset failed");
      }
    });
  }

  const testBtn = document.getElementById("settings-test-llm");
  if (testBtn) {
    testBtn.addEventListener("click", async () => {
      setFeedback("Testing LLM…");
      try {
        const res = await testLlm();
        setFeedback(typeof res === "object" ? JSON.stringify(res) : String(res));
      } catch (e) {
        setFeedback(e instanceof Error ? e.message : "Test failed");
      }
    });
  }
}
