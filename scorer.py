import re
import json
from llm import call_groq, call_cerebras
from core.constants import SCORE_WEIGHTS

# ── Vague words ───────────────────────────────────────────────────────────────
VAGUE_WORDS = [
    "good", "nice", "appropriate", "proper", "relevant",
    "if possible", "as needed", "when applicable",
    "make sure", "try to", "attempt to",
    "should be good", "high quality", "best practices",
    "be accurate", "be helpful",
]

# ── Required sections per model ───────────────────────────────────────────────
REQUIRED_SECTIONS = {
    "claude-code": ["# role", "# task"],
    "claude":      ["# role", "# task"],
    "gpt-4":       ["## role", "## task"],
    "cursor":      [],
    "gemini":      ["task:", "output:"],
    "llama":       ["role:", "task:", "output:"],
    "mistral":     ["## role", "## task"],
    "copilot":     ["language:", "file"],
    "cline":       ["goal:", "requirements:"],
    "aider":       ["requirements:"],
    "deepseek":    ["role:", "task:"],
    "windsurf":    ["requirements:"],
    "general":     ["role", "task"],
}

# ── Task requirements ─────────────────────────────────────────────────────────
TASK_REQUIREMENTS = {
    "code_generation": ["input", "output", "error", "return"],
    "debugging":       ["error", "root cause", "fix", "prevent"],
    "code_review":     ["critical", "warning", "suggest"],
    "extraction":      ["null", "json", "field", "missing"],
    "summarization":   ["length", "audience", "exclude"],
    "system_prompt":   ["role", "scope", "tone", "behavior"],
    "analysis":        ["finding", "recommend", "evidence"],
    "refactoring":     ["goal", "behavior", "change"],
    "documentation":   ["param", "return", "example"],
    "writing":         ["tone", "audience", "length"],
    "general":         [],
}

# ── Model awareness checks ────────────────────────────────────────────────────
MODEL_CHECKS = {
    "claude-code": {
        "good": ["# role", "# task", "<role>", "<task>"],
        "bad":  [],
        "note": "Should use clear section headers (# ROLE, # TASK).",
    },
    "claude": {
        "good": ["# role", "# task", "<role>", "<task>"],
        "bad":  [],
        "note": "Should use clear section headers (# ROLE, # TASK).",
    },
    "gpt-4": {
        "good": ["##", "## role", "## task"],
        "bad":  [],
        "note": "Should use markdown headers (##), not XML tags.",
    },
    "cline": {
        "good": ["goal:", "files:", "requirements:", "verify:"],
        "bad":  [],
        "note": "Should be agentic with goal, requirements, and verification.",
    },
    "aider": {
        "good": ["requirements:", "verify:", "in "],
        "bad":  [],
        "note": "Should name files and explicit requirements.",
    },
    "deepseek": {
        "good": ["role:", "task:", "output:"],
        "bad":  [],
        "note": "Should be structured with reasoning steps.",
    },
    "windsurf": {
        "good": ["verify:", "in "],
        "bad":  [],
        "note": "Should be concise and file-aware.",
    },
    "cursor": {
        "good": ["you are working inside cursor", "verify", "inside cursor"],
        "bad":  ["<role>", "<task>", "## role", "## task"],
        "note": "Should be minimal and action-oriented.",
    },
    "gemini": {
        "good": ["task:", "steps:", "output:", "step 1", "1."],
        "bad":  ["<role>", "<task>"],
        "note": "Should use numbered steps format.",
    },
    "llama": {
        "good": ["role:", "task:", "steps:", "constraints:", "output:"],
        "bad":  ["<role>", "<task>"],
        "note": "Should use clear labeled sections with numbered steps.",
    },
    "mistral": {
        "good": ["##", "## role", "## task", "## requirements"],
        "bad":  ["<role>", "<task>"],
        "note": "Should use markdown headers.",
    },
    "copilot": {
        "good": ["language:", "file", "function", "implement"],
        "bad":  ["<role>", "## role"],
        "note": "Should be code-focused and file-aware.",
    },
    "general": {
        "good": ["**role**", "**task**", "**output**", "role:", "task:"],
        "bad":  [],
        "note": "Should have clear bold or labeled sections.",
    },
}


def score_structure(output: str, target_model: str) -> dict:
    required = REQUIRED_SECTIONS.get(target_model, [])
    if not required:
        return {
            "score":   10.0,
            "found":   [],
            "missing": [],
            "note":    "No strict structure requirements for this model.",
        }

    output_lower = output.lower()
    found        = [s for s in required if s.lower() in output_lower]
    missing      = [s for s in required if s.lower() not in output_lower]
    score        = (len(found) / len(required)) * 10.0

    return {
        "score":   round(score, 1),
        "found":   found,
        "missing": missing,
        "note":    f"{len(found)}/{len(required)} required sections present.",
    }


