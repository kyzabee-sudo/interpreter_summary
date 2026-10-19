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
passage is clear, and unverifiable locators or quotes are dropped. A second
pass then checks typos, verbatim quotations, journal-page locators, counts,
and (unless `--no-verify`) claims against the article. See [Accuracy check](#accuracy-check).
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
- `--no-verify` to skip the model accuracy review and the revision pass. The offline checks still run.

## Accuracy check

Before a draft is saved, the app checks it and writes a short **Check report**
next to the output (`summary.check.md` when the post is `summary.md`). The
report is also printed on stderr. It is not inserted into the Markdown post
or the Word file.

Two layers:

1. **Offline checks** (no API call). For every locator, the quoted link phrase
   must appear on the stated **journal** page. Hyphenation, line breaks, and
   curly quotes are ignored when matching. A unique wrong page is corrected;
   the report names the journal page where the phrase actually is. The offset
   is derived from the PDF (journal page = PDF viewer page + offset). Direct
   quotations must appear verbatim; a near miss such as “mislocate” for
   “mislocates” is flagged with the article’s wording and page. The pass also
   flags placeholder junk (`XXXXX`, empty brackets, `TODO`), double spaces,
   leading or trailing spaces, doubled words, unbalanced quotes or parentheses,
   hyphens in numeric ranges, a missing final period, straight apostrophes,
   a dropped initial (`from . Robb Smith`), Takeaway length (20–35 words),
   Summary length on the existing page-scaled band (**not** a flat 250–400),
   a video table that is not about 10 complete rows, and a last row that does
   not end `and I'll see you next time.`
2. **One model review**, using the same xAI client and model. The article is
   sent as text with journal page markers. The PDF is not attached again, so
   xAI does not search the file a second time, and the call uses reasoning
   effort `low` (the draft call stays on the model’s default). The review
   looks for wrong attributions, hedging that is stronger or weaker than the
   author’s, quote and verse errors, counts and names, Q&A answers that
   contradict the article, script lines that disagree with the draft, and
   leftover typos. Findings are structured: location, problem, a quotation
   from the article with its journal page, and a suggested fix.

If either layer finds something to fix, the app makes **one** revision call
under the same cheap rules (text only, low reasoning) and then re-runs the
offline checks. The revision is told not to invent claims. Whatever is still
unresolved stays in the Check report for Kyler. `--no-verify` skips both
model calls.

Summary length follows the bands already in the app (about 200–330 words
before the closing quote for a short article, up to about 450–750 for a long
one). The count excludes locator parentheticals `(link to "…"; page N)` and
the bracketed labels in front of them. That counting rule is unchanged.

**Added cost.** At the published grok-4.6 rates ($2 per million input tokens
and $6 per million output, below 200k prompt tokens), a typical article plus
the draft is a few tens of thousands of tokens. The review is usually on the
order of **$0.05–$0.20**. A revision, only when something needs fixing, is
about the same again, so a run that rewrites once is about **$0.10–$0.40**
on top of the draft. The draft call is unchanged and is still the larger
share, because it attaches the PDF and uses default (high) reasoning. The
article extract is capped so the check stays under the doubled long-context
rate.

**Limits.** The offline locator check can confirm that a phrase is on the
stated page; it cannot tell that a different phrase on another page is the
one that supports the claim. Hedging and attribution are model judgments, and
they are not reviewed a second time after the revision. A badly altered quote
can be flagged without a usable article excerpt. Justified departures from
the Summary band stay a heads-up rather than a forced rewrite.

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

Future work, parked and not implemented: [Instagram reel pipeline plan](docs/reel-pipeline-plan.md).
