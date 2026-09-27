# ⚡ Promptini

[![Marketplace Version](https://img.shields.io/visual-studio-marketplace/v/BecherZribi.promptini?color=amber&label=Marketplace)](https://marketplace.visualstudio.com/items?itemName=BecherZribi.promptini)
[![Installs](https://img.shields.io/visual-studio-marketplace/i/BecherZribi.promptini?color=emerald)](https://marketplace.visualstudio.com/items?itemName=BecherZribi.promptini)
[![Rating](https://img.shields.io/visual-studio-marketplace/r/BecherZribi.promptini)](https://marketplace.visualstudio.com/items?itemName=BecherZribi.promptini)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/Bechir02/promptini/blob/main/LICENSE)

**Turn a rough idea in Tunisian Derja, Arabic, French, or English into a clean, model-ready prompt, without leaving VS Code.**

Promptini reads messy, code-switched developer input and rewrites it into a precise, structured prompt you can paste straight into Claude, ChatGPT, Gemini, or Cursor. Whatever language you type in, the optimized prompt always comes out in clear English.

## Features

- **Derja-first understanding** — handles authentic Tunisian Derja and Arabizi transliteration (`3 → ع`, `7 → ح`, `9 → ق`), mixed freely with Arabic, French, and English.
- **Model-aware formatting** — structures the prompt for your target tool: Claude, ChatGPT, Gemini, Cursor, or a generic "Any".
- **Always-English output** — type in any language; the result is a clean English prompt.
- **Sidebar panel** — a dedicated Activity Bar view: type an idea, pick a model, get the optimized prompt in one click, and copy it.
- **Optimize Selection** — highlight rough text anywhere in the editor and turn it into a structured prompt from the right-click menu.

## Getting started

1. Click the **⚡ Promptini** icon in the Activity Bar to open the panel.
2. Type or paste a rough idea and choose your target **Model**.
3. Press **⚡ Promptini**, then **Copy prompt**.

By default the extension uses the hosted Promptini engine, so there is nothing to install and no API key to configure. To run the engine yourself, see [Cloud vs. local](#cloud-vs-local).

### Optimize a selection

Select text in any editor, right-click, and choose:

- **Promptini: Optimize Selection** — sends the selection to the sidebar panel.
- **Promptini: Optimize Selection via API** — optimizes it through your local engine and replaces the selection in place.

## Commands

| Command | Description |
| --- | --- |
| `Promptini: Open App` | Open the full-page Promptini panel in the editor. |
| `Promptini: Optimize Selection` | Send the highlighted text to the sidebar. |
| `Promptini: Optimize Selection via API` | Optimize the selection through the local API and replace it in place. |
| `Promptini: Stop App` | Stop the local engine and close the panel. |

Open the Command Palette (`Ctrl/Cmd + Shift + P`) and type "Promptini" to find them.

## Extension settings

| Setting | Default | Description |
| --- | --- | --- |
| `promptini.mode` | `cloud` | `cloud` uses the hosted engine; `local` runs your own Python server. |
| `promptini.hfUrl` | hosted Space URL | URL of the hosted Promptini engine (used in cloud mode). |
| `promptini.apiUrl` | `http://127.0.0.1:8000` | Base URL of your local engine, used by **Optimize Selection via API**. |
| `promptini.apiModel` | `general` | Target model used by **Optimize Selection via API**. |
| `promptini.pythonPath` | `""` | Optional path to a Python interpreter for local mode. A workspace `.venv` is auto-detected otherwise. |

## Cloud vs. local

- **Cloud (default).** The extension calls the hosted Promptini engine. Nothing to install; it works out of the box.
- **Local.** Set `promptini.mode` to `local` to run the engine on your own machine. The extension starts the FastAPI app (`uvicorn api:app`) from your workspace, so you need the Promptini repository open as the workspace folder with its Python dependencies installed.

## Requirements

- VS Code `1.88.0` or newer.
- For **local mode** only: Python `3.11+`, with the Promptini repository open as your workspace and its dependencies installed (`pip install -r requirements.txt`).

## How it works

Promptini sends your input to a prompt-engineering engine that detects the task type, understands Derja and Arabizi natively, and rewrites the request into a model-specific structure — for example `# ROLE`, `# TASK`, `# REQUIREMENTS`, `# OUTPUT FORMAT`, and `# CONSTRAINTS` for Claude. It runs on a fully free, open-source stack: Groq for inference and Hugging Face for hosting.

## Known issues

- Local mode requires the Promptini repository open as the workspace folder; it will not start without `api.py` present.
- The hosted engine may take a few seconds to wake on the first request after a period of inactivity.

## Release notes

### 1.0.0

- Rebranded to Promptini with a new bolt icon and a redesigned sidebar panel.
- Output is now always English, regardless of the input language.
- **Optimize Selection via API** updated to match the current engine contract.

## Feedback

Found a bug or have an idea? Open an issue on the [GitHub repository](https://github.com/Bechir02/promptini).
