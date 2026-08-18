from interpreter_summary.export import parse_sections
from interpreter_summary.length import length_hint, summary_length_note, summary_word_target
from interpreter_summary.locators import locator_count, verify_locators
from interpreter_summary.pdf_utils import PdfCorpus, PdfPage, normalize_for_match
from interpreter_summary.prompts import SYSTEM_PROMPT, build_user_prompt
from interpreter_summary.quotes import verify_quotes
from interpreter_summary.style import load_style_text, strip_video_script


def test_system_prompt_forbids_video_script():
    assert "video" in SYSTEM_PROMPT.lower()
    assert "The Takeaway" in SYSTEM_PROMPT
    assert "The Reflection" in SYSTEM_PROMPT
    assert "printed journal page" in SYSTEM_PROMPT.lower()
    assert "viewer" in SYSTEM_PROMPT.lower()
    assert "verbatim" in SYSTEM_PROMPT.lower()
    assert "briefing" in SYSTEM_PROMPT.lower()
    assert "reservation" in SYSTEM_PROMPT.lower()
    assert "cheerleader" in SYSTEM_PROMPT.lower()
    assert "40–70" in SYSTEM_PROMPT or "40-70" in SYSTEM_PROMPT
    assert "throat-clearing" in SYSTEM_PROMPT.lower()
    assert "delve" in SYSTEM_PROMPT.lower()
    assert "chatbot" in SYSTEM_PROMPT.lower()


def test_style_guide_teaches_published_voice():
    guide = load_style_text()
    assert "briefing" in guide.lower()
    assert "cheerleader" in guide.lower()
    assert "reservation" in guide.lower()
    assert "Lamanite Political Development" in guide
    assert "Alma 29-shaped heart" in guide
    assert "On Abstracting Thought" in guide
    assert "Video Script" not in guide
    assert "500–650" in guide
    assert "41+" in guide
    assert "Clarity first" in guide
    assert "sheds light" in guide
    assert "Banned habits" in guide
    assert "green cacao" in guide
    assert "I could only hope to be so lucky" in guide


def test_user_prompt_includes_style_and_drops_script_instruction():
    prompt = build_user_prompt(
        "House style goes here",
        extra_instructions="Keep it short.",
        pagination_hint="Printed journal pages are 425–450.",
        length_hint_text="The Summary: about 500–650 words.",
    )
    assert "House style goes here" in prompt
    assert "Do not include a video script" in prompt
    assert "Keep it short." in prompt
    assert "Printed journal pages are 425–450." in prompt
    assert "The Summary: about 500–650 words." in prompt


def test_summary_word_targets_match_published_bands():
    assert summary_word_target(8) == (250, 400, 450)
    assert summary_word_target(20) == (400, 550, 600)
    assert summary_word_target(26) == (500, 650, 700)
    assert summary_word_target(82) == (600, 800, 850)
    hint = length_hint(26, printed_start=425, printed_end=450)
    assert "26 PDF pages" in hint
    assert "500–650" in hint
    assert "printed 425–450" in hint
    note = summary_length_note(1098, 26)
    assert "over max" in note
    assert summary_length_note(519, 26).startswith("summary 519 words (on target")


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
    assert locator_count('[Lamanite politics] (link to “The present article”; page 426)') == 1


def _corpus_from_pages(pages: dict[int, str], *, used_printed: bool = True) -> PdfCorpus:
    return PdfCorpus(
        pages=[
            PdfPage(
                viewer_page=index,
                journal_page=journal,
                text=text,
                normalized=normalize_for_match(text),
            )
            for index, (journal, text) in enumerate(pages.items(), start=1)
        ],
        used_printed_pages=used_printed,
    )


