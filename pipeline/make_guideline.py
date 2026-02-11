# pipeline/make_guideline.py
from __future__ import annotations

import argparse
from pathlib import Path

from .source_to_guideline import (
    SourceToGuidelineConfig,
    build_guideline_txt_from_pdf,
    build_guideline_txt_from_html,
)

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--pdf", type=str, default=None, help="Path to source PDF")
    p.add_argument("--html", type=str, default=None, help="Path to source HTML file")
    p.add_argument("--out", type=str, default="data/guideline.txt", help="Output guideline.txt path")
    args = p.parse_args()

    out_path = Path(args.out)
    cfg = SourceToGuidelineConfig()

    if args.pdf:
        build_guideline_txt_from_pdf(Path(args.pdf), out_path, cfg)
        print(f"Wrote {out_path} from PDF.")
    elif args.html:
        build_guideline_txt_from_html(Path(args.html), out_path, cfg)
        print(f"Wrote {out_path} from HTML.")
    else:
        raise SystemExit("Provide --pdf or --html")

if __name__ == "__main__":
    main()
