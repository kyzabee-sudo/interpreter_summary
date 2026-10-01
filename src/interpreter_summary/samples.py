from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

SAMPLE_ARTICLE_TITLE = "Copper, Covenants, and the Case of the Missing Ingots"
SAMPLE_AUTHOR = "A. Sample Scholar"

SAMPLE_PDF_PARAGRAPHS = [
    (
        1,
        [
            f"{SAMPLE_ARTICLE_TITLE}",
            f"by {SAMPLE_AUTHOR}",
            "Interpreter: A Journal of Latter-day Saint Faith and Scholarship 99 (2099): 1-8",
            "Abstract: This sample article exists only to exercise the summarizer. It argues that "
            "references to 'bright copper' in a fictional Nephite warehouse list are better read "
            "as covenant tokens than as a metallurgical report, because the surrounding clauses "
            "echo treaty language rather than assay notes.",
            "[Page 1]",
            "The warehouse fragment under discussion -- hereafter Fragment W -- lists 'ten ingots of "
            "bright copper' immediately after an oath formula. Critics have treated the ingots as "
            "a straightforward inventory of trade goods. That reading is possible, but it ignores "
            "how the fragment frames the metal.",
        ],
    ),
    (
        2,
        [
            "[Page 2]",
            "Three features of the surrounding clauses matter. First, the verb translated 'weigh' "
            "elsewhere in the corpus regularly means 'confirm' when the object is a promise rather "
            "than a commodity. Second, the adjective 'bright' clusters with words for holiness, not "
            "with words for ore. Third, the list ends with a witness formula ('in the presence of "
            "three') that would be odd in a shipping receipt and ordinary in a covenant text.",
            "Taken together, these features suggest the ingots function as tokens that the covenant "
            "has been 'made sure,' not as a report of what sat on a shelf.",
        ],
    ),
    (
        3,
        [
            "[Page 3]",
            "A comparative table of treaty deposits from the Late Bronze Age shows similar pairing "
            "of metal tokens with oath witnesses. The analogy is suggestive rather than decisive: "
            "Fragment W is short, and we lack the preceding column. Still, the burden of proof sits "
            "with the inventory reading, which must explain the witness formula as decorative.",
            "As I conclude: although copper can be cargo, in this fragment it more plausibly "
            "memorializes a promise. Readers who come to the passage looking for a foundry will "
            "leave disappointed; readers who come looking for a covenant will find one hiding in "
            "plain sight.",
        ],
    ),
]

SAMPLE_SUMMARY_MARKDOWN = """\
# Interpreting Interpreter: Tokens, Not Tonnage

## The Takeaway

Scholar argues that the bright copper in Fragment W is a covenant token rather than warehouse cargo, because the clauses around it use oath and witness language.

## The Q&A

### What is Fragment W?

Fragment W is a short warehouse list that places ten ingots of bright copper immediately after an oath formula. Critics have read those ingots as ordinary trade goods sitting on a shelf.

### Why does Scholar reject the inventory reading?

Three features of the surrounding clauses point the other way. The verb often rendered "weigh" means "confirm" when the object is a promise, the adjective "bright" clusters with words for holiness, and the list ends with a witness formula that belongs in a covenant text.

### How strong is the comparative evidence?

A table of Late Bronze Age treaty deposits shows metal tokens paired with oath witnesses. Scholar treats the analogy as suggestive rather than decisive, because Fragment W is short and the preceding column is missing.

## The Summary

In this article, A. Sample Scholar revisits Fragment W, which lists ten ingots of bright copper immediately after an oath formula (link to "The warehouse fragment"; page 1). Critics have treated the ingots as a straightforward inventory. Scholar instead walks through three features of the surrounding clauses (link to "Three features"; page 2):

* **[The verb]** (link to "Three features"; page 2). The word translated "weigh" regularly means "confirm" when the object is a promise rather than a commodity.
* **[The adjective]** (link to "Three features"; page 2). "Bright" clusters with words for holiness, not with words for ore.
* **[The witness formula]** (link to "Three features"; page 2). The list ends "in the presence of three," which would be odd in a shipping receipt and ordinary in a covenant text.

A comparative table of Late Bronze Age treaty deposits pairs metal tokens with oath witnesses (link to "A comparative table"; page 3). Scholar treats that analogy as suggestive, because the fragment is incomplete and the preceding column is missing.

As Scholar concludes (link to "although copper can be cargo"; page 3):

> although copper can be cargo, in this fragment it more plausibly memorializes a promise.

## Video Script

| # | Text | Image |
| --- | --- | --- |
| 1 | Ten ingots of bright copper show up on a warehouse list, right after an oath. | Bright copper ingots |
| 2 | Most readers would call that cargo. A. Sample Scholar thinks it might be a covenant you can hold in your hand. | Oath formula |
| 3 | There's an article this week, Copper, Covenants, and the Case of the Missing Ingots, that walks through three clues in the wording. | Title page |
| 4 | The verb that looks like "weigh" is the same one the corpus uses when someone confirms a promise. | Weigh and confirm |
| 5 | And the word "bright" keeps company with holiness, not with ore. | Bright and holy |
| 6 | Then the list closes with a witness formula, the kind you expect in a treaty and not on a packing slip. | Witness formula |
| 7 | A comparative table of treaty deposits pairs metal tokens with oath witnesses. Scholar is careful here: the fragment is short. | Treaty deposits |
| 8 | Still, the inventory reading has to explain that witness line as decoration. | Shipping receipt |
| 9 | As he concludes: although copper can be cargo, in this fragment it more plausibly memorializes a promise. | Covenant token |
| 10 | Check out the full article, Copper, Covenants, and the Case of the Missing Ingots, and I'll see you next time. | Title page |
"""


class SamplePDF(FPDF):
    def header(self) -> None:
        self.set_font("Times", "I", 9)
        self.cell(0, 8, "Interpreter: A Journal of Latter-day Saint Faith and Scholarship (sample)", align="C")
        self.ln(12)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Times", "I", 9)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")


def write_sample_pdf(path: Path) -> Path:
    pdf = SamplePDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    for _page_number, paragraphs in SAMPLE_PDF_PARAGRAPHS:
        pdf.add_page()
        for index, paragraph in enumerate(paragraphs):
            if index == 0:
                pdf.set_font("Times", "B", 16)
            elif index == 1:
                pdf.set_font("Times", "I", 12)
            else:
                pdf.set_font("Times", "", 12)
            pdf.multi_cell(0, 6, paragraph)
            pdf.ln(3)
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(path))
    return path


def write_sample_docx(path: Path) -> Path:
    from interpreter_summary.export import markdown_to_docx

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(markdown_to_docx(SAMPLE_SUMMARY_MARKDOWN))
    return path


def generate_samples(directory: Path) -> tuple[Path, Path]:
    pdf_path = write_sample_pdf(directory / "sample_article.pdf")
    docx_path = write_sample_docx(directory / "interpreting_interpreter_style.docx")
    return pdf_path, docx_path
