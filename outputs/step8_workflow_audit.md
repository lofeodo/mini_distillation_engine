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

**[1]** `c0001:6-15`

```text
[c0001:6-15]
0006: ► Personne de 18 ans ou plus atteinte d’hypertension artérielle
0007: CONTRE-INDICATIONS À L’APPLICATION DE CE PROTOCOLE
0008: ► Grossesse ou allaitement
0009: ► Pression artérielle systolique supérieure ou égale à 180 mm Hg OU pression artérielle diastolique supérieure ou égale à 110 mm Hg
0010: DIRECTIVES
0011: 1. PRÉCAUTIONS
0012: Consulter le guide Prise en charge systématisée des personnes atteintes d’hypertension artérielle, élaboré par la
0013: Société québécoise d’hypertension artérielle (SQHA), pour les méthodes de mesure de la pression artérielle.
0014: Optimiser avec une équipe interprofessionnelle les habitudes de vie et la prise en charge des conditions qui font augmenter la pression artérielle.
0015: 2. PRINCIPES GÉNÉRAUX
```

**[2]** `c0002:16-35`

```text
[c0002:16-35]
0016: Atteindre les valeurs cibles chez les personnes atteintes d’hypertension artérielle afin de prévenir les complications cardiovasculaires et cérébrovasculaires.
0017: INESSS | Protocole médical national – Médication antihypertensive 1
0018: Mars 2020
0019: 3. INVESTIGATION
0020: 3.1 Analyses et examens de laboratoire pour le suivi de l’ajustement du traitement de l’hypertension artérielle
0021: Effectuer les analyses et examens de laboratoire pour le suivi de l’ajustement du traitement de l’hypertension artérielle selon le tableau ci-dessous :
0022: ANALYSES ET EXAMENS DE LABORATOIRE
0023: 10 à 14 jours
0024: 10 à 14 jours
0025: Avant le début après Une fois par
0026: Analyses / examens Au diagnostic après le début du traitement l’ajustement de année du traitement la dose
0027: Diurétiques Diurétiques Diurétiques
0028: IECA* IECA* IECA*
0029: ARA† ARA† ARA†
0030: Ions : sodium, potassium     
0031: Créatinine     
0032: Glycémie à jeun ou
0033:   hémoglobine glyquée (HbA )
0034: 1C
0035: Bilan lipidique  
```

**[3]** `c0004:55-70`

```text
[c0004:55-70]
0055: Effets indésirables Déshydratation médicamenteux les plus Dysfonction sexuelle (homme et femme) fréquents
0056: Hyperuricémie
0057: Hypokaliémie, hyponatrémie, hypomagnésémie
0058: Insuffisance rénale
0059: Interactions médicamenteuses Anti-inflammatoires non stéroïdiens (AINS) (coxibs et non coxibs) : ↓ de l’effet antihypertenseur les plus significatives Calcium : ↓ de l’excrétion rénale du calcium
0060: Corticostéroïdes : ↑ du risque d’hypokaliémie et ↓ de l’effet antihypertenseur
0061: Digoxine : ↑ du risque de toxicité à la digoxine lié aux perturbations électrolytiques
0062: Hypoglycémiants oraux : ↑ possible de la glycémie
0063: Lithium : ↑ de la lithémie (risque de toxicité accrue)
0064: Inhibiteur du SGLT2 : peut accroître le risque de déshydratation et/ou d’hypotension
0065: Ajuster les diurétiques thiazidiques et apparentés selon les modalités d’ajustement suivantes :
0066: MODALITÉS D’AJUSTEMENT POSOLOGIQUE POUR LA CLASSE DES DIURÉTIQUES THIAZIDIQUES ET APPARENTÉS
0067: Médicaments Modalités d’ajustement posologique†
0068: Chlorthalidone 12,5 → 25 mg PO DIE
0069: Hydrochlorothiazide (HCTZ) 12,5 → 25 mg PO DIE
0070: Indapamide 0,625 → 1,25 → 2,5 mg PO DIE
```

