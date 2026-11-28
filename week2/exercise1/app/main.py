"""
EASY-ASSISTANT — EASY-CHATGPT plus assistants that answer from a document.

An assistant = name + system prompt + prompt template (with {context} and
{user_input} gaps) + one plain-text document. On every chat turn the backend
fills the template with the WHOLE document and the user's message, and sends
that to the model. This is single-file RAG: no chunking, no retrieval, just
"put the answer in front of the model".

Like Week 1, the chat endpoint is stateless: the browser keeps the BARE
conversation (what the user typed, what the model answered) and sends it every
turn. Only the newest user message is augmented; earlier turns stay bare, so
the document is re-injected fresh each turn instead of piling up in history.

Assistants are stored in a JSON file (data/assistants.json). No database.
"""
import json
import os
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel, Field, field_validator

load_dotenv()

BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
API_KEY = os.environ.get("LLM_API_KEY", "ollama")
MODEL = os.environ.get("LLM_MODEL", "qwen3:1.7b")
TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.2"))
MAX_DOC_BYTES = int(os.environ.get("MAX_DOC_BYTES", str(1_000_000)))  # 1 MB of text is already ~250k tokens

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data"))
STORE = DATA_DIR / "assistants.json"

DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant. Answer briefly and in Markdown."
DEFAULT_TEMPLATE = """Use only the information in the context below to answer the question.
If the answer is not in the context, say that you do not know.

Context:
----
{context}
----

Question: {user_input}"""

client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)
app = FastAPI(title="EASY-ASSISTANT")


# ---------- storage: one JSON file ----------

_lock = threading.Lock()


def load_all() -> dict[str, dict]:
    if not STORE.exists():
        return {}
    return json.loads(STORE.read_text(encoding="utf-8"))


