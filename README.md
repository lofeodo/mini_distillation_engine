# Mini Guideline Distillation Engine

This repository contains a small, end-to-end demonstration of how large language models can be used responsibly to transform short clinical guidelines into structured, auditable, machine-executable workflows.

The project is intentionally scoped and conservative. It does **not** claim clinical autonomy or replacement. Instead, it focuses on traceability, validation, and engineering discipline aligned with real-world clinical workflow software.

---

## Overview

The system ingests a short clinical guideline (1–2 pages of text), stored verbatim with line numbers for traceability, and produces:

- A validated `workflow.json` representing a structured clinical decision workflow
- A human-readable `workflow.md` preview for review and auditing

The pipeline uses **local inference only** with an instruction-tuned LLM and consists of two explicit model passes:

1. **Extraction pass**  
   The model extracts only explicitly stated clinical facts (e.g. thresholds, populations, exclusions, actions) under a strict JSON schema.  
   Every extracted item must include a citation referencing a specific source chunk and line range.

2. **Synthesis pass**  
   Extracted facts are deterministically transformed into a structured decision workflow composed of inputs, decision nodes, and actions.  
   Ambiguous guideline language (e.g. “consider”, “may”) is explicitly flagged for human review.

All outputs are validated using deterministic schema checks to ensure correctness, citation completeness, and auditability.

---

## Design Principles

- **Local, offline inference** (no external APIs)
- **Strict schema enforcement** (Pydantic / JSON Schema)
- **Full traceability** from workflow nodes back to source text
- **Deterministic validation layers**
- **No over-engineering** (no vector databases, no orchestration frameworks)

The goal is to demonstrate engineering judgment and safety, not LLM “magic”.

---

## Environment Setup

```bash
conda env create -f environment.yml
conda activate guideline-distiller
```

Alternatively:

```bash
conda create -n guideline-distiller python=3.10
conda activate guideline-distiller
pip install -r requirements.txt
```

---

## Sanity Check

A notebook is provided to verify the environment, model loading, tokenization, and schema validation:

```
notebooks/00_environment_sanity.ipynb
```

---

## Repository Structure
```
.
├── data/
│   └── guideline.txt # Verbatim guideline line numbers
├── notebooks/
│   └── 00_environment_sanity.ipynb
├── schemas/
│   ├── extraction_schema.py
│   └── workflow_schema.py
├── pipeline/
│   ├── extract.py
│   ├── synthesize.py
│   └── validate.py
├── outputs/
│   ├── workflow.json
│   └── workflow.md
├── environment.yml
├── requirements.txt
└── README.md
```

---

## Disclaimer

This project is a technical demonstration only.
It is not intended for clinical use and does not replace clinical judgment, professional guidelines, or regulatory review.

---
