from interpreter_summary.export import locator_count, parse_sections
from interpreter_summary.prompts import SYSTEM_PROMPT, build_user_prompt
from interpreter_summary.style import strip_video_script


def test_system_prompt_forbids_video_script():
    assert "video" in SYSTEM_PROMPT.lower()
    assert "The Takeaway" in SYSTEM_PROMPT
    assert "The Reflection" in SYSTEM_PROMPT


def test_user_prompt_includes_style_and_drops_script_instruction():
    prompt = build_user_prompt("House style goes here", extra_instructions="Keep it short.")
    assert "House style goes here" in prompt
    assert "Do not include a video script" in prompt
    assert "Keep it short." in prompt


def test_strip_video_script_removes_script_section():
    text = """
## The Takeaway
Keep this.

## Video Script
Ignore this entire pitch.

## The Reflection
Keep this too.
"""
    stripped = strip_video_script(text)
    assert "Keep this" in stripped
    assert "Ignore this entire pitch" not in stripped
    assert "Video Script" not in stripped


def test_parse_sections_and_locators():
    markdown = """
# Interpreting Interpreter: Tokens, Not Tonnage

This post is a summary of the article "Copper" by A. Sample Scholar.

## The Takeaway

Scholar argues that copper is a token.

## The Summary

The warehouse fragment lists ingots (link to "The warehouse fragment"; page 1).
Later evidence appears (link to "Three features"; page 2).

## The Reflection

I like the caution.
"""
    sections = parse_sections(markdown)
    assert sections["title"] == "Interpreting Interpreter: Tokens, Not Tonnage"
    assert "summary of the article" in sections["intro"]
    assert sections["takeaway"].startswith("Scholar argues")
    assert "warehouse fragment" in sections["summary"]
    assert sections["reflection"].startswith("I like")
    assert locator_count(markdown) == 2