**[4]** `c0005:71-83`

```text
[c0005:71-83]
0071: *L’intervalle d’ajustement minimal indiqué représente le temps requis généralement pour obtenir l’effet maximal.
0072: †Les doses présentées sont celles recommandées dans la majorité des cas.
0073: INESSS | Protocole médical national – Médication antihypertensive 3
0074: Mars 2020
0075: 4.2 Inhibiteurs de l’enzyme de conversion de l’angiotensine (IECA)
0076: INFORMATION GÉNÉRALE POUR LA CLASSE DES IECA
0077: Contre-indications Antécédent de réaction allergique, intolérance ou antécédent d’angiœdème lié à un traitement antérieur avec un IECA ou un ARA
0078: Sténose bilatérale des artères rénales ou sténose unilatérale sur un rein unique
0079: Utilisation concomitante avec un ARA ou un inhibiteur direct de la rénine
0080: Grossesse ou allaitement
0081: Précautions Attention à l’hyperkaliémie, surtout chez les personnes atteintes d’insuffisance rénale chronique, d’insuffisance cardiaque, de diabète ou chez les personnes qui prennent des diurétiques épargneurs de potassium ou des suppléments potassiques.
0082: La prise du médicament doit cesser temporairement si présence de signes de déshydratation
0083: (vomissements, diarrhées importantes) afin d’éviter une insuffisance rénale aiguë.
```

**[5]** `c0006:84-97`

```text
[c0006:84-97]
0084: La réévaluation de la posologie ou une interruption du traitement peuvent être nécessaires si l’instauration de l’IECA induit une augmentation de la créatinine de base de plus de 30 % ou en présence d’insuffisance rénale grave.
0085: Prudence chez les personnes à risque d’hypotension ou d’étourdissements lors de l’administration concomitante d’un IECA et d’un inhibiteur du SGLT2
0086: Effets indésirables Toux médicamenteux les plus Étourdissements fréquents
0087: Hyperkaliémie
0088: Angiœdème (rare, mais grave)
0089: Interactions médicamenteuses Agents causant une ↑ additive des taux de potassium sérique (p. ex. supplément de potassium, les plus significatives diurétiques épargneurs de potassium, succédanés de sel, héparine, triméthoprime)
0090: AINS (coxibs et non coxibs) : ↓ de l’effet antihypertenseur, ↑ de la créatinine
0091: Lithium : ↑ de la lithémie (risque de toxicité accru)
0092: Ajuster les IECA selon les modalités d’ajustement suivantes :
0093: MODALITÉS D’AJUSTEMENT POSOLOGIQUE POUR LA CLASSE DES IECA
0094: Médicaments et combinaisons à
0095: Modalités d’ajustement posologique† dose fixe
0096: Bénazépril 5 → 10 → 20 → 40 mg PO DIE
0097: Captopril 25 → 37,5 → 50 mg PO BID → 50 mg PO TID
```

**[6]** `c0007:112-113`

```text
[c0007:112-113]
0112: *L’intervalle d’ajustement minimal indiqué représente le temps requis généralement pour obtenir l’effet maximal.
0113: † Les doses présentées sont celles recommandées dans la majorité des cas.
```

**[7]** `c0009:127-143`

