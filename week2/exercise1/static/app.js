// EASY-ASSISTANT frontend — vanilla JS, no framework.
// The browser keeps the BARE conversation (what you typed, what the model said)
// and sends it every turn. The server fills the active assistant's template
// with the whole document + your newest message, and reports back what it sent.

const $ = (sel) => document.querySelector(sel);
const els = {
  model: $("#model"), mode: $("#mode"), reset: $("#reset"),
  list: $("#assistant-list"), newBtn: $("#new-assistant"),
  form: $("#assistant-form"), formTitle: $("#form-title"), formError: $("#form-error"),
  fName: $("#f-name"), fSystem: $("#f-system"), fTemplate: $("#f-template"), fFile: $("#f-file"),
  fCurrentDoc: $("#f-current-doc"), fCancel: $("#f-cancel"), fDelete: $("#f-delete"), fSave: $("#f-save"),
  chatTitle: $("#chat-title"), chatDoc: $("#chat-doc"), editBtn: $("#edit-assistant"),
  messages: $("#messages"), composer: $("#composer"), input: $("#input"), send: $("#send"),
  bars: $("#bars"), usageBody: $("#usage tbody"),
  filled: $("#filled"), filledStats: $("#filled-stats"), request: $("#request"), msgcount: $("#msgcount"),
};

let config = {};
let assistants = [];
let active = null;      // the selected assistant (summary, no document text)
let editing = null;     // id of the assistant being edited, or null when creating
let history = [];       // bare OpenAI-format messages for the active assistant
let turns = [];         // [{q, prompt, completion, total}]
let busy = false;

const renderMarkdown = (text) => DOMPurify.sanitize(marked.parse(text || ""));
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    // FastAPI validation errors come back as a list
    const d = data.detail;
    throw new Error(Array.isArray(d) ? d.map((x) => x.msg.replace(/^Value error, /, "")).join("; ") : d || res.statusText);
  }
  return data;
}

// ---------- assistants ----------

async function loadAssistants(selectId) {
  assistants = await api("/api/assistants");
  renderList();
  const pick = assistants.find((a) => a.id === (selectId ?? active?.id)) || assistants[0];
  if (pick) select(pick.id, pick.id === active?.id);
  else { active = null; renderChatHead(); }
}

function renderList() {
  els.list.innerHTML = assistants.length
    ? assistants.map((a) => `
      <li class="${a.id === active?.id ? "active" : ""}" data-id="${a.id}">
        <span class="a-name">${esc(a.name)}</span>
        <span class="muted">${a.document ? `📄 ${esc(a.document.filename)}` : "⚠️ no document"}</span>
      </li>`).join("")
    : '<li class="muted none">No assistants yet.</li>';
}

els.list.addEventListener("click", (e) => {
  const li = e.target.closest("li[data-id]");
  if (li && !busy) select(li.dataset.id);
});

function select(id, keepChat = false) {
  active = assistants.find((a) => a.id === id) || null;
  if (!keepChat) resetChat();
  renderList();
  renderChatHead();
}

function renderChatHead() {
  els.editBtn.hidden = !active;
  if (!active) {
    els.chatTitle.textContent = "No assistant selected";
    els.chatDoc.textContent = "";
  } else {
    els.chatTitle.textContent = active.name;
    const d = active.document;
    els.chatDoc.textContent = d
      ? `📄 ${d.filename} · ${d.chars.toLocaleString()} chars · ${d.words.toLocaleString()} words`
      : "⚠️ no document uploaded — edit the assistant to add one";
  }
  const ready = !!active?.document;
  els.input.disabled = !ready;
  els.send.disabled = !ready || busy;
}

