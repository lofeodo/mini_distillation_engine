# pipeline/normalize.py
from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, List, Tuple, Optional, Set, Any

from schemas.schemas_extraction import (
    ExtractionOutput,
    ExtractedFact,
    Citation,
    FactType,
    Strength,
)

_WS_RE = re.compile(r"\s+")
_DASHES_RE = re.compile(r"[‐-‒–—]")
# keep some punctuation useful in medical text: % / . : - ( ) ’ '
_KEEP_PUNCT_RE = re.compile(r"[^\w\s/%\.\:\-\(\)’']+")

_STOP = {
    # EN
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "with", "on", "at", "by", "as", "is", "are",
    # FR
    "le", "la", "les", "un", "une", "des", "et", "ou", "de", "du", "au", "aux", "dans", "pour", "avec",
    "sur", "chez", "en", "est", "sont", "être",
}

# High-precision header-ish tokens (FR + EN)
_HEADER_TOKENS = {
    "table", "figure", "annexe", "référence", "references",
    "médicament", "médicaments", "medicament", "medicaments",
    "posologie", "dose", "doses", "dosage",
    "modalités", "modalites", "ajustement",
    "contre-indications", "contreindications", "contraindications",
    "effets", "indésirables", "indesirables", "adverse", "effects",
    "classe", "class",
    "sbp", "dbp", "ta", "pa", "bp", "mmhg", "mg", "g", "ml",
    "bid", "tid", "qid", "po",
}


@dataclass(frozen=True)
class NormalizeConfig:
    min_chars: int = 10
    fuzzy_threshold: float = 0.94
    max_fuzzy_comp_per_type: int = 8000  # safety cap
    citation_tighten_max_window: int = 4  # max lines to join when matching statements


def normalize_text(s: str) -> str:
    t = s.strip()
    t = _DASHES_RE.sub("-", t)
    t = t.replace("•", "- ")
    t = _KEEP_PUNCT_RE.sub("", t)
    t = _WS_RE.sub(" ", t).strip()
    # drop trailing ":" (common header formatting)
    if t.endswith(":"):
        t = t[:-1].strip()
    return t


def tokenize(s: str) -> List[str]:
    t = s.lower()
    t = _DASHES_RE.sub(" ", t)
    t = re.sub(r"[^\w\s/%\.\']", " ", t)
    t = _WS_RE.sub(" ", t).strip()
    return [x for x in t.split(" ") if x]


def fingerprint(s: str) -> str:
    toks = tokenize(s)
    kept: List[str] = []
    for tok in toks:
        if tok in _STOP:
            continue
        if tok.isdigit() or len(tok) >= 2:
            kept.append(tok)
    kept.sort()
    return " ".join(kept)


def looks_like_header_or_junk(stmt: str, cfg: NormalizeConfig) -> bool:
    if len(stmt) < cfg.min_chars:
        return True

    toks = tokenize(stmt)
    if not toks:
        return True

    header_hits = sum(1 for x in toks if x in _HEADER_TOKENS)
    if header_hits >= 2 and len(toks) <= 10:
        return True

    if toks[0] in {"table", "figure", "annexe"}:
        return True

    return False


