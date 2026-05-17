// ════════════════════════════════════════════════════════════
// Aurora AI — Browser Agent (content script)
// Runs on every page. Provides a floating chat panel that
// connects to the backend and executes DOM operations.
// ════════════════════════════════════════════════════════════

const AURORA_WS = "ws://127.0.0.1:8080/ws";
const AURORA_SESSION_KEY = "aurora_session";

// ── State ──────────────────────────────────────────────────
let ws = null;
let sessionId = null;
let isProcessing = false;
let pendingCommandResolve = null;
let chatInitialized = false;

// ── Create chat UI ─────────────────────────────────────────
function createChatUI() {
  if (chatInitialized) return;
  chatInitialized = true;

  const style = document.createElement("style");
  style.textContent = `
    #aurora-fab {
      position: fixed; bottom: 24px; right: 24px; z-index: 2147483647;
      width: 54px; height: 54px; border-radius: 50%; border: none;
      background: linear-gradient(135deg, #8b6dff, #6a4fd8);
      color: #fff; font-size: 1.4em; cursor: pointer;
      box-shadow: 0 4px 20px rgba(139,109,255,0.4);
      transition: transform 0.2s, box-shadow 0.2s;
      display: flex; align-items: center; justify-content: center;
      font-family: system-ui, sans-serif;
    }
    #aurora-fab:hover { transform: scale(1.06); box-shadow: 0 6px 28px rgba(139,109,255,0.5); }
    #aurora-fab.open { transform: rotate(45deg); }

    #aurora-panel {
      position: fixed; bottom: 88px; right: 24px; z-index: 2147483646;
      width: 380px; height: 540px;
      background: rgba(16,16,26,0.98);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 18px;
      box-shadow: 0 16px 64px rgba(0,0,0,0.6);
      display: flex; flex-direction: column;
      transform-origin: bottom right;
      transform: scale(0.92); opacity: 0;
      pointer-events: none;
      transition: transform 0.25s ease, opacity 0.2s ease;
      overflow: hidden;
      font-family: system-ui, -apple-system, sans-serif;
    }
    #aurora-panel.open {
      transform: scale(1); opacity: 1;
      pointer-events: all;
    }
    #aurora-panel * { box-sizing: border-box; }

    .aurora-header {
      padding: 14px 18px;
      border-bottom: 1px solid rgba(255,255,255,0.06);
      display: flex; align-items: center; gap: 10px;
      flex-shrink: 0;
    }
    .aurora-header .ava {
      width: 30px; height: 30px; border-radius: 50%;
      background: linear-gradient(135deg, #8b6dff, #5ba8ff);
      display: flex; align-items: center; justify-content: center;
      font-size: 0.75em; color: #fff; flex-shrink: 0;
    }
    .aurora-header .info { flex: 1; min-width: 0; }
    .aurora-header .name { font-size: 0.85em; font-weight: 600; color: #e8e8f0; }
    .aurora-header .sub { font-size: 0.72em; color: #666; }
    .aurora-header .close-btn {
      background: none; border: none; color: #666; cursor: pointer;
      font-size: 1.1em; padding: 4px; transition: color 0.2s;
    }
    .aurora-header .close-btn:hover { color: #e8e8f0; }

    .aurora-msgs {
      flex: 1; overflow-y: auto; padding: 14px;
      display: flex; flex-direction: column; gap: 6px;
    }
    .aurora-msgs::-webkit-scrollbar { width: 4px; }
    .aurora-msgs::-webkit-scrollbar-track { background: transparent; }
    .aurora-msgs::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }

    .aurora-msg {
      max-width: 88%; padding: 9px 13px; border-radius: 12px;
      font-size: 0.85em; line-height: 1.5; word-break: break-word;
      animation: aurora-fadein 0.25s ease-out;
    }
    @keyframes aurora-fadein { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }

    .aurora-msg.user {
      align-self: flex-end;
      background: linear-gradient(135deg, #8b6dff, #6a4fd8);
      color: #fff;
      border-bottom-right-radius: 4px;
    }
    .aurora-msg.bot {
      align-self: flex-start;
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.06);
      color: #d0d0e0;
      border-bottom-left-radius: 4px;
    }
    .aurora-msg.thinking {
      align-self: flex-start;
      background: rgba(139,109,255,0.08);
      border: 1px solid rgba(139,109,255,0.12);
      color: #b8a5ff; font-size: 0.8em;
      border-radius: 8px;
    }
    .aurora-msg.action {
      align-self: flex-start;
      background: rgba(91,168,255,0.06);
      border: 1px solid rgba(91,168,255,0.1);
      color: #7bbfff; font-size: 0.8em; padding: 7px 11px;
      font-family: 'SF Mono', 'Fira Code', monospace;
      border-radius: 8px;
    }
    .aurora-msg.error {
      align-self: flex-start;
      background: rgba(231,76,60,0.08);
      border: 1px solid rgba(231,76,60,0.12);
      color: #e8857a; font-size: 0.8em; border-radius: 8px;
    }
    .aurora-msg .hl { color: #b8a5ff; font-weight: 500; }

    .aurora-typing {
      align-self: flex-start;
      display: flex; gap: 4px; padding: 10px 16px;
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.06);
      border-radius: 12px; border-bottom-left-radius: 4px;
    }
    .aurora-typing span {
      width: 6px; height: 6px; border-radius: 50%;
      background: #666; display: inline-block;
      animation: aurora-blink 1.4s infinite;
    }
    .aurora-typing span:nth-child(2) { animation-delay: 0.2s; }
    .aurora-typing span:nth-child(3) { animation-delay: 0.4s; }
    @keyframes aurora-blink { 0%,60%,100% { opacity: 0.3; } 30% { opacity: 1; } }

    .aurora-input-area {
      padding: 10px 14px;
      border-top: 1px solid rgba(255,255,255,0.06);
      display: flex; gap: 8px; flex-shrink: 0;
    }
    .aurora-input-area input {
      flex: 1; padding: 9px 13px; border-radius: 10px; border: none;
      background: rgba(255,255,255,0.05);
      color: #e8e8f0; font-size: 0.85em; outline: 1px solid rgba(255,255,255,0.08);
      font-family: inherit;
    }
    .aurora-input-area input:focus { outline-color: rgba(139,109,255,0.4); }
    .aurora-input-area input::placeholder { color: #555; }
    .aurora-send {
      width: 38px; height: 38px; border-radius: 10px; border: none;
      background: linear-gradient(135deg, #8b6dff, #6a4fd8);
      color: #fff; font-size: 1em; cursor: pointer;
      transition: opacity 0.2s; flex-shrink: 0;
      display: flex; align-items: center; justify-content: center;
    }
    .aurora-send:disabled { opacity: 0.4; cursor: not-allowed; }

    @media (max-width: 500px) {
      #aurora-panel { right: 10px; bottom: 78px; width: calc(100vw - 20px); height: 440px; }
      #aurora-fab { right: 14px; bottom: 18px; width: 48px; height: 48px; }
    }
  `;
  document.head.appendChild(style);

  // FAB
  const fab = document.createElement("button");
  fab.id = "aurora-fab";
  fab.textContent = "✦";
  fab.setAttribute("aria-label", "Toggle Aurora AI");
  document.body.appendChild(fab);

  // Panel
  const panel = document.createElement("div");
  panel.id = "aurora-panel";
  panel.innerHTML = `
    <div class="aurora-header">
      <div class="ava">✦</div>
      <div class="info">
        <div class="name">Aurora AI</div>
        <div class="sub">Browser agent</div>
      </div>
      <button class="close-btn" id="auroraClose">✕</button>
    </div>
    <div class="aurora-msgs" id="auroraMsgs"></div>
    <div class="aurora-input-area">
      <input type="text" id="auroraInput" placeholder="Tell Aurora what to do..." autocomplete="off">
      <button class="aurora-send" id="auroraSend">➤</button>
    </div>
  `;
  document.body.appendChild(panel);

  // Welcome message
  const msgs = document.getElementById("auroraMsgs");
  addMsg("bot", "👋 Hi! I'm Aurora. Tell me what to do on this page.<br>比如：<span class='hl'>「帮我搜索xxx」</span>、<span class='hl'>「点击那个按钮」</span>");

  // Events
  fab.addEventListener("click", toggleChat);
  document.getElementById("auroraClose").addEventListener("click", toggleChat);
  document.getElementById("auroraSend").addEventListener("click", sendMessage);
  document.getElementById("auroraInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });
}

function toggleChat() {
  const panel = document.getElementById("aurora-panel");
  const fab = document.getElementById("aurora-fab");
  const isOpen = panel.classList.toggle("open");
  fab.classList.toggle("open", isOpen);
  if (isOpen) {
    document.getElementById("auroraInput").focus();
    connectWS();
  }
}

// ── WebSocket ──────────────────────────────────────────────
function connectWS() {
  if (ws && ws.readyState === WebSocket.OPEN) return;

  ws = new WebSocket(AURORA_WS);

  ws.onopen = () => {
    // If we have a session from a previous navigation, resume it
    const savedSession = sessionStorage.getItem(AURORA_SESSION_KEY);
    if (savedSession) {
      sessionStorage.removeItem(AURORA_SESSION_KEY);
      ws.send(JSON.stringify({ type: "resume", session: savedSession, url: location.href, title: document.title, content: getPageText() }));
    }
  };

  ws.onmessage = (e) => {
    const data = JSON.parse(e.data);
    handleServerMsg(data);
  };

  ws.onclose = () => {
    ws = null;
    if (document.getElementById("aurora-panel")?.classList.contains("open")) {
      setTimeout(connectWS, 2000);
    }
  };

  ws.onerror = () => { ws = null; };
}

function handleServerMsg(data) {
  removeTyping();

  switch (data.type) {
    case "thinking":
      addMsg("thinking", "💭 " + data.content);
      break;

    case "command":
      executeCommand(data);
      break;

    case "done":
      isProcessing = false;
      updateInputState();
      break;

    case "error":
      addMsg("error", "❌ " + data.content);
      isProcessing = false;
      updateInputState();
      break;
  }
}

// ── Execute commands in the page ───────────────────────────
async function executeCommand(cmd) {
  addMsg("action", `<b>${cmd.action}</b>(${JSON.stringify(cmd.params)})`);

  let result = "";

  try {
    switch (cmd.action) {
      case "navigate":
      case "browser_navigate": {
        const url = cmd.params.url;
        // Save session before navigating
        if (cmd.session) {
          sessionStorage.setItem(AURORA_SESSION_KEY, cmd.session);
        }
        addMsg("thinking", `🌐 Navigating to ${url}...`);
        // Send result immediately, then navigate
        sendResult(cmd.id, `Navigating to: ${url}`);
        // Navigate after a brief delay so the WS message goes through
        await sleep(100);
        window.location.href = url;
        return; // Don't send result again
      }

      case "click":
      case "browser_click": {
        const sel = cmd.params.selector;
        const el = findElement(sel);
        if (!el) throw new Error(`Element not found: ${sel}`);
        el.click();
        await sleep(300);
        result = `Clicked: ${sel}`;
        break;
      }

      case "fill":
      case "browser_fill": {
        const sel = cmd.params.selector;
        const val = cmd.params.value;
        const el = findElement(sel);
        if (!el) throw new Error(`Element not found: ${sel}`);
        el.value = "";
        el.focus();
        // Use execCommand for reliable input
        document.execCommand("insertText", false, val);
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
        await sleep(200);
        result = `Filled ${val.length} chars into: ${sel}`;
        break;
      }

      case "select":
      case "browser_select": {
        const sel2 = cmd.params.selector;
        const optVal = cmd.params.value;
        const el2 = findElement(sel2);
        if (!el2) throw new Error(`Element not found: ${sel2}`);
        el2.value = optVal;
        el2.dispatchEvent(new Event("change", { bubbles: true }));
        result = `Selected "${optVal}" in ${sel2}`;
        break;
      }

      case "get_text":
      case "browser_get_text": {
        if (cmd.params.selector) {
          const el3 = findElement(cmd.params.selector);
          result = el3 ? el3.innerText.slice(0, 2000) : "Element not found";
        } else {
          result = getPageText();
        }
        break;
      }

      case "scroll":
      case "browser_scroll": {
        const dir = cmd.params.direction || "down";
        const amt = cmd.params.amount || 500;
        window.scrollBy(0, dir === "up" ? -amt : amt);
        await sleep(200);
        result = `Scrolled ${dir} ${amt}px`;
        break;
      }

      case "evaluate":
      case "browser_evaluate": {
        result = String(await evalInPage(cmd.params.code));
        break;
      }

      case "screenshot":
      case "browser_screenshot": {
        result = "📸 Screenshot: check assets/aurora_screenshot.png";
        break;
      }

      default:
        result = `Unknown action: ${cmd.action}`;
    }
  } catch (err) {
    result = `❌ Error: ${err.message}`;
  }

  sendResult(cmd.id, result);
}

function findElement(sel) {
  // Try as CSS selector first
  try {
    const el = document.querySelector(sel);
    if (el) return el;
  } catch (_) {}

  // Try by visible text (for button text, link text, etc.)
  if (sel.includes("=") && !sel.startsWith(".") && !sel.startsWith("#")) {
    // Might be an attribute selector already
  } else {
    // Try to find by text content
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (node.textContent.trim().toLowerCase().includes(sel.toLowerCase())) {
        const parent = node.parentElement;
        if (parent && (parent.tagName === "BUTTON" || parent.tagName === "A" || parent.tagName === "LABEL" || parent.tagName === "SPAN" || parent.tagName === "LI")) {
          return parent;
        }
      }
    }
  }

  return null;
}