function openForm(a) {
  editing = a?.id ?? null;
  els.formTitle.textContent = a ? `Edit “${a.name}”` : "New assistant";
  els.fName.value = a?.name ?? "";
  els.fSystem.value = a?.system_prompt ?? config.default_system_prompt ?? "";
  els.fTemplate.value = a?.prompt_template ?? config.default_template ?? "";
  els.fFile.value = "";
  els.fFile.required = !a?.document;
  els.fCurrentDoc.textContent = a?.document ? `Current: ${a.document.filename} (${a.document.chars.toLocaleString()} chars). Pick a file to replace it.` : "";
  els.fDelete.hidden = !a;
  els.formError.hidden = true;
  els.form.hidden = false;
  els.fName.focus();
}

function closeForm() { els.form.hidden = true; editing = null; }

els.newBtn.addEventListener("click", () => openForm(null));
els.editBtn.addEventListener("click", () => active && openForm(active));
els.fCancel.addEventListener("click", closeForm);

els.form.addEventListener("submit", async (e) => {
  e.preventDefault();
  els.formError.hidden = true;
  els.fSave.disabled = true;
  try {
    const body = JSON.stringify({ name: els.fName.value, system_prompt: els.fSystem.value, prompt_template: els.fTemplate.value });
    const headers = { "Content-Type": "application/json" };
    let a = editing
      ? await api(`/api/assistants/${editing}`, { method: "PUT", headers, body })
      : await api("/api/assistants", { method: "POST", headers, body });
    editing = a.id; // if the upload below fails, a retry edits this assistant instead of creating a duplicate
    const file = els.fFile.files[0];
    if (file) {
      const fd = new FormData();
      fd.append("file", file);
      a = await api(`/api/assistants/${a.id}/document`, { method: "POST", body: fd });
    }
    const changedActive = a.id === active?.id;
    closeForm();
    await loadAssistants(a.id);
    if (changedActive) resetChat(); // template or document changed → old turns no longer comparable
  } catch (err) {
    els.formError.textContent = err.message;
    els.formError.hidden = false;
    if (editing) await loadAssistants(editing).catch(() => {});
  } finally {
    els.fSave.disabled = false;
  }
});

els.fDelete.addEventListener("click", async () => {
  if (!editing || !confirm("Delete this assistant and its document?")) return;
  await api(`/api/assistants/${editing}`, { method: "DELETE" });
  closeForm();
  active = null;
  await loadAssistants();
});

// ---------- chat window ----------

function addBubble(role, text) {
  els.messages.querySelector(".empty")?.remove();
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  const body = document.createElement("div");
  body.className = "body";
  if (role === "user") body.textContent = text;
  else body.innerHTML = renderMarkdown(text);
  div.appendChild(body);
  els.messages.appendChild(div);
  scrollDown();
  return body;
}

function addReasoning(bubbleBody) {
  const det = document.createElement("details");
  det.className = "reasoning";
  det.innerHTML = "<summary>thinking…</summary><div class=\"r-body\"></div>";
  bubbleBody.parentElement.insertBefore(det, bubbleBody);
  return det.querySelector(".r-body");
}

function scrollDown() { els.messages.scrollTop = els.messages.scrollHeight; }

function setBusy(b) {
  busy = b;
  els.send.textContent = b ? "…" : "Send";
  renderChatHead();
}

function resetChat() {
  history = []; turns = [];
  els.messages.innerHTML = `<p class="empty">${active?.document
    ? `Ask <b>${esc(active.name)}</b> a question about <b>${esc(active.document.filename)}</b>.`
    : "Create an assistant, upload a text file, and ask questions about it."}</p>`;
  els.filled.textContent = "—"; els.filledStats.textContent = "";
  els.request.textContent = "—"; els.msgcount.textContent = "";
  renderUsage();
}
els.reset.addEventListener("click", resetChat);

// ---------- context view ----------