def score_specificity(raw: str, output: str) -> dict:
    output_lower = output.lower()
    found_vague  = [w for w in VAGUE_WORDS if w in output_lower]

    deduction = min(len(found_vague) * 1.5, 6.0)
    score     = max(10.0 - deduction, 4.0)

    concrete_patterns = [
        r"\{[\w_]+\}",
        r"\b\d+\b",
        r"ValueError|TypeError|KeyError|NullPointer",
        r"DataFrame|JSON|CSV|XML|dict|list",
        r"step \d|^\d\.\s",
        r"raise|return|assert",
    ]
    bonuses = sum(
        1 for p in concrete_patterns
        if re.search(p, output, re.IGNORECASE | re.MULTILINE)
    )
    score = min(score + bonuses * 0.4, 10.0)

    placeholders         = re.findall(r"\{[\w_-]+\}", raw)
    missing_placeholders = [p for p in placeholders if p not in output]
    if missing_placeholders:
        score = max(score - len(missing_placeholders) * 2.0, 0.0)

    note = []
    if found_vague:
        note.append(f"{len(found_vague)} vague words found")
    if missing_placeholders:
        note.append(f"missing placeholders: {', '.join(missing_placeholders)}")
    if not note:
        note = ["No vague wording or placeholder drift detected. ✓"]

    return {
        "score":       round(score, 1),
        "vague_words": found_vague,
        "note":        "; ".join(note),
    }


def score_model_awareness(output: str, target_model: str) -> dict:
    output_lower = output.lower()
    check        = MODEL_CHECKS.get(target_model, MODEL_CHECKS["general"])

    good_hit = sum(1 for g in check["good"] if g.lower() in output_lower)
    bad_hit  = sum(1 for b in check["bad"]  if b.lower() in output_lower)

    score = (good_hit / max(len(check["good"]), 1)) * 10.0
    score = max(score - bad_hit * 2.5, 0.0)

    return {
        "score": round(score, 1),
        "note":  check["note"],
    }


def score_task_coverage(output: str, task_type: str) -> dict:
    required = TASK_REQUIREMENTS.get(task_type, [])
    if not required:
        return {
            "score":   10.0,
            "found":   [],
            "missing": [],
            "note":    "No specific task requirements.",
        }

    output_lower = output.lower()
    found        = [r for r in required if r.lower() in output_lower]
    missing      = [r for r in required if r.lower() not in output_lower]
    score        = (len(found) / len(required)) * 10.0

    return {
        "score":   round(score, 1),
        "found":   found,
        "missing": missing,
        "note":    f"{len(found)}/{len(required)} task elements present.",
    }


def score_improvement(raw: str, output: str) -> dict:
    raw_words    = len(raw.split())
    output_words = len(output.split())
    ratio        = output_words / max(raw_words, 1)

    if ratio < 1.2:
        score = 3.0
        note  = "Output barely longer than input — likely too thin."
    elif ratio < 1.8:
        score = 5.0
        note  = "Small improvement over input."
    elif ratio <= 3.5:
        score = 9.0
        note  = f"Good expansion — {ratio:.1f}x longer. ✓"
    elif ratio <= 5.0:
        score = 8.0
        note  = "Very detailed — review for conciseness."
    else:
        score = 6.0
        note  = f"Very long ({ratio:.1f}x) — may have padding."

    return {
        "score":        round(score, 1),
        "input_words":  raw_words,
        "output_words": output_words,
        "ratio":        round(ratio, 2),
        "note":         note,
    }


def judge_battle(raw_prompt: str, output_a: str, model_a: str, output_b: str, model_b: str) -> dict:
    """Uses LLM-as-a-judge to compare two transformations and pick a winner."""
    prompt = f"""
    You are an expert Prompt Engineer comparing two different optimized versions of the same raw input.
    
    RAW INPUT:
    {raw_prompt}
    
    VERSION A (Target: {model_a}):
    {output_a}
    
    VERSION B (Target: {model_b}):
    {output_b}
    
    Evaluate both and decide which is better for the user's likely intent.
    Consider:
    1. Structure and clarity.
    2. Adherence to model-specific best practices.
    3. Removal of ambiguity.
    4. Prefer an explicit output format and testable constraints over mere length.

    Respond with ONLY a valid JSON object — no markdown fences, no commentary.
    
    Return a JSON object:
    {{
        "winner": "A" or "B",
        "reasoning": "Brief explanation of why the winner was chosen.",
        "strengths_a": ["..."],
        "strengths_b": ["..."]
    }}
    """
    
    try:
        from llm import call_llm
        # Use the configured Groq model (previously hard-coded to a non-existent
        # "llama-3.1-70b-versatile" string that call_llm also ignored).
        response = call_llm(prompt, model="groq", response_format="json")
        import json, re
        match = re.search(r"\{.*\}", response, re.DOTALL)
        data = json.loads(match.group(0) if match else response)
        winner = str(data.get("winner", "A")).strip().upper()
        return {
            "winner":      winner if winner in ("A", "B") else "A",
            "reasoning":   data.get("reasoning", ""),
            "strengths_a": data.get("strengths_a", []),
            "strengths_b": data.get("strengths_b", []),
        }
    except Exception as e:
        return {
            "winner": "A",
            "reasoning": f"Defaulting to A due to judge error: {str(e)}",
            "strengths_a": [],
            "strengths_b": []
        }


