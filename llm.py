import logging
import time
from dotenv import load_dotenv
load_dotenv()
from groq import Groq
from cerebras.cloud.sdk import Cerebras

from core.config import get_settings
from core.templates import OUTPUT_FORMATS, TASK_GUIDANCE, ANTI_GENERIC, DERJA_INPUT_NOTE, build_language_block, CHAIN_DIRECTIVE
from core.exemplars import get_exemplars

logger = logging.getLogger(__name__)
_settings = get_settings()

# ── Provider routing ──────────────────────────────────────────────────────────
# Only Groq (primary) and Cerebras (fallback) are supported, by design.
GROQ_MODEL     = _settings.groq_model
CEREBRAS_MODEL = _settings.cerebras_model

# ── Optional OpenAI-compatible providers (used only when their key is set) ─────
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
TOGETHER_BASE   = "https://api.together.xyz/v1"
GOOGLE_BASE     = "https://generativelanguage.googleapis.com/v1beta/openai/"

_TRANSIENT_MARKERS = (
    "429", "rate limit", "rate_limit", "timeout", "timed out", "temporarily",
    "overloaded", "500", "502", "503", "504", "unavailable", "connection reset",
)


def _is_transient(err: Exception) -> bool:
    """True for errors worth retrying (rate limits, 5xx, timeouts)."""
    msg = str(err).lower()
    return any(m in msg for m in _TRANSIENT_MARKERS)


def _retry(fn, *args, retries: int = 2, base_delay: float = 0.6, **kwargs):
    """Call ``fn`` with exponential backoff on transient errors only."""
    attempt = 0
    while True:
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            attempt += 1
            if attempt > retries or not _is_transient(e):
                raise
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning("Transient error (%s) — retry %d/%d in %.1fs", e, attempt, retries, delay)
            time.sleep(delay)


def _openai_compatible(base_url: str, api_key: str, model: str,
                       system_prompt: str, user_prompt: str) -> tuple[str, dict]:
    """Call any OpenAI-compatible chat endpoint (OpenRouter / Together / Google)."""
    from openai import OpenAI  # lazy: only needed if such a provider is configured
    client = OpenAI(api_key=api_key, base_url=base_url)
    resp = client.chat.completions.create(
        model    = model,
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        max_tokens  = _settings.max_tokens,
        temperature = _settings.temperature,
    )
    u = resp.usage
    usage = {
        "prompt_tokens":     getattr(u, "prompt_tokens", 0),
        "completion_tokens": getattr(u, "completion_tokens", 0),
        "total_tokens":      getattr(u, "total_tokens", 0),
    }
    return resp.choices[0].message.content.strip(), usage


def build_provider_order(settings) -> list[str]:
    """Ordered list of provider names to try, based on which keys are set."""
    order = []
    if settings.groq_api_key:       order.append("groq")
    if settings.cerebras_api_key:   order.append("cerebras")
    if settings.openrouter_api_key: order.append("openrouter")
    if settings.together_api_key:   order.append("together")
    if settings.google_api_key:     order.append("google")
    return order


def _provider_model(name: str) -> str:
    return {
        "groq":       GROQ_MODEL,
        "cerebras":   CEREBRAS_MODEL,
        "openrouter": _settings.openrouter_model,
        "together":   _settings.together_model,
        "google":     _settings.google_model,
    }.get(name, name)


def _call_provider(name: str, system_prompt: str, user_prompt: str) -> tuple[str, dict]:
    if name == "groq":
        return call_groq(system_prompt, user_prompt)
    if name == "cerebras":
        return call_cerebras(system_prompt, user_prompt)
    if name == "openrouter":
        return _openai_compatible(OPENROUTER_BASE, _settings.openrouter_api_key, _settings.openrouter_model, system_prompt, user_prompt)
    if name == "together":
        return _openai_compatible(TOGETHER_BASE, _settings.together_api_key, _settings.together_model, system_prompt, user_prompt)
    if name == "google":
        return _openai_compatible(GOOGLE_BASE, _settings.google_api_key, _settings.google_model, system_prompt, user_prompt)
    raise ValueError(f"Unknown provider: {name}")