```text
[c0009:127-143]
0127: Prudence chez les personnes à risque d’hypotension ou d’étourdissements lors de l’administration concomitante d’un ARA et d’un inhibiteur du SGLT2
0128: Effets indésirables Céphalées médicamenteux les plus Étourdissements fréquents
0129: Hyperkaliémie
0130: Angiœdème (rare, mais grave)
0131: Interactions médicamenteuses Agents causant une ↑ additive des taux de potassium sérique (p. ex. supplément de potassium, les plus significatives diurétiques épargneurs de potassium, succédanés de sel, héparine, triméthoprime)
0132: AINS (coxibs et non coxibs) : ↓ de l’effet antihypertenseur, ↑ de la créatinine
0133: Lithium : ↑ de la lithémie (risque de toxicité accrue)
0134: Ajuster les ARA selon les modalités d’ajustement suivantes :
0135: MODALITÉS D’AJUSTEMENT POSOLOGIQUE POUR LA CLASSE DES ARA
0136: Médicaments et combinaisons à
0137: Modalités d’ajustement posologique† dose fixe
0138: Azilsartan 40 → 80 mg PO DIE
0139: Azilsartan / Chlorthalidone 40/12,5 → 40/25 mg PO DIE
0140: Candésartan 4 → 8 → 16 → 32 mg PO DIE
0141: Candésartan / HCTZ 16/12,5 → 32/12,5 → 32/25 mg PO DIE
0142: Irbésartan 75 → 150 → 300 mg PO DIE
0143: Irbésartan / HCTZ 150/12,5 → 300/12,5 → 300/25 mg PO DIE
```

**[8]** `c0010:152-153`

```text
[c0010:152-153]
0152: *L’intervalle d’ajustement minimal indiqué représente le temps requis généralement pour obtenir l’effet maximal.
0153: † Les doses présentées sont celles recommandées dans la majorité des cas.
```


### `d0001` (decision)

- condition: `in001 == true`
- true_next: `d0002`
- false_next: `e0001`

_Citations: 1_

**[1]** `c0001:6-15`

```text
[c0001:6-15]
0006: ► Personne de 18 ans ou plus atteinte d’hypertension artérielle
0007: CONTRE-INDICATIONS À L’APPLICATION DE CE PROTOCOLE
0008: ► Grossesse ou allaitement
0009: ► Pression artérielle systolique supérieure ou égale à 180 mm Hg OU pression artérielle diastolique supérieure ou égale à 110 mm Hg
0010: DIRECTIVES
0011: 1. PRÉCAUTIONS
0012: Consulter le guide Prise en charge systématisée des personnes atteintes d’hypertension artérielle, élaboré par la
0013: Société québécoise d’hypertension artérielle (SQHA), pour les méthodes de mesure de la pression artérielle.
0014: Optimiser avec une équipe interprofessionnelle les habitudes de vie et la prise en charge des conditions qui font augmenter la pression artérielle.
0015: 2. PRINCIPES GÉNÉRAUX
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

**[2]** `c0003:49-50`

```text
[c0003:49-50]
0049: Contre-indications Antécédent de réaction allergique ou intolérance connue aux diurétiques thiazidiques ou apparentés
0050: Anurie
```

**[3]** `c0008:118-126`

```text
[c0008:118-126]
0118: Contre-indications Antécédent de réaction allergique, intolérance ou antécédent d’angiœdème lié à un traitement antérieur avec un ARA
0119: Sténose bilatérale grave des artères rénales ou sténose unilatérale grave sur un rein unique
0120: Utilisation concomitante avec un IECA ou un inhibiteur direct de la rénine
0121: Grossesse ou allaitement
0122: Précautions Attention à l’hyperkaliémie, surtout chez les personnes atteintes d’insuffisance rénale chronique, d’insuffisance cardiaque, de diabète ou chez les personnes qui prennent des diurétiques épargneurs de potassium ou des suppléments potassiques.
0123: Le médicament doit être cessé temporairement si présence de signes de déshydratation
0124: (vomissements, diarrhées importantes) afin d’éviter une insuffisance rénale aiguë.
0125: La réévaluation de la posologie ou une interruption du traitement peuvent être nécessaires si l’instauration de l’ARA induit une augmentation de la créatinine de base de plus de 30 % ou en présence d’insuffisance rénale grave.
0126: Antécédent d’angiœdème lié à un traitement antérieur à un IECA
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
