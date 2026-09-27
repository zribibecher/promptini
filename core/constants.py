"""Single source of truth for models, depths, scoring weights and thresholds.

Previously these lived (and drifted) across app.py, rag.py, llm.py and
scorer.py. Import them from here everywhere instead.
"""

from __future__ import annotations

# ── Target models ─────────────────────────────────────────────────────────────
# Order is the display order in the UI.
MODELS: list[str] = [
    "claude-code",
    "claude",
    "gpt-4",
    "cursor",
    "cline",
    "aider",
    "gemini",
    "llama",
    "mistral",
    "copilot",
    "deepseek",
    "qwen",
    "grok",
    "v0",
    "bolt",
    "windsurf",
    "general",
]
ALLOWED_MODELS: frozenset[str] = frozenset(MODELS)
DEFAULT_MODEL: str = "general"

# ── Depth levels ──────────────────────────────────────────────────────────────
DEPTHS: list[str] = ["concise", "standard", "comprehensive"]
ALLOWED_DEPTHS: frozenset[str] = frozenset(DEPTHS)
DEFAULT_DEPTH: str = "standard"

# ── Output languages ──────────────────────────────────────────────────────────
# "auto" mirrors the user's input language. English is the default because target
# models generally perform best with English prompts.
OUTPUT_LANGUAGES: list[str] = ["auto", "english", "arabic", "derja", "french"]
ALLOWED_LANGUAGES: frozenset[str] = frozenset(OUTPUT_LANGUAGES)
DEFAULT_LANGUAGE: str = "english"

# ── Task types ────────────────────────────────────────────────────────────────
TASK_TYPES: list[str] = [
    "extraction",
    "system_prompt",
    "agentic",
    "code_review",
    "debugging",
    "refactoring",
    "documentation",
    "analysis",
    "summarization",
    "writing",
    "code_generation",
    "translation",
    "localization",
    "data_cleaning",
    "sql",
    "marketing_copy",
    "general",
]
DEFAULT_TASK_TYPE: str = "general"

# ── Retrieval ─────────────────────────────────────────────────────────────────
DEFAULT_TOP_K: int = 3
DEFAULT_MIN_QUALITY: float = 7.0
# Reciprocal Rank Fusion constant. Larger -> flatter weighting of rank.
RRF_K: int = 60

# ── Scoring weights ───────────────────────────────────────────────────────────
# Heuristic checks are cheap "lint" signals and are intentionally capped so a
# keyword-stuffed prompt cannot dominate the score; the LLM judge carries the
# most weight. Weights must sum to 1.0 (asserted below).
SCORE_WEIGHTS: dict[str, float] = {
    "structure":   0.15,
    "specificity": 0.15,
    "model_aware": 0.10,
    "task_cover":  0.15,
    "improvement": 0.05,
    "llm_judge":   0.40,
}

assert abs(sum(SCORE_WEIGHTS.values()) - 1.0) < 1e-9, "SCORE_WEIGHTS must sum to 1.0"
