"""Prompt-engineering templates — the product's domain knowledge in one place.

Previously these dicts lived inside llm.py. They are extracted here so prompt
iteration is a single, reviewable location, and so ``validate_templates()`` can
guarantee every model and task type is covered (run by the test suite and the
``__main__`` linter below).

Each OUTPUT_FORMATS entry needs: ``format``, ``description``, ``example``.
Each TASK_GUIDANCE entry is a guidance string. Coverage is checked against
core.constants.MODELS / TASK_TYPES.
"""

from __future__ import annotations

import os

from .constants import MODELS, TASK_TYPES, OUTPUT_LANGUAGES, ALLOWED_LANGUAGES, DEFAULT_LANGUAGE

REQUIRED_FORMAT_KEYS = ("format", "description", "example")

# ── Output format per model ───────────────────────────────────────────────────
OUTPUT_FORMATS: dict[str, dict[str, str]] = {
    "claude-code": {
        "format":      "xml",
        "description": "Markdown section headers only: # ROLE, # TASK, # REQUIREMENTS, # OUTPUT FORMAT, # CONSTRAINTS. One blank line between sections. Clear and action-first for a coding agent. No XML tags. Omit any section the request does not need.",
        "example": """# ROLE
Senior Python engineer.

# TASK
Implement a CSV duplicate finder that returns duplicate rows with their counts.

# REQUIREMENTS
1. Use pandas only; never modify the input file.
2. Return an empty result (not an error) when there are no duplicates.

# OUTPUT FORMAT
One code block, then a one-line summary line stating how many duplicate rows were found.""",
    },

    "claude": {
        "format":      "xml",
        "description": "Markdown section headers: # ROLE, # TASK, # REQUIREMENTS, # OUTPUT FORMAT, # CONSTRAINTS, one blank line between them. Explicit and specific; give context and WHY when it matters. No XML tags. Omit sections the request does not need.",
        "example": """# ROLE
Expert data analyst.

# TASK
Analyze the dataset and identify the top 3 trends.

# REQUIREMENTS
1. Cite specific data points for each trend.
2. No speculation beyond the data.

# OUTPUT FORMAT
Three numbered trends, each with: trend name, supporting data, business implication.""",
    },

    "gpt-4": {
        "format":      "markdown",
        "description": "Markdown headers only — ## Role, ## Task, ## Instructions, ## Output Format. No XML tags. Instructions as numbered list.",
        "example": """## Role
You are a senior Python engineer.

## Task
Build a CSV duplicate finder that returns duplicate rows with their counts.

## Instructions
1. Accept a file path as input
2. Load the CSV using pandas
3. Identify all duplicate rows
4. Return a DataFrame with columns: duplicate_row, count

## Output Format
- A pandas DataFrame
- Print summary: "Found X duplicate rows."
- Raise ValueError if file not found""",
    },

    "cursor": {
        "format":      "minimal",
        "description": "Minimal, action-first. No headers, no XML. Short paragraphs. One clear task per sentence. You are working inside Cursor IDE. End with a concrete verification step.",
        "example": """You are working inside Cursor IDE on a Python project.

Find all duplicate rows in {csv_path} using pandas. Return a DataFrame with columns duplicate_row and count. Handle missing files with a clear error message.

Verify: run the function on a test CSV with known duplicates and confirm the output matches.""",
    },

    "gemini": {
        "format":      "numbered",
        "description": "Role statement, then numbered steps, then explicit output section. No XML. Clean and direct. Put the most important instruction at the end.",
        "example": """You are a data processing assistant specialized in Python and pandas.

Task: Find duplicate rows in a CSV file and return them with counts.

Steps:
1. Load the CSV from {csv_path} using pandas
2. Identify all fully duplicate rows
3. Count occurrences of each duplicate
4. Return results as a DataFrame

Output: DataFrame with columns [duplicate_row, count]. Print "Found X duplicate rows." as summary.

Edge cases: empty file returns empty DataFrame, missing file raises ValueError.""",
    },

    "llama": {
        "format":      "structured",
        "description": "Clear role at top. Numbered steps for sequential tasks. Explicit constraints list. Output format section. Direct and explicit — Llama models respond well to clear delimiters.",
        "example": """Role: You are a Python data engineer.

Task: Find all duplicate rows in a CSV file and return them with occurrence counts.

Steps:
1. Accept file path as input parameter
2. Load CSV using pandas read_csv
3. Identify fully duplicate rows using duplicated()
4. Count occurrences and return as DataFrame

Constraints:
- Use only pandas and standard library
- Handle FileNotFoundError explicitly
- Do not modify the input file

Output: DataFrame with columns [duplicate_row, count] plus summary string.""",
    },

    "mistral": {
        "format":      "markdown",
        "description": "Markdown headers for structure. Direct and concise. Clear delimiters between sections. Specify output format explicitly.",
        "example": """## Role
Python data engineer specializing in data quality.

## Task
Find duplicate rows in a CSV file and return them with counts.

## Requirements
- Input: file path as string
- Use pandas for all operations
- Return DataFrame with columns: duplicate_row, count
- Raise ValueError for missing files

## Output Format
DataFrame + one-line summary: "Found X duplicates." """,
    },

    "copilot": {
        "format":      "minimal",
        "description": "Code-focused and file-aware. Reference specific files, functions, line numbers. Action-oriented. One task at a time. Always specify the programming language.",
        "example": """Language: Python

In the file {file_path}, implement a function called find_duplicates(csv_path: str) -> pd.DataFrame.

The function should read the CSV, find all duplicate rows, and return them with occurrence counts as a DataFrame with columns [duplicate_row, count].

Handle FileNotFoundError. Do not modify existing functions in the file.""",
    },

    "general": {
        "format":      "structured",
        "description": "Clear sections with bold headers. Role, Task, Context, Constraints, Output Format. Readable and model-agnostic.",
        "example": """**Role:** You are a Python data engineer.

**Task:** Find duplicate rows in a CSV file and return them with occurrence counts.

**Context:** Input is a CSV file at {csv_path}. Caller expects a pandas DataFrame back.

**Constraints:**
- Use pandas only
- Handle missing files gracefully
- Do not modify the input file

**Output Format:** DataFrame with columns [duplicate_row, count] plus a summary string.""",
    },

    "deepseek": {
        "format":      "structured",
        "description": "Clear labeled sections (Role, Task, Requirements, Output). DeepSeek follows explicit step-by-step instructions well; put reasoning steps before the answer for reasoning tasks. No XML.",
        "example": """Role: You are a senior Python engineer.

Task: Find duplicate rows in a CSV and return them with counts.

Requirements:
- Use pandas; do not modify the source file
- Raise ValueError on a missing file

Output: DataFrame[duplicate_row, count] + a one-line summary.""",
    },

    "qwen": {
        "format":      "markdown",
        "description": "Markdown sections with explicit numbered steps and clear delimiters. State the output format explicitly. Qwen responds well to structured, unambiguous instructions.",
        "example": """## Role
Python data engineer.

## Task
Find duplicate rows in a CSV and return them with counts.

## Steps
1. Load the CSV with pandas
2. Identify duplicate rows
3. Return a DataFrame [duplicate_row, count]

## Output
DataFrame + one-line summary.""",
    },

    "grok": {
        "format":      "minimal",
        "description": "Direct and concise. Lead with the task in one sentence, then only the essential constraints. No long preamble.",
        "example": """Find duplicate rows in {csv_path} with pandas and return a DataFrame [duplicate_row, count]. Raise ValueError if the file is missing, return empty if none, and print "Found X duplicates." """,
    },

    "v0": {
        "format":      "minimal",
        "description": "For Vercel v0 UI generation. Describe the component/page, the stack (React/Next.js + Tailwind + shadcn/ui), layout, states and data shape. Visual and specific; one screen per prompt.",
        "example": """Build a responsive pricing page in Next.js + Tailwind + shadcn/ui.

- Three plan cards (Starter, Pro, Enterprise) with a monthly/annual toggle
- Highlight the Pro card; a CTA button on each
- Mobile: stacked; Desktop: 3 columns

Use placeholder copy and prices.""",
    },

    "bolt": {
        "format":      "structured",
        "description": "For bolt.new full-app scaffolding. State the app, the stack, the pages/files and the data model. Action-oriented — build end-to-end, not a single snippet.",
        "example": """Build a to-do web app.

Stack: React + Vite + Tailwind, localStorage persistence.

Features:
- Add / complete / delete tasks
- Filter: all / active / done
- Persist across reloads

Deliver a runnable project with components split into files.""",
    },

    "windsurf": {
        "format":      "minimal",
        "description": "For the Windsurf (Cascade) IDE agent. Minimal, action-first, file-aware. Name the file/function, the exact change, and a verification step. One task at a time.",
        "example": """In src/utils/csv.py, add find_duplicates(csv_path: str) -> pd.DataFrame that returns duplicate rows with counts.

Handle FileNotFoundError. Do not touch other functions.

Verify: run it on a test CSV with known duplicates.""",
    },

    "cline": {
        "format":      "minimal",
        "description": "Agentic and action-first for the Cline IDE agent. State the goal, the files/functions involved, constraints, and a verification step. One task at a time. Cline will plan and execute autonomously.",
        "example": """Goal: Add input validation to the /api/users POST endpoint.

Files: src/routes/users.ts, src/validators/user.ts

Requirements:
- Validate email format and name length (2-50 chars)
- Return 400 with specific field errors on invalid input
- Do not change existing response shape for valid requests

Verify: run the existing test suite and confirm all pass, then add a test for invalid email.""",
    },

    "aider": {
        "format":      "minimal",
        "description": "For the Aider AI pair-programming tool. Direct and file-aware. Name the files to edit, describe the change clearly, and state what should NOT change. Aider works best with focused, single-concern requests.",
        "example": """In src/utils/csv.py, add a function find_duplicates(csv_path: str) -> pd.DataFrame that loads the CSV, finds duplicate rows, and returns them with occurrence counts.

Handle FileNotFoundError. Do not modify existing functions in the file.

The function signature must match: find_duplicates(csv_path: str) -> pd.DataFrame""",
    },
}

