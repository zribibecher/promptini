<!--
---
title: Promptini
emoji: ⚡
colorFrom: yellow
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---
-->

<div align="center">

# ⚡ Promptini

**Turn a rough idea — in Tunisian Derja, Arabic, French, or English into a clean, model-ready prompt.**

Promptini understands messy, code-switched developer input (the way people in Tunisia actually type) and rewrites it into a precise, structured, model-optimized prompt you can paste straight into Claude, ChatGPT, Gemini, Cursor, or Copilot.

[**Live app →**](https://becher-zribi-prompt-forge-rag.hf.space) · Built entirely on free / open-source infrastructure.

</div>

---

## What it does

You type (or paste) something rough and mixed-language:

> `3andi API Flask, n7eb endpoint yraja3 les users w ykoun fih pagination w JWT`

Promptini returns a tidy, English, model-specific prompt:

```
# ROLE
Senior backend engineer specialised in Python/Flask REST APIs.
# TASK
Implement a GET /users endpoint that returns paginated user records.
# REQUIREMENTS
1. Pagination — query params `page` (default 1) and `per_page` (default 20, max 100).
2. Auth — protect the route with JWT bearer tokens; 401 on missing/expired.
3. Errors — consistent JSON envelope: { "error": { "code", "message" } }.
...
```

The **output is always English** (best for the target models) — the Derja is only used to *understand* what you want.

## Key features

- **Derja-first understanding** — authentic Tunisian vocabulary + Arabizi mapping (`3→ع, 7→ح, 9→ق`), tuned in the system prompt and a mined lexicon.
- **Model-aware output** — formats the prompt for the chosen tool (Claude Code, Claude, ChatGPT, Gemini, Cursor, or any model), using each model's 2026 best-practices.
- **Internal best-of-N judge** — every request generates 3 candidates; an LLM judge silently picks the best one. No noisy scores shown.
- **Restraint built in** — no invented requirements or bloat; a simple ask stays a simple prompt.
- **Curated few-shot corpus** — Derja→optimized-prompt exemplars, matched by task type and target model (no heavy vector DB at runtime).
- **Minimal, fast UI** — two-panel layout, one-click copy, clean monochrome design. Zero heavy ML at startup.
- **100% free stack** — Groq (primary) + Cerebras/Google (fallback) inference, Hugging Face Spaces hosting.

## How it works

```
rough input ──▶ task classifier ──▶ system-prompt builder ──▶ best-of-N generate (Groq)
   (Derja/…)      (16 task types)     (restraint + Derja +        │
                                       curated few-shot)          ▼
                                                          internal judge picks best ──▶ optimized prompt
```

- `core/tasks.py` — multilingual task classifier (English/French/Arabic/Arabizi).
- `core/templates.py` — per-model output formats + task guidance.
- `core/exemplars.py` — curated few-shot bank (`data/exemplars.json`), matched by task + model.
- `llm.py` — provider chain (Groq → Cerebras → Google), builds the system prompt.
- `scorer.py` — `pick_best()` internal judge for best-of-N selection.
- `app.py` — Gradio UI. `api.py` — FastAPI engine for the VS Code extension.

## Tech stack (all free tier)

| Layer | Choice |
|---|---|
| Inference | **Groq** `openai/gpt-oss-120b` (primary), Cerebras / Google Gemini (fallback) |
| UI | Gradio 6 |
| API | FastAPI |
| Hosting | Hugging Face Spaces (CPU basic) |
| Derja corpus | `hamzabouajila/tunisian-derja-unified-raw-corpus` (CC-BY-SA) |

## Quick start (local)

```bash
git clone <this-repo> && cd promptini
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# add your free Groq key
echo "GROQ_API_KEY=gsk_..." > .env

python app.py          # → http://localhost:7860
```

### Configuration (env vars)

| Var | Purpose |
|---|---|
| `GROQ_API_KEY` | **required** — free key from console.groq.com |
| `GROQ_MODEL` | default `openai/gpt-oss-120b` |
| `CEREBRAS_API_KEY` | optional free fallback provider |
| `GOOGLE_API_KEY` | optional free Gemini fallback (`GOOGLE_MODEL=gemini-2.5-flash`) |

## Deploy (free 24/7)

1. Push to a Hugging Face Space (Gradio SDK). Set `GROQ_API_KEY` as a **Space secret** and `GROQ_MODEL` as a variable.
2. Keep it awake: point **UptimeRobot** (5-min HTTP monitor) at the Space URL, and/or enable the included GitHub Action (`.github/workflows/keepalive.yml`).

## Building / refreshing the corpus

```bash
# expand the curated few-shot corpus (uses Groq) — task × model
python scripts/build_corpus.py --per-combo 4

# mine a Tunisian Derja lexicon from the open corpus
python scripts/build_derja_lexicon.py --max-rows 200000 --top 500
```

## VS Code extension

`vscode-extension/` — "Promptini — Derja Prompt Studio". Sidebar webview (cloud mode → the Space) plus a "Forge Selection" command that sends editor text to the API. See `vscode-extension/SETUP.md`.

## Project structure

```
app.py            Gradio UI              scripts/          corpus + lexicon builders
api.py            FastAPI engine         data/             exemplars.json, derja_lexicon.json
llm.py            provider chain         docs/             benchmarks, deployment, roadmap
scorer.py         best-of-N judge        tests/            pytest suite
core/             classifier, templates, exemplars, config, rate-limit, cache
vscode-extension/ VS Code extension
```




