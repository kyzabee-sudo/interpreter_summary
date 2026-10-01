# Interpreting Interpreter summarizer

A small local app that accepts an *Interpreter* journal PDF and asks the
[xAI Grok API](https://docs.x.ai) to draft a post in the style of
[Interpreting Interpreter](https://interpreterfoundation.org/interpreting-interpreter-on-abstracting-thought/).

The draft follows Kyler's format from early September 2026: Takeaway, Q&A,
Summary, and a video-script table. There is no Reflection section.

## What it produces

1. **Title** — `Interpreting Interpreter: [Punchy Title]`
2. **The Takeaway** — one or two sentences, including the concrete claim
3. **The Q&A** — three questions, each with an answer of a few sentences
4. **The Summary** — opens `In this article, [Full Name]…`, walks the argument
   in order, and uses bullets when the article is a list of people, parallels,
   or elements. Locators look like `[label] (link to "opening words"; page N)`
   and use **printed journal pages**. The section usually ends
   `As [Author] concludes (link to "…"; page N):` plus a longer verbatim block
   quote. Length scales with PDF page count and then caps (about 450–900 words
   for a 13–24 page article; a long element list may run higher, up to a hard
   max). After Grok drafts, locators and block quotes in the Summary and Q&A
   are checked against the PDF text: wrong pages are corrected when the phrase
   is unique, paraphrased quotes are repaired to the article wording when the
   passage is clear, and unverifiable locators or quotes are dropped.
5. **Video Script** — a table of about 10 rows pairing spoken narration with a
   short image cue, ending `and I'll see you next week.`

The built-in house style lives in
`src/interpreter_summary/style_assets/style_guide.md`. A matching Word
fixture is written to `samples/` when you generate samples. Word export follows
Kyler's template: bold section labels, bold-italic questions, summary bullets,
a plain closing quotation, and the video script as a three-column table
(`#`, `Text`, `Image`).

## Setup

Python 3.11+ and an [xAI API key](https://console.x.ai).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# put XAI_API_KEY in .env
interpreter-summary init-samples
```

The default model is `grok-4.6`, which supports PDF file attachments via the
xAI Files API. Override with `XAI_MODEL` if needed.

## Web app

```bash
interpreter-summary serve
```

Open http://127.0.0.1:8000, drop in a PDF, and download Markdown or Word.

## CLI

```bash
interpreter-summary summarize samples/sample_article.pdf -o summary.md --docx summary.docx
```

Optional flags:

- `--style path/to/style.docx` to replace the built-in house style
- `--notes "emphasize the linguistic argument"` for a one-off instruction

## Tests

```bash
pytest
```

Tests mock the Grok API. A live call needs `XAI_API_KEY` and will upload the
sample PDF to xAI, then delete it.

## Project layout

```
src/interpreter_summary/   # library, CLI, and web UI
samples/                   # generated sample PDF + style Word doc
tests/
```

Replace the generated sample PDF with a real *Interpreter* article when you
have one locally. Do not commit copyrighted journal PDFs unless you have
permission to distribute them.