# ── Task-specific guidance ────────────────────────────────────────────────────
TASK_GUIDANCE: dict[str, str] = {
    "code_generation": """
- Specify the exact function/class signature expected
- List input types and output types explicitly
- Include error handling requirements
- Mention performance constraints if relevant
- Add at least one concrete usage example
- For complex tasks, ask the model to think step-by-step before coding
""",
    "debugging": """
- ALWAYS include these four elements — no exceptions:
  1. The exact error message or exception type
  2. Root cause analysis BEFORE any fix is proposed
  3. The concrete fix with corrected code
  4. Prevention strategy for this class of bug
- Keep scope narrow — fix this specific bug only
- End with a concrete verification step
- Use the words: error, root cause, fix, prevent
- Ask the model to explain WHY the bug occurs before jumping to the fix
""",
    "code_review": """
- Define review criteria explicitly (security, performance, style, correctness)
- Specify severity levels (critical / warning / suggestion)
- Ask for positive observations too
- Set scope — what NOT to review
- Request actionable fixes, not just observations
""",
    "refactoring": """
- State the refactoring goal precisely (e.g., reduce cognitive complexity, improve DRY, add type hints)
- Explicitly require: preserve all existing behavior and pass all current tests
- Ask for a "Before/After" comparison table or summary
- Limit scope — focus on one architectural concern at a time
- Request an explanation of EACH pattern applied (e.g., "Extracted Method", "Replaced Magic Number")
- Require that no new dependencies be added unless specified
""",
    "documentation": """
- Specify doc format (docstring / JSDoc / README / inline)
- Define the audience
- List what must be covered (params, returns, exceptions, examples)
- Specify length constraints
- Ask for usage examples
""",
    "analysis": """
- Define what "interesting" means — patterns, anomalies, trends
- Specify output structure (summary + findings + recommendations)
- Ask for confidence levels on conclusions
- Request that assumptions be stated explicitly
- Define the audience
""",
    "extraction": """
- List every field to extract with its expected type
- Specify null handling explicitly
- Prohibit hallucination — extract only what is present in the source
- Define output format (JSON schema preferred) — treat it as an API contract
- Handle edge cases: nested fields, arrays, ambiguous values
- If multiple records, specify how to delimit them
""",
    "summarization": """
- Specify target length EXACTLY (e.g., "between 100 and 150 words" or "3-5 bullet points")
- Define what "Key Information" must be preserved (e.g., names, dates, core argument)
- Define what to exclude (e.g., examples, preamble, meta-commentary)
- Specify the reading level (e.g., "Grade 10", "Executive Summary", "Layperson")
- Prohibit generic openings like "This document discusses..." or "The text covers..."
- Ask for a "TL;DR" one-liner at the very top
""",
    "system_prompt": """
- Define the persona with specific traits, not generic ones
- List behavioral rules as explicit do/don't pairs
- Define the scope boundary — what topics are in/out
- Specify tone with concrete adjectives
- Add an out-of-scope redirect behavior
- Use delimiters (<context>, <instructions>) to isolate sections and prevent injection
- Include 1-2 few-shot examples of ideal responses
""",
    "agentic": """
- Define the agent's goal as a single, measurable outcome
- List available tools/actions and when to use each
- Specify the reasoning loop: Observe → Think → Act → Reflect
- Set explicit guardrails: max steps, fallback behavior, when to stop
- Require the agent to verify its own output before finalizing
- Define what "done" looks like — concrete success criteria, not vague goals
""",
    "writing": """
- Specify genre, tone, and target audience with descriptive adjectives (e.g., "Professional yet witty", "Technical but accessible")
- Define length in word count range
- List stylistic constraints (e.g., "No passive voice", "Use short paragraphs", "Include a punchy headline")
- Prohibit meta-commentary — do not talk about the writing, just WRITE
- Give one concrete example of the desired style and one example of a style to avoid
- Specify the perspective (1st person, 3rd person objective, etc.)
""",
    "general": """
- Make the task as specific as possible
- Add at least one concrete constraint
- Define the output format explicitly (JSON schema, markdown, plain text)
- Specify what success looks like with measurable criteria
- Separate instructions from input data using clear delimiters
""",
    "translation": """
- State the source and target languages explicitly
- Specify register/tone (formal, casual, technical) and audience
- Preserve meaning, names, numbers, code and {placeholders} exactly
- Say how to handle idioms (localize vs. literal) and untranslatable terms
- Return only the translation — no commentary
""",
    "localization": """
- Name the target locale(s) and their conventions (dates, currency, units, RTL)
- Adapt idioms, examples and references to the local culture, not just the words
- Preserve product names, code and {placeholders}
- Flag anything needing human/legal review
- Keep tone and intent consistent with the source
""",
    "data_cleaning": """
- Describe the dataset shape (columns, types) and the tool (pandas / SQL / Excel)
- List the exact steps: missing values, duplicates, types, outliers, formatting
- Specify how to handle each (drop / impute / flag) — never silently change data
- Do not mutate the original; output a cleaned copy + a change log
- Define the expected output schema
""",
    "sql": """
- Name the SQL dialect (PostgreSQL, MySQL, SQL Server, SQLite…)
- Give the relevant table/column names and relationships
- State the exact result columns, filters, grouping and ordering wanted
- Require safe, readable SQL (explicit JOINs, no SELECT * in production)
- Ask for a one-line explanation of what the query returns
""",
    "marketing_copy": """
- Define the product, the audience, and the single desired action (CTA)
- Specify channel/format (landing hero, ad, email subject, social post) and length
- Set tone/brand voice with concrete adjectives; list words to avoid
- Lead with the benefit; make claims specific, not generic hype
- Provide the requested number of distinct variants
""",
}

