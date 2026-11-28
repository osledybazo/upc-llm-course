# Week 2 · Exercise 1 — EASY-ASSISTANT

EASY-CHATGPT (Week 1) extended with **assistants that answer from a document**. This is
single-file RAG in its simplest form: the backend pastes the **whole file** into the prompt
on every turn.

An assistant has:

- a **name**,
- a **system prompt** (role, tone, rules),
- a **prompt template** with two gaps, `{context}` and `{user_input}`,
- one **plain-text document** (its context).

```text
browser ──(bare history + new question)──▶ FastAPI ──▶ LLM
                                             │
             fills template: {context} = whole file, {user_input} = question
             sends: [system] + bare history + [filled template]
```

## Run it

```bash
ollama serve
ollama pull qwen3:1.7b
cp .env.example .env
docker compose up --build
```

Open **<http://localhost:6662>**. Click **+ New**, keep the default template, and upload
[`samples/nimbus-bakery.txt`](samples/nimbus-bakery.txt) (a made-up bakery, so the model
can't know these facts from training). Then ask:

- *"How much is a cloud loaf?"* → 4.80 euros (it's in the file)
- *"Who is the president of France?"* → "I do not know" (it's not in the file)

To use a frontier model instead, change the three `LLM_*` lines in `.env`. You don't need
to change any code.

Without Docker:

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
LLM_BASE_URL=http://localhost:11434/v1 .venv/bin/uvicorn app.main:app --port 6662
```

## What the page shows

- **Left:** the assistants. You can create, edit (name, system prompt, template, replace the document) or delete them.
- **Centre:** the chat. If the model sends its reasoning separately (qwen3 through Ollama does), it appears in a collapsed "thought for a bit" box.
- **Right, the context view:**
  - **Tokens per turn:** `prompt_tokens` stays large even when the question is tiny, because the whole document is in every call.
  - **Filled-in prompt:** the exact text sent as the last user message. The document is highlighted in yellow and the question in green. The view also shows what share of the prompt is the document (about 90% with the sample).
  - **Full request JSON:** system prompt, the bare earlier turns, and the filled template. The document is shortened here because it is already shown in full above.

## Design notes

- **Storage:** `data/assistants.json`, mounted as a Docker volume so it survives rebuilds. Writes are atomic (write to a temp file, then rename) and protected by a lock. There is no database.
- **The backend is stateless:** the browser keeps the *bare* conversation. Only the newest user message is filled with the template. Earlier turns are sent as they were typed, so the document is not copied into the history again on each turn. This is the same approach as the course's `single-file-rag` demo (`user-augment` mode in `context-explorer-rag`).
- **Template filling:** one regex pass over the *template* only. It does not use `str.format`, because the document may contain `{` `}`. It does not use two chained `.replace()` calls either: then a user typing `{context}` would get the whole file pasted in again.
- **Validation:**
  - The template must contain both gaps.
  - The upload must be UTF-8 text with no NUL bytes, not empty, and at most 1 MB (`MAX_DOC_BYTES`).
  - You can't chat until the assistant has a document.
- **Temperature:** 0.2 by default, because a document assistant should stick to the facts.

## API

| method | path | |
|---|---|---|
| GET | `/api/config` | model, defaults for new assistants |
| GET / POST | `/api/assistants` | list / create (`name`, `system_prompt`, `prompt_template`) |
| GET / PUT / DELETE | `/api/assistants/{id}` | read / update / delete |
| POST | `/api/assistants/{id}/document` | multipart upload of one text file (replaces the old one) |
| GET | `/api/assistants/{id}/document` | the stored document |
| POST | `/api/assistants/{id}/chat` | non-streaming. Returns `content`, `usage`, `filled_parts`, `request` |
| POST | `/api/assistants/{id}/chat/stream` | SSE events: `request`, then any number of `reasoning` and `delta`, then `done` (with `usage`) |

## Files

```text
app/main.py              FastAPI: assistants CRUD, upload, template filling, chat (JSON + SSE)
static/index.html        assistants sidebar, chat, context view
static/app.js            UI logic, SSE parsing, filled-prompt highlighting, token chart
static/style.css         layout (light/dark)
samples/nimbus-bakery.txt  test document (fictional)
data/                    assistants.json (git-ignored, created at runtime)
```
