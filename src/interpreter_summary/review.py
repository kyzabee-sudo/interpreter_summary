"""One cheap model review of a draft, and at most one revision.

The article is sent as text with journal page markers. The PDF is not
attached, so xAI does not search that file again. Both calls use reasoning
effort low. The draft call itself is unchanged and still uses the default
effort.
"""

from __future__ import annotations

import json
import re

from interpreter_summary.checks import Finding
from interpreter_summary.export import strip_preamble

REVIEW_REASONING_EFFORT = "low"

REVIEW_SYSTEM_PROMPT = """\
You are checking a draft Interpreting Interpreter post against the article it \
summarizes. You do not rewrite the post in this step. Return only JSON.

Find real mismatches. Do not invent a problem to look thorough. If the draft \
is faithful, return {"findings": []}.

Check all of these:
- Locators. A link phrase can sit on the stated journal page and still point \
at the wrong passage. The bracketed claim must be supported by that phrase. \
If the support is a different phrase on another journal page, say so.
- Attributions. Who said it, and of which model or structure. If the article \
says it of the five-part chiasm, the draft must not say it of Reynolds’s \
model, and must not say the author said it of both.
- Named people. If the article names one scholar, the draft and the video \
script must not say “some scholars.”
- Hedging. The draft must not be more certain or less certain than the author. \
“May extend… and possibly beyond” must not become “doesn’t appear to be \
repeated,” and a direct claim must not be softened into a hedge.
- Quotations. Verbatim, including verb endings (mislocates, not mislocate). \
The quote must be attributed to the sentence’s actual subject.
- Counts, names, and verse ranges.
- Q&A answers that contradict the article.
- Video-script narration that contradicts the article or the rest of the draft.
- Typos and grammar the draft still has, including a dropped initial \
(“from . Robb Smith”), an article glued to a possessive (“sees the Nephi’s”), \
and a plural or verb that does not agree (“appendices weigh” when the article \
has one appendix).

Each finding must quote the article. Use the journal page printed in the \
[Page N] markers, never the PDF viewer index. If you cannot quote the article, \
do not file the finding.

Return at most 12 findings, the clearest ones only. JSON shape:

{"findings": [
  {
    "location": "The Q&A, question 2",
    "problem": "The answer says the pattern \\"doesn't appear to be repeated.\\"",
    "evidence": "may extend through the rest of 1 Nephi and possibly beyond",
    "page": 155,
    "suggested_fix": "Keep the author's may and possibly. Do not say the pattern is absent."
  }
]}
"""

REVISION_SYSTEM_PROMPT = """\
You are revising an Interpreting Interpreter draft so it matches the article. \
Output only the revised post. The first characters are the markdown title. \
No planning, no check report, no preamble.

Rules:
- Do not invent claims, quotations, scholars, verses, or pages.
- Fix only the findings you are given, plus an obvious typo those findings \
already describe. Leave a true sentence alone.
- Copy quotations verbatim from the article, including verb endings.
- Match the author’s hedging. Do not assert more certainty or less.
- Attribute each claim to the scholar and the model or structure the article names.
- If the article names one scholar, do not write “some scholars.”
- Use en dashes in numeric and verse ranges, and curly apostrophes.
- Keep the house format: title, The Takeaway, The Q&A (exactly three questions), \
The Summary, Video Script. No Reflection.
- Do not add claims in order to hit a word count. If the summary is short \
because the article is a close reading, keep it short and add one HTML comment \
after the video script: <!-- length-note: why, in one sentence -->.
- The last video row still ends with “and I'll see you next time.”
- Locators stay in the form (link to "opening words"; page N) and use journal pages.
- Do not bold bracketed labels.
"""


def build_review_user_prompt(
    *,
    pagination: str,
    article_text: str,
    article_truncated: bool,
    draft: str,
    open_findings: list[Finding],
) -> str:
    recorded = _format_findings(open_findings) or "None."
    truncated = ""
    if article_truncated:
        truncated = (
            "\nThe article text below was truncated. Do not file a finding about "
            "a page that was not sent.\n"
        )
    return (
        "Compare the draft to the article text. The PDF is not attached.\n\n"
        f"Printed pagination:\n{pagination}\n"
        f"{truncated}\n"
        "Deterministic findings already recorded. Prefer claim, attribution, "
        "hedging, and quotation problems over repeating these:\n"
        f"{recorded}\n\n"
        "Article text, with journal pages:\n"
        f"{article_text}\n\n"
        "Draft:\n"
        f"{draft}"
    )


def build_revision_user_prompt(
    *,
    pagination: str,
    article_text: str,
    article_truncated: bool,
    draft: str,
    findings: list[Finding],
) -> str:
    truncated = ""
    if article_truncated:
        truncated = "The article extract was truncated. Do not add facts from pages that were not sent.\n"
    return (
        "Revise the draft to fix the findings. Do not invent claims.\n\n"
        f"{truncated}"
        f"Printed pagination:\n{pagination}\n\n"
        "Findings:\n"
        f"{_format_findings(findings)}\n\n"
        "Article text, with journal pages:\n"
        f"{article_text}\n\n"
        "Draft:\n"
        f"{draft}"
    )


def parse_model_findings(text: str) -> tuple[list[Finding], str | None]:
    """Return findings and an error string when the response is not usable JSON."""
    raw = text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        return [], "Model review did not return JSON findings."
    try:
        payload = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return [], "Model review returned JSON that could not be parsed."
    if isinstance(payload, dict):
        items = payload.get("findings")
    elif isinstance(payload, list):
        items = payload
    else:
        items = None
    if items is None:
        return [], "Model review JSON had no findings list."
    if not isinstance(items, list):
        return [], "Model review findings were not a list."
    findings: list[Finding] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        problem = str(item.get("problem") or "").strip()
        if not problem:
            continue
        location = str(item.get("location") or "Draft").strip() or "Draft"
        findings.append(
            Finding(
                code="model",
                location=location,
                problem=problem,
                evidence=str(item.get("evidence") or "").strip(),
                page=_page_number(item.get("page")),
                suggested_fix=str(
                    item.get("suggested_fix") or item.get("suggestedFix") or ""
                ).strip(),
                source="model",
                severity="error",
            )
        )
    return findings[:12], None


def looks_like_post(text: str) -> bool:
    stripped = strip_preamble(text).lstrip()
    return stripped.startswith("# ") and "Takeaway" in stripped


def _format_findings(findings: list[Finding]) -> str:
    lines: list[str] = []
    for finding in findings:
        if finding.severity == "info":
            continue
        page = f" Journal page {finding.page}." if finding.page else ""
        evidence = f' Article: "{finding.evidence}".' if finding.evidence else ""
        fix = f" Suggested fix: {finding.suggested_fix}" if finding.suggested_fix else ""
        lines.append(f"- [{finding.location}]{page} {finding.problem}{evidence}{fix}")
    return "\n".join(lines)


def _page_number(value: object) -> int | None:
    if value is None or value is False:
        return None
    if isinstance(value, int):
        return value
    match = re.search(r"\d+", str(value))
    if not match:
        return None
    return int(match.group(0))
