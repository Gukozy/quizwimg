import base64
import json
from pathlib import Path

import pytest

from quizwimg.builder import DEFAULT_TEMPLATE, build

# 1x1 red pixel
PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

TEMPLATE_STUB = (
    "__LANG__\n__TITLE__\n__SUBTITLE__\n__FOOTER__\n"
    "STRINGS=__STRINGS_JSON__\nQUESTIONS=__QUESTIONS_JSON__"
)


def _questions_json(html: str) -> str:
    return html.split("QUESTIONS=", 1)[1]


def _write_template(tmp_path: Path) -> Path:
    template = tmp_path / "template.html"
    template.write_text(TEMPLATE_STUB, encoding="utf-8")
    return template


def _question(idx: int, correct: int, **overrides) -> dict:
    q = {
        "id": f"q{idx}",
        "category": "QA",
        "vignette": f"case {idx}",
        "prompt": "best answer?",
        "choices": ["a", "b", "c", "d", "e"],
        "correct": correct,
        "explanation": "because",
    }
    q.update(overrides)
    return q


def _write_config(tmp_path: Path, questions: list, **cfg_overrides) -> Path:
    cfg = {"title": "Quiz", "subtitle": "QA", "questions": questions}
    cfg.update(cfg_overrides)
    config = tmp_path / "quiz.json"
    config.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    return config


def test_build_prints_answer_distribution(tmp_path, capsys):
    questions = [_question(i, c) for i, c in enumerate([0, 1, 2, 3, 4], start=1)]
    config = _write_config(tmp_path, questions)
    out = tmp_path / "quiz.html"

    build(config, out, _write_template(tmp_path))

    stdout = capsys.readouterr().out
    assert "answer_distribution: 1=1, 2=1, 3=1, 4=1, 5=1" in stdout
    assert "all_same_correct_index=False" in stdout
    assert "all_first_answer=False" in stdout
    assert out.exists()


def test_build_fails_when_all_answers_use_same_position(tmp_path, capsys):
    questions = [_question(i, 1) for i in range(1, 5)]
    config = _write_config(tmp_path, questions)
    out = tmp_path / "quiz.html"

    with pytest.raises(SystemExit) as excinfo:
        build(config, out, _write_template(tmp_path))

    stdout = capsys.readouterr().out
    assert "all_same_correct_index=True" in stdout
    assert "all_first_answer=False" in stdout
    assert "answer distribution QA failed" in str(excinfo.value)
    assert not out.exists()


def test_markdown_stripped_from_choices_and_text(tmp_path):
    q = _question(
        1,
        0,
        choices=["**bold answer**", "plain", "`code`", "_ital_"],
        explanation="see **this**",
    )
    config = _write_config(tmp_path, [q, _question(2, 2)])
    out = tmp_path / "quiz.html"

    build(config, out, _write_template(tmp_path))

    html = out.read_text(encoding="utf-8")
    assert "**" not in html
    assert "bold answer" in html
    assert "`code`" not in html


def test_choice_length_imbalance_warns(tmp_path, capsys):
    q = _question(
        1,
        0,
        choices=["the correct one, padded with a long rationale tail", "a", "b", "c"],
    )
    config = _write_config(tmp_path, [q, _question(2, 3)])

    build(config, tmp_path / "quiz.html", _write_template(tmp_path))

    stderr = capsys.readouterr().err
    assert "possible answer leakage via length imbalance" in stderr


def test_duplicate_question_ids_fail(tmp_path):
    questions = [_question(1, 0), _question(1, 2)]
    config = _write_config(tmp_path, questions)

    with pytest.raises(SystemExit) as excinfo:
        build(config, tmp_path / "quiz.html", _write_template(tmp_path))

    assert "duplicate id" in str(excinfo.value)


