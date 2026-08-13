# Interpreting Interpreter summarizer

A small local app that accepts an *Interpreter* journal PDF and asks the
[xAI Grok API](https://docs.x.ai) to draft a summary in the style of
[Interpreting Interpreter](https://interpreterfoundation.org/interpreting-interpreter-on-abstracting-thought/).

The written summary is the product. Video scripts that sometimes travel with
the Word house-style document are ignored.

## What it produces

1. **Title** — `Interpreting Interpreter: [Punchy Title]`
2. **Boilerplate intro** naming the article, author, and journal volume
3. **The Takeaway** — one or two thesis sentences, including the surprising detail
4. **The Summary** — an accessible walk through the argument, with locators
   of the form `[label] (link to "opening words"; page N)` using **printed
   journal pages**. Length scales with PDF page count and then caps (about
   500–650 words for a ~26-page article). After Grok drafts, locators and
   block quotes are checked against the PDF text: wrong pages are corrected
   when the phrase is unique, paraphrased quotes are repaired to the article
   wording when the passage is clear, and unverifiable locators or quotes are
   dropped.
5. **The Reflection** — first-person closing thoughts, usually with an honest reservation

The built-in house style lives in
`src/interpreter_summary/style_assets/style_guide.md`. A matching Word
document, including a sample video script that the app strips out, is written
to `samples/` when you generate fixtures.

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