def refine_fact_type(stmt: str, current: FactType) -> FactType:
    s = stmt.lower()

    if any(k in s for k in ["contre-indication", "contre indication", "contraindication", "do not", "ne pas", "éviter", "eviter"]):
        return FactType.CONTRAINDICATION

    if any(k in s for k in ["exclusion", "grossesse", "allaitement", "pregnancy", "breastfeeding"]):
        return FactType.EXCLUSION

    if any(k in s for k in ["urgence", "urgent", "immédiat", "immediat", "emergency", "immediately", "référer", "refer"]):
        return FactType.RED_FLAG

    if re.search(r"\b(\d{2,3})\s*(mmhg|mg|g|ml)\b", s) or any(k in s for k in ["≥", ">=", "<=", ">", "<"]):
        if current in {FactType.OTHER, FactType.FOLLOW_UP, FactType.DIAGNOSTIC}:
            return FactType.THRESHOLD

    if any(k in s for k in ["suivi", "réévaluation", "reevaluation", "monitor", "reassess", "follow-up", "follow up", "répéter", "repeter", "mesurer", "measure"]):
        if current == FactType.OTHER:
            return FactType.FOLLOW_UP

    if any(k in s for k in ["prescrire", "initier", "commencer", "start", "initiate", "titrer", "titrate", "administrer", "administer"]):
        if current == FactType.OTHER:
            return FactType.ACTION

    if current == FactType.POPULATION:
        if any(k in s for k in ["contre-indication", "contre indication", "contraindication"]):
            return FactType.CONTRAINDICATION

    if current == FactType.POPULATION:
        if any(k in s for k in ["apparition", "aggravation", "signes", "symptômes", "symptomes", "atteinte des organes cibles"]):
            return FactType.FOLLOW_UP

    return current


def refine_strength(stmt: str, current: Strength, fact_type: FactType) -> Strength:
    s = stmt.lower()

    if any(k in s for k in ["do not", "ne pas", "jamais", "never", "contre-indication", "contraindication", "doit", "must", "required"]):
        return Strength.MUST

    if any(k in s for k in ["devrait", "should", "recommand", "recommended", "recommandé", "recommandee"]):
        return Strength.SHOULD

    if any(k in s for k in ["considérer", "consider", "peut être envisagé", "peut etre envisage", "may", "peut"]):
        return Strength.CONSIDER if ("consid" in s or "envisag" in s) else Strength.MAY

    if fact_type in {FactType.EXCLUSION, FactType.CONTRAINDICATION}:
        return Strength.MUST

    if current == Strength.MUST and not any(k in s for k in ["doit", "must", "ne pas", "do not", "recommand", "should", "devrait"]):
        return Strength.UNCLEAR

    return current


def compute_requires_human_review(strength: Strength, current: bool) -> bool:
    if strength in {Strength.MAY, Strength.CONSIDER, Strength.UNCLEAR}:
        return True
    return current


def citation_key(c: Citation) -> Tuple[str, int, int]:
    return (c.chunk_id, c.line_start, c.line_end)


def merge_citations(cits: List[Citation]) -> List[Citation]:
    best: Dict[Tuple[str, int, int], Citation] = {}
    for c in cits:
        k = citation_key(c)
        if k not in best:
            best[k] = c
        else:
            if best[k].quote is None and c.quote is not None:
                best[k] = c

    out = list(best.values())
    out.sort(key=lambda x: (x.chunk_id, x.line_start, x.line_end))
    return out


def choose_rep(facts: List[ExtractedFact]) -> ExtractedFact:
    return sorted(facts, key=lambda f: (-len(f.statement), f.fact_id))[0]


def merge_optional_fields(facts: List[ExtractedFact], rep: ExtractedFact) -> Dict[str, Any]:
    subject = rep.subject
    condition = rep.condition
    action = rep.action
    notes = rep.notes
    raw = rep.raw

    for f in facts:
        if subject is None and f.subject is not None:
            subject = f.subject
        if condition is None and f.condition is not None:
            condition = f.condition
        if action is None and f.action is not None:
            action = f.action
        if notes is None and f.notes is not None:
            notes = f.notes
        if raw is None and f.raw is not None:
            raw = f.raw

    return {
        "subject": subject,
        "condition": condition,
        "action": action,
        "notes": notes,
        "raw": raw,
    }


