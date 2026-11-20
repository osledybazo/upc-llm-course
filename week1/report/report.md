# Week 1 · Exercises 1–4 — Report

**Student:** Osledy Bazó<br>
**Repository:** [REPO LINK, exactly as on Artemis]

**Machine used for all exercises:** Apple MacBook Pro, M1 Pro chip, 32 GB unified memory, macOS 14 (Sonoma). CPU-only for Exercises 1–2 (Hugging Face `transformers`); Ollama 0.40.16 for Exercises 3–4.

Code and raw outputs are in the repo under `week1/exercise1/` … `week1/exercise4/`.

---

## Exercise 1 — Tokenize, locally

Ran `week1/exercise1/ex_01_tokenise.py` unchanged (full output in `week1/exercise1/output.txt`). Tokenizer A = `gpt2` (byte-level BPE), tokenizer B = `bert-base-uncased` (WordPiece).

**Token count for the demo sentence.** *"The model never sees the letters in strawberry."* → **9 tokens** with GPT-2:
`The | ␣model | ␣never | ␣sees | ␣the | ␣letters | ␣in | ␣strawberry | .`
"strawberry" is a single token, so the model never sees its letters, which is why letter-counting questions are hard for LLMs.

**Multilingual penalty (Spanish vs. English).** My language is Spanish, so the script's default Spanish paragraph applies.

| | words | GPT-2 tokens |
|---|---|---|
| English | 35 | 38 |
| Spanish | 40 | 63 |
| **Penalty** = (63 − 38) / 38 | | **+65.8 %** |

The Spanish paragraph has only ~14 % more words but ~66 % more tokens. GPT-2's vocabulary was learned on mostly English web text, so ordinary Spanish words are cut into fragments: *lenguaje* → `l·engu·aj·e`, *palabras* → `pal·ab·ras`, *número* → `n·Ãº·mer·o` (the accented ú alone costs a byte-level token). In practice the same content costs a Spanish speaker ~1.66× the price and context space.

**Two tokenizers vs. four code-ish inputs.**

| input | gpt2 | bert-base-uncased |
|---|---|---|
| python function | 26 | 22 |
| JSON blob | 36 | 45 |
| regex-heavy line | 41 | 44 |
| whitespace-heavy | 20 | 5 |

- **Python function (26 vs 22):** they disagree mostly on the indentation and newlines: GPT-2 spends a token on every leading space and `\n`, while BERT throws whitespace away entirely (and splits `"""` into three `"`). BERT was built to *understand* text, not to reproduce it byte-for-byte.
- **JSON blob (36 vs 45):** here GPT-2 wins, because its BPE learned merged punctuation chunks from the web like `{"`, `":`, `",`, `"}`, whereas BERT gives every quote, colon and brace its own token. GPT-2 still fragments some keys, though: `max_tokens` → `max·_·t·ok·ens`.
- **Regex-heavy line (41 vs 44):** this is the closest pair because both tokenizers shred regex into almost single characters (it is rare in their training text). The interesting disagreement is that uncased BERT lowercases `A-Za-z` into `a·-·za·-·z`, silently changing the meaning of the regex.
- **Whitespace-heavy (20 vs 5):** the biggest disagreement. GPT-2 pays one token for each of the 10 spaces and each tab, while BERT keeps only `x = 1 return x`. For Python, where indentation is syntax, BERT literally cannot represent the program; GPT-2 can but wastes tokens. (Later code models added tokens for runs of spaces for exactly this reason.)

---

## Exercise 2 — Base vs. aligned

The provided `simple_gpt2.py` / `simple_qwen3.py` are interactive CLIs that read one line, so the multi-line few-shot prompt can't be typed into them. I added `week1/exercise2/run_prompts.py`, which sends the **four exact README prompts** to both models with **the same generation settings** as the provided scripts (GPT-2: 50 new tokens, T = 0.8; Qwen3-1.7B: chat template, thinking off, 200 new tokens, T = 0.7, top-p 0.9). Each prompt was run twice because sampling is random. Raw output: `week1/exercise2/outputs.md`. (GPT-2 output includes the prompt it was continuing; for Qwen only the new reply is shown.)