function showRequest(payload, parts) {
  // The full JSON, with the (long) document shortened — it's shown in full above.
  const doc = parts.find((p) => p.kind === "context")?.text;
  const shortDoc = doc && doc.length > 300 ? `${doc.slice(0, 120)}…[document: ${doc.length.toLocaleString()} chars]…${doc.slice(-60)}` : doc;
  els.request.textContent = JSON.stringify(payload, (k, v) =>
    doc && typeof v === "string" && v.includes(doc) ? v.replace(doc, shortDoc) : v, 2);
  els.msgcount.textContent = `(${payload.messages.length} messages)`;

  els.filled.innerHTML = parts.map((p) =>
    p.kind === "template" ? esc(p.text) : `<mark class="${p.kind === "context" ? "ctx" : "usr"}">${esc(p.text)}</mark>`
  ).join("");
  const total = parts.reduce((n, p) => n + p.text.length, 0);
  els.filledStats.textContent = `(${total.toLocaleString()} chars, ${doc ? Math.round((doc.length / total) * 100) : 0}% is the document)`;
}

function addUsage(usage, question) {
  if (!usage) return;
  turns.push({ q: question.length, prompt: usage.prompt_tokens, completion: usage.completion_tokens, total: usage.total_tokens });
  renderUsage();
}

function renderUsage() {
  els.usageBody.innerHTML = turns.map((t, i) =>
    `<tr><td>${i + 1}</td><td>${t.q}</td><td><b>${t.prompt}</b></td><td>${t.completion}</td><td>${t.total}</td></tr>`
  ).join("");
  const max = Math.max(1, ...turns.map((t) => t.total));
  els.bars.innerHTML = turns.map((t, i) => `
    <div class="bar" title="turn ${i + 1}: ${t.prompt} prompt + ${t.completion} completion">
      <span class="p" style="height:${(t.prompt / max) * 100}%"></span>
      <span class="c" style="height:${(t.completion / max) * 100}%"></span>
    </div>`).join("");
}

// ---------- sending ----------

async function sendBaseline(body, question) {
  const data = await api(`/api/assistants/${active.id}/chat`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ messages: history }),
  });
  showRequest(data.request, data.filled_parts);
  if (data.reasoning) addReasoning(body).textContent = data.reasoning;
  body.innerHTML = renderMarkdown(data.content);
  addUsage(data.usage, question);
  return data.content;
}

// SSE over POST: EventSource only does GET, so we read the fetch body stream and parse events ourselves.
async function sendStream(body, question) {
  const res = await fetch(`/api/assistants/${active.id}/chat/stream`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ messages: history }),
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "", text = "", thinking = "", thinkingEl = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let sep;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const raw = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      let event = "message", data = "";
      for (const line of raw.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7);
        else if (line.startsWith("data: ")) data += line.slice(6);
      }
      const payload = JSON.parse(data);
      if (event === "request") showRequest(payload.request, payload.filled_parts);
      else if (event === "reasoning") {
        thinkingEl ??= addReasoning(body);
        thinking += payload.content;
        thinkingEl.textContent = thinking;
        scrollDown();
      } else if (event === "delta") {
        text += payload.content;
        body.innerHTML = renderMarkdown(text);
        scrollDown();
      } else if (event === "done") addUsage(payload.usage, question);
      else if (event === "error") throw new Error(payload.detail);
    }
  }
  if (thinkingEl) thinkingEl.closest("details").querySelector("summary").textContent = "thought for a bit";
  return text;
}

els.composer.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = els.input.value.trim();
  if (busy || !text || !active?.document) return;

  history.push({ role: "user", content: text }); // bare — the server adds the document
  addBubble("user", text);
  els.input.value = "";

  const body = addBubble("assistant", "");
  body.classList.add("typing");
  setBusy(true);
  try {
    const reply = els.mode.value === "stream" ? await sendStream(body, text) : await sendBaseline(body, text);
    history.push({ role: "assistant", content: reply });
  } catch (err) {
    history.pop(); // drop the user turn that failed so the conversation stays consistent
    body.closest(".msg").classList.add("error");
    body.textContent = `Error: ${err.message}`;
  } finally {
    body.classList.remove("typing");
    setBusy(false);
    els.input.focus();
  }
});

els.input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); els.composer.requestSubmit(); }
});

// ---------- boot ----------

(async () => {
  config = await api("/api/config");
  els.model.textContent = config.model;
  await loadAssistants();
  if (!assistants.length) openForm(null);
})();