def save_all(assistants: dict[str, dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STORE.with_suffix(".tmp")
    tmp.write_text(json.dumps(assistants, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(STORE)  # atomic: a crash never leaves a half-written file


def get_or_404(assistant_id: str) -> dict:
    a = load_all().get(assistant_id)
    if a is None:
        raise HTTPException(404, "Assistant not found")
    return a


def summary(a: dict) -> dict:
    """Assistant without the (possibly huge) document text."""
    doc = a.get("document")
    return {
        **{k: v for k, v in a.items() if k != "document"},
        "document": None if doc is None else {k: v for k, v in doc.items() if k != "text"},
    }


# ---------- assistants API ----------

class AssistantIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    system_prompt: str = ""
    prompt_template: str = DEFAULT_TEMPLATE

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be empty")
        return v

    @field_validator("prompt_template")
    @classmethod
    def has_both_gaps(cls, v: str) -> str:
        missing = [g for g in ("{context}", "{user_input}") if g not in v]
        if missing:
            raise ValueError(f"prompt template must contain {' and '.join(missing)}")
        return v


@app.get("/api/config")
async def config():
    # Never expose the key — only what the UI needs.
    return {
        "model": MODEL,
        "base_url": BASE_URL,
        "default_system_prompt": DEFAULT_SYSTEM_PROMPT,
        "default_template": DEFAULT_TEMPLATE,
    }


@app.get("/api/assistants")
async def list_assistants():
    items = sorted(load_all().values(), key=lambda a: a["created_at"])
    return [summary(a) for a in items]


@app.post("/api/assistants", status_code=201)
async def create_assistant(body: AssistantIn):
    a = {
        "id": uuid.uuid4().hex[:12],
        **body.model_dump(),
        "document": None,
        "created_at": time.time(),
    }
    with _lock:
        all_ = load_all()
        all_[a["id"]] = a
        save_all(all_)
    return summary(a)


@app.get("/api/assistants/{assistant_id}")
async def get_assistant(assistant_id: str):
    return summary(get_or_404(assistant_id))


@app.put("/api/assistants/{assistant_id}")
async def update_assistant(assistant_id: str, body: AssistantIn):
    with _lock:
        all_ = load_all()
        if assistant_id not in all_:
            raise HTTPException(404, "Assistant not found")
        all_[assistant_id].update(body.model_dump())
        save_all(all_)
        return summary(all_[assistant_id])


@app.delete("/api/assistants/{assistant_id}", status_code=204)
async def delete_assistant(assistant_id: str):
    with _lock:
        all_ = load_all()
        if all_.pop(assistant_id, None) is None:
            raise HTTPException(404, "Assistant not found")
        save_all(all_)


@app.post("/api/assistants/{assistant_id}/document")
async def upload_document(assistant_id: str, file: UploadFile = File(...)):
    """Attach ONE plain-text file as the assistant's context. Replaces any previous one."""
    raw = await file.read(MAX_DOC_BYTES + 1)
    if len(raw) > MAX_DOC_BYTES:
        raise HTTPException(413, f"File too large (max {MAX_DOC_BYTES:,} bytes)")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(415, "Only plain-text UTF-8 files are supported (.txt, .md, …)")
    if "\x00" in text:
        raise HTTPException(415, "That looks like a binary file, not plain text")
    if not text.strip():
        raise HTTPException(400, "The file is empty")
    with _lock:
        all_ = load_all()
        if assistant_id not in all_:
            raise HTTPException(404, "Assistant not found")
        all_[assistant_id]["document"] = {
            "filename": file.filename or "document.txt",
            "chars": len(text),
            "words": len(text.split()),
            "uploaded_at": time.time(),
            "text": text,
        }
        save_all(all_)
        return summary(all_[assistant_id])


@app.get("/api/assistants/{assistant_id}/document")
async def get_document(assistant_id: str):
    doc = get_or_404(assistant_id).get("document")
    if doc is None:
        raise HTTPException(404, "This assistant has no document yet")
    return doc


# ---------- chat ----------

class ChatRequest(BaseModel):
    # BARE conversation as the user sees it; the last item is the new user message.
    messages: list[dict[str, Any]]


GAP = re.compile(r"\{(context|user_input)\}")


def fill_template(template: str, context: str, user_input: str) -> list[dict[str, str]]:
    """Fill the two gaps. Returns the prompt as labelled parts so the UI can
    highlight which text came from the file and which from the user;
    "".join(p["text"] for p in parts) is the exact string sent to the model.

    One pass over the TEMPLATE only. Not str.format (the document may contain
    { } — code, JSON…), and not two chained .replace() calls (then a user typing
    "{context}", or a document containing "{user_input}", would get expanded too).
    """
    values = {"context": context, "user_input": user_input}
    parts, pos = [], 0
    for m in GAP.finditer(template):
        if m.start() > pos:
            parts.append({"kind": "template", "text": template[pos:m.start()]})
        parts.append({"kind": m.group(1), "text": values[m.group(1)]})
        pos = m.end()
    if pos < len(template):
        parts.append({"kind": "template", "text": template[pos:]})
    return parts


def build_payload(a: dict, req: ChatRequest, stream: bool) -> tuple[dict[str, Any], list[dict[str, str]]]:
    msgs = req.messages
    if not msgs or msgs[-1].get("role") != "user" or not isinstance(msgs[-1].get("content"), str):
        raise HTTPException(400, "The last message must be a user message with text content")
    if a.get("document") is None:
        raise HTTPException(400, "Upload a document to this assistant before chatting")

    parts = fill_template(a["prompt_template"], a["document"]["text"], msgs[-1]["content"])
    filled = "".join(p["text"] for p in parts)
    messages: list[dict[str, Any]] = []
    if a.get("system_prompt"):
        messages.append({"role": "system", "content": a["system_prompt"]})
    messages += [{"role": m["role"], "content": m["content"]} for m in msgs[:-1]]  # history stays bare
    messages.append({"role": "user", "content": filled})

    payload: dict[str, Any] = {"model": MODEL, "messages": messages, "temperature": TEMPERATURE}
    if stream:
        payload["stream"] = True
        payload["stream_options"] = {"include_usage": True}  # final chunk carries token usage
    return payload, parts


@app.post("/api/assistants/{assistant_id}/chat")
async def chat(assistant_id: str, req: ChatRequest):
    """Baseline: wait for the whole answer, return it in one JSON blob."""
    payload, parts = build_payload(get_or_404(assistant_id), req, stream=False)
    try:
        resp = await client.chat.completions.create(**payload)
    except OpenAIError as e:
        raise HTTPException(502, f"LLM call failed: {e}") from e
    msg = resp.choices[0].message
    return {
        "content": msg.content or "",
        "reasoning": (msg.model_extra or {}).get("reasoning"),  # e.g. qwen3 thinking, via Ollama
        "finish_reason": resp.choices[0].finish_reason,
        "usage": resp.usage.model_dump() if resp.usage else None,
        "filled_parts": parts,
        "request": payload,  # what was actually sent to the model
    }


def sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.post("/api/assistants/{assistant_id}/chat/stream")
async def chat_stream(assistant_id: str, req: ChatRequest):
    """Relay the model's token stream to the browser as server-sent events."""
    payload, parts = build_payload(get_or_404(assistant_id), req, stream=True)

    async def relay():
        yield sse("request", {"request": payload, "filled_parts": parts})
        usage = None
        finish_reason = None
        try:
            stream = await client.chat.completions.create(**payload)
            async for chunk in stream:
                if chunk.usage:
                    usage = chunk.usage.model_dump()
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                if choice.delta:
                    reasoning = (choice.delta.model_extra or {}).get("reasoning")
                    if reasoning:
                        yield sse("reasoning", {"content": reasoning})
                    if choice.delta.content:
                        yield sse("delta", {"content": choice.delta.content})
                if choice.finish_reason:
                    finish_reason = choice.finish_reason
        except OpenAIError as e:
            yield sse("error", {"detail": f"LLM call failed: {e}"})
            return
        yield sse("done", {"usage": usage, "finish_reason": finish_reason})

    return StreamingResponse(
        relay(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