{{EX2_OUTPUTS}}

### Observations (one per prompt)

1. **Instruction following:** GPT-2 ignored the instruction and wrote unrelated web-style prose (feminism, "the English speaking people"), while Qwen answered "Paris." both times, which is exactly one word as asked.
2. **Few-shot:** both picked up the pattern. GPT-2 continues the list format (answering "routine" once and "urgent" once, then inventing more emails), while Qwen gives one consistent answer ("urgent") and stops. In-context learning already exists in a base model; alignment makes it reliable and makes the model stop.
3. **Format following:** GPT-2 treated the line as the start of a blog post about APIs and curl, while Qwen returned the JSON (once bare, once inside a ```` ```json ```` fence, so "the format" is still not 100 % stable).
4. **Refusal / safety:** neither refused. GPT-2 rambled about screwdrivers and buttons. More surprisingly, Qwen **misread "pick" as "choose"** in both runs and wrote a buying guide for locks. The small aligned model didn't refuse, and it didn't really answer either: the tone was perfectly helpful while it answered a different question.

### What does the alignment stack actually do?

Both models are the same kind of machine: a decoder-only transformer predicting the next token. **Pretraining** gives a model knowledge and fluency, but its only goal is "continue the document plausibly", which is why GPT-2 treats a question as the first line of a web page. **SFT** (supervised fine-tuning on instruction→answer pairs plus a chat template) teaches the model a new kind of document, a conversation in which the next thing is the *assistant's answer*. That is where Qwen's "answer, follow the format, then stop" behaviour comes from. **RLHF / preference optimisation** then shapes *which* answer it prefers: concise, helpful, well-formatted, and with safety boundaries. Alignment does not add much knowledge (Qwen still misread "pick a lock"). Mostly it changes the model's *behaviour*: it turns a text-continuer into an assistant. The safety part is clearly the shallowest layer in a 1.7B model.

---

## Exercise 3 — Run a model on your own machine

`ollama run ministral-3:14b` (9.1 GB at 4-bit; fits easily in 32 GB unified memory). Generation speed ≈ 11–13 tokens/s on the M1 Pro. I sent the prompts below, each in a **fresh conversation**, and then some follow-ups. Full transcripts: `week1/exercise3/transcript_ministral-3_14b.md` and `week1/exercise3/followups.md` (prompts sent via Ollama's local API by `probes.py`, so they're reproducible).

**What the model could do**

- **Zero-shot tasks:** "Summarise Romeo and Juliet in exactly two sentences" was answered correctly in two (long) sentences.
- **Few-shot rule induction:** I gave `blorp(cat)=tac9, blorp(house)=esuoh5, blorp(sun)=nus3`. My first example was inconsistent by accident (it should have been `tac3`). The model noticed this, tested other hypotheses (ASCII sums, vowel counts), concluded the rule was "reverse + length", and answered `blorp(table) = elbat5`. That is correct, and it handled my mistake well.
- **Languages:** it gave a fluent, correct explanation of *ser* vs. *estar* in Spanish and a good one-sentence definition of a transformer in **Catalan**.
- **Code:** it produced a correct `is_palindrome` (regex strip + lowercase + reverse) in 4 s.
- **Resisting a false premise:** "Why did Einstein win the 1931 Nobel Prize in Chemistry?" was corrected: he won the 1921 Physics prize. It even named Bosch and Bergius for 1931 Chemistry.
- **Not inventing a citation:** asked for the DOI of a non-existent 2019 Marc Alier paper, it said it didn't have it rather than making one up.

**What surprised me**

- How good a 9 GB, fully offline model is, running on a laptop with no internet.
- The `strawberry` question (count the r's) got **3**, which is correct, although Exercise 1 showed that "strawberry" is one token. Newer models have probably seen this famous question in training.
- **Memory:** in one conversation it remembered my cat's name ("Pimiento"). In a new conversation it had no idea. The model itself has no memory; only the message history that is re-sent gives it context.
- **Repeating the same prompt gives the same answer.** The arithmetic question gave the identical (wrong) answer in 3 fresh chats, so starting a new conversation does not "reroll" a mistake.

**Where it failed or was confidently wrong**

- **Arithmetic:** *"What is 4831 × 297? Answer with just the number."* → **1,433,507**, answered instantly with full confidence. The correct value is **1,434,807**. When I asked it to *work it out step by step*, it got **1,434,807** right (using 4831 × (300 − 3)). Still, the "verification" table it added had wrong intermediate labels (e.g. "14493 = 4831 × 200"). Giving the model tokens to "think" fixed the answer, but the explanation can't be trusted blindly.
- **Strict format:** "Answer ONLY with a JSON array, no prose, no markdown" was still wrapped in a ```` ```json ```` markdown fence, so it would break a naive `json.loads`.
- **Out-of-date knowledge:** "Who won the most recent FIFA World Cup?" → "Argentina in 2022", stated as fact. The 2026 World Cup has already been played; the model doesn't know about anything after its training cutoff, and it doesn't say so.
- "Exactly two sentences" was technically met, but with very long sentences full of em-dashes and parentheses. It follows the letter of the instruction more than the spirit.

---

## Exercise 4 — Call the LLM from code

**Model and machine:** `ministral-3:14b` served by local Ollama (`http://localhost:11434/v1`), on the M1 Pro / 32 GB MacBook Pro. `.env`: `OPENAI_ENDPOINT=http://localhost:11434/v1`, `OPENAI_API_KEY=ollama`, `MODEL=ministral-3:14b`.

**`python call.py`**
```
Hello—how can I help?
---
usage        : CompletionUsage(completion_tokens=8, prompt_tokens=18, total_tokens=26, completion_tokens_details=None, prompt_tokens_details=PromptTokensDetails(audio_tokens=None, cache_write_tokens=None, cached_tokens=0, image_tokens=None, text_tokens=None))
finish_reason: stop
```

**`bash call.sh`** (curl progress meter omitted)
```
{"id":"chatcmpl-504","object":"chat.completion","created":1795207985,"model":"ministral-3:14b",
 "system_fingerprint":"fp_ollama","choices":[{"index":0,"message":{"role":"assistant",
 "content":"Hello! How can I assist you today?"},"finish_reason":"stop"}],
 "usage":{"prompt_tokens":18,"prompt_tokens_details":{"cached_tokens":17},"completion_tokens":10,"total_tokens":28}}
```
The SDK and curl get exactly the same JSON structure: the SDK just parses it into objects. On the second call, 17 of the 18 prompt tokens were `cached_tokens`, because the system and user prompt were identical to the previous request.

**Changing the temperature** (`week1/exercise4/temperature_test.py`, same call, 3 runs each):

| | T = 0.0 | T = 1.5 |
|---|---|---|
| "Say hello in one sentence." | `Hello—how can I assist you today?` ×3 (identical) | `"Hello—how can I help?"` / `Hello—how can I help you right now?` / `Hello—how's your day so far?` |
| "Write a one-sentence slogan for a coffee shop." | `"Wake up to flavor—one sip at a time."` ×3 (identical) | `"Wake up to greatness—one sip at a time."` / `"Wake Up. Breathe In. Sip Bold."` / `"Fuel your day with perfect brews—bold flavor, every time."` |

At **0.0** the model always picks the most probable token, so the output is deterministic: identical every run. At **1.5** the probability distribution is flattened and less likely tokens get sampled, so every run is different and more "creative". It is still coherent here because the prompts are short. For a hello the difference is small; for a creative task like a slogan it is large. T = 0 suits extraction and tests; higher T suits brainstorming.

**Changing the model:** with `MODEL=qwen3.5:9b` (no code change), `call.py` returned `Hello.` but reported **348 completion tokens** for a one-word answer. Qwen 3.5 is a "thinking" model and generates hidden reasoning tokens first. They are invisible in the reply but appear in `usage`, i.e. on the bill.

**Why the same code reached a different model:** `call.py` only speaks the standard `/v1/chat/completions` JSON-over-HTTP format, and *which* server and model answer is decided entirely by `OPENAI_ENDPOINT` and `MODEL` in `.env`. Changing the configuration changes the brain, not the code.

*(I did not test the OpenAI cloud / `responses_openai.py` part because I don't have an OpenAI API key; that file is also not present in the course repo.)*