def fuzzy_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _tighten_citation_span(
    statement: str,
    citation: Citation,
    line_text_by_no: Dict[int, str],
    *,
    max_window: int,
) -> Citation:
    """
    Deterministically shrink a citation's [line_start, line_end] within its current span
    to the smallest sub-span that contains the statement text.
    """
    stmt_norm = normalize_text(statement).lower()

    ls, le = citation.line_start, citation.line_end
    if le < ls:
        ls, le = le, ls

    # collect normalized lines present in span
    span: List[Tuple[int, str]] = []
    for n in range(ls, le + 1):
        txt = line_text_by_no.get(n)
        if txt is None:
            continue
        span.append((n, normalize_text(txt).lower()))

    if not span or not stmt_norm:
        return citation

    # 1) single-line containment
    for n, txt in span:
        if stmt_norm in txt:
            return Citation(chunk_id=citation.chunk_id, line_start=n, line_end=n, quote=citation.quote)

    # 2) sliding window (2..max_window lines)
    # (helps if statement was split across lines)
    max_window = max(2, int(max_window))
    for w in range(2, max_window + 1):
        for i in range(0, len(span) - w + 1):
            n0 = span[i][0]
            n1 = span[i + w - 1][0]
            joined = " ".join(x[1] for x in span[i:i + w])
            if stmt_norm in joined:
                return Citation(chunk_id=citation.chunk_id, line_start=n0, line_end=n1, quote=citation.quote)

    return citation


