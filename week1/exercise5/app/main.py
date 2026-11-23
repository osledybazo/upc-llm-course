"""
EASY-CHATGPT — a FastAPI proxy between a browser chat window and an LLM.

The browser never talks to the model. It POSTs the conversation here; we add
the system prompt, call the model over the OpenAI-compatible API, and pass the
answer back — either whole (/api/chat) or as a live SSE stream (/api/chat/stream).

The backend is stateless: the client sends the full message list every turn,
which is exactly what the model sees. That makes the context view honest.
"""
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel

load_dotenv()

BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
API_KEY = os.environ.get("LLM_API_KEY", "ollama")
MODEL = os.environ.get("LLM_MODEL", "ministral-3:14b")
SYSTEM_PROMPT = os.environ.get("SYSTEM_PROMPT", "You are a helpful assistant. Answer in Markdown.")
TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.7"))

client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)
app = FastAPI(title="EASY-CHATGPT")
STATIC = Path(__file__).resolve().parent.parent / "static"


class ChatRequest(BaseModel):
    # OpenAI chat format. `content` is a string, or a list of parts
    # ([{"type":"text",...},{"type":"image_url",...}]) when an image is attached.
    messages: list[dict[str, Any]]


def build_payload(req: ChatRequest, stream: bool) -> dict[str, Any]:
    messages = list(req.messages)
    if SYSTEM_PROMPT:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    payload: dict[str, Any] = {"model": MODEL, "messages": messages, "temperature": TEMPERATURE}
    if stream:
        payload["stream"] = True
        payload["stream_options"] = {"include_usage": True}  # final chunk carries token usage
    return payload


@app.get("/api/config")
async def config():
    # Never expose the key — only what the UI needs to label itself.
    return {"model": MODEL, "base_url": BASE_URL}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Baseline: wait for the whole answer, return it in one JSON blob."""
    payload = build_payload(req, stream=False)
    try:
        resp = await client.chat.completions.create(**payload)
    except OpenAIError as e:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}") from e
    return {
        "content": resp.choices[0].message.content or "",
        "finish_reason": resp.choices[0].finish_reason,
        "usage": resp.usage.model_dump() if resp.usage else None,
        "request": payload,  # what was actually sent to the model
    }


def sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    """Advanced: relay the model's token stream to the browser as server-sent events."""
    payload = build_payload(req, stream=True)

    async def relay():
        yield sse("request", payload)
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
                if choice.delta and choice.delta.content:
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