# ── Anti-generic rules ────────────────────────────────────────────────────────
CHAIN_DIRECTIVE = """━━━ CHAIN MODE ━━━
Do NOT produce a single prompt. Instead decompose the task into an ordered chain
of 2–5 self-contained sub-prompts. Number them "Step 1:", "Step 2:", … Each step
must be runnable on its own, state what it consumes (including the previous step's
output) and what it produces, and keep the target-model format."""

ANTI_GENERIC = """
WHAT TO AVOID — these make prompts weak:
- Vague words: "good", "nice", "appropriate", "proper", "clear", "relevant"
- Redundant phrases: "please", "if possible", "as needed", "when applicable"
- Obvious instructions: "make sure it works", "test your code", "be accurate"
- Copying exemplar text verbatim
- Adding sections that add no value for this specific task
- Hedging language: "try to", "consider", "you might want to" — be direct
- Filler sections that only restate the task in different words
- Unsupported claims: "ensure high performance" without defining what "high" means
"""


# ── Input: Tunisian Derja / Arabizi understanding (always injected) ────────────
DERJA_INPUT_NOTE = """
INPUT LANGUAGE NOTE:
The user's raw prompt may be written in Tunisian Derja (Tunisian Arabic), or in
"Arabizi" / franco-arabe (Derja written in Latin letters, often code-switched with
French and English). Interpret it faithfully before optimizing. Common Arabizi
digit substitutions: 3=ع, 7=ح, 9=ق, 5=خ, 2=ء (hamza), 8=غ, 6=ط. Treat mixed
Derja + French + English in one sentence as normal. Never refuse or ask for a
translation — infer the intent and proceed.
"""

