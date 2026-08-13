from __future__ import annotations

import re
from io import BytesIO

from docx import Document
from docx.enum.text import WD_LINE_SPACING
from docx.shared import Pt

HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")


def parse_sections(markdown: str) -> dict[str, str]:
    """Split a generated summary into named sections for the UI."""
    sections = {"title": "", "intro": "", "takeaway": "", "summary": "", "reflection": ""}
    current = "intro"
    intro_lines: list[str] = []
    buckets: dict[str, list[str]] = {
        "takeaway": [],
        "summary": [],
        "reflection": [],
    }
    for raw in markdown.replace("\r\n", "\n").split("\n"):
        heading = HEADING_RE.match(raw)
        if heading:
            level = len(heading.group(1))
            title = heading.group(2).strip()
            lower = title.lower()
            if level == 1:
                sections["title"] = title
                current = "intro"
                continue
            if lower.startswith("the takeaway"):
                current = "takeaway"
                continue
            if lower.startswith("the summary"):
                current = "summary"
                continue
            if lower.startswith("the reflection"):
                current = "reflection"
                continue
        if current == "intro":
            intro_lines.append(raw)
        elif current in buckets:
            buckets[current].append(raw)
    sections["intro"] = "\n".join(intro_lines).strip()
    for key, lines in buckets.items():
        sections[key] = "\n".join(lines).strip()
    return sections


def markdown_to_docx(markdown: str) -> bytes:
    document = Document()
    style = document.styles["Normal"]
    style.font.name = "Georgia"
    style.font.size = Pt(11)
    paragraph_format = style.paragraph_format
    paragraph_format.space_after = Pt(8)
    paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE

    for raw in markdown.replace("\r\n", "\n").split("\n"):
        line = raw.rstrip()
        if not line.strip():
            continue
        heading = HEADING_RE.match(line)
        if heading:
            level = min(len(heading.group(1)), 2)
            document.add_heading(heading.group(2).strip(), level=level)
            continue
        if line.startswith("> "):
            paragraph = document.add_paragraph(line[2:])
            paragraph.paragraph_format.left_indent = Pt(24)
            paragraph.runs[0].italic = True
            continue
        if line.startswith(("- ", "* ")):
            document.add_paragraph(line[2:], style="List Bullet")
            continue
        document.add_paragraph(line)

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()
