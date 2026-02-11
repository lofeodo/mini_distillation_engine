# pipeline/source_to_guideline.py
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

# PDF
try:
    import pdfplumber  # type: ignore
except Exception:
    pdfplumber = None

try:
    from pypdf import PdfReader  # type: ignore
except Exception:
    PdfReader = None

# HTML
from bs4 import BeautifulSoup  # type: ignore


@dataclass(frozen=True)
class SourceToGuidelineConfig:
    # Paragraph formatting
    wrap_width: int = 0  # 0 = don't hard-wrap; keep paragraphs as single lines
    # Basic cleanup
    remove_multiple_spaces: bool = True
    dehyphenate_linebreaks: bool = True
    # Heuristics for PDF cleanup
    drop_page_numbers: bool = True
    drop_repeated_headers_footers: bool = True
    header_footer_max_lines: int = 2  # consider top/bottom N lines as header/footer candidates


# ----------------------------
# Public API
# ----------------------------

def build_guideline_txt_from_pdf(pdf_path: Path, out_path: Path, cfg: SourceToGuidelineConfig = SourceToGuidelineConfig()) -> None:
    text_blocks = _extract_pdf_text_blocks(pdf_path)
    if not text_blocks or not any(b.strip() for b in text_blocks):
        raise ValueError(
            f"No text extracted from PDF: {pdf_path}. "
            "PDF may be protected, have unusual encoding/layout, or extraction backend failed."
        )
    
    lines = _normalize_blocks_to_lines(text_blocks, cfg=cfg)
    if not lines:
        raise ValueError(
            f"Text extracted but normalization produced 0 lines for: {pdf_path}. "
            "Normalization heuristics may be too aggressive."
        )

    numbered = _apply_line_numbers(lines)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(numbered, encoding="utf-8")


def build_guideline_txt_from_html(html_path: Path, out_path: Path, cfg: SourceToGuidelineConfig = SourceToGuidelineConfig()) -> None:
    html = html_path.read_text(encoding="utf-8")
    blocks = _extract_html_text_blocks(html)
    lines = _normalize_blocks_to_lines(blocks, cfg=cfg)
    numbered = _apply_line_numbers(lines)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(numbered, encoding="utf-8")


# ----------------------------
# PDF extraction
# ----------------------------

def _extract_pdf_text_blocks(pdf_path: Path) -> List[str]:
    """
    Returns a list of "blocks" (roughly paragraphs/lines). No OCR.
    If the PDF is scanned (image-only), this will likely return empty text.
    """
    if pdfplumber is not None:
        blocks: List[str] = []
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                # extract_text gives a best-effort layout text with line breaks
                txt = page.extract_text() or ""
                if txt.strip():
                    blocks.extend(txt.splitlines())
        if blocks:
            return blocks

    # fallback: pypdf
    if PdfReader is None:
        raise RuntimeError("No PDF backend available. Install pdfplumber or pypdf.")

    reader = PdfReader(str(pdf_path))
    blocks = []
    for page in reader.pages:
        txt = page.extract_text() or ""
        if txt.strip():
            blocks.extend(txt.splitlines())
    return blocks


# ----------------------------
# HTML extraction
# ----------------------------

def _extract_html_text_blocks(html: str) -> List[str]:
    soup = BeautifulSoup(html, "lxml")

    # remove common non-content
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
        tag.decompose()

    # Prefer semantically meaningful blocks
    blocks: List[str] = []

    # headings + paragraphs + list items are usually enough for guidelines
    for el in soup.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        txt = el.get_text(" ", strip=True)
        if txt:
            blocks.append(txt)

    # Fallback if it's super minimal HTML
    if not blocks:
        txt = soup.get_text("\n", strip=True)
        blocks = [line.strip() for line in txt.splitlines() if line.strip()]

    return blocks


# ----------------------------
# Normalization / cleanup
# ----------------------------

