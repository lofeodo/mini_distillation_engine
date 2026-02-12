# Mini Guideline Distillation Engine

This repository contains a small, end-to-end demonstration of how large language models can be used responsibly to transform short clinical guidelines into structured, auditable, machine-executable workflows.

The project is intentionally scoped and conservative. It does **not** claim clinical autonomy or replacement. Instead, it focuses on traceability, validation, deterministic synthesis, and engineering discipline aligned with real-world clinical workflow software.

---

## Overview

The system ingests a short clinical guideline (1–2 pages of text), stored verbatim with line numbers for full traceability, and produces:

* A validated `step7_workflow.json` representing a structured clinical decision workflow
* A human-readable audit view (`step8_workflow_audit.md`)
* A clinician-oriented summary (`step9_clinical_summary.md`)
* Artifact integrity metadata (`step10_run_metadata.json`)

The pipeline uses **local inference only** with an instruction-tuned LLM and consists of two explicit model passes:

### 1. Extraction Pass

The model extracts only explicitly stated clinical facts (e.g. population definitions, thresholds, exclusions, contraindications, actions) under a strict JSON schema.

Every extracted item must include:

* A citation
* A chunk reference
* A line number range

Outputs are validated against strict Pydantic schemas and rejected if malformed.

---

### 2. Synthesis Pass

Extracted facts are deterministically transformed into a structured decision workflow composed of:

* Inputs
* Decision nodes
* Action nodes
* End states

Ambiguous language (e.g. “consider”, “may”) is explicitly flagged for human review.

No medical logic is invented.
The workflow structure is derived strictly from validated extracted facts.

---

## End-to-End Flow

```
Guideline Text
→ Deterministic Ingestion
→ Schema Validation
→ Citation Index
→ LLM Extraction
→ Deterministic Post-Processing
→ Workflow Synthesis
→ Audit Rendering
→ Human-Readable Summary
→ Integrity Metadata
```

---

## Design Principles

* **Local, offline inference** (no external APIs)
* **Strict schema enforcement** (Pydantic v2 with `extra="forbid"`)
* **Full traceability** from workflow nodes back to source lines
* **Deterministic post-processing**
* **Fail-closed validation at every stage**
* **Clear separation of machine view vs. human view**
* **No unnecessary infrastructure** (no vector DB, no orchestration frameworks)

The LLM performs interpretation.
The system performs control.

---

## Repository Structure

```
.
├── data/
│   └── guideline.txt                # Verbatim guideline (line-numbered)
│
├── notebooks/
│   └── 00_environment_sanity.ipynb
│
├── schemas/
│   ├── schemas_extraction.py
│   └── schemas_workflow.py
│
├── pipeline/
│   ├── ingest.py
│   ├── chunk.py
│   ├── llm.py
│   ├── extract.py
│   ├── normalize.py
│   ├── synthesize_workflow.py
│   ├── traceability.py
│   ├── validate_citations.py
│   ├── validate_workflow.py
│   ├── render_workflow_md.py
│   ├── render_clinical_summary.py
│   ├── run_step1.py
│   ├── run_step2.py
│   ├── run_step3.py
│   ├── run_step4.py
│   ├── run_step5.py
│   ├── run_step6.py
│   ├── run_step7.py
│   ├── run_step8.py
│   ├── run_step9.py
│   └── run_all.py
│
├── outputs/
│   ├── step7_workflow.json
│   ├── step8_workflow_audit.md
│   ├── step9_clinical_summary.md
│   ├── step10_artifact_hashes.json
│   └── step10_run_metadata.json
│
├── environment.yml
├── requirements.txt
└── README.md
```

---

## Environment Setup

Using Conda:

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

The system runs fully offline after the initial model download.

---

## Running the Full Pipeline

From the repository root:

```bash
python -m pipeline.run_all
```

Optional:

```bash
python -m pipeline.run_all --resume
python -m pipeline.run_all --no-hashes
```

This executes Steps 1–9 sequentially and generates:

* Structured workflow (`step7_workflow.json`)
* Audit preview (`step8_workflow_audit.md`)
* Human summary (`step9_clinical_summary.md`)
* Execution metadata (`step10_run_metadata.json`)

---

## Output Types

### 1. Machine Workflow (`step7_workflow.json`)

A strict DAG containing:

* Stable node IDs
* Deterministic edges
* Explicit human review flags
* Full citation references

This file is executable.

---

### 2. Audit View (`step8_workflow_audit.md`)

Shows:

* Nodes
* Transitions
* Citations
* Source line references

Designed for traceability and regulatory review.

---

### 3. Human Summary (`step9_clinical_summary.md`)

Presents the workflow in plain-language format using:

* Real guideline text snippets
* Sequential clinical questions
* Clear YES/NO routing

Engine IDs are hidden in the main view and retained only in an appendix.

---

### 4. Integrity Metadata (`step10_run_metadata.json`)

Records:

* Python version
* CUDA availability
* Model ID
* Artifact hashes
* Execution order

Ensures reproducibility and auditability.

---

## What This Demonstrates

This project demonstrates:

* Responsible LLM integration
* Deterministic validation layers
* Strict schema contracts
* Full source traceability
* Offline reproducibility
* Clear separation between:

  * Extraction (probabilistic)
  * Synthesis (deterministic)
  * Rendering (presentation)

The objective is engineering rigor, not generative novelty.

---

## Limitations

* Designed for short, structured guidelines
* No multi-document reconciliation
* No probabilistic decision scoring
* Not intended for production clinical deployment
* Requires clinician review for all outputs

---

## Disclaimer

This project is a technical demonstration only.
It is not intended for clinical use and does not replace clinical judgment, professional guidelines, or regulatory review.