# ── Output language directives ────────────────────────────────────────────────
LANGUAGE_GUIDANCE: dict[str, str] = {
    "auto": (
        "Write the optimized prompt in the SAME language and script the user used in "
        "their raw prompt (mirror their language and register). If they wrote in "
        "Arabizi, prefer Arabic-script Derja unless they clearly want Latin script."
    ),
    "english": "Write the optimized prompt in clear, professional English.",
    "arabic": (
        "Write the optimized prompt in Modern Standard Arabic (الفصحى). Keep code, "
        "placeholders like {var}, API names and technical identifiers in their "
        "original English / Latin form."
    ),
    "derja": (
        "Write the optimized prompt in natural, idiomatic Tunisian Derja (Tunisian "
        "Arabic) in Arabic script. Keep code, placeholders like {var}, API names and "
        "technical identifiers in their original English / Latin form."
    ),
    "french": "Write the optimized prompt in clear, professional French.",
}


def normalize_language(language: str | None) -> str:
    """Return a valid output language, defaulting when unknown/empty."""
    if not language:
        return DEFAULT_LANGUAGE
    lang = str(language).strip().lower()
    return lang if lang in ALLOWED_LANGUAGES else DEFAULT_LANGUAGE


def build_language_block(language: str | None) -> str:
    """Render the OUTPUT LANGUAGE directive for the system prompt."""
    lang = normalize_language(language)
    return LANGUAGE_GUIDANCE.get(lang, LANGUAGE_GUIDANCE[DEFAULT_LANGUAGE])