function getPageText() {
  // Get main content, skip scripts, styles, etc.
  const clone = document.body.cloneNode(true);
  clone.querySelectorAll("script, style, svg, noscript, iframe").forEach(e => e.remove());
  return (clone.innerText || "").trim().slice(0, 5000);
}

async function evalInPage(code) {
  // Create and evaluate a function to handle async code
  const fn = new Function(`return (async () => { ${code} })()`);
  return await fn();
}

function sendResult(cmdId, content) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "result", id: cmdId, content }));
    addMsg("result", String(content).slice(0, 300));
  }
}

// ── Send chat message ──────────────────────────────────────
function sendMessage() {
  const input = document.getElementById("auroraInput");
  const text = input.value.trim();
  if (!text || isProcessing) return;

  input.value = "";
  addMsg("user", text);
  showTyping();

  if (!ws || ws.readyState !== WebSocket.OPEN) {
    addMsg("error", "Connecting to server...");
    connectWS();
    setTimeout(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        isProcessing = true;
        updateInputState();
        ws.send(JSON.stringify({ type: "chat", content: text, url: location.href, title: document.title }));
      }
    }, 1500);
    return;
  }

  isProcessing = true;
  updateInputState();
  ws.send(JSON.stringify({ type: "chat", content: text, url: location.href, title: document.title, pageContent: getPageText() }));
}

function updateInputState() {
  const input = document.getElementById("auroraInput");
  const sendBtn = document.getElementById("auroraSend");
  if (input) input.disabled = isProcessing;
  if (sendBtn) sendBtn.disabled = isProcessing;
}

// ── Chat UI helpers ────────────────────────────────────────
function addMsg(type, content) {
  const msgs = document.getElementById("auroraMsgs");
  if (!msgs) return;
  const div = document.createElement("div");
  div.className = "aurora-msg " + type;
  div.innerHTML = content;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

function showTyping() {
  removeTyping();
  const msgs = document.getElementById("auroraMsgs");
  if (!msgs) return;
  const div = document.createElement("div");
  div.className = "aurora-typing";
  div.id = "auroraTyping";
  div.innerHTML = "<span></span><span></span><span></span>";
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

function removeTyping() {
  const t = document.getElementById("auroraTyping");
  if (t) t.remove();
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ── Init ───────────────────────────────────────────────────
// Wait a tiny bit to let the page settle
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => setTimeout(createChatUI, 500));
} else {
  setTimeout(createChatUI, 500);
}