def test_local_image_inlined_as_data_uri(tmp_path):
    (tmp_path / "fig.png").write_bytes(PNG_1PX)
    q = _question(1, 0, image="fig.png", explanation_image="fig.png")
    config = _write_config(tmp_path, [q, _question(2, 1)])
    out = tmp_path / "quiz.html"

    build(config, out, _write_template(tmp_path))

    html = out.read_text(encoding="utf-8")
    assert html.count("data:image/png;base64,") >= 2


def test_missing_image_warns_and_drops_field(tmp_path, capsys):
    q = _question(1, 0, image="nope.png")
    config = _write_config(tmp_path, [q, _question(2, 1)])
    out = tmp_path / "quiz.html"

    build(config, out, _write_template(tmp_path))

    assert "image not found" in capsys.readouterr().err
    assert '"image"' not in out.read_text(encoding="utf-8")


def test_vignette_and_category_are_optional(tmp_path):
    bare = {
        "id": "bare",
        "prompt": "2 + 2?",
        "choices": ["3", "4"],
        "correct": 1,
        "explanation": "arithmetic",
    }
    config = _write_config(tmp_path, [bare, _question(2, 0)])
    out = tmp_path / "quiz.html"

    build(config, out, _write_template(tmp_path))

    questions = json.loads(_questions_json(out.read_text(encoding="utf-8")))
    assert questions[0]["category"] == "General"  # localized default filled in


def test_english_strings_by_default(tmp_path):
    config = _write_config(tmp_path, [_question(1, 0), _question(2, 1)])
    out = tmp_path / "quiz.html"

    build(config, out, _write_template(tmp_path))

    html = out.read_text(encoding="utf-8")
    assert html.startswith("en\n")
    assert '"submit_btn": "Submit"' in html


def test_korean_locale_via_config(tmp_path):
    config = _write_config(tmp_path, [_question(1, 0), _question(2, 1)], lang="ko")
    out = tmp_path / "quiz.html"

    build(config, out, _write_template(tmp_path))

    html = out.read_text(encoding="utf-8")
    assert html.startswith("ko\n")
    assert '"submit_btn": "제출"' in html


def test_lang_argument_overrides_config(tmp_path):
    config = _write_config(tmp_path, [_question(1, 0), _question(2, 1)], lang="ko")
    out = tmp_path / "quiz.html"

    build(config, out, _write_template(tmp_path), lang="en")

    assert '"submit_btn": "Submit"' in out.read_text(encoding="utf-8")


def test_string_overrides_applied_and_unknown_warned(tmp_path, capsys):
    config = _write_config(
        tmp_path,
        [_question(1, 0), _question(2, 1)],
        strings={"submit_btn": "Lock it in", "not_a_key": "x"},
    )
    out = tmp_path / "quiz.html"

    build(config, out, _write_template(tmp_path))

    assert '"submit_btn": "Lock it in"' in out.read_text(encoding="utf-8")
    assert "unknown UI string override" in capsys.readouterr().err


def test_script_breakout_is_escaped(tmp_path):
    q = _question(1, 0, explanation="tricky </script><script>alert(1)</script>")
    config = _write_config(tmp_path, [q, _question(2, 1)])
    out = tmp_path / "quiz.html"

    build(config, out, _write_template(tmp_path))

    questions_json = _questions_json(out.read_text(encoding="utf-8"))
    assert "</script" not in questions_json
    assert "<\\/script" in questions_json


def test_default_template_builds_complete_html(tmp_path):
    config = _write_config(
        tmp_path,
        [_question(1, 0), _question(2, 3)],
        title="A & B <Quiz>",
        footer="made with quizwimg",
    )
    out = tmp_path / "quiz.html"

    build(config, out, DEFAULT_TEMPLATE)

    html = out.read_text(encoding="utf-8")
    for token in ("__TITLE__", "__SUBTITLE__", "__FOOTER__", "__LANG__",
                  "__QUESTIONS_JSON__", "__STRINGS_JSON__"):
        assert token not in html
    assert "A &amp; B &lt;Quiz&gt;" in html  # title is HTML-escaped
    assert "made with quizwimg" in html