# ── Build system prompt ───────────────────────────────────────────────────────
def build_system_prompt(
    target_model: str,
    task_type:    str,
    depth:        str,
    exemplars:    list[dict],
    language:     str = "english",
    chain:        bool = False,
) -> str:

    fmt        = OUTPUT_FORMATS.get(target_model, OUTPUT_FORMATS["general"])
    task_guide = TASK_GUIDANCE.get(task_type, TASK_GUIDANCE["general"])
    language_block = build_language_block(language)
    chain_block = ("\n" + CHAIN_DIRECTIVE + "\n") if chain else ""

    depth_guidance = {
        "concise": (
            "CONCISE MODE: under 120 words. Role + task + only the one or two "
            "constraints the user actually stated. No context block, no output-format "
            "block, no examples."
        ),
        "standard": (
            "STANDARD MODE: 120-250 words. Role, task, and only the constraints the "
            "user stated or clearly implied. Add a context or output-format block ONLY "
            "if the request truly needs it. Never invent requirements to fill space."
        ),
        "comprehensive": (
            "COMPREHENSIVE MODE: as long as the task genuinely needs — no filler. "
            "Role, task, the stated constraints, plus an output format or a single "
            "example only where they add real value. Elaborate on what the user asked "
            "for; never fabricate scope, edge-cases, or performance targets they never "
            "mentioned."
        ),
    }.get(depth, "STANDARD MODE: 120-250 words.")

    _ex = get_exemplars(task_type, target_model, k=2)
    fewshot_block = ""
    if _ex:
        fewshot_block = "\n━━━ REFERENCE TRANSFORMATIONS (quality bar — adapt to THIS request, never copy) ━━━\n"
        for _i, _e in enumerate(_ex, 1):
            fewshot_block += (
                f"\n[{_i}] Rough idea: {_e.get('input','').strip()}\n"
                f"Optimized prompt:\n{_e.get('output','').strip()}\n"
            )

    return f"""You are Promptini — an expert prompt engineer and native Tunisian Derja linguist, running as the backend of a VS Code extension. You turn messy, vague inputs (in Derja, Arabic, French, or English) into precise, structured, model-optimized prompts that produce dramatically better results.

TARGET MODEL: {target_model}
TASK TYPE: {task_type}
DEPTH: {depth}
{DERJA_INPUT_NOTE}
━━━ OUTPUT LANGUAGE ━━━
{language_block}

━━━ OUTPUT FORMAT FOR {target_model.upper()} ━━━
{fmt['description']}

EXAMPLE of correct format for {target_model}:
{fmt['example']}

━━━ TASK-SPECIFIC REQUIREMENTS FOR {task_type.upper()} ━━━
{task_guide}

━━━ DEPTH REQUIREMENT ━━━
{depth_guidance}
{chain_block}

━━━ 2026 PROMPT ENGINEERING TECHNIQUES ━━━
Apply these modern techniques when they genuinely improve the prompt:
- STRUCTURED CHAIN-OF-THOUGHT: For reasoning-heavy tasks, decompose into logical steps BEFORE asking for the answer. State "Think step-by-step:" only when the task genuinely needs multi-step reasoning.
- SELF-CRITIQUE PATTERN: For complex outputs, instruct the model to produce a draft, critique it against specific criteria, then produce the final version.
- CONTEXT ISOLATION: Use clear delimiters (XML tags, markdown headers, or labeled sections) to separate instructions from user data — prevents instruction drift and injection.
- FEW-SHOT GROUNDING: When the task needs a specific format or style, include 1-2 concrete examples of the desired output — not generic ones.
- STRUCTURED OUTPUT CONTRACT: When the output must be machine-readable (JSON, YAML, CSV), specify the exact schema, required fields, and types — treat it as an API contract.
- ROLE SPECIFICITY: Assign a role with domain expertise relevant to the task (e.g., "Senior Python engineer with pandas expertise" not just "Python developer").
Only apply techniques that add real value to THIS specific task. A simple request does not need chain-of-thought or self-critique.

━━━ TUNISIAN DERJA MASTERY ━━━
The input may be Tunisian Derja or Arabizi — understand it fully using authentic Tunisian knowledge. ALWAYS write the optimized prompt itself in clear English, whatever language the input is in.
- Natural vocabulary: برشا، وقتاش، علاش، شكون، ديجا، فاش قام، بالك، يزي، عيّشك، توا، مريڤل.
- Arabizi (Latin + numerals): map 3=ع، 7=ح، 5=خ، 9=ق، 2=ء — read and write both scripts fluently.
- Natural code-switching: keep tech terms the way Tunisian devs say them (API, merge request, déploiement, dashboard, bug, deploy) — never force-translate them into formal Arabic.

━━━ VS CODE CONTEXT ━━━
Infer the developer's environment (file type, selected code, stack) from the input — never ask them to re-explain it. Produce a prompt ready to inject into the editor or run in the terminal, with no formatting that would break a parser.

━━━ RESTRAINT — THE MOST IMPORTANT RULE ━━━
Match the prompt's scope to the request. Include ONLY requirements the user stated or clearly implied. NEVER invent constraints, edge-cases, performance targets, file-size assumptions, custom error types, or output schemas the user did not ask for. A short, casual request gets a short, precise prompt — a rough "read a CSV" must NOT become a spec for huge files, streaming, and custom exceptions. The best prompt is the SMALLEST one that fully captures the user's real intent. When in doubt, leave it out. Never add a Context or Output-Format section that only restates the task, the signature, or the obvious — for a simple request, role + task + one-to-three real constraints IS the whole prompt.

━━━ QUALITY RULES ━━━
1. Every section must earn its place — cut anything that adds no value.
2. Be specific to THIS task — no generic boilerplate.
3. Preserve all {{placeholders}} and the user's exact intent — restructure, never redirect.
4. Use the correct format for {target_model} — see the example above.
5. Make constraints concrete and testable, not vague.
6. Prefer explicit over implicit — state assumptions, define ambiguous terms.
{ANTI_GENERIC}
{fewshot_block}
━━━ ABSOLUTE OUTPUT RULES ━━━
- Output ONLY the transformed prompt — nothing else.
- NO preamble ("Here is…", "I have transformed…"), NO explanation, NO markdown code fences, NO commentary after the prompt.
- First character of your response = first character of the prompt."""