def validate_templates() -> list[str]:
    """Return a list of coverage/shape problems. Empty list == healthy.

    Checks every model in MODELS has an OUTPUT_FORMATS entry with the required
    keys, and every task type in TASK_TYPES has TASK_GUIDANCE.
    """
    problems: list[str] = []

    for model in MODELS:
        entry = OUTPUT_FORMATS.get(model)
        if entry is None:
            problems.append(f"OUTPUT_FORMATS missing model: {model}")
            continue
        for key in REQUIRED_FORMAT_KEYS:
            if not entry.get(key):
                problems.append(f"OUTPUT_FORMATS[{model}] missing/empty key: {key}")

    for task in TASK_TYPES:
        if not TASK_GUIDANCE.get(task):
            problems.append(f"TASK_GUIDANCE missing task type: {task}")

    for lang in OUTPUT_LANGUAGES:
        if not LANGUAGE_GUIDANCE.get(lang):
            problems.append(f"LANGUAGE_GUIDANCE missing language: {lang}")

    return problems


# ── Optional YAML overrides (B7) — edit prompts without touching Python ────────
def apply_overrides(data: dict) -> None:
    """Merge {output_formats, task_guidance, language_guidance} into live dicts."""
    for model, entry in (data.get("output_formats") or {}).items():
        if isinstance(entry, dict):
            OUTPUT_FORMATS[model] = {**OUTPUT_FORMATS.get(model, {}), **entry}
    for task, guide in (data.get("task_guidance") or {}).items():
        if guide:
            TASK_GUIDANCE[task] = guide
    for lang, guide in (data.get("language_guidance") or {}).items():
        if guide:
            LANGUAGE_GUIDANCE[lang] = guide


def load_yaml_overrides(path: str) -> dict:
    """Load a YAML overrides file if present (and PyYAML is installed)."""
    from pathlib import Path
    p = Path(path)
    if not p.exists():
        return {}
    try:
        import yaml
    except Exception:
        return {}
    try:
        data = yaml.safe_load(p.read_text()) or {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


# Apply overrides at import if a templates file exists (default: templates.yaml).
apply_overrides(load_yaml_overrides(os.environ.get("PF_TEMPLATES_FILE", "templates.yaml")))


if __name__ == "__main__":
    issues = validate_templates()
    if issues:
        print("Template problems found:")
        for p in issues:
            print(f"  - {p}")
        raise SystemExit(1)
    print(f"✅ Templates valid: {len(OUTPUT_FORMATS)} models, {len(TASK_GUIDANCE)} task types, {len(LANGUAGE_GUIDANCE)} languages.")
