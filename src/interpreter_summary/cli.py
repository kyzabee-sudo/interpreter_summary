from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from interpreter_summary.config import get_settings
from interpreter_summary.export import markdown_to_docx
from interpreter_summary.samples import generate_samples
from interpreter_summary.service import summarize_pdf


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Draft Interpreting Interpreter posts from Interpreter PDFs: "
            "Takeaway, Q&A, Summary, and a video script."
        )
    )
    sub = parser.add_subparsers(dest="command", required=True)

    summarize = sub.add_parser("summarize", help="Summarize a PDF via the Grok API")
    summarize.add_argument("pdf", type=Path, help="Path to an Interpreter article PDF")
    summarize.add_argument("-o", "--output", type=Path, help="Write Markdown to this path")
    summarize.add_argument("--docx", type=Path, help="Also write a Word document to this path")
    summarize.add_argument("--style", type=Path, help="Optional style .docx or .md override")
    summarize.add_argument("--notes", help="Extra instructions for this run")
    summarize.add_argument(
        "--no-verify",
        action="store_true",
        help=(
            "Skip the model accuracy review and the one revision pass. "
            "Deterministic checks still run offline."
        ),
    )

    serve = sub.add_parser("serve", help="Start the local web app")
    serve.add_argument("--host", default=None)
    serve.add_argument("--port", type=int, default=None)

    samples = sub.add_parser("init-samples", help="Write sample PDF and style Word files")
    samples.add_argument(
        "--dir",
        type=Path,
        default=Path("samples"),
        help="Directory for sample files (default: ./samples)",
    )

    args = parser.parse_args(argv)
    if args.command == "summarize":
        _summarize(args)
    elif args.command == "serve":
        _serve(args)
    elif args.command == "init-samples":
        pdf_path, docx_path = generate_samples(args.dir)
        print(f"Wrote {pdf_path}")
        print(f"Wrote {docx_path}")


def _summarize(args: argparse.Namespace) -> None:
    settings = get_settings()
    pdf_bytes = args.pdf.read_bytes()
    style_bytes = args.style.read_bytes() if args.style else None
    style_filename = args.style.name if args.style else None
    result = asyncio.run(
        summarize_pdf(
            pdf_bytes,
            args.pdf.name,
            settings,
            style_bytes=style_bytes,
            style_filename=style_filename,
            extra_instructions=args.notes,
            model_verify=not args.no_verify,
        )
    )
    if args.output:
        args.output.write_text(result.markdown, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        sys.stdout.write(result.markdown)
        if not result.markdown.endswith("\n"):
            sys.stdout.write("\n")
    if args.docx:
        args.docx.write_bytes(markdown_to_docx(result.markdown))
        print(f"Wrote {args.docx}")
    report_path = _check_report_path(args.output, args.docx)
    if report_path is not None:
        report_path.write_text(result.check_report, encoding="utf-8")
        print(f"Wrote {report_path}")
    print(result.check_report, file=sys.stderr)
    print(
        f"{result.page_count} PDF pages · {result.verify_summary_line()} · {result.model}",
        file=sys.stderr,
    )


def _check_report_path(markdown_path: Path | None, docx_path: Path | None) -> Path | None:
    """Sibling ``*.check.md``. Prefer the Markdown output when both are set."""
    anchor = markdown_path or docx_path
    if anchor is None:
        return None
    return anchor.with_name(f"{anchor.stem}.check.md")


def _serve(args: argparse.Namespace) -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "interpreter_summary.web.app:app",
        host=args.host or settings.host,
        port=args.port or settings.port,
        reload=False,
    )