def score_with_llm(raw_prompt: str, output: str, target_model: str, task_type: str) -> dict:
    """Uses an LLM to evaluate the transformation on tone, utility, and adherence."""
    system_prompt = f"""You are an expert prompt engineering evaluator. Grade the following transformation from a "Messy Prompt" to a "Structured Prompt".

TARGET MODEL: {target_model}
TASK TYPE: {task_type}

EVALUATION CRITERIA:
1. TONE (0-3 pts): Is the tone appropriate for the target model? (e.g., XML for Claude, Markdown for GPT-4).
2. UTILITY (0-4 pts): Does the structured prompt add meaningful constraints and context that were missing?
3. FAITHFULNESS (0-3 pts): Did it preserve the user's original intent without adding unrelated fluff?

OUTPUT FORMAT:
Return ONLY a JSON object with:
- "score": (total float 0-10)
- "reasoning": (brief explanation)
- "strengths": [list]
- "weaknesses": [list]
"""
    user_message = f"Messy Prompt:\n{raw_prompt}\n\nStructured Prompt:\n{output}"

    try:
        # Use Groq for scoring as it's fast
        llm_output, _ = call_groq(system_prompt, user_message)
        # Simple JSON extraction
        match = re.search(r"\{.*\}", llm_output, re.DOTALL)
        if match:
            res = json.loads(match.group(0))
            return {
                "score":     float(res.get("score", 7.0)),
                "note":      res.get("reasoning", "LLM-based evaluation complete."),
                "strengths": res.get("strengths", []),
                "weaknesses": res.get("weaknesses", []),
            }
    except Exception as e:
        print(f"LLM scoring failed: {e}")

    return {
        "score": 7.5,
        "note":  "LLM evaluation unavailable — using heuristic fallback.",
        "strengths": [],
        "weaknesses": [],
    }


def score_transformation(
    raw_prompt:   str,
    output:       str,
    target_model: str,
    task_type:    str,
) -> dict:
    structure   = score_structure(output, target_model)
    specificity = score_specificity(raw_prompt, output)
    model_aware = score_model_awareness(output, target_model)
    task_cover  = score_task_coverage(output, task_type)
    improvement = score_improvement(raw_prompt, output)
    llm_judge   = score_with_llm(raw_prompt, output, target_model, task_type)

    # Heuristic checks are cheap lint signals (kept low-weight so keyword
    # stuffing can't dominate); the rubric-driven LLM judge carries the most
    # weight. Defined once in core.constants.
    weights = SCORE_WEIGHTS

    overall = (
        structure["score"]   * weights["structure"]   +
        specificity["score"] * weights["specificity"] +
        model_aware["score"] * weights["model_aware"] +
        task_cover["score"]  * weights["task_cover"]  +
        improvement["score"] * weights["improvement"] +
        llm_judge["score"]   * weights["llm_judge"]
    )

    if overall >= 9.0:
        grade = "A — Excellent"
    elif overall >= 7.5:
        grade = "B — Good"
    elif overall >= 6.0:
        grade = "C — Acceptable"
    elif overall >= 4.0:
        grade = "D — Needs Work"
    else:
        grade = "F — Poor"

    return {
        "overall":   round(overall, 1),
        "grade":     grade,
        "breakdown": {
            "structure":   structure,
            "specificity": specificity,
            "model_aware": model_aware,
            "task_cover":  task_cover,
            "improvement": improvement,
            "llm_judge":   llm_judge,
        },
    }


def format_score_for_ui(score_result: dict) -> str:
    s = score_result
    b = s["breakdown"]
    lines = [
        f"Overall: {s['overall']}/10  |  Grade: {s['grade']}",
        f"",
        f"Structure     {b['structure']['score']:4.1f}/10  — {b['structure']['note']}",
        f"Specificity   {b['specificity']['score']:4.1f}/10  — {b['specificity']['note']}",
        f"Model-aware   {b['model_aware']['score']:4.1f}/10  — {b['model_aware']['note']}",
        f"Task coverage {b['task_cover']['score']:4.1f}/10  — {b['task_cover']['note']}",
        f"Improvement   {b['improvement']['score']:4.1f}/10  — {b['improvement']['note']}",
        f"Human-grade   {b['llm_judge']['score']:4.1f}/10  — {b['llm_judge']['note']}",
    ]
    return "\n".join(lines)