def normalize_and_canonicalize(
    extraction: ExtractionOutput,
    cfg: NormalizeConfig = NormalizeConfig(),
    line_text_by_no: Optional[Dict[int, str]] = None,
) -> Tuple[ExtractionOutput, List[str]]:
    warnings: List[str] = []

    # 1) normalize + filter + light refine
    kept: List[ExtractedFact] = []
    dropped = 0
    for f in extraction.extracted_facts:
        stmt = normalize_text(f.statement)

        if looks_like_header_or_junk(stmt, cfg):
            dropped += 1
            continue

        new_type = refine_fact_type(stmt, f.fact_type)
        new_strength = refine_strength(stmt, f.strength, new_type)
        new_rhr = compute_requires_human_review(new_strength, f.requires_human_review)

        kept.append(
            ExtractedFact(
                fact_id=f.fact_id,  # re-id later
                fact_type=new_type,
                statement=stmt,
                strength=new_strength,
                requires_human_review=new_rhr,
                subject=f.subject,
                condition=f.condition,
                action=f.action,
                notes=f.notes,
                citations=f.citations,
                raw=f.raw,
            )
        )

    if dropped:
        warnings.append(f"Step6: dropped {dropped} header/junk facts deterministically.")

    # 2) exact dedup by (fact_type, fingerprint)
    buckets: Dict[Tuple[FactType, str], List[ExtractedFact]] = {}
    for f in kept:
        buckets.setdefault((f.fact_type, fingerprint(f.statement)), []).append(f)

    merged_exact: List[ExtractedFact] = []
    exact_merges = 0
    for (ft, fp), facts in buckets.items():
        if len(facts) == 1:
            merged_exact.append(facts[0])
            continue

        exact_merges += (len(facts) - 1)
        rep = choose_rep(facts)
        merged = ExtractedFact(
            fact_id=rep.fact_id,
            fact_type=ft,
            statement=rep.statement,
            strength=max(
                (x.strength for x in facts),
                key=lambda s: [Strength.UNCLEAR, Strength.MAY, Strength.CONSIDER, Strength.SHOULD, Strength.MUST].index(s),
            ),
            requires_human_review=any(x.requires_human_review for x in facts),
            citations=merge_citations([c for x in facts for c in x.citations]),
            **merge_optional_fields(facts, rep),
        )
        merged_exact.append(merged)

    if exact_merges:
        warnings.append(f"Step6: merged {exact_merges} duplicates by canonical fingerprint.")

    # 3) fuzzy dedup within same fact_type (bounded)
    by_type: Dict[FactType, List[ExtractedFact]] = {}
    for f in merged_exact:
        by_type.setdefault(f.fact_type, []).append(f)

    merged_fuzzy: List[ExtractedFact] = []
    fuzzy_merges = 0

    for ft, facts in by_type.items():
        facts = sorted(facts, key=lambda x: x.statement.lower())
        used: Set[int] = set()
        comps = 0

        for i in range(len(facts)):
            if i in used:
                continue
            group = [facts[i]]
            used.add(i)
            a = facts[i].statement.lower()

            for j in range(i + 1, len(facts)):
                if j in used:
                    continue
                comps += 1
                if comps > cfg.max_fuzzy_comp_per_type:
                    warnings.append(f"Step6: fuzzy scan capped for {ft.value}; remaining kept as-is.")
                    break

                b = facts[j].statement.lower()
                if fuzzy_ratio(a, b) >= cfg.fuzzy_threshold:
                    group.append(facts[j])
                    used.add(j)

            if len(group) == 1:
                merged_fuzzy.append(group[0])
            else:
                fuzzy_merges += (len(group) - 1)
                rep = choose_rep(group)
                merged = ExtractedFact(
                    fact_id=rep.fact_id,
                    fact_type=ft,
                    statement=rep.statement,
                    strength=max(
                        (x.strength for x in group),
                        key=lambda s: [Strength.UNCLEAR, Strength.MAY, Strength.CONSIDER, Strength.SHOULD, Strength.MUST].index(s),
                    ),
                    requires_human_review=any(x.requires_human_review for x in group),
                    citations=merge_citations([c for x in group for c in x.citations]),
                    **merge_optional_fields(group, rep),
                )
                merged_fuzzy.append(merged)

    if fuzzy_merges:
        warnings.append(f"Step6: merged {fuzzy_merges} near-duplicates by fuzzy matching.")

    # 3.5) tighten citations deterministically using line text (if provided)
    if line_text_by_no is not None:
        tightened: List[ExtractedFact] = []
        changed = 0
        for f in merged_fuzzy:
            new_cits = []
            for c in f.citations:
                tightened_c = _tighten_citation_span(
                    f.statement,
                    c,
                    line_text_by_no,
                    max_window=cfg.citation_tighten_max_window,
                )
                if (tightened_c.line_start, tightened_c.line_end) != (c.line_start, c.line_end):
                    changed += 1
                new_cits.append(tightened_c)

            tightened.append(
                ExtractedFact(
                    fact_id=f.fact_id,
                    fact_type=f.fact_type,
                    statement=f.statement,
                    strength=f.strength,
                    requires_human_review=f.requires_human_review,
                    subject=f.subject,
                    condition=f.condition,
                    action=f.action,
                    notes=f.notes,
                    citations=new_cits,
                    raw=f.raw,
                )
            )

        merged_fuzzy = tightened
        if changed:
            warnings.append(f"Step6: tightened {changed} citation spans using exact statement matching.")

    # 4) deterministic re-id
    merged_fuzzy.sort(key=lambda f: (f.fact_type.value, f.statement.lower(), f.fact_id))
    re_facts: List[ExtractedFact] = []
    for idx, f in enumerate(merged_fuzzy, start=1):
        re_facts.append(
            ExtractedFact(
                fact_id=f"f{idx:04d}",
                fact_type=f.fact_type,
                statement=f.statement,
                strength=f.strength,
                requires_human_review=f.requires_human_review,
                subject=f.subject,
                condition=f.condition,
                action=f.action,
                notes=f.notes,
                citations=f.citations,
                raw=f.raw,
            )
        )

    out = ExtractionOutput(
        guideline_id=extraction.guideline_id,
        model_id=extraction.model_id,
        chunking=extraction.chunking,
        extracted_facts=re_facts,
        warnings=list(extraction.warnings) + warnings,
        meta={**extraction.meta, "step6": {"dropped": dropped, "exact_merges": exact_merges, "fuzzy_merges": fuzzy_merges}},
    )
    return out, warnings