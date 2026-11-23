// EASY-CHATGPT frontend — vanilla JS, no framework.
// The conversation lives here; every turn we POST the whole list to the proxy.

const $ = (sel) => document.querySelector(sel);
const els = {
  messages: $("#messages"), form: $("#composer"), input: $("#input"), send: $("#send"),
  mode: $("#mode"), reset: $("#reset"), model: $("#model"),
  image: $("#image"), attachment: $("#attachment"), preview: $("#preview"), clearImage: $("#clear-image"),
  bars: $("#bars"), usageBody: $("#usage tbody"), request: $("#request"), msgcount: $("#msgcount"),
};

let history = [];      // OpenAI-format messages (without the system prompt — the server adds it)
let turns = [];        // [{prompt, completion, total, mode}]
let pendingImage = null; // data URL of the attached image, if any
let busy = false;

const renderMarkdown = (text) => DOMPurify.sanitize(marked.parse(text || ""));

fetch("/api/config").then((r) => r.json()).then((c) => { els.model.textContent = c.model; });

// ---------- chat window ----------

function addBubble(role, text, imageUrl) {
  els.messages.querySelector(".empty")?.remove();
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  if (imageUrl) {
    const img = document.createElement("img");
    img.src = imageUrl;
    img.className = "thumb";
    div.appendChild(img);
  }
  const body = document.createElement("div");
  body.className = "body";
  if (role === "user") body.textContent = text;
  else body.innerHTML = renderMarkdown(text);
  div.appendChild(body);
  els.messages.appendChild(div);
  scrollDown();
  return body;
}

function scrollDown() { els.messages.scrollTop = els.messages.scrollHeight; }

function setBusy(b) {
  busy = b;
  els.send.disabled = b;
  els.send.textContent = b ? "…" : "Send";
}

// ---------- image attachment (vision) ----------

els.image.addEventListener("change", () => {
  const file = els.image.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    pendingImage = reader.result; // data:image/...;base64,...
    els.preview.src = pendingImage;
    els.attachment.hidden = false;
  };
  reader.readAsDataURL(file);
});

function clearImage() {
  pendingImage = null;
  els.image.value = "";
  els.attachment.hidden = true;
}
els.clearImage.addEventListener("click", clearImage);

// ---------- context view ----------

// Data URLs are huge; shorten them so the JSON stays readable.
function displayPayload(payload) {
  return JSON.stringify(payload, (k, v) =>
    typeof v === "string" && v.startsWith("data:") && v.length > 80
      ? `${v.slice(0, 40)}…[${v.length.toLocaleString()} chars]`
      : v, 2);
}

function showRequest(payload) {
  els.request.textContent = displayPayload(payload);
  els.msgcount.textContent = `(${payload.messages.length} messages)`;
}

function addUsage(usage, mode) {
  if (!usage) return;
  turns.push({ prompt: usage.prompt_tokens, completion: usage.completion_tokens, total: usage.total_tokens, mode });
  renderUsage();
}

function renderUsage() {
  els.usageBody.innerHTML = turns.map((t, i) =>
    `<tr><td>${i + 1}</td><td>${t.prompt}</td><td>${t.completion}</td><td>${t.total}</td><td>${t.mode}</td></tr>`
  ).join("");
  const max = Math.max(1, ...turns.map((t) => t.total));
  els.bars.innerHTML = turns.map((t, i) => `
    <div class="bar" title="turn ${i + 1}: ${t.prompt} prompt + ${t.completion} completion">
      <span class="p" style="height:${(t.prompt / max) * 100}%"></span>
      <span class="c" style="height:${(t.completion / max) * 100}%"></span>
    </div>`).join("");
}

// ---------- sending ----------

async function sendBaseline(body) {
  const res = await fetch("/api/chat", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ messages: history }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || res.statusText);
  showRequest(data.request);
  body.innerHTML = renderMarkdown(data.content);
  addUsage(data.usage, "baseline");
  return data.content;
}

// SSE over POST: EventSource only does GET, so we read the fetch body stream and parse events ourselves.
async function sendStream(body) {
  const res = await fetch("/api/chat/stream", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ messages: history }),
  });
  if (!res.ok) throw new Error((await res.json()).detail || res.statusText);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let text = "";

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
      if (event === "request") showRequest(payload);
      else if (event === "delta") {
        text += payload.content;
        body.innerHTML = renderMarkdown(text);
        scrollDown();
      } else if (event === "done") addUsage(payload.usage, "stream");
      else if (event === "error") throw new Error(payload.detail);
    }
  }
  return text;
}

els.form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = els.input.value.trim();
  if (busy || (!text && !pendingImage)) return;

  // With an image, content becomes a list of parts (OpenAI vision format).
  const content = pendingImage
    ? [{ type: "text", text: text || "Describe this image." }, { type: "image_url", image_url: { url: pendingImage } }]
    : text;
  history.push({ role: "user", content });
  addBubble("user", text || "Describe this image.", pendingImage);
  els.input.value = "";
  clearImage();

  const body = addBubble("assistant", "");
  body.classList.add("typing");
  setBusy(true);
  try {
    const reply = els.mode.value === "stream" ? await sendStream(body) : await sendBaseline(body);
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
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); els.form.requestSubmit(); }
});

els.reset.addEventListener("click", () => {
  history = []; turns = [];
  els.messages.innerHTML = '<p class="empty">New conversation.</p>';
  els.request.textContent = "—"; els.msgcount.textContent = "";
  renderUsage(); clearImage();
});
