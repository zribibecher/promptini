"""Promptini FastAPI engine — serves the UI and the /forge endpoint.

Run:  uvicorn api:app --host 0.0.0.0 --port 7860
"""
from dotenv import load_dotenv
load_dotenv()

import os

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from llm import transform_prompt
from scorer import pick_best
from core.tasks import detect_task_type
from core.concurrency import map_ordered
from core.config import get_settings
from core.metrics import metrics

BEST_OF = int(os.getenv("BEST_OF", "1"))  # 1 = fast/free-tier; raise if you upgrade Groq
_HERE = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="Promptini", version="2.0")


class ForgeRequest(BaseModel):
    prompt: str
    target_model: str = "claude-code"
    depth: str = "standard"
    language: str = "english"


@app.get("/")
def index():
    return FileResponse(os.path.join(_HERE, "web", "index.html"))


@app.get("/health")
def health():
    s = get_settings()
    return {"ok": getattr(s, "has_any_provider", True), "metrics": metrics.snapshot()}


@app.post("/forge")
def forge(req: ForgeRequest):
    prompt = (req.prompt or "").strip()
    if not prompt:
        return {"transformed": "", "error": "empty prompt", "task_type": ""}

    task_type = detect_task_type(prompt)
    lang = req.language or "english"

    def _gen(_i):
        try:
            txt, _p, _u = transform_prompt(prompt, req.target_model, task_type, req.depth, [], lang, False)
            return (txt or "").strip()
        except Exception as e:
            return f"__ERR__{e}"

    results = map_ordered(_gen, list(range(BEST_OF)), max_workers=BEST_OF)
    cands = [r for r in results if r and not r.startswith("__ERR__")]
    if not cands:
        err = next((r[7:] for r in results if r.startswith("__ERR__")), "generation failed")
        return {"transformed": "", "error": err, "task_type": task_type}

    best = cands[pick_best(prompt, cands, req.target_model) if len(cands) > 1 else 0]
    metrics.incr("requests")
    return {"transformed": best, "error": None, "task_type": task_type}
