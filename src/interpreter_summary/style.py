from __future__ import annotations

import re
from pathlib import Path

from docx import Document

VIDEO_HEADING_RE = re.compile(r"^\s*(video\s+script|script)\s*:?\s*$", re.IGNORECASE)
RESUME_HEADINGS = {"the takeaway", "the summary", "the reflection"}
PACKAGE_STYLE = Path(__file__).resolve().parent / "style_assets" / "style_guide.md"


def load_style_text(path: Path | None = None) -> str:
    """Load a Markdown or Word style document, dropping any video-script section."""
    target = path or PACKAGE_STYLE
    if not target.exists():
        raise FileNotFoundError(f"Style file not found: {target}")
    suffix = target.suffix.lower()
    if suffix in {".md", ".txt"}:
        text = target.read_text(encoding="utf-8")
    elif suffix in {".docx"}:
        text = _docx_to_text(target)
    else:
        raise ValueError(f"Unsupported style file type: {suffix}")
    return strip_video_script(text)


def load_style_bytes(data: bytes, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in {".md", ".txt"}:
        text = data.decode("utf-8")
    elif suffix == ".docx":
        from io import BytesIO

        text = _docx_to_text(BytesIO(data))
    else:
        raise ValueError(f"Unsupported style file type: {suffix}")
    return strip_video_script(text)


def strip_video_script(text: str) -> str:
    lines = text.replace("\r\n", "\n").split("\n")
    kept: list[str] = []
    skipping = False
    for line in lines:
        heading = line.lstrip("#").strip().lower()
        if VIDEO_HEADING_RE.match(heading):
            skipping = True
            continue
        if skipping and heading in RESUME_HEADINGS:
            skipping = False
        if skipping:
            continue
        kept.append(line)
    return "\n".join(kept).strip() + "\n"


def _docx_to_text(source) -> str:
    document = Document(source)
    paragraphs = [p.text for p in document.paragraphs]
    return "\n".join(paragraphs).strip() + "\n"
