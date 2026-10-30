"""Lay Academic video script: a separate document from the main summary.

The on-camera Interpreting Interpreter post is unchanged. This module pulls a
Lay Academic script out of a model response, checks its length and caption
shape, and writes ``<article> - Lay Academic Script.docx``.
"""

from __future__ import annotations

import re
from pathlib import Path

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement

from interpreter_summary.export import (
    HEADING_RE,
    VIDEO_WIDTHS,
    _add_body,
    _add_bullet,
    _add_inline,
    _add_quote,
    _add_run,
    _add_title,
    _apply_page_setup,
    _document_from_template,
    _is_separator,
    _is_table_start,
    _set_cell_width,
    _set_table_widths,
    _split_row,
)
from interpreter_summary.length import (
    LAY_CAPTION_LINES,
    LAY_CAPTION_WORDS,
    _SEPARATOR_CELL_RE,
    extract_length_note,
    lay_academic_length_note,
    video_row_count,
)

LAY_DOCX_SUFFIX = " - Lay Academic Script"

# A heading that opens the separate document. A mention of the words inside
# the main post is not enough; the line has to be the script's own title.
_LAY_START_RE = re.compile(
    r"(?im)^(?:#{1,2}[ \t]+.*\bLay Academic Script\b.*|"
    r"#{1,2}[ \t]+Video Script \(Lay Academic Version\)[ \t]*|"
    r"<!--\s*lay-academic-script\s*-->)[ \t]*$"
)
_SMALL_WORDS = frozenset(
    "a an the of to and or but in on for with as at by from into over".split()
)
_PAGE_RE = re.compile(r"\b(?:pp?|pages?)\.?\s*\d+", re.IGNORECASE)
_LOCATOR_RE = re.compile(
    r"(?:\[[^\]]+\]\s*)?\(link to\s+[“\"”][^“\"”]+[“\"”];\s*page\s+\d+\)",
    re.IGNORECASE,
)
_SIGNOFF_RE = re.compile(
    r"see you next time|welcome back|like and subscribe|thanks for watching|let me know what you think",
    re.IGNORECASE,
)
_SERIES_RE = re.compile(r"Interpreting\s+Interpreter", re.IGNORECASE)
_CARD_SPLIT_RE = re.compile(r"\s+/\s+")
_NAME_SPLIT_RE = re.compile(r"\b[A-Z][a-z]+\s+/\s+[A-Z]")
_WORD_RE = re.compile(r"[A-Za-z0-9'’]+")


def lay_academic_docx_path(article: str | Path) -> Path:
    """``VV_AA (MmmYY) Author.AI.docx`` → ``… Author - Lay Academic Script.docx``."""
    path = Path(article)
    stem = path.name
    for ext in (".docx", ".markdown", ".md", ".pdf"):
        if stem.lower().endswith(ext):
            stem = stem[: -len(ext)]
            break
    if stem.lower().endswith(".ai"):
        stem = stem[:-3]
    if stem.endswith(LAY_DOCX_SUFFIX):
        stem = stem[: -len(LAY_DOCX_SUFFIX)]
    stem = stem.rstrip()
    return path.with_name(f"{stem}{LAY_DOCX_SUFFIX}.docx")


def looks_like_lay_script(markdown: str) -> bool:
    lowered = markdown.lower()
    if "narration (spoken)" in lowered and "on-screen caption" in lowered:
        return True
    return "lay academic script" in lowered and "|" in markdown


def split_lay_academic(markdown: str) -> tuple[str, str]:
    """Return ``(main_post, lay_script)``. The lay half is empty when absent.

    The main Interpreting Interpreter post must not keep this script. A model
    that appends it is split here so the ``.AI.docx`` stays the summary only.
    """
    text = markdown.replace("\r\n", "\n")
    match = _LAY_START_RE.search(text)
    if match is None:
        return text, ""
    main = text[: match.start()].strip()
    lay = text[match.start() :].strip()
    return (f"{main}\n" if main else ""), (f"{lay}\n" if lay else "")


