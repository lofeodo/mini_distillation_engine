# Workflow Audit Preview — `inesss_hypertension__v1`

- guideline_id: `inesss_hypertension`
- start_node_id: `d0001`
- requires_human_review: `True`

## Warnings

- Step7: no RED_FLAG facts found; the red-flag decision node is a template gate with no fact-derived criteria in this run.

## Inputs

- **in001** `meets_population` (bool): True if the patient matches the guideline population definition.
- **in002** `has_exclusion_or_contraindication` (bool): True if any guideline exclusion or contraindication applies.
- **in003** `has_red_flags` (bool): True if any guideline red flag is present.

## Nodes

### `a0001` (action)

- action: Guideline red flags present: escalate to urgent evaluation / clinician-directed management per guideline context.
- requires_human_review: `True`

_No citations._

### `a0002` (action)

- action: No exclusions/contraindications and no red flags detected. Review the extracted guideline facts and apply clinically. This workflow is a structured summary, not autonomous medical decision-making.
- requires_human_review: `True`

_Citations: 8_

**[1]** `c0001:6-6`

```text
[c0001:6-6]
0006: ► Personne de 18 ans ou plus atteinte d’hypertension artérielle
```

**[2]** `c0002:16-16`

```text
[c0002:16-16]
0016: Atteindre les valeurs cibles chez les personnes atteintes d’hypertension artérielle afin de prévenir les complications cardiovasculaires et cérébrovasculaires.
```

**[3]** `c0004:55-55`

```text
[c0004:55-55]
0055: Effets indésirables Déshydratation médicamenteux les plus Dysfonction sexuelle (homme et femme) fréquents
```

**[4]** `c0005:71-71`

```text
[c0005:71-71]
0071: *L’intervalle d’ajustement minimal indiqué représente le temps requis généralement pour obtenir l’effet maximal.
```

**[5]** `c0006:84-84`

```text
[c0006:84-84]
0084: La réévaluation de la posologie ou une interruption du traitement peuvent être nécessaires si l’instauration de l’IECA induit une augmentation de la créatinine de base de plus de 30 % ou en présence d’insuffisance rénale grave.
```

**[6]** `c0007:112-112`

```text
[c0007:112-112]
0112: *L’intervalle d’ajustement minimal indiqué représente le temps requis généralement pour obtenir l’effet maximal.
```

**[7]** `c0009:127-127`

```text
[c0009:127-127]
0127: Prudence chez les personnes à risque d’hypotension ou d’étourdissements lors de l’administration concomitante d’un ARA et d’un inhibiteur du SGLT2
```

**[8]** `c0010:152-152`

```text
[c0010:152-152]
0152: *L’intervalle d’ajustement minimal indiqué représente le temps requis généralement pour obtenir l’effet maximal.
```


### `d0001` (decision)

- condition: `in001 == true`
- true_next: `d0002`
- false_next: `e0001`

_Citations: 1_

**[1]** `c0001:6-6`

```text
[c0001:6-6]
0006: ► Personne de 18 ans ou plus atteinte d’hypertension artérielle
```


### `d0002` (decision)

- condition: `in002 == true`
- true_next: `e0002`
- false_next: `d0003`

_Citations: 3_

**[1]** `c0001:9-15`

```text
[c0001:9-15]
0009: ► Pression artérielle systolique supérieure ou égale à 180 mm Hg OU pression artérielle diastolique supérieure ou égale à 110 mm Hg
0010: DIRECTIVES
0011: 1. PRÉCAUTIONS
0012: Consulter le guide Prise en charge systématisée des personnes atteintes d’hypertension artérielle, élaboré par la
0013: Société québécoise d’hypertension artérielle (SQHA), pour les méthodes de mesure de la pression artérielle.
0014: Optimiser avec une équipe interprofessionnelle les habitudes de vie et la prise en charge des conditions qui font augmenter la pression artérielle.
0015: 2. PRINCIPES GÉNÉRAUX
```

**[2]** `c0003:49-49`

```text
[c0003:49-49]
0049: Contre-indications Antécédent de réaction allergique ou intolérance connue aux diurétiques thiazidiques ou apparentés
```

**[3]** `c0008:118-118`

```text
[c0008:118-118]
0118: Contre-indications Antécédent de réaction allergique, intolérance ou antécédent d’angiœdème lié à un traitement antérieur avec un ARA
```


### `d0003` (decision)

- condition: `in003 == true`
- true_next: `a0001`
- false_next: `a0002`

_No citations._

### `e0001` (end)

- label: Not applicable (outside population)

_No citations._

### `e0002` (end)

- label: Excluded / contraindicated

_No citations._
