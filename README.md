# Interpreting Interpreter summarizer

A small local app that accepts an *Interpreter* journal PDF and asks the
[xAI Grok API](https://docs.x.ai) to draft a post in the style of
[Interpreting Interpreter](https://interpreterfoundation.org/interpreting-interpreter-on-abstracting-thought/).

The draft follows Kyler's format from early September 2026: Takeaway, Q&A,
Summary, and a video-script table. There is no Reflection section.

## What it produces

1. **Title** — `Interpreting Interpreter: [Punchy Title]`
2. **The Takeaway** — one or two sentences, about 20–35 words, in Kyler’s words rather than a rewrite of the abstract
3. **The Q&A** — three questions: the main claim, how it is supported, and one implication. Each answer is about 35–70 words
4. **The Summary** — opens `In this article, [Full Name]…`, walks the argument
   in order, and uses bullets when the article is a list of people, parallels,
   or elements. Locators are woven into the sentence
   (`After [briefly summarizing] (link to "opening words"; page N) the chapter`)
   and use **printed journal pages**. The section ends
   `As [Author] concludes (link to "…"; page N):` plus a verbatim block quote
   of about 60–125 words. Summary length scales with the article: about
   200–330 words before the quote for a short article, up to about 450–750
   for a long one. A close reading of one passage may go shorter (Squire,
   Bowen); a list of many parallels may go longer (Ahlstrom). After
   Grok drafts, locators and block quotes in the Summary and Q&A
   are checked against the PDF text: wrong pages are corrected when the phrase
   is unique, paraphrased quotes are repaired to the article wording when the
   passage is clear, and unverifiable locators or quotes are dropped.
5. **Video Script** — a table of about 10 rows pairing spoken narration with a
   short image cue, ending `and I'll see you next time.`

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
xAI Files API. Override with `XAI_MODEL` if needed. The client streams the
response so a long reasoning model is not cut off by one silent wait.
`REQUEST_TIMEOUT_SECONDS` (default 1200) is the gap allowed between streamed
chunks. The PDF stays attached; xAI may search that file on its own, and there
is no documented switch to turn those searches off without dropping the file.

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