def extract_lay_script(raw: str) -> str:
    """Keep a Lay Academic script and drop preamble, or return ''."""
    text, _reason = extract_length_note(raw)
    text = text.replace("\r\n", "\n").strip()
    match = _LAY_START_RE.search(text)
    if match is not None:
        text = text[match.start() :].strip()
    if not looks_like_lay_script(text):
        return ""
    return f"{text}\n"


def lay_script_notes(markdown: str) -> list[str]:
    """Heads-up notes for caption shape, page numbers, and sign-offs.

    Image Sources may cite a page. The script above that section may not.
    """
    notes: list[str] = []
    region = _script_region(markdown)
    region_without_locators = _LOCATOR_RE.sub("", region)
    if _PAGE_RE.search(region_without_locators):
        notes.append("page number in the script")
    if _SERIES_RE.search(region):
        notes.append("series branding in the script")
    rows = _lay_rows(markdown)
    for index, row in enumerate(rows, start=1):
        narration = row.get("narration", "")
        caption = row.get("caption", "")
        if _SIGNOFF_RE.search(narration):
            notes.append(f"row {index} narration signs off")
        for problem in _caption_problems(caption):
            notes.append(f"row {index} caption {problem}")
    if rows:
        closing = rows[-1].get("narration", "") + " " + rows[-1].get("caption", "")
        if "interpreterfoundation.org" not in closing.lower() and "interpreter foundation" not in closing.lower():
            notes.append("outro does not point to interpreterfoundation.org")
    return notes


def lay_script_length_note(markdown: str) -> str:
    return lay_academic_length_note(video_row_count(markdown), lay_script_notes(markdown))


def lay_academic_to_docx(markdown: str) -> bytes:
    """Write the Lay Academic script with Kyler's template formatting.

    Same theme font, same unbolded bracketed labels, and the same red locator
    colour when a locator is actually present. The title is not given the
    series italic. Caption cards become line breaks. The document has no page
    number field.
    """
    from io import BytesIO

    document = _document_from_template()
    _apply_page_setup(document)
    document.core_properties.author = "Kyler Rasmussen"

    lines = markdown.replace("\r\n", "\n").split("\n")
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if line.strip().startswith("<!--"):
            index += 1
            continue
        if _is_table_start(lines, index):
            index = _add_lay_table(document, lines, index)
            continue
        heading = HEADING_RE.match(line.strip())
        if heading:
            level = len(heading.group(1))
            title = heading.group(2).strip()
            if level == 1:
                _add_title(document, title)
            elif level == 2:
                _add_lay_heading(document, title)
            else:
                paragraph = document.add_paragraph()
                _add_inline(paragraph, title, bold=True, italic=True)
            index += 1
            continue
        if line.startswith(">"):
            parts: list[str] = []
            while index < len(lines) and lines[index].startswith(">"):
                body = lines[index][2:] if lines[index].startswith("> ") else lines[index][1:]
                parts.append(body.strip())
                index += 1
            _add_quote(document, " ".join(part for part in parts if part))
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


def _script_region(markdown: str) -> str:
    """Title, opening sentence, and table. Not Post Caption or Image Sources."""
    text = markdown.replace("\r\n", "\n")
    cut = len(text)
    for marker in ("## Post Caption", "## Image Sources"):
        found = text.find(marker)
        if found != -1:
            cut = min(cut, found)
    return text[:cut]


