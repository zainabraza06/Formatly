"""Execute a paper-spec JSON and produce the DOCX.

    # render an existing spec
    python -m app.paper.cli spec.json paper.docx

    # generate the spec from raw material, then render it
    python -m app.paper.cli --from-text material.txt paper.docx \
        --code model.py --results results.txt --save-spec spec.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.paper.generator import PaperGenerationError, generate_paper
from app.paper.renderer import render_paper
from app.paper.schema import PaperSpec
from app.paper.styles import DEFAULT_STYLE, list_styles
from app.paper.stylesheet import resolve


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="paper", description="Render an IEEE paper DOCX from a JSON spec.")
    ap.add_argument("spec", nargs="?", help="path to the paper-spec JSON (omit when using --from-text)")
    ap.add_argument("out", help="output .docx path")
    ap.add_argument("--from-text", help="generate the spec from this raw material file via the LLM")
    ap.add_argument("--code", help="optional source-code file to inform the paper")
    ap.add_argument("--results", help="optional model-results file")
    ap.add_argument("--reference", help="optional reference example paper to imitate")
    ap.add_argument("--instructions", help="extra instructions for the writer")
    ap.add_argument("--title", help="title hint")
    ap.add_argument("--save-spec", help="write the generated spec JSON here")
    ap.add_argument("--style", default=None,
                    help=f"document style: {', '.join(s['id'] for s in list_styles())}")
    ap.add_argument("--kind", default="paper", help="what to write: paper, report, thesis…")
    args = ap.parse_args(argv)

    if args.from_text:
        try:
            spec, provider = generate_paper(
                raw_text=Path(args.from_text).read_text(encoding="utf-8"),
                style=args.style or DEFAULT_STYLE,
                doc_kind=args.kind,
                code=_read(args.code),
                results=_read(args.results),
                reference_example=_read(args.reference),
                instructions=args.instructions,
                title_hint=args.title,
            )
        except PaperGenerationError as exc:
            print(f"generation failed: {exc}", file=sys.stderr)
            return 1
        print(f"generated spec via {provider}")
        if args.save_spec:
            Path(args.save_spec).write_text(
                json.dumps(spec.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"spec written to {args.save_spec}")
    else:
        if not args.spec:
            ap.error("provide a spec JSON path, or use --from-text")
        raw = json.loads(Path(args.spec).read_text(encoding="utf-8"))
        spec = resolve(PaperSpec.model_validate(raw), args.style)

    out = render_paper(spec, args.out, style=args.style)
    print(f"DOCX written to {out} [{spec.meta.style}]")
    return 0


def _read(path: str | None) -> str | None:
    return Path(path).read_text(encoding="utf-8") if path else None


if __name__ == "__main__":
    raise SystemExit(main())
