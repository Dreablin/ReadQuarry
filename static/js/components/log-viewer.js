/**
 * Polls `/api/logs` and renders ring-buffer entries into a scrollable `<pre>`.
 */

import { fetchLogs } from "../api.js";

/**
 * @param {object} [options]
 * @param {number} [options.pollMs]
 * @param {string} [options.containerId]
 */
export function initLogViewer(options = {}) {
  const pollMs = options.pollMs ?? 2000;
  const containerId = options.containerId ?? "log-viewer-output";
  const pre = document.getElementById(containerId);
  if (!(pre instanceof HTMLElement)) {
    throw new Error(`initLogViewer: #${containerId} not found`);
  }

  /** @type {ReturnType<typeof setInterval> | null} */
  let timer = null;
  let lastCount = -1;

  async function refresh() {
    try {
      const data = await fetchLogs();
      const entries = Array.isArray(data?.entries) ? data.entries : [];
      const count = Number.isFinite(data?.count) ? Number(data.count) : entries.length;
      if (count === lastCount) {
        return;
      }
      const lines = entries.map((e) => (typeof e?.message === "string" ? e.message : JSON.stringify(e)));
      pre.textContent = lines.join("\n");
      pre.scrollTop = pre.scrollHeight;
      lastCount = count;
    } catch {
      /* keep previous content on transient errors */
    }
  }

  return {
    start() {
      if (timer != null) return;
      void refresh();
      timer = setInterval(() => void refresh(), pollMs);
    },
    stop() {
      if (timer != null) {
        clearInterval(timer);
        timer = null;
      }
    },
  };
}
