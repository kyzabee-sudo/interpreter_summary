from __future__ import annotations

import re
from io import BytesIO

from docx import Document
from docx.enum.text import WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, Twips

HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")
REFLECTION_RE = re.compile(r"^#{1,3}\s+(?:the\s+)?reflection\s*:?\s*$", re.IGNORECASE)
RESUME_HEADING_RE = re.compile(r"^#{1,2}\s+\S")
SEPARATOR_CELL_RE = re.compile(r":?-{3,}:?")
LOCATOR_LABEL_RE = re.compile(r"(?<!\*)(\[[^\]]+\])\s+(?=\(link to\b)")
INLINE_RE = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*)")

# Column widths from Kyler's September 2026 template (twips): #, Text, Image.
VIDEO_WIDTHS = (450, 6325, 2226)


def section_key(title: str) -> str | None:
    lowered = title.strip().rstrip(":").lower()
    lowered = re.sub(r"\s+", " ", lowered)
    if lowered in {"the takeaway", "takeaway"}:
        return "takeaway"
    if lowered in {"the q&a", "q&a", "the q & a", "q & a", "questions and answers", "the questions and answers"}:
        return "qa"
    if lowered in {"the summary", "summary"}:
        return "summary"
    if lowered in {"video script", "the video script", "script"}:
        return "video_script"
    if lowered in {"the reflection", "reflection"}:
        return "reflection"
    return None


def parse_sections(markdown: str) -> dict[str, str]:
    """Split a generated draft into named sections for the UI and length checks."""
    sections = {
        "title": "",
        "intro": "",
        "takeaway": "",
        "qa": "",
        "summary": "",
        "video_script": "",
    }
    current = "intro"
    buckets: dict[str, list[str]] = {key: [] for key in sections if key != "title"}
    for raw in markdown.replace("\r\n", "\n").split("\n"):
        heading = HEADING_RE.match(raw.strip())
        if heading and len(heading.group(1)) <= 2:
            title = heading.group(2).strip()
            if len(heading.group(1)) == 1:
                sections["title"] = title
                current = "intro"
                continue
            key = section_key(title)
            if key:
                current = key
                continue
        if current == "reflection":
            continue
        buckets[current].append(raw)
    for key, lines in buckets.items():
        sections[key] = "\n".join(lines).strip()
    return sections


def strip_reflection_section(markdown: str) -> str:
    """Drop a Reflection block if the model still emits the retired section."""
    lines = markdown.replace("\r\n", "\n").split("\n")
    kept: list[str] = []
    skipping = False
    for line in lines:
        stripped = line.strip()
        if REFLECTION_RE.match(stripped):
            skipping = True
            continue
        if skipping and RESUME_HEADING_RE.match(stripped) and not REFLECTION_RE.match(stripped):
            skipping = False
        if skipping:
            continue
        kept.append(line)
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()
    return f"{text}\n" if text else ""


def markdown_to_docx(markdown: str) -> bytes:
    """Write a draft that follows Kyler's September 2026 Word template."""
    document = Document()
    _apply_page_setup(document)
    normal = document.styles["Normal"]
    normal.font.size = Pt(11)
    paragraph_format = normal.paragraph_format
    paragraph_format.space_after = Pt(8)
    paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    document.core_properties.author = "Kyler Rasmussen"

    lines = markdown.replace("\r\n", "\n").split("\n")
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if _is_table_start(lines, index):
            index = _add_table(document, lines, index)
            continue
        heading = HEADING_RE.match(line.strip())
        if heading:
            level = len(heading.group(1))
            title = heading.group(2).strip()
            if level == 1:
                _add_title(document, title)
            elif level == 2:
                _add_section_heading(document, title)
            else:
                _add_question(document, title)
            index += 1
            continue
        if line.startswith(">"):
            parts: list[str] = []
            while index < len(lines) and lines[index].startswith(">"):
                body = lines[index][2:] if lines[index].startswith("> ") else lines[index][1:]
                parts.append(body.strip())
                index += 1
            _add_body(document, " ".join(part for part in parts if part))
            continue
        if line.startswith(("- ", "* ")):
            _add_bullet(document, line[2:].strip())
            index += 1
            continue
        if re.fullmatch(r"(-{3,}|\*{3,})", line.strip()):
            index += 1
            continue
        _add_body(document, line.strip())
        index += 1

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _apply_page_setup(document: Document) -> None:
    section = document.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)


