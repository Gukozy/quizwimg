#!/usr/bin/env python3
"""quizwimg builder — fill template.html with questions from a JSON config.

Usage:
    quizwimg build --config quiz.json --out quiz.html
    quizwimg build --config quiz.json --out quiz.html --lang ko

Config JSON schema:
{
  "title": "Page title",
  "subtitle": "Subtitle",                    // optional
  "footer": "Footer text",                   // optional
  "lang": "en",                              // optional: en | ko (default en)
  "strings": {"submit_btn": "Go!"},          // optional UI string overrides
  "questions": [
    {
      "id": "unique_id",
      "category": "Topic",                   // optional (defaults to localized "General")
      "vignette": "Scenario / passage",      // optional
      "prompt": "The question itself",
      "choices": ["choice 1", "choice 2"],   // 2 or more
      "correct": 0,                          // index into choices
      "explanation": "Why that answer is right",
      "image": "figure.png",                 // optional: path / http(s) / data URI
      "image_caption": "Figure 1. ...",      // optional
      "explanation_image": "answer.png"      // optional, shown inside the explanation
    }
  ]
}

Local image paths are resolved relative to the config file and inlined as
base64 data URIs, so the output HTML is a single self-contained file.
"""
from __future__ import annotations

import base64
import html
import json
import mimetypes
import re
import sys
from pathlib import Path

from quizwimg.i18n import resolve_strings

DEFAULT_TEMPLATE = Path(__file__).parent / "template.html"

_MD_PATTERNS = [
    (re.compile(r"\*\*([^*\n]+)\*\*"), r"\1"),
    (re.compile(r"__([^_\n]+)__"), r"\1"),
    (re.compile(r"(?<![\w*])\*([^*\n]+)\*(?!\w)"), r"\1"),
    (re.compile(r"(?<![\w_])_([^_\n]+)_(?!\w)"), r"\1"),
    (re.compile(r"`([^`\n]+)`"), r"\1"),
]


def _sanitize_md(s):
    """Strip inline markdown (bold/italic/code) so the template's escapeHTML
    doesn't render raw ** / __ / * markers as literal characters. A choice
    containing **answer** would otherwise leak the answer visually."""
    if not isinstance(s, str):
        return s
    for pat, repl in _MD_PATTERNS:
        s = pat.sub(repl, s)
    return s


def _sanitize_question(q):
    for k in ("category", "vignette", "prompt", "explanation", "image_caption"):
        if k in q:
            q[k] = _sanitize_md(q[k])
    if isinstance(q.get("choices"), list):
        q["choices"] = [_sanitize_md(c) for c in q["choices"]]
    return q


def _image_to_data_uri(value, config_dir):
    """File path → base64 data URI; http(s)/data URIs pass through unchanged.

    Inlining keeps the output a single HTML file that works offline, on
    phones, and when shared — no external asset dependencies."""
    if not value:
        return ""
    s = str(value).strip()
    if s.startswith(("data:", "http://", "https://")):
        return s
    p = Path(s).expanduser()
    if not p.is_absolute():
        p = (config_dir / p).resolve()
    if not p.exists():
        sys.stderr.write(f"[warn] image not found: {p}\n")
        return ""
    mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    try:
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    except OSError as exc:
        sys.stderr.write(f"[warn] image read failed ({p}): {exc}\n")
        return ""
    return f"data:{mime};base64,{b64}"


def _process_image(q, config_dir):
    for key in ("image", "explanation_image"):
        if q.get(key):
            q[key] = _image_to_data_uri(q[key], config_dir)
            if not q[key]:
                # conversion failed → drop the field so the template treats it as absent
                q.pop(key, None)


def _check_choice_balance(q, idx):
    """Warn (stderr) if the correct choice is markedly longer than decoys —
    a known giveaway where the model pads the answer with rationale text."""
    choices = q.get("choices") or []
    correct_idx = q.get("correct")
    if not choices or not isinstance(correct_idx, int):
        return
    if not (0 <= correct_idx < len(choices)):
        return
    lens = [len(str(c)) for c in choices]
    others = [l for i, l in enumerate(lens) if i != correct_idx]
    if not others:
        return
    avg_other = sum(others) / len(others)
    correct_len = lens[correct_idx]
    if avg_other > 0 and correct_len > avg_other * 1.5 and (correct_len - avg_other) > 12:
        sys.stderr.write(
            f"[warn] question[{idx}] id={q.get('id')}: "
            f"correct choice is {correct_len}ch vs other avg {avg_other:.0f}ch — "
            f"possible answer leakage via length imbalance\n"
        )