# ── HTML score card (used by the redesigned UI) ───────────────────────────────
_GRADE_COLOR = {
    "A": "var(--pf-good)",
    "B": "var(--pf-good)",
    "C": "var(--pf-warn)",
    "D": "var(--pf-warn)",
    "F": "var(--pf-bad)",
}


def _bar_color(score: float) -> str:
    if score >= 7.5:
        return "var(--pf-good)"
    if score >= 5.0:
        return "var(--pf-warn)"
    return "var(--pf-bad)"


def _esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def collect_fix_hints(score_result: dict) -> list[str]:
    """Actionable suggestions from the heuristic breakdown (B5)."""
    b = score_result["breakdown"]
    hints: list[str] = []
    missing = b["structure"].get("missing") or []
    if missing:
        hints.append("Add sections: " + ", ".join(missing[:4]))
    vague = b["specificity"].get("vague_words") or []
    if vague:
        hints.append("Replace vague words: " + ", ".join(vague[:4]))
    task_missing = b["task_cover"].get("missing") or []
    if task_missing:
        hints.append("Cover task elements: " + ", ".join(task_missing[:4]))
    return hints


def format_score_html(score_result: dict, reasoning: str = "") -> str:
    """Render a compact score card: grade chip + per-dimension bars + reasoning."""
    s = score_result
    b = s["breakdown"]
    grade_letter = s["grade"].split(" ")[0]
    grade_col = _GRADE_COLOR.get(grade_letter, "var(--pf-warn)")

    rows = [
        ("Structure",     b["structure"]["score"]),
        ("Specificity",   b["specificity"]["score"]),
        ("Model-aware",   b["model_aware"]["score"]),
        ("Task coverage", b["task_cover"]["score"]),
        ("Improvement",   b["improvement"]["score"]),
        ("Human-grade",   b["llm_judge"]["score"]),
    ]

    bar_html = ""
    for label, val in rows:
        pct = max(0.0, min(val / 10.0, 1.0)) * 100
        col = _bar_color(val)
        bar_html += f"""
        <div class="pf-score-row">
          <span class="pf-score-label">{label}</span>
          <span class="pf-score-track"><span class="pf-score-fill" style="width:{pct:.0f}%;background:{col};"></span></span>
          <span class="pf-score-val">{val:.1f}</span>
        </div>"""

    reasoning_html = ""
    if reasoning:
        reasoning_html = f'<div class="pf-score-reason">{_esc(reasoning)}</div>'

    hints = collect_fix_hints(s)
    hints_html = ""
    if hints:
        items = "".join(f"<li>{_esc(h)}</li>" for h in hints)
        hints_html = f'<div class="pf-score-hints"><span class="pf-hint-label">Make it better</span><ul>{items}</ul></div>'

    return f"""
    <div class="pf-score-card">
      <div class="pf-score-head">
        <span class="pf-grade-chip" style="background:{grade_col};">{_esc(s['grade'])}</span>
        <span class="pf-score-overall">{s['overall']}<span class="pf-score-overall-max">/10</span></span>
      </div>
      <div class="pf-score-bars">{bar_html}</div>
      {reasoning_html}
      {hints_html}
    </div>"""

def pick_best(raw_prompt: str, candidates: list, target_model: str) -> int:
    """Internal LLM judge: return the 0-based index of the best candidate prompt.

    Reads the raw input and all candidate optimized prompts, and selects the single
    best one for the user's intent. Used for best-of-N selection (no score shown).
    """
    if not candidates:
        return 0
    if len(candidates) == 1:
        return 0
    n = len(candidates)
    blocks = "\n\n".join(f"CANDIDATE {i + 1}:\n{c}" for i, c in enumerate(candidates))
    prompt = f"""You are an expert prompt engineer choosing the single best optimized prompt.

RAW USER INPUT:
{raw_prompt}

TARGET MODEL: {target_model}

{blocks}

Choose the ONE best candidate for the user's real intent. Judge by: correct format for
the target model; RESTRAINT (no invented requirements, constraints, or edge-cases the
user never asked for); clarity; and concrete, testable constraints. When quality is
equal, prefer the shorter, tighter prompt.

Respond with ONLY JSON, no prose: {{"best": <integer from 1 to {n}>}}"""
    try:
        from llm import call_llm
        resp = call_llm(prompt, model="groq", response_format="json")
        m = re.search(r'"best"\s*:\s*(\d+)', resp) or re.search(r"\d+", resp)
        idx = (int(m.group(1)) if (m and m.lastindex) else int(m.group(0)) if m else 1) - 1
        return idx if 0 <= idx < len(candidates) else 0
    except Exception:
        return 0
