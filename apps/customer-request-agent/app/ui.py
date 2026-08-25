"""Minimal self-contained web UI for invoking the A2A agent locally.

Served at GET /ui by main.py. No build step, no extra dependency: inline
HTML/CSS/JS that talks to the agent's own JSON-RPC endpoint (POST /).
Inspired by the a2a-inspector: connect to an agent-card URL, view the card,
then chat with the agent over a streaming (message/stream) SSE session.
"""

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Customer Requests agent</title>
<link rel="icon" href="./img/favicon.ico"/>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
  :root { --bg:#fff; --fg:#1a1a1a; --muted:#666; --border:#e0e0e0;
          --panel:#f7f7f8; --accent:#2563eb; --user:#dbe7ff; --agent:#eceef1;
          --ok:#16a34a; --err:#dc2626; }
  * { box-sizing: border-box; }
  body { margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
         color:var(--fg); background:var(--bg); }
  .wrap { max-width:900px; margin:0 auto; padding:24px; }
  h1 { font-size:24px; margin:0 0 20px; }
  h2 { font-size:18px; margin:24px 0 12px; }
  .row { display:flex; gap:8px; align-items:center; }
  input[type=text], input[type=password], textarea {
    width:100%; padding:10px 12px; border:1px solid var(--border); border-radius:8px;
    font-size:14px; font-family:inherit; }
  button { background:var(--accent); color:#fff; border:0; border-radius:8px;
           padding:10px 18px; font-size:14px; cursor:pointer; white-space:nowrap; }
  button:disabled { opacity:.5; cursor:default; }
  details { margin:12px 0; }
  summary { cursor:pointer; color:var(--muted); font-size:14px; padding:4px 0; }
  hr { border:0; border-top:1px solid var(--border); margin:20px 0; }
  .status { text-align:center; font-weight:600; margin:8px 0; }
  .status.ok { color:var(--ok); }
  .status.err { color:var(--err); }
  pre { background:var(--panel); border:1px solid var(--border); border-radius:8px;
        padding:16px; overflow:auto; font-size:12px; max-height:340px; margin:0; }
  #chat { border:1px solid var(--border); border-radius:8px; background:var(--panel);
          padding:12px; height:360px; overflow-y:auto; display:flex; flex-direction:column; gap:10px; }
  .msg { padding:10px 14px; border-radius:10px; max-width:80%; white-space:pre-wrap;
         word-wrap:break-word; font-size:14px; line-height:1.45; }
  .msg.user { background:var(--user); align-self:flex-end; }
  .msg.agent { background:var(--agent); align-self:flex-start; white-space:normal; }
  .meta { font-size:11px; color:var(--muted); align-self:center; }
  .msg.agent p { margin:0 0 8px; }
  .msg.agent p:last-child { margin-bottom:0; }
  .msg.agent ul, .msg.agent ol { margin:0 0 8px; padding-left:20px; }
  .msg.agent li { margin:2px 0; }
  .msg.agent code { background:rgba(0,0,0,.07); border-radius:4px; padding:1px 5px; font-size:12px; font-family:monospace; }
  .msg.agent pre { background:rgba(0,0,0,.07); border:none; border-radius:6px; padding:10px 12px; font-size:12px; overflow-x:auto; margin:6px 0; max-height:none; }
  .msg.agent pre code { background:none; padding:0; }
  .msg.agent h1,.msg.agent h2,.msg.agent h3 { margin:8px 0 4px; font-size:15px; }
  .msg.agent blockquote { border-left:3px solid var(--border); margin:6px 0; padding:4px 10px; color:var(--muted); }
  .chatbar { margin-top:12px; }
  .hidden { display:none; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Customer Requests agent - AI-enabled Integrations CodeJam</h1>

  <div class="row">
    <input type="text" id="cardUrl" placeholder="Agent card URL" />
    <button id="connectBtn">Connect</button>
  </div>
  <details>
    <summary>Authentication &amp; Headers</summary>
    <div style="margin-top:8px;">
      <input type="password" id="token" placeholder="Bearer token (optional)" />
    </div>
  </details>

  <h2>Agent Card</h2>
  <div id="cardStatus" class="status"></div>
  <pre id="cardJson" class="hidden"></pre>

  <hr />

  <div class="row" style="margin:24px 0 12px;align-items:baseline;">
    <h2 style="margin:0;flex:1;">Chat</h2>
    <button id="newChatBtn" disabled style="background:var(--panel);color:var(--fg);
      border:1px solid var(--border);font-size:13px;padding:6px 14px;">New Chat</button>
  </div>
  <div id="chat"></div>
  <div class="row chatbar">
    <input type="text" id="chatInput" placeholder="Type a message..." disabled />
    <button id="sendBtn" disabled>Send</button>
  </div>
</div>

<script>
(function () {
  const origin = window.location.origin;
  const $ = (id) => document.getElementById(id);
  $("cardUrl").value = origin + "/.well-known/agent-card.json";

  let rpcUrl = origin + "/";   // JSON-RPC endpoint (POST /)
  let contextId = null;        // captured to continue the conversation
  let taskId = null;           // only reused while a task awaits more input

  function uuid() {
    if (crypto.randomUUID) return crypto.randomUUID();
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
    });
  }

  function authHeaders() {
    const t = $("token").value.trim();
    return t ? { Authorization: "Bearer " + t } : {};
  }

  function setCardStatus(text, cls) {
    const el = $("cardStatus");
    el.textContent = text;
    el.className = "status " + (cls || "");
  }

  function addMsg(role, text) {
    const el = document.createElement("div");
    el.className = "msg " + role;
    el.textContent = text;
    $("chat").appendChild(el);
    $("chat").scrollTop = $("chat").scrollHeight;
    return el;
  }

  function addMeta(text) {
    const el = document.createElement("div");
    el.className = "meta";
    el.textContent = text;
    $("chat").appendChild(el);
    $("chat").scrollTop = $("chat").scrollHeight;
  }

  // ---- Connect: fetch and display the agent card ----
  $("connectBtn").addEventListener("click", async () => {
    const url = $("cardUrl").value.trim();
    setCardStatus("Connecting...", "");
    $("cardJson").classList.add("hidden");
    try {
      const res = await fetch(url, { headers: authHeaders() });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const card = await res.json();
      $("cardJson").textContent = JSON.stringify(card, null, 2);
      $("cardJson").classList.remove("hidden");
      setCardStatus("Agent card is valid.", "ok");
      // Derive the RPC endpoint from the card URL's origin (same-origin default).
      try { rpcUrl = new URL(url).origin + "/"; } catch (e) {}
      contextId = null; taskId = null;
      $("chatInput").disabled = false;
      $("sendBtn").disabled = false;
      $("newChatBtn").disabled = false;
      $("chatInput").focus();
    } catch (e) {
      setCardStatus("Failed to load agent card: " + e.message, "err");
      $("chatInput").disabled = true;
      $("sendBtn").disabled = true;
    }
  });

  // ---- New Chat: reset session state and clear messages ----
  $("newChatBtn").addEventListener("click", () => {
    contextId = null; taskId = null;
    $("chat").innerHTML = "";
  });

  // ---- Send: stream a message via message/stream (SSE over POST) ----
  async function send() {
    const text = $("chatInput").value.trim();
    if (!text) return;
    $("chatInput").value = "";
    addMsg("user", text);
    $("sendBtn").disabled = true;
    $("chatInput").disabled = true;

    const message = {
      role: "user",
      parts: [{ kind: "text", text: text }],
      messageId: uuid(),
      kind: "message",
    };
    if (contextId) message.contextId = contextId;
    if (taskId) message.taskId = taskId;

    const body = {
      jsonrpc: "2.0",
      id: uuid(),
      method: "message/stream",
      params: { message: message },
    };

    let agentEl = null;
    const artifacts = {}; // artifactId -> accumulated text
    const ensureAgentEl = () => (agentEl = agentEl || addMsg("agent", ""));

    try {
      const res = await fetch(rpcUrl, {
        method: "POST",
        headers: Object.assign(
          { "Content-Type": "application/json", Accept: "text/event-stream" },
          authHeaders()
        ),
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error("HTTP " + res.status);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      let done = false;

      const handleEvent = (rawEvent) => {
        // An SSE event may have multiple lines; collect data: lines,
        // ignore comment/ping lines (":" prefix) and empty frames.
        const dataLines = rawEvent
          .split("\n")
          .filter((l) => l.startsWith("data:"))
          .map((l) => l.slice(5).trim());
        if (!dataLines.length) return;
        let obj;
        try { obj = JSON.parse(dataLines.join("")); } catch (e) { return; }

        if (obj.error) {
          ensureAgentEl().innerHTML = "Error: " + (obj.error.message || JSON.stringify(obj.error));
          done = true; return;
        }
        const r = obj.result;
        if (!r) return;

        if (r.kind === "task") {
          if (r.id) taskId = r.id;
          if (r.contextId) contextId = r.contextId;
          (r.artifacts || []).forEach((a) => {
            const t = partsText(a.parts);
            if (t) { artifacts[a.artifactId] = t; ensureAgentEl().innerHTML = renderMd(joinArtifacts(artifacts)); }
          });
        } else if (r.kind === "artifact-update") {
          if (r.taskId) taskId = r.taskId;
          if (r.contextId) contextId = r.contextId;
          const a = r.artifact || {};
          const t = partsText(a.parts);
          const prev = artifacts[a.artifactId] || "";
          artifacts[a.artifactId] = r.append ? prev + t : t;
          ensureAgentEl().innerHTML = renderMd(joinArtifacts(artifacts));
        } else if (r.kind === "status-update") {
          if (r.taskId) taskId = r.taskId;
          if (r.contextId) contextId = r.contextId;
          const st = r.status && r.status.state;
          const smsg = r.status && r.status.message && partsText(r.status.message.parts);
          if (smsg) { ensureAgentEl().innerHTML = renderMd(joinArtifacts(artifacts) || smsg); }
          if (r.final) {
            done = true;
            if (st) addMeta("State: " + st);
            // Keep taskId only if the agent is waiting for more input on this
            // task; a completed/failed task is terminal and cannot be resumed.
            if (st !== "input-required") taskId = null;
          }
        } else if (r.kind === "message") {
          const t = partsText(r.parts);
          if (t) ensureAgentEl().innerHTML = renderMd(t);
          done = true;
        }
      };

      while (!done) {
        const { value, done: rdDone } = await reader.read();
        if (rdDone) break;
        // Normalize CRLF -> LF so event framing (blank line) is consistent.
        buf += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

        let sep;
        while ((sep = buf.indexOf("\n\n")) !== -1) {
          handleEvent(buf.slice(0, sep));
          buf = buf.slice(sep + 2);
          if (done) break;
        }
      }
      // Flush any trailing event not terminated by a blank line.
      if (!done && buf.trim()) handleEvent(buf);

      if (agentEl && !agentEl.innerHTML) agentEl.innerHTML = "(no text response)";
    } catch (e) {
      ensureAgentEl().innerHTML = "Error: " + e.message;
    } finally {
      $("chatInput").disabled = false;
      $("sendBtn").disabled = false;
      $("newChatBtn").disabled = false;
      $("chatInput").focus();
    }
  }

  function renderMd(text) {
    if (window.marked) return marked.parse(text || "");
    const el = document.createElement("div");
    el.textContent = text || "";
    return el.innerHTML;
  }

  function partsText(parts) {
    if (!parts) return "";
    return parts.filter((p) => p.kind === "text").map((p) => p.text).join("");
  }
  function joinArtifacts(map) {
    return Object.values(map).join("\n");
  }

  $("sendBtn").addEventListener("click", send);
  $("chatInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  });
})();
</script>
</body>
</html>
"""
