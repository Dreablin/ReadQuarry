/**
 * Chat panel: history, SSE streaming from `sendChatMessage`, typing indicator.
 */

import { getChatMessages, sendChatMessage } from "../api.js";

/**
 * Parse `text/event-stream` body: events separated by blank lines, lines `data: {...}`.
 *
 * @param {Response} response
 * @param {(data: { type?: string, content?: string, message?: string, referenced_chunk_ids?: number[] }) => void} onEvent
 */
async function consumeSseJson(response, onEvent) {
  const body = response.body;
  if (!body) return;
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let sep;
    while ((sep = buffer.indexOf("\n\n")) >= 0) {
      const block = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      for (const line of block.split("\n")) {
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));
            onEvent(data);
          } catch {
            /* ignore malformed chunk */
          }
        }
      }
    }
  }
}

/**
 * @param {object} options
 * @param {() => number | null} options.getSessionId
 * @param {(msg: string) => void} [options.onError]
 * @param {(chunkIds: number[]) => void} [options.onDone]
 * @param {string} [options.messagesId]
 * @param {string} [options.formId]
 * @param {string} [options.inputId]
 * @param {string} [options.sendButtonId]
 * @returns {Promise<{ loadHistory: (sessionId: number | string) => Promise<void>, clearMessages: () => void }>}
 */
export async function initChat(options) {
  if (!options || typeof options.getSessionId !== "function") {
    throw new Error("initChat: options.getSessionId is required");
  }

  const messagesEl = document.getElementById(options.messagesId ?? "chat-messages");
  const form = document.getElementById(options.formId ?? "chat-form");
  const input = document.getElementById(options.inputId ?? "message-input");
  const sendButton = document.getElementById(options.sendButtonId ?? "send-button");

  if (!messagesEl || !form || !input || !sendButton) {
    throw new Error("initChat: required DOM nodes missing");
  }

  /** @type {HTMLElement | null} */
  let typingEl = null;

  function showTypingIndicator() {
    if (typingEl) return;
    typingEl = document.createElement("div");
    typingEl.className = "typing-indicator";
    typingEl.setAttribute("aria-label", "Assistant is typing");
    typingEl.innerHTML = "<span></span><span></span><span></span>";
    messagesEl.appendChild(typingEl);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function hideTypingIndicator() {
    if (typingEl) {
      typingEl.remove();
      typingEl = null;
    }
  }

  /**
   * @param {"user" | "assistant"} role
   * @param {string} text
   */
  function appendMessage(role, text) {
    const wrap = document.createElement("div");
    wrap.className = `message message--${role}`;
    const roleLine = document.createElement("div");
    roleLine.className = "message__role";
    roleLine.textContent = role === "user" ? "You" : "Assistant";
    const body = document.createElement("div");
    body.className = "message__body";
    body.textContent = text;
    wrap.appendChild(roleLine);
    wrap.appendChild(body);
    messagesEl.appendChild(wrap);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  async function loadHistory(sessionId) {
    const rows = await getChatMessages(sessionId);
    messagesEl.innerHTML = "";
    hideTypingIndicator();
    if (!Array.isArray(rows)) return;
    for (const row of rows) {
      const role = row.role === "user" ? "user" : "assistant";
      const content = typeof row.content === "string" ? row.content : "";
      appendMessage(role, content);
    }
  }

  function clearMessages() {
    messagesEl.innerHTML = "";
    hideTypingIndicator();
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const sessionId = options.getSessionId();
    if (sessionId == null) {
      if (options.onError) options.onError("Choose a book and open a chat session first.");
      return;
    }

    const text = input.value.trim();
    if (!text) return;

    input.value = "";
    appendMessage("user", text);
    showTypingIndicator();
    sendButton.disabled = true;

    try {
      const response = await sendChatMessage(sessionId, text);
      hideTypingIndicator();

      const assistantWrap = document.createElement("div");
      assistantWrap.className = "message message--assistant";
      const roleLine = document.createElement("div");
      roleLine.className = "message__role";
      roleLine.textContent = "Assistant";
      const body = document.createElement("div");
      body.className = "message__body";
      body.textContent = "";
      assistantWrap.appendChild(roleLine);
      assistantWrap.appendChild(body);
      messagesEl.appendChild(assistantWrap);

      await consumeSseJson(response, (ev) => {
        if (ev.type === "delta" && ev.content) {
          body.textContent += ev.content;
          messagesEl.scrollTop = messagesEl.scrollHeight;
        } else if (ev.type === "error") {
          const msg = typeof ev.message === "string" ? ev.message : "Stream error";
          if (options.onError) options.onError(msg);
          body.textContent += body.textContent ? `\n[Error] ${msg}` : msg;
        } else if (ev.type === "done" && options.onDone && Array.isArray(ev.referenced_chunk_ids)) {
          options.onDone(ev.referenced_chunk_ids);
        }
      });
    } catch (err) {
      hideTypingIndicator();
      const msg = err instanceof Error ? err.message : String(err);
      if (options.onError) options.onError(msg);
      appendMessage("assistant", `Error: ${msg}`);
    } finally {
      sendButton.disabled = false;
    }
  });

  return { loadHistory, clearMessages };
}
