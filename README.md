# QuizWimg — quiz, with images

Turn any document — lecture slides, textbooks, scanned past exams — into a polished, offline, single-file HTML quiz. Built to be driven by an AI coding agent (Claude Code, Codex, and friends), with the parts LLMs get wrong handled by deterministic tooling.

> **Why another quiz generator?** Tools like NotebookLM generate decent text questions but can't crop figures out of your PDFs, and they misread documents that are mostly tables and diagrams. QuizWimg's whole point is the *images*: extract the actual figures from your source material and put them in the questions — the way real exams do.

## What you get

- **Single-file HTML quiz** — works offline, on your phone, no server, no account. Images are inlined as base64.
- **Real exam UX** — one question at a time, submit-to-reveal explanations, skip/bookmark, jump grid, category score breakdown, retry-wrong-only.
- **Figure extraction from PDFs** — pull embedded images and crop regions from rendered pages, so questions can show the exact chart/diagram/photo from your source.
- **Anti-leakage QA built in** — the builder *fails or warns* on the classic LLM tells: every answer in the same position, the correct choice suspiciously longer than decoys, markdown bold leaking `**answer**` into the page.
- **Agent-native** — ships as a skill/prompt for AI coding agents, with a strict JSON schema between "LLM writes questions" and "deterministic builder renders HTML".

## Status

🚧 Early days — extracted from a tool I built and use daily in med school. Generalizing it in public. Watch the repo if you want to follow along.

## Quick start

```bash
pip install "quizwimg[pdf] @ git+https://github.com/Gukozy/quizwimg"

# build the example quiz
quizwimg build --config examples/getting-started/quiz.json --out quiz.html
open quiz.html   # works offline, share the single file anywhere
```

Write your own `quiz.json` (or have your AI agent write it — that's the point):

```json
{
  "title": "My Quiz",
  "questions": [
    {
      "id": "q1",
      "category": "Topic A",
      "vignette": "Optional scenario or passage shown above the question.",
      "prompt": "The question itself?",
      "choices": ["First", "Second", "Third", "Fourth"],
      "correct": 1,
      "explanation": "Why the answer is right.",
      "image": "figures/fig1.png"
    }
  ]
}
```

UI language: `"lang": "en"` (default) or `"ko"`, with per-string overrides via `"strings": {...}` for any other language.

### Pull figures out of your PDFs

```bash
# embedded raster images (photos, scans), at original resolution
quizwimg extract embedded lecture.pdf --out-dir figures/

# render whole pages to PNG (for your agent to read tables/diagrams visually)
quizwimg extract pages lecture.pdf --out-dir pages/ --pages 12-15

# crop a chart/table region (PDF points); repeat --clip to stitch across a page break
quizwimg extract region lecture.pdf --clip 13:28,120,567,430 --out figures/fig1.png
```

Reference the cropped files from `quiz.json` — the builder inlines them as base64 so the output stays a single file.

## How it works

```
source docs (PDF/notes)
   │  read visually by your AI agent (tables & figures included)
   ▼
questions.json  ← LLM writes this, schema-validated
   │
   ▼
quizwimg build  ← deterministic: sanitize, QA checks, inline images
   │
   ▼
quiz.html  ← single file, offline, shareable
```

## License

MIT
