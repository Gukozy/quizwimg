"""UI string locales for the quiz template.

The builder injects the resolved string table into the template as JSON
(`__STRINGS_JSON__`). Configs may override individual keys via a top-level
``"strings"`` object, so any language (or wording) is reachable without
shipping a locale here.
"""
from __future__ import annotations

import sys

LOCALES = {
    "en": {
        "default_category": "General",
        "progress": "{answered} / {total} answered",
        "score": "Score {score}",
        "results_btn": "Results",
        "sections_label": "Sections",
        "all_label": "All",
        "jump_label": "Go to question",
        "prev_btn": "← Prev",
        "next_btn": "Next →",
        "see_results_btn": "See results →",
        "submit_btn": "Submit",
        "skip_btn": "Skip →",
        "bookmark_btn": "🔖 Mark",
        "bookmarked_btn": "🔖 Marked",
        "bookmark_hint": "Mark this question for review",
        "verdict_correct": "✅ Correct!",
        "verdict_wrong": "❌ Incorrect",
        "answer_line": "Answer: {num}. {text}",
        "image_alt": "Question figure",
        "summary_title": "🎯 Results",
        "msg_unanswered": "⚠️ {count} unanswered — skipped questions don't count toward your score.",
        "msg_perfect": "🏆 Perfect!",
        "msg_excellent": "🎯 Excellent — exam ready.",
        "msg_good": "👍 Good. Review the explanations you missed.",
        "msg_fair": "📚 Fair. Revisit the key concepts.",
        "msg_review": "⚠️ Review the fundamentals.",
        "breakdown_title": "Score by category",
        "breakdown_unanswered": "({count} unanswered)",
        "wrong_section_title": "❌ Wrong answers",
        "marked_section_title": "🔖 Marked questions",
        "tag_wrong": "wrong",
        "tag_unanswered": "unanswered",
        "retry_wrong_btn": "Retry wrong only",
        "retry_marked_btn": "Retry marked only",
        "retry_all_btn": "Retry all (reshuffle)",
        "retry_wrong_label": "Retry: wrong",
        "retry_marked_label": "Retry: marked",
    },
    "ko": {
        "default_category": "일반",
        "progress": "{answered} / {total} 완료",
        "score": "정답 {score}",
        "results_btn": "결과",
        "sections_label": "섹션",
        "all_label": "전체",
        "jump_label": "문제 이동",
        "prev_btn": "← 이전",
        "next_btn": "다음 문제 →",
        "see_results_btn": "결과 보기 →",
        "submit_btn": "제출",
        "skip_btn": "건너뛰기 →",
        "bookmark_btn": "🔖 체크",
        "bookmarked_btn": "🔖 체크됨",
        "bookmark_hint": "다시 봐야 할 문제로 표시",
        "verdict_correct": "✅ 정답!",
        "verdict_wrong": "❌ 오답",
        "answer_line": "정답: {num}번 · {text}",
        "image_alt": "문항 이미지",
        "summary_title": "🎯 결과",
        "msg_unanswered": "⚠️ 미응답 {count}문항 있음 — 건너뛴 문제는 정답 수에 반영되지 않음.",
        "msg_perfect": "🏆 완벽!",
        "msg_excellent": "🎯 매우 우수. 시험 준비 충분.",
        "msg_good": "👍 양호. 틀린 문제 해설 복습 권장.",
        "msg_fair": "📚 보통. 핵심 개념 재학습 필요.",
        "msg_review": "⚠️ 기본 개념 재학습 필요.",
        "breakdown_title": "카테고리별 정답률",
        "breakdown_unanswered": "({count}문 미응답)",
        "wrong_section_title": "❌ 틀린 문제",
        "marked_section_title": "🔖 체크한 문제",
        "tag_wrong": "오답",
        "tag_unanswered": "미응답",
        "retry_wrong_btn": "오답만 다시 풀기",
        "retry_marked_btn": "체크 문제만 다시 풀기",
        "retry_all_btn": "전체 다시 풀기 (재셔플)",
        "retry_wrong_label": "오답 재시도",
        "retry_marked_label": "체크 재시도",
    },
}


def resolve_strings(lang, overrides=None):
    """Return the string table for ``lang`` with config overrides applied."""
    if lang not in LOCALES:
        sys.exit(f"unsupported lang: {lang!r} (available: {', '.join(sorted(LOCALES))})")
    strings = dict(LOCALES[lang])
    for key, value in (overrides or {}).items():
        if key not in strings:
            sys.stderr.write(f"[warn] unknown UI string override ignored: {key}\n")
            continue
        strings[key] = str(value)
    return strings
