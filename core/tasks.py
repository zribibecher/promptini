# -*- coding: utf-8 -*-
"""Canonical task-type classifier (multilingual + Tunisian Derja/Arabizi).

Single implementation used by the live pipeline (rag.py) and the corpus builder
(fetch_corpus.py). English keyword behavior is unchanged (locked by tests);
French, Arabic (script) and Derja/Arabizi (Latin, franco-arabe) keywords are
added so Tunisian users get correctly-classified prompts in any register.

Pure and dependency-free (stdlib only) so it stays trivially testable.
"""

from __future__ import annotations

import re
import unicodedata

from .constants import DEFAULT_TASK_TYPE

# ── Light normalization for matching ─────────────────────────────────────────
_ARABIZI_MAP = {"3": "", "7": "", "9": "q", "2": "", "5": "kh", "8": "gh", "6": "t"}


def normalize_arabizi(text: str) -> str:
    """Light normalization of Latin-script Derja (Arabizi).

    Lowercases, collapses elongations (``loool`` -> ``lool``) and maps common
    Arabizi digit-letters so franco-arabe still matches Latin keywords. Heuristic
    aid, not a full transliteration.
    """
    t = text.lower()
    t = re.sub(r"(.)\1{2,}", r"\1\1", t)
    for digit, repl in _ARABIZI_MAP.items():
        t = t.replace(digit, repl)
    return t


def _normalize(text: str) -> str:
    """Lowercase + strip Arabic diacritics/tatweel so keyword matching is robust."""
    t = unicodedata.normalize("NFKD", text)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t.lower().replace("ـ", "")  # tatweel