def _add_title(document: Document, text: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(0)
    match = re.match(r"^Interpreting Interpreter:\s*(.*)$", text)
    if match:
        _add_run(paragraph, "Interpreting ", bold=True, size=16)
        _add_run(paragraph, "Interpreter", bold=True, italic=True, size=16)
        _add_run(paragraph, f": {match.group(1)}", bold=True, size=16)
    else:
        _add_run(paragraph, text, bold=True, size=16)
    document.add_paragraph()


def _add_section_heading(document: Document, text: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(14)
    paragraph.paragraph_format.space_after = Pt(4)
    if section_key(text) == "video_script":
        _add_run(paragraph, text, bold=False, italic=True)
    else:
        _add_run(paragraph, text, bold=True, italic=False)


def _add_question(document: Document, text: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(8)
    paragraph.paragraph_format.space_after = Pt(2)
    _add_inline(paragraph, text, bold=True, italic=True)


def _add_body(document: Document, text: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(8)
    _add_inline(paragraph, text, bold=False, italic=False)


def _add_bullet(document: Document, text: str) -> None:
    paragraph = document.add_paragraph(style="List Bullet")
    paragraph.paragraph_format.space_after = Pt(6)
    _add_inline(paragraph, text, bold=False, italic=False)


def _add_inline(paragraph, text: str, *, bold: bool, italic: bool) -> None:
    prepared = LOCATOR_LABEL_RE.sub(lambda match: f"**{match.group(1)}** ", text)
    cursor = 0
    for match in INLINE_RE.finditer(prepared):
        if match.start() > cursor:
            _add_run(paragraph, prepared[cursor : match.start()], bold=bold, italic=italic)
        token = match.group(0)
        if token.startswith("**"):
            _add_run(paragraph, token[2:-2], bold=True, italic=italic)
        else:
            _add_run(paragraph, token[1:-1], bold=bold, italic=True)
        cursor = match.end()
    if cursor < len(prepared):
        _add_run(paragraph, prepared[cursor:], bold=bold, italic=italic)
    if not prepared:
        _add_run(paragraph, "", bold=bold, italic=italic)


def _add_run(paragraph, text: str, *, bold: bool, italic: bool = False, size: int | None = None):
    run = paragraph.add_run(text)
    run.bold = bold
    run.italic = italic
    if size is not None:
        run.font.size = Pt(size)
    return run


def _is_table_start(lines: list[str], index: int) -> bool:
    if not lines[index].lstrip().startswith("|"):
        return False
    return index + 1 < len(lines) and lines[index + 1].lstrip().startswith("|")


def _split_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(SEPARATOR_CELL_RE.fullmatch(cell.replace(" ", "")) for cell in cells)


def _add_table(document: Document, lines: list[str], index: int) -> int:
    rows: list[list[str]] = []
    while index < len(lines) and lines[index].lstrip().startswith("|"):
        cells = _split_row(lines[index])
        if not _is_separator(cells):
            rows.append(cells)
        index += 1
    if not rows:
        return index
    columns = max(len(row) for row in rows)
    table = document.add_table(rows=len(rows), cols=columns)
    table.style = "Table Grid"
    table.autofit = False
    widths = _column_widths(columns)
    _set_table_widths(table, widths)
    for row_index, row in enumerate(rows):
        for col_index in range(columns):
            value = row[col_index] if col_index < len(row) else ""
            cell = table.rows[row_index].cells[col_index]
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_before = Pt(0)
            paragraph.paragraph_format.space_after = Pt(0)
            _add_inline(paragraph, value, bold=row_index == 0, italic=False)
            _set_cell_width(cell, widths[col_index])
    return index


def _column_widths(columns: int) -> tuple[int, ...]:
    if columns == 3:
        return VIDEO_WIDTHS
    total = sum(VIDEO_WIDTHS)
    each = total // max(columns, 1)
    return tuple(each for _ in range(columns))


def _set_table_widths(table, widths: tuple[int, ...]) -> None:
    table.autofit = False
    table.allow_autofit = False
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    total = sum(widths)
    tbl_w.set(qn("w:w"), str(total))
    tbl_w.set(qn("w:type"), "dxa")
    grid = tbl.find(qn("w:tblGrid"))
    if grid is None:
        grid = OxmlElement("w:tblGrid")
        tbl_pr.addnext(grid)
    else:
        for child in list(grid):
            grid.remove(child)
    for width in widths:
        column = OxmlElement("w:gridCol")
        column.set(qn("w:w"), str(width))
        grid.append(column)


def _set_cell_width(cell, width: int) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_w = tc_pr.find(qn("w:tcW"))
    if tc_w is None:
        tc_w = OxmlElement("w:tcW")
        tc_pr.append(tc_w)
    tc_w.set(qn("w:w"), str(width))
    tc_w.set(qn("w:type"), "dxa")
    cell.width = Twips(width)
