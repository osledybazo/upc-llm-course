# Exercise 5 — EASY-CHATGPT

A small chatbot server. A **FastAPI proxy** sits between a vanilla JS chat window and
any OpenAI-compatible LLM. The browser never calls the model directly.

```
browser (HTML/CSS/JS)  ──POST /api/chat(/stream)──▶  FastAPI  ──OpenAI API──▶  LLM
        ◀────────── JSON or SSE token stream ─────────  proxy  ◀───────────────
```

## Run it

```bash
cp .env.example .env      # then edit: base URL, key, model
docker compose up --build
```

Open **http://localhost:6661**.

The default `.env` points at **Ollama on your host machine**
(`http://host.docker.internal:11434/v1`). Inside the container, `localhost` is the
container itself, so the host has to be reached as `host.docker.internal`. Make sure
Ollama is running and the model is pulled (`ollama pull ministral-3:14b`). To use a cloud
model instead, change the three `LLM_*` lines in `.env`. You don't need to touch any code.

### Without Docker

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
LLM_BASE_URL=http://localhost:11434/v1 .venv/bin/uvicorn app.main:app --port 6661
```

## Configuration (`.env`)

| var | meaning |
|---|---|
| `LLM_BASE_URL` | OpenAI-compatible endpoint (Ollama, OpenAI, OpenRouter, Groq…) |
| `LLM_API_KEY` | API key (any string for Ollama) |
| `LLM_MODEL` | model name |
| `SYSTEM_PROMPT` | optional system message the proxy adds to every request |
| `LLM_TEMPERATURE` | optional, default 0.7 |

`.env` is git-ignored. Only `.env.example` is committed.

## The three versions

All three ship together. Pick **Mode** in the header.

1. **Baseline (no streaming).** `POST /api/chat` waits for the whole completion and
   returns it as JSON (`content`, `usage`, and the exact `request` sent to the model).
2. **Advanced (streaming).** `POST /api/chat/stream` opens a streaming completion
   and relays it to the browser as server-sent events:
   `request` (the payload sent) → many `delta` (token text) → `done` (with `usage`).
   It asks for `stream_options.include_usage` so token counts arrive even when streaming.
   The browser reads the stream with `fetch` + `ReadableStream`, because `EventSource`
   only supports GET.
3. **Best (vision).** 📎 attaches an image. The user message becomes a list of parts
   (`text` + `image_url` as a base64 data URL), which is the OpenAI vision format. This needs a
   vision-capable model (e.g. `ministral-3`, `gemma4`, `gpt-4.1-mini`).

## Context view

The right-hand panel shows:

- **Tokens per turn.** A bar chart and table of `prompt` / `completion` / `total`
  tokens. The prompt bar grows every turn because the whole history is re-sent each time.
- **Last request.** The exact JSON the proxy sent to the model: system prompt, every
  previous turn, and the model and temperature. Image data URLs are shortened for display.

The backend is **stateless**: the browser holds the conversation and sends all of it
each turn. That's how chat-completion APIs work, and it's what the context view shows.

## Files

```
app/main.py           FastAPI proxy: /api/config, /api/chat, /api/chat/stream, static files
static/index.html     chat window + context view
static/app.js         chat logic, SSE parsing, image attach, context view
static/style.css      layout (light/dark)
static/vendor/        marked (Markdown → HTML) + DOMPurify (sanitise it), vendored so it works offline
Dockerfile            python:3.12-slim + uvicorn on 0.0.0.0:6661
docker-compose.yml    builds, loads .env, maps 6661:6661, adds host.docker.internal
```