def detect_task_type(raw_prompt: str) -> str:
    """Classify a prompt into a known task type via keyword rules.

    Order matters: earlier branches win. Keywords span English, French, Arabic
    and Derja/Arabizi. Both the raw-normalized text and an Arabizi-normalized copy
    are checked, so ``salla7`` / ``sala7`` style spellings still match.
    Returns ``"general"`` as fallback.
    """
    p = _normalize(raw_prompt)
    pa = normalize_arabizi(p)   # digit-folded copy for franco-arabe

    def has(words):
        return any(w in p or w in pa for w in words)

    if has([
        # en
        "extract", "pull out", "get fields", "fetch fields", "retrieve fields",
        "parse json", "parse xml", "pull the", "grab the fields",
        # fr
        "extraire", "extrais", "extraction",
        # ar
        "استخرج", "استخراج", "جيب لي", "هات لي", "استخلص",
        # derja/arabizi
        "estakhrej", "estakhrejli", "5rejli", "kharrejli", "jibli", "hatli",
    ]):
        return "extraction"

    if has([
        # en
        "system prompt", "persona", "act as", "you are a",
        # fr
        "tu es un", "comporte-toi", "assistant qui", "prompt systeme",
        # ar
        "برومبت", "شخصية", "تصرف ك", "انت مساعد",
        # derja/arabizi
        "chatbot", "bot bech",
    ]) and not has([
        "agent", "agentic", "workflow", "tool use", "loop", "autonomous",
        "ايجنت", "وركفلو",
    ]):
        return "system_prompt"

    if has([
        # en
        "build an agent", "make an agent", "create an agent", "design an agent",
        "agentic", "agent workflow", "tool use", "autonomous", "reasoning loop",
        "react pattern", "agent that", "multi-step agent",
        # fr
        "agent qui", "agent autonome", "flux agent",
        # ar
        "اعمل ايجنت", "اصنع ايجنت", "صمم ايجنت", "وركفلو",
        # derja/arabizi
        "na3mel agent", "a3mel agent", "3mel agent", "3malli agent", "agent bech",
        "agent mte3",
    ]):
        return "agentic"

    if has([
        # en
        "review", "audit", "evaluate", "assess", "critique", "check for bugs",
        "check for issues", "check for errors", "monitor", "scan for", "look for issues",
        # fr
        "revise", "reviser", "revue", "audite", "verifie", "verifier", "evalue",
        # ar
        "راجع", "مراجعة", "دقق", "افحص", "قيم", "تحقق من",
        # derja/arabizi
        "raja3", "raje3", "raja3li", "raj3li", "9ayem",
    ]) and not has([
        "fix", "debug", "corrige", "صلح", "صحح", "salla7", "sale7", "asle7",
    ]):
        return "code_review"

    if has([
        # en
        "fix", "debug", "error", "bug", "issue", "broken", "crash", "exception",
        "not working", "fails",
        # fr
        "corrige", "corriger", "debogue", "deboguer", "erreur", "plante", "ne marche pas",
        # ar
        "صلح", "صحح", "خطأ", "باڨ", "ما يخدمش", "تعطل", "ما يمشيش", "علاش ما",
        # derja/arabizi
        "salla7", "sale7", "asle7", "salla7li", "ma yekhdemch", "ma yemchich",
        "ma ykhdemch", "planti", "3andi bug", "3andi erreur",
    ]) and not has([
        "review", "monitor", "check for", "agent", "scan", "راجع", "audite",
        "raja3", "raje3",
    ]):
        return "debugging"

    if has([
        # en
        "translate", "translation",
        # fr
        "traduire", "traduis", "traduction",
        # ar
        "ترجم", "ترجمة", "ترجملي",
        # derja/arabizi
        "7awel", "7awil", "7awelli", "7awilli", "tarjem", "tarjemli", "traji",
    ]):
        return "translation"

    if has([
        # en
        "localize", "localise", "localization", "localisation", "adapt for", "adapt this for",
        # fr
        "localiser",
        # ar
        "توطين", "اقلمة", "تعريب",
        # derja/arabizi
        "2aqlem", "aqlem", "waten",
    ]):
        return "localization"

    if has([
        # en
        "clean the data", "clean up the data", "data cleaning", "deduplicate",
        "drop duplicates", "remove duplicates", "duplicates", "missing values", "impute",
        "normalize the data",
        # fr
        "nettoyer les donnees", "nettoyage des donnees", "nettoie les donnees",
        "supprime les doublons", "doublons", "valeurs manquantes",
        # ar
        "تنظيف البيانات", "نظف البيانات", "احذف التكرارات", "القيم المفقودة",
        # derja/arabizi
        "naddaf el data", "naddaf data", "na77i el data", "na77i el duplicates",
        "naddaf el donnees",
    ]):
        return "data_cleaning"

    if has([
        # en
        "refactor", "clean up", "improve", "optimize", "restructure", "simplify",
        "rewrite", "dry", "boilerplate", "modularize", "decouple",
        # fr
        "refactorise", "refactoriser", "nettoie", "ameliore", "ameliorer", "optimise",
        "simplifie", "reecris", "reecrire",
        # ar
        "نظف", "حسن", "بسط", "اعد كتابة", "اعادة هيكلة", "ريفاكتور",
        # derja/arabizi
        "na9es el complexite", "naddaf el code", "bassat", "2a99el", "na9esli",
        "sa77a7 el code",
    ]):
        return "refactoring"

    # Summarization before documentation (the word "document" would shadow
    # "summarize this document").
    if has([
        # en
        "summarize", "summary", "tldr", "brief", "overview", "recap", "condense",
        "main points", "key takeaways", "gist", "abstract",
        # fr
        "resume", "resumer", "synthese", "synthetise", "en bref",
        # ar
        "لخص", "تلخيص", "اختصر", "ملخص", "باختصار", "اهم النقاط",
        # derja/arabizi
        "lakhes", "lkhes", "lakhesli", "lkhesli", "rakhesli", "2ossor", "2osorli",
    ]):
        return "summarization"

    if has([
        # en
        "document", "docs", "docstring", "readme", "comment", "explain this code",
        # fr
        "documente", "documentation", "commente", "explique le code",
        # ar
        "وثق", "توثيق", "اشرح الكود", "تعليقات",
        # derja/arabizi
        "fassar", "fasser", "fassarli", "echrah el code", "echrahli", "chrahli el code",
        "commenti",
    ]):
        return "documentation"

    if has([
        # en
        "analyze", "analysis", "compare", "research", "investigate", "study", "examine",
        # fr
        "analyse", "analyser", "comparer", "etudie", "etudier",
        # ar
        "صلل", "تحليل", "قارن", "ادرس", "ابحث",
        # derja/arabizi
        "7alel", "7allel", "7allili", "9aren", "9arenli", "dros",
    ]):
        return "analysis"

    if has([
        # en
        "sql", "sql query", "select from", "select * from", "joins", "jointure",
        # fr
        "requete sql", "requete",
        # ar
        "قاعدة بيانات", "استعلام",
        # derja/arabizi
        "sql query", "base de donnees",
    ]):
        return "sql"

    if has([
        # en
        "marketing copy", "ad copy", "advert", "advertisement", "slogan", "tagline",
        "landing page copy", "call to action", "product description",
        # fr
        "publicite", "annonce publicitaire", "texte marketing",
        # ar
        "وصف منتج", "اعلان", "شعار", "نص تسويقي",
        # derja/arabizi
        "chi3ar", "e3lan", "publicite mte3",
    ]):
        return "marketing_copy"

    if has([
        # en
        "story", "essay", "blog post", "article", "creative", "poem", "write about",
        "draft a", "composing", "narrative", "script a",
        # fr  (note: bare "ecris/ecrire" removed — too broad, collided with code)
        "redige", "rediger", "redaction", "essai", "histoire", "poeme", "article de blog",
        # ar
        "اكتب مقال", "قصة", "مقال", "انشئ نص", "تدوينة", "قصيدة",
        # derja/arabizi
        "ekteb maqal", "kteb maqal", "ekteb article", "9essa",
    ]):
        return "writing"

    if has([
        # en
        "write", "create", "build", "implement", "generate", "code", "function",
        "class", "script", "program", "develop",
        # fr
        "cree", "creer", "genere", "generer", "fonction", "classe", "programme",
        "implemente", "implementer", "developpe", "developper",
        # ar
        "اكتب كود", "اعمل فنكشن", "برمج", "انشئ", "ولد", "سكريبت", "دالة", "كلاس",
        # derja/arabizi
        "3malli", "3melli", "a3melli", "aktebli code", "ekteb code", "kteb fonction",
        "na3mel fonction", "code python",
    ]):
        return "code_generation"

    return DEFAULT_TASK_TYPE
