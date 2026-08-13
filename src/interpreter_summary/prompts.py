from __future__ import annotations

from pathlib import Path

from interpreter_summary.style import load_style_text

PACKAGE_ROOT = Path(__file__).resolve().parent
STYLE_GUIDE_PATH = PACKAGE_ROOT / "style_assets" / "style_guide.md"

SYSTEM_PROMPT = """\
You are Kyler Rasmussen drafting a new Interpreting Interpreter summary for \
The Interpreter Foundation. Write the published blog post only—never a video \
script, social caption, or behind-the-scenes note.

Follow the attached house style exactly: title, boilerplate intro, The Takeaway, \
The Summary, and The Reflection. Use in-text locators of the form \
(link to "quoted phrase"; page N) with printed journal page numbers from the PDF.

Be faithful to the article. Do not invent evidence, quotations, Hebrew, or pages. \
If a bibliographic detail (volume, exact title, author) is present in the PDF, use it. \
If a volume number is missing, write “Volume [unknown]” rather than guessing.

Return Markdown with these headings:

# Interpreting Interpreter: <Punchy Title>

<boilerplate paragraph>

## The Takeaway

## The Summary

## The Reflection
"""


def build_user_prompt(style_text: str | None = None, extra_instructions: str | None = None) -> str:
    guide = style_text if style_text and style_text.strip() else load_style_text()
    parts = [
        "Read the attached Interpreter journal article PDF in full.",
        "Write a complete Interpreting Interpreter summary of that article.",
        "Do not include a video script.",
        "",
        "House style and worked example:",
        guide.strip(),
    ]
    if extra_instructions and extra_instructions.strip():
        parts.extend(["", "Additional instructions from the user:", extra_instructions.strip()])
    return "\n".join(parts)


def default_system_prompt() -> str:
    return SYSTEM_PROMPT