# ── Groq call ─────────────────────────────────────────────────────────────────
def call_groq(system_prompt: str, user_prompt: str, model: str | None = None) -> tuple[str, dict]:
    if not _settings.groq_api_key:
        raise ValueError("GROQ_API_KEY not set.")

    client   = Groq(api_key=_settings.groq_api_key)
    response = client.chat.completions.create(
        model    = model or GROQ_MODEL,
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        max_tokens  = _settings.max_tokens,
        temperature = _settings.temperature,
    )
    usage = {
        "prompt_tokens":     response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens":      response.usage.total_tokens,
    }
    return response.choices[0].message.content.strip(), usage


# ── Cerebras fallback ─────────────────────────────────────────────────────────
def call_cerebras(system_prompt: str, user_prompt: str, model: str | None = None) -> tuple[str, dict]:
    if not _settings.cerebras_api_key:
        raise ValueError("CEREBRAS_API_KEY not set.")

    client   = Cerebras(api_key=_settings.cerebras_api_key)
    response = client.chat.completions.create(
        model    = model or CEREBRAS_MODEL,
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        max_tokens = _settings.max_tokens,
    )
    usage = {
        "prompt_tokens":     getattr(response.usage, "prompt_tokens", 0),
        "completion_tokens": getattr(response.usage, "completion_tokens", 0),
        "total_tokens":      getattr(response.usage, "total_tokens", 0),
    }
    return response.choices[0].message.content.strip(), usage


# ── Main transform ────────────────────────────────────────────────────────────
def transform_prompt(
    raw_prompt:   str,
    target_model: str,
    task_type:    str,
    depth:        str,
    exemplars:    list[dict],
    language:     str = "english",
    chain:        bool = False,
) -> tuple[str, str, dict]:
    """
    Returns (transformed_prompt, provider_name, usage_dict).
    Tries Groq first, falls back to Cerebras.
    """
    system_prompt = build_system_prompt(
        target_model = target_model,
        task_type    = task_type,
        depth        = depth,
        exemplars    = exemplars,
        language     = language,
        chain        = chain,
    )
    user_message = f"Raw prompt to transform:\n\n{raw_prompt}"

    order = build_provider_order(_settings)
    if not order:
        raise RuntimeError("No LLM provider configured. Set GROQ_API_KEY and/or CEREBRAS_API_KEY.")

    errors = []
    for name in order:
        try:
            result, usage = _retry(_call_provider, name, system_prompt, user_message)
            return result, f"{name} ({_provider_model(name)})", usage
        except Exception as e:
            errors.append(f"{name}({_provider_model(name)}): {e}")
            logger.warning("Provider %s (%s) failed: %s — trying next.", name, _provider_model(name), e)

    raise RuntimeError("All providers failed — " + " | ".join(errors))


