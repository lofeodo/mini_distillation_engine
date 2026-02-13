# Hypertension Protocol — Human Summary (`inesss_hypertension__v1`)

**Guideline:** `inesss_hypertension`
**Human review required:** `True`

## How to read this
Answer each question in order. The question text is pulled directly from the guideline whenever possible. Citations show exactly where it came from.

## 1. Eligibility
**Guideline text:** ► Personne de 18 ans ou plus atteinte d’hypertension artérielle

- ✅ If **YES** → Continue to next step.
- ❌ If **NO**  → Not applicable (outside population)

**Evidence:** `c0001:6-6`

## 2. Exclusions / Contraindications
**Guideline text:** ► Pression artérielle systolique supérieure ou égale à 180 mm Hg OU pression artérielle diastolique supérieure ou égale à 110 mm Hg DIRECTIVES 1. PRÉCAUTIONS Consulter le guide Prise en charge systématisée des personnes atteintes d’hypertension artérielle, élaboré par la Société québécoise d’hypertension artérielle (S…

- ✅ If **YES** → Excluded / contraindicated
- ❌ If **NO**  → Continue to next step.

**Evidence:** `c0001:9-15`, `c0003:49-49`, `c0008:118-118`

## 3. Red Flags / Escalation
**Guideline text:** True if any guideline red flag is present.

- ✅ If **YES** → Guideline red flags present: escalate to urgent evaluation / clinician-directed management per guideline context.
- ❌ If **NO**  → No exclusions/contraindications and no red flags detected. Review the extracted guideline facts and apply clinically. This workflow is a structured summary, not autonomous medical decision-making.

**Evidence:** *(none found in this run)*

---
# Appendix — Engine View (for audit/debug)

- start_node_id: `d0001`

## Inputs (engine IDs)
- `in001` `meets_population` (bool): True if the patient matches the guideline population definition.
- `in002` `has_exclusion_or_contraindication` (bool): True if any guideline exclusion or contraindication applies.
- `in003` `has_red_flags` (bool): True if any guideline red flag is present.

## Decision chain (engine)
- `d0001`: condition=`in001 == true` true_next=`d0002` false_next=`e0001`
- `d0002`: condition=`in002 == true` true_next=`e0002` false_next=`d0003`
- `d0003`: condition=`in003 == true` true_next=`a0001` false_next=`a0002`

## Actions (engine)
- `a0001`: Guideline red flags present: escalate to urgent evaluation / clinician-directed management per guideline context.
- `a0002`: No exclusions/contraindications and no red flags detected. Review the extracted guideline facts and apply clinically. This workflow is a structured summary, not autonomous medical decision-making.
  - Evidence: `c0001:6-6`, `c0002:16-16`, `c0004:55-55`, `c0005:71-71`, `c0006:84-84`, `c0007:112-112`, `c0009:127-127`, `c0010:152-152`

## End states (engine)
- `e0001`: Not applicable (outside population)
- `e0002`: Excluded / contraindicated