def _normalize_blocks_to_lines(blocks: List[str], cfg: SourceToGuidelineConfig) -> List[str]:
    # Trim and drop empties
    raw_lines = [b.strip() for b in blocks if b and b.strip()]

    # Remove repeated headers/footers across pages (best-effort for PDFs)
    lines = raw_lines
    if cfg.drop_repeated_headers_footers:
        lines = _drop_repeated_header_footer_lines(lines, cfg)

    # Cleanup spaces
    cleaned: List[str] = []
    for ln in lines:
        if cfg.drop_page_numbers and _looks_like_page_number(ln):
            continue

        ln2 = ln
        if cfg.remove_multiple_spaces:
            ln2 = re.sub(r"\s{2,}", " ", ln2).strip()

        cleaned.append(ln2)

    # Dehyphenate cases like:
    # "recom-\n mendation"  -> "recommendation"
    if cfg.dehyphenate_linebreaks:
        cleaned = _dehyphenate(cleaned)

    # Merge broken lines into paragraphs (simple heuristic):
    # If a line doesn't end with punctuation and next line starts lowercase, merge.
    merged = _merge_soft_wrapped_lines(cleaned)

    # Optional hard wrap (usually you DON'T want this—keep each paragraph as one line)
    if cfg.wrap_width and cfg.wrap_width > 0:
        merged = _hard_wrap(merged, width=cfg.wrap_width)

    return merged


def _drop_repeated_header_footer_lines(lines: List[str], cfg: SourceToGuidelineConfig) -> List[str]:
    """
    Best-effort: detect lines that repeat very frequently and look like headers/footers.
    This is intentionally conservative: only removes lines that occur many times.
    """
    from collections import Counter

    counts = Counter(lines)
    # heuristic: if a line appears >= 4 times, it's likely a header/footer/boilerplate
    frequent = {ln for ln, c in counts.items() if c >= 4 and len(ln) <= 120}

    # But avoid removing genuine repeated guideline phrases:
    # only remove if it contains typical header/footer patterns
    def is_header_footerish(s: str) -> bool:
        s_low = s.lower()
        return any(k in s_low for k in ["page", "copyright", "©", "http", "www.", "ines", "msss"]) or _looks_like_page_number(s)

    remove = {ln for ln in frequent if is_header_footerish(ln)}

    return [ln for ln in lines if ln not in remove]


def _looks_like_page_number(s: str) -> bool:
    s2 = s.strip().lower()
    if re.fullmatch(r"\d{1,3}", s2):
        return True
    if re.fullmatch(r"page\s*\d{1,3}", s2):
        return True
    if re.fullmatch(r"\d{1,3}\s*/\s*\d{1,3}", s2):
        return True
    return False


def _dehyphenate(lines: List[str]) -> List[str]:
    out: List[str] = []
    i = 0
    while i < len(lines):
        cur = lines[i]
        if cur.endswith("-") and i + 1 < len(lines):
            nxt = lines[i + 1]
            # only dehyphenate if next starts with a lowercase letter (common word break)
            if nxt and nxt[0].islower():
                out.append(cur[:-1] + nxt)
                i += 2
                continue
        out.append(cur)
        i += 1
    return out


def _merge_soft_wrapped_lines(lines: List[str]) -> List[str]:
    if not lines:
        return []

    merged: List[str] = []
    buf = lines[0]

    def ends_like_paragraph(s: str) -> bool:
        return bool(re.search(r"[.;:!?]$", s.strip()))

    for nxt in lines[1:]:
        # Bullet lines should stay separate
        if re.match(r"^(\-|\*|•|\d+\.)\s+", nxt):
            merged.append(buf)
            buf = nxt
            continue

        # If buffer doesn't end like a paragraph, and next starts lowercase, merge
        if (not ends_like_paragraph(buf)) and nxt and nxt[0].islower():
            buf = f"{buf} {nxt}".strip()
        else:
            merged.append(buf)
            buf = nxt

    merged.append(buf)
    return merged


def _hard_wrap(lines: List[str], width: int) -> List[str]:
    wrapped: List[str] = []
    for ln in lines:
        if len(ln) <= width:
            wrapped.append(ln)
            continue
        # naive wrap on spaces
        words = ln.split(" ")
        cur = ""
        for w in words:
            if not cur:
                cur = w
            elif len(cur) + 1 + len(w) <= width:
                cur += " " + w
            else:
                wrapped.append(cur)
                cur = w
        if cur:
            wrapped.append(cur)
    return wrapped


# ----------------------------
# Line numbering output
# ----------------------------

def _apply_line_numbers(lines: List[str]) -> str:
    """
    Emit the canonical guideline.txt format:
      1. first line
      2. second line
      ...
    """
    out_lines = []
    n = 1
    for ln in lines:
        ln2 = ln.strip()
        if not ln2:
            continue
        out_lines.append(f"{n}. {ln2}")
        n += 1
    return "\n".join(out_lines) + "\n"