def test_verify_locators_keeps_corrects_and_drops():
    corpus = _corpus_from_pages(
        {
            426: "The present article continues an earlier study of Nephite politics.",
            427: "The earliest Book of Mormon references to Lamanite politics are thin.",
            449: "The Book of Mormon does not provide a continuous narrative.",
        }
    )
    markdown = """
Hudson looks at [Lamanite politics] (link to "The present article"; page 426).
He also notes early glimpses (link to "The earliest Book"; page 1).
A fake claim appears (link to "No such paragraph exists here"; page 440).
As he concludes (link to “The Book of Mormon does not”; page 449):
"""
    report = verify_locators(markdown, corpus)
    assert report.kept == 2
    assert report.corrected == 1
    assert report.dropped == 1
    assert '(link to "The present article"; page 426)' in report.markdown
    assert '(link to "The earliest Book"; page 427)' in report.markdown
    assert "page 1" not in report.markdown
    assert "No such paragraph exists here" not in report.markdown
    assert "A fake claim appears." in report.markdown
    assert locator_count(report.markdown) == 3


def test_verify_locators_does_not_guess_ambiguous_hits():
    corpus = _corpus_from_pages(
        {
            425: "The aftermath of the schism is narrated immediately.",
            440: "The aftermath of the massacre reshaped the coalition.",
            445: "The aftermath of Ammoron's death weakened the war effort.",
        }
    )
    markdown = 'Later (link to "The aftermath of"; page 99) the coalition broke.'
    report = verify_locators(markdown, corpus)
    assert report.dropped == 1
    assert report.corrected == 0
    assert "link to" not in report.markdown


def test_verify_locators_keeps_claimed_page_among_ambiguous_hits():
    corpus = _corpus_from_pages(
        {
            425: "The aftermath of the schism is narrated immediately.",
            440: "The aftermath of the massacre reshaped the coalition.",
        }
    )
    markdown = 'Later (link to "The aftermath of"; page 440) the coalition broke.'
    report = verify_locators(markdown, corpus)
    assert report.kept == 1
    assert '(link to "The aftermath of"; page 440)' in report.markdown


def test_verify_quotes_keeps_exact_and_ellipsis_spans():
    corpus = _corpus_from_pages(
        {
            449: (
                "A close reading of Mosiah through Helaman suggests that Lamanite "
                "history was shaped by more than inherited hostility toward the Nephites. "
                "The text instead reveals a dynamic society whose institutions evolved."
            ),
            450: (
                "The result is a more historically textured picture of the Lamanites, "
                "not merely a static foil to the Nephites."
            ),
        }
    )
    markdown = """
As Hudson concludes:

> A close reading of Mosiah through Helaman suggests that Lamanite history was shaped by more than inherited hostility toward the Nephites. ... The result is a more historically textured picture of the Lamanites, not merely a static foil to the Nephites.
"""
    report = verify_quotes(markdown, corpus)
    assert report.kept == 1
    assert report.corrected == 0
    assert report.dropped == 0
    assert "As Hudson concludes:" in report.markdown


def test_verify_quotes_repairs_paraphrase_using_pdf_wording():
    corpus = _corpus_from_pages(
        {
            3: (
                "As I conclude: although copper can be cargo, in this fragment it more "
                "plausibly memorializes a promise."
            )
        }
    )
    markdown = """
As Scholar concludes:

> although copper can be cargo, in this fragment it obviously memorializes a promise.
"""
    report = verify_quotes(markdown, corpus)
    assert report.corrected == 1
    assert "obviously" not in report.markdown
    assert "more plausibly memorializes a promise" in report.markdown
    assert report.markdown.strip().startswith("> ") or "> although copper can be cargo" in report.markdown


def test_verify_quotes_drops_unverified_quote_and_attribution():
    corpus = _corpus_from_pages({1: "The warehouse fragment lists ten ingots of bright copper."})
    markdown = """
The fragment lists ingots.

As Scholar concludes:

> This sentence does not appear anywhere in the article at all.

The Reflection follows.
"""
    report = verify_quotes(markdown, corpus)
    assert report.dropped == 1
    assert "This sentence does not appear" not in report.markdown
    assert "As Scholar concludes:" not in report.markdown
    assert "The fragment lists ingots." in report.markdown
    assert "The Reflection follows." in report.markdown