def _lay_rows(markdown: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    header: list[str] | None = None
    for raw in markdown.replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if cells and all(_SEPARATOR_CELL_RE.fullmatch(cell.replace(" ", "")) for cell in cells):
            continue
        if header is None:
            header = [cell.lower() for cell in cells]
            continue
        if not any(cells):
            continue
        padded = cells + [""] * max(0, len(header) - len(cells))
        record = {header[index]: padded[index] if index < len(padded) else "" for index in range(len(header))}
        narration = _cell(record, "narration")
        caption = _cell(record, "caption")
        image = _cell(record, "image")
        rows.append({"narration": narration, "caption": caption, "image": image})
    return rows


def _cell(record: dict[str, str], needle: str) -> str:
    for key, value in record.items():
        if needle in key:
            return value
    return ""


def _caption_cards(caption: str) -> list[str]:
    return [part.strip() for part in _CARD_SPLIT_RE.split(caption) if part.strip()]


def _caption_lines(card: str) -> list[str]:
    return [part.strip() for part in re.split(r"\s+//\s+", card) if part.strip()]


def _caption_problems(caption: str) -> list[str]:
    problems: list[str] = []
    if _NAME_SPLIT_RE.search(caption):
        problems.append("may split a name")
    for card in _caption_cards(caption):
        lines = _caption_lines(card)
        words = _WORD_RE.findall(card.replace("//", " "))
        if len(words) > LAY_CAPTION_WORDS:
            problems.append(f"has {len(words)} words (about {LAY_CAPTION_WORDS})")
        if len(lines) > LAY_CAPTION_LINES:
            problems.append(f"has {len(lines)} lines (at most {LAY_CAPTION_LINES})")
        for line in lines:
            line_words = _WORD_RE.findall(line)
            if line_words and line_words[-1].lower().strip("'’") in _SMALL_WORDS:
                problems.append(f"ends on “{line_words[-1]}”")
    # One note per problem type keeps the length line readable.
    seen: list[str] = []
    for problem in problems:
        if problem not in seen:
            seen.append(problem)
    return seen


def _add_lay_heading(document, text: str) -> None:
    paragraph = document.add_paragraph()
    if text.lower().startswith("video script"):
        _add_run(paragraph, text, bold=False, italic=True)
    else:
        _add_run(paragraph, text, bold=True, italic=False)


def _add_lay_table(document, lines: list[str], index: int) -> int:
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
    widths = _lay_widths(columns)
    _set_table_widths(table, widths)
    caption_at = _caption_column(rows[0])
    for row_index, row in enumerate(rows):
        for col_index in range(columns):
            value = row[col_index] if col_index < len(row) else ""
            cell = table.rows[row_index].cells[col_index]
            paragraph = cell.paragraphs[0]
            if row_index == 0:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                _add_inline(paragraph, value, bold=True, italic=False)
            elif col_index == caption_at:
                _add_caption(paragraph, value)
            else:
                _add_inline(paragraph, value, bold=False, italic=False)
            _set_cell_width(cell, widths[col_index])
    return index


def _caption_column(header: list[str]) -> int | None:
    for index, cell in enumerate(header):
        if "caption" in cell.lower():
            return index
    return None


def _lay_widths(columns: int) -> tuple[int, ...]:
    if columns == 4:
        # #, narration, caption, image. Same total as the on-camera table.
        number, narration, caption, image = 450, 3400, 2850, 2301
        return (number, narration, caption, image)
    if columns == 3:
        return VIDEO_WIDTHS
    total = sum(VIDEO_WIDTHS)
    each = total // max(columns, 1)
    return tuple(each for _ in range(columns))


def _add_caption(paragraph, text: str) -> None:
    """Turn `` / `` cards and `` // `` line breaks into Word line breaks."""
    normalized = text.replace(" // ", "\n")
    pieces = [piece.strip() for piece in re.split(r"\s+/\s+|\n", normalized)]
    pieces = [piece for piece in pieces if piece]
    if not pieces:
        _add_inline(paragraph, "", bold=False, italic=False)
        return
    for offset, piece in enumerate(pieces):
        if offset:
            run = paragraph.add_run()
            run.bold = False
            run.italic = False
            run._r.append(OxmlElement("w:br"))
        _add_inline(paragraph, piece, bold=False, italic=False)