def _check_answer_distribution(qs):
    counts = {}
    max_choices = 0
    for q in qs:
        choices = q.get("choices") or []
        max_choices = max(max_choices, len(choices))
        correct_idx = q.get("correct")
        if isinstance(correct_idx, int):
            counts[correct_idx] = counts.get(correct_idx, 0) + 1

    total = sum(counts.values())
    active_positions = [idx for idx, count in counts.items() if count]
    all_same = total > 0 and len(active_positions) == 1
    all_first = total > 0 and counts.get(0, 0) == total
    dist = ", ".join(f"{idx + 1}={counts.get(idx, 0)}" for idx in range(max_choices))
    print(
        f"answer_distribution: {dist}; "
        f"all_same_correct_index={all_same}; all_first_answer={all_first}"
    )

    if all_same and total >= 4:
        only_idx = active_positions[0]
        sys.exit(
            "answer distribution QA failed: "
            f"all {total} questions use answer position {only_idx + 1}"
        )
    if all_same:
        sys.stderr.write(
            f"[warn] only {total} question(s), but all correct answers use "
            f"position {active_positions[0] + 1}; review manually\n"
        )


def _check_unique_ids(qs):
    seen = {}
    for i, q in enumerate(qs):
        qid = q.get("id")
        if qid in seen:
            sys.exit(f"question[{i}] duplicate id: {qid!r} (also used by question[{seen[qid]}])")
        seen[qid] = i


def _json_for_script(obj):
    # "</" would terminate the surrounding <script> tag if a string contains it
    return json.dumps(obj, ensure_ascii=False, indent=2).replace("</", "<\\/")


def build(config_path, out_path, template_path=None, lang=None):
    config_path = Path(config_path)
    out_path = Path(out_path)
    template_path = Path(template_path) if template_path else DEFAULT_TEMPLATE

    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    tmpl = template_path.read_text(encoding="utf-8")
    config_dir = config_path.parent.resolve()

    missing = {"title", "questions"} - cfg.keys()
    if missing:
        sys.exit(f"config missing keys: {missing}")

    resolved_lang = lang or cfg.get("lang") or "en"
    strings = resolve_strings(resolved_lang, cfg.get("strings"))

    qs = cfg["questions"]
    if not isinstance(qs, list) or not qs:
        sys.exit("config.questions must be a non-empty list")

    image_count = 0
    for i, q in enumerate(qs):
        for k in ("id", "prompt", "choices", "correct", "explanation"):
            if k not in q:
                sys.exit(f"question[{i}] missing key: {k}")
        if not isinstance(q["choices"], list) or len(q["choices"]) < 2:
            sys.exit(f"question[{i}].choices must be list of ≥2")
        if not isinstance(q["correct"], int) or not (0 <= q["correct"] < len(q["choices"])):
            sys.exit(f"question[{i}].correct must be valid index")
        if not q.get("category"):
            q["category"] = strings["default_category"]
        _sanitize_question(q)
        _process_image(q, config_dir)
        if q.get("image"):
            image_count += 1
        _check_choice_balance(q, i)
    _check_unique_ids(qs)
    _check_answer_distribution(qs)

    out = (
        tmpl.replace("__LANG__", html.escape(resolved_lang, quote=True))
        .replace("__TITLE__", html.escape(str(cfg["title"])))
        .replace("__SUBTITLE__", html.escape(str(cfg.get("subtitle", ""))))
        .replace("__FOOTER__", html.escape(str(cfg.get("footer", ""))))
        .replace("__STRINGS_JSON__", _json_for_script(strings))
        .replace("__QUESTIONS_JSON__", _json_for_script(qs))
    )
    out_path.write_text(out, encoding="utf-8")
    print(
        f"built: {out_path}  ({len(qs)} questions, {image_count} with image, "
        f"lang={resolved_lang}, {len(out)} bytes)"
    )


def main(args=None):
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    ap.add_argument("--lang", default=None, help="UI language (en, ko); overrides config")
    ns = ap.parse_args(args)

    if not ns.config.exists():
        sys.exit(f"config not found: {ns.config}")
    if not ns.template.exists():
        sys.exit(f"template not found: {ns.template}")

    build(ns.config, ns.out, ns.template, lang=ns.lang)


if __name__ == "__main__":
    main()