# ── Streaming (B8) ────────────────────────────────────────────────────────────
def call_groq_stream(system_prompt: str, user_prompt: str, model: str | None = None):
    if not _settings.groq_api_key:
        raise ValueError("GROQ_API_KEY not set.")
    client = Groq(api_key=_settings.groq_api_key)
    stream = client.chat.completions.create(
        model    = model or GROQ_MODEL,
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        max_tokens  = _settings.max_tokens,
        temperature = _settings.temperature,
        stream      = True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def call_cerebras_stream(system_prompt: str, user_prompt: str, model: str | None = None):
    if not _settings.cerebras_api_key:
        raise ValueError("CEREBRAS_API_KEY not set.")
    client = Cerebras(api_key=_settings.cerebras_api_key)
    stream = client.chat.completions.create(
        model    = model or CEREBRAS_MODEL,
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        max_tokens = _settings.max_tokens,
        stream     = True,
    )
    for chunk in stream:
        delta = getattr(chunk.choices[0].delta, "content", None)
        if delta:
            yield delta


_STREAMERS = {"groq": call_groq_stream, "cerebras": call_cerebras_stream}


def transform_prompt_stream(
    raw_prompt:   str,
    target_model: str,
    task_type:    str,
    depth:        str,
    exemplars:    list[dict],
    language:     str = "english",
    chain:        bool = False,
):
    """Yield (accumulated_text, provider_label) as tokens arrive.

    Streams via Groq/Cerebras; if only non-streaming (OpenAI-compatible) providers
    are configured, falls back to a single non-streamed yield.
    """
    system_prompt = build_system_prompt(
        target_model = target_model,
        task_type    = task_type,
        depth        = depth,
        exemplars    = exemplars,
        language     = language,
        chain        = chain,
    )
    user_message = f"Raw prompt to transform:\n\n{raw_prompt}"

    order = build_provider_order(_settings)
    streamable = [n for n in order if n in _STREAMERS]

    if not streamable:
        result, provider, _ = transform_prompt(
            raw_prompt, target_model, task_type, depth, exemplars, language, chain
        )
        yield result, provider
        return

    errors = []
    for name in streamable:
        try:
            acc = ""
            label = f"{name} ({_provider_model(name)})"
            for delta in _STREAMERS[name](system_prompt, user_message):
                acc += delta
                yield acc, label
            return
        except Exception as e:
            errors.append(f"{name}({_provider_model(name)}): {e}")
            logger.warning("Stream provider %s (%s) failed: %s — trying next.", name, _provider_model(name), e)

    raise RuntimeError("All streaming providers failed — " + " | ".join(errors))


def _route_model(model: str | None) -> tuple[str, str | None]:
    """Parse a model spec into (provider, model_name).

    Accepts ``None``/``"groq"``/``"cerebras"`` or a ``"provider/model"`` form
    such as ``"groq/llama-3.3-70b-versatile"``. Unknown providers default to
    Groq. Returns the explicit model name (or None to use the provider default).
    """
    if not model:
        return "groq", None
    spec = model.strip().lower()
    provider, _, name = spec.partition("/")
    if provider not in ("groq", "cerebras"):
        # No provider prefix — treat the whole thing as a provider keyword.
        return ("cerebras" if provider == "cerebras" else "groq"), None
    return provider, (name or None)


def call_llm(prompt: str, model: str = "groq", response_format: str = "text") -> str:
    """Unified helper used by scorer.py for LLM-as-a-Judge evaluations.

    Honors the requested ``model`` (provider and optional model name) and still
    falls back to the other provider on failure.
    """
    system = "You are a helpful assistant."
    if "json" in response_format:
        system += " You must respond in valid JSON format."

    provider, model_name = _route_model(model)
    primary, secondary = (
        (call_groq, call_cerebras) if provider == "groq" else (call_cerebras, call_groq)
    )

    try:
        res, _ = _retry(primary, system, prompt, model=model_name)
        return res
    except Exception as e:
        logger.warning("Primary provider (%s) failed: %s — trying fallback.", provider, e)
        res, _ = _retry(secondary, system, prompt)
        return res