# Results

A factual record of every result in this repository: the two pre-registered studies, the exploratory analyses run after the first of them, and the development run that preceded both. Every number below is read from the result files named in each section by `scripts/make_results_doc.py`; nothing is retyped. Interpretation is limited to what the pre-registrations allow.

## Overview

The question is whether perspective-taking, cognitive-empathy and justice-sensitivity content brings a language model's distribution of moral verdicts closer to the distribution of human verdicts than a matched control does: in Study 1 an appraisal prompt of the same shape without that content, in Study 2 a mixture of personas varied on morally irrelevant traits. The model is `openai/gpt-oss-20b`, served through OpenRouter by `parasail` only, at temperature 0.8 and top-p 1. The items are 60 anecdotes drawn at random from the Scruples Anecdotes test split, each with a spread of human annotator verdicts over four labels (author, other party, everybody, nobody at fault). The measure is the base-2 Jensen-Shannon divergence (JSD; 0 = identical, 1 = disjoint) between the model's verdicts over 10 samples and the human verdicts (INFO excluded), compared between prompts item by item with 95% paired-item bootstrap intervals (10,000 resamples); a negative difference means the first-named prompt is closer to humans.

**Inference rule** (pre-registered, both studies): a comparison is reported as showing a direction only if its 95% interval excludes zero; otherwise it is reported as not distinguishing the conditions. The intervals cover variation over anecdotes only, not sampling error in the model's draws or uncertainty in the human labels.

## Study 1: held-out three-condition evaluation

Run `results/heldout/7edf899cb4bf44f4`, protocol `heldout_frozen_v1`, pre-registered in [preregistration.md](preregistration.md). Three prompts on the same 60 items, 10 samples per item and prompt: **direct judgment** (`baseline`), a **generic** factual appraisal of similar structure and length (`generic`), and the **moral-cognitive** appraisal (`original`). Parser `final_marker_tolerant_v1`. Responses were collected 2026-10-11 22:44 to 2026-10-12 09:43 UTC.

### Coverage

| Arm | Planned | Recorded | Valid | Failures by status |
| --- | ---: | ---: | ---: | --- |
| direct judgment (`baseline`) | 600 | 600 | 587 | `request_error` 12, `invalid_label_format` 1 |
| generic appraisal (`generic`) | 600 | 600 | 584 | `request_error` 13, `invalid_label_format` 3 |
| moral-cognitive appraisal (`original`) | 600 | 600 | 587 | `request_error` 8, `missing_or_multiple_choices` 1, `invalid_label_format` 1, `unexpected_finish_reason` 2, `missing_content` 1 |

### Primary comparisons

| Comparison | n | Mean JSD, left | Mean JSD, right | Mean difference | 95% CI | Closer / farther / tied | Pre-registered verdict |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| P1: moral-cognitive appraisal − generic appraisal | 60 | 0.2939 | 0.2999 | -0.0059 | [-0.0494, +0.0371] | 26 / 27 / 7 | Not distinguished (interval includes zero) |
| P2: generic appraisal − direct judgment | 60 | 0.2999 | 0.2558 | +0.0441 | [+0.0156, +0.0717] | 12 / 30 / 18 | Generic appraisal farther from humans than direct judgment (interval excludes zero) |

Left and right are the first- and second-named prompts. Each item enters when both of its cells have at least one valid label.

### S1: complete cases

Restricted to items with all planned responses valid in all three arms.

| Comparison | n | Mean JSD, left | Mean JSD, right | Mean difference | 95% CI | Closer / farther / tied | Pre-registered verdict |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| P1: moral-cognitive appraisal − generic appraisal | 29 | 0.2981 | 0.3141 | -0.0160 | [-0.0768, +0.0445] | 13 / 11 / 5 | Not distinguished (interval includes zero) |
| P2: generic appraisal − direct judgment | 29 | 0.3141 | 0.2763 | +0.0378 | [-0.0073, +0.0765] | 4 / 16 / 9 | Not distinguished (interval includes zero) |

### S2: strict parser

The saved responses reparsed under `exact_label_or_final_marker_v3` (`analysis_reparsed.json`). Coverage under that parser:

| Arm | Planned | Recorded | Valid | Failures by status |
| --- | ---: | ---: | ---: | --- |
| direct judgment (`baseline`) | 600 | 600 | 587 | `request_error` 12, `invalid_label_format` 1 |
| generic appraisal (`generic`) | 600 | 600 | 540 | `invalid_label_format` 47, `request_error` 13 |
| moral-cognitive appraisal (`original`) | 600 | 600 | 534 | `invalid_label_format` 54, `request_error` 8, `missing_or_multiple_choices` 1, `unexpected_finish_reason` 2, `missing_content` 1 |

| Comparison | n | Mean JSD, left | Mean JSD, right | Mean difference | 95% CI | Closer / farther / tied | Pre-registered verdict |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| P1: moral-cognitive appraisal − generic appraisal | 60 | 0.2982 | 0.2990 | -0.0008 | [-0.0458, +0.0428] | 25 / 27 / 8 | Not distinguished (interval includes zero) |
| P2: generic appraisal − direct judgment | 60 | 0.2990 | 0.2558 | +0.0432 | [+0.0143, +0.0714] | 12 / 31 / 17 | Generic appraisal farther from humans than direct judgment (interval excludes zero) |

### Moral-cognitive − direct (descriptive)

Not a pre-registered comparison; it conflates the effects that P1 and P2 separate.

| Analysis | n | Mean difference | 95% CI | Closer / farther / tied |
| --- | ---: | ---: | --- | --- |
| Primary | 60 | +0.0381 | [-0.0076, +0.0821] | 19 / 33 / 8 |
| S1 complete cases | 29 | +0.0218 | [-0.0568, +0.0937] | 10 / 14 / 5 |
| S2 strict parser | 60 | +0.0424 | [-0.0029, +0.0866] | 17 / 36 / 7 |

Mean JSD from humans per arm, over items with a defined distribution:

| Arm | n | Mean JSD |
| --- | ---: | ---: |
| direct judgment | 60 | 0.2558 |
| generic appraisal | 60 | 0.2999 |
| moral-cognitive appraisal | 60 | 0.2939 |

Figure: [figures/fig2_results.png](../figures/fig2_results.png) (filled markers; hollow markers are the development run).

## Exploratory analyses (post hoc, not pre-registered)

Defined after the Study 1 results had been seen, on the same run; see [exploratory_log.md](exploratory_log.md) (entries E1 and E2) for when and why each was run. Source: `results/heldout/7edf899cb4bf44f4/exploratory/dispersion.json`, status `EXPLORATORY`. Labels as recorded, no reparse; resampling seed 20261012. None of these is a test of a pre-registered comparison, and no interval below has nominal coverage as a test.

### Dispersion

Per item, the base-2 Shannon entropy (bits; maximum 2) and the modal-label share of each distribution, averaged over items.

| Source | n | Mean entropy (bits) | Mean modal share |
| --- | ---: | ---: | ---: |
| direct judgment | 60 | 0.6908 | 0.7941 |
| generic appraisal | 60 | 0.6380 | 0.7987 |
| moral-cognitive appraisal | 60 | 0.8517 | 0.7422 |
| humans | 60 | 0.7789 | 0.7705 |

Entropy, paired differences:

| Comparison | n | Mean difference | 95% CI | Lower / higher / tied | Interval excludes zero |
| --- | ---: | ---: | --- | --- | --- |
| generic appraisal − direct judgment | 60 | -0.0528 | [-0.1498, +0.0509] | 29 / 15 / 16 | no |
| moral-cognitive appraisal − generic appraisal | 60 | +0.2137 | [+0.0829, +0.3380] | 15 / 38 / 7 | yes |
| direct judgment − humans | 60 | -0.0881 | [-0.2902, +0.1089] | 29 / 23 / 8 | no |

Modal share, paired differences:

| Comparison | n | Mean difference | 95% CI | Lower / higher / tied | Interval excludes zero |
| --- | ---: | ---: | --- | --- | --- |
| generic appraisal − direct judgment | 60 | +0.0047 | [-0.0322, +0.0415] | 15 / 24 / 21 | no |
| moral-cognitive appraisal − generic appraisal | 60 | -0.0566 | [-0.1040, -0.0077] | 37 / 16 / 7 | yes |
| direct judgment − humans | 60 | +0.0236 | [-0.0433, +0.0917] | 21 / 30 / 9 | no |

Contested vs consensus items. Spearman correlation between human entropy and the per-item JSD difference, and the mean difference in each half of a split at the median human entropy (0.8259 bits; low half = at or below the median):

| Difference | n | Spearman ρ | 95% CI | Mean, low-entropy half | Mean, high-entropy half |
| --- | ---: | ---: | --- | ---: | ---: |
| generic appraisal − direct judgment | 60 | +0.1303 | [-0.1238, +0.3732] | +0.0342 (n=30) | +0.0540 (n=30) |
| moral-cognitive appraisal − generic appraisal | 60 | -0.2333 | [-0.4538, +0.0087] | +0.0031 (n=30) | -0.0150 (n=30) |

### Disjoint 10-human ceiling

How close ten humans get to the rest of the human panel: per item, the mean over 1,000 draws of the JSD between 10 non-INFO votes drawn without replacement and the item's remaining non-INFO votes. Only items with at least 20 non-INFO votes qualify: 14 of 60 (votes 23–186, median 41). These items are not representative of the 60.

| Source, same items | n | Mean JSD |
| --- | ---: | ---: |
| 10-human panel vs remaining humans | 14 | 0.0681 |
| direct judgment vs all humans | 14 | 0.2209 |
| generic appraisal vs all humans | 14 | 0.2689 |
| moral-cognitive appraisal vs all humans | 14 | 0.2490 |

A first-pass version scored each panel against the full distribution, which contains the panel itself; it is biased low (0.0399) and superseded.

### Verdict shift

Mean share of each verdict, averaging each item's distribution with equal weight per item. Figure: [figures/fig3_shift.png](../figures/fig3_shift.png).

| Source | n | Author | Other | Everybody | Nobody |
| --- | ---: | ---: | ---: | ---: | ---: |
| humans | 60 | 0.2117 | 0.6233 | 0.0581 | 0.1070 |
| direct judgment | 60 | 0.2846 | 0.5563 | 0.0374 | 0.1217 |
| generic appraisal | 60 | 0.2776 | 0.5097 | 0.0256 | 0.1872 |
| moral-cognitive appraisal | 60 | 0.3644 | 0.4394 | 0.0484 | 0.1478 |

Paired per-label differences (16 intervals, no multiplicity adjustment; within a comparison the four labels sum to zero, so they are not independent):

| Comparison | Verdict | n | Mean difference | 95% CI | Interval excludes zero |
| --- | --- | ---: | ---: | --- | --- |
| generic appraisal − direct judgment | Author | 60 | -0.0070 | [-0.0393, +0.0257] | no |
| generic appraisal − direct judgment | Other | 60 | -0.0466 | [-0.0803, -0.0144] | yes |
| generic appraisal − direct judgment | Everybody | 60 | -0.0119 | [-0.0276, +0.0033] | no |
| generic appraisal − direct judgment | Nobody | 60 | +0.0655 | [+0.0348, +0.0984] | yes |
| moral-cognitive appraisal − generic appraisal | Author | 60 | +0.0869 | [+0.0456, +0.1306] | yes |
| moral-cognitive appraisal − generic appraisal | Other | 60 | -0.0703 | [-0.1183, -0.0201] | yes |
| moral-cognitive appraisal − generic appraisal | Everybody | 60 | +0.0228 | [+0.0034, +0.0433] | yes |
| moral-cognitive appraisal − generic appraisal | Nobody | 60 | -0.0394 | [-0.0826, +0.0024] | no |
| direct judgment − humans | Author | 60 | +0.0730 | [-0.0065, +0.1552] | no |
| direct judgment − humans | Other | 60 | -0.0670 | [-0.1731, +0.0408] | no |
| direct judgment − humans | Everybody | 60 | -0.0206 | [-0.0478, +0.0085] | no |
| direct judgment − humans | Nobody | 60 | +0.0147 | [-0.0565, +0.0853] | no |
| generic appraisal − humans | Author | 60 | +0.0659 | [-0.0229, +0.1570] | no |
| generic appraisal − humans | Other | 60 | -0.1136 | [-0.2227, -0.0020] | yes |
| generic appraisal − humans | Everybody | 60 | -0.0325 | [-0.0621, -0.0016] | yes |
| generic appraisal − humans | Nobody | 60 | +0.0802 | [+0.0001, +0.1615] | yes |

### Modal agreement

Share of items on which the model's most frequent verdict matches the humans' most frequent verdict. A tie on either side counts as a match if any tied label matches; the rule for model ties was not specified in advance, so the matches that depend on it are counted separately.

| Arm | n | Agreement | Items with a model tie | Matches relying on a model tie |
| --- | ---: | ---: | ---: | ---: |
| direct judgment | 60 | 0.6500 | 1 | 1 |
| generic appraisal | 60 | 0.6167 | 5 | 4 |
| moral-cognitive appraisal | 60 | 0.5667 | 3 | 3 |

Items with a human tie: 1. Paired differences (0/1 per item, so the intervals are coarse):

| Comparison | n | Mean difference | 95% CI | Lower / higher / tied | Interval excludes zero |
| --- | ---: | ---: | --- | --- | --- |
| generic appraisal − direct judgment | 60 | -0.0333 | [-0.1167, +0.0500] | 4 / 2 / 54 | no |
| moral-cognitive appraisal − generic appraisal | 60 | -0.0500 | [-0.1333, +0.0333] | 5 / 2 / 53 | no |
| moral-cognitive appraisal − direct judgment | 60 | -0.0833 | [-0.1667, +0.0000] | 6 / 1 / 53 | no |

## Study 2: trait-varied vs irrelevant-varied persona mixtures

Run `results/study2/2e2b551529945ff6`, protocol `study2_persona_mixture_v1`, pre-registered in [preregistration_study2.md](preregistration_study2.md). The same 60 items and human scores as Study 1, with the Study 1 direct-judgment prompt preceded by a persona; sample *i* of each item is judged by persona *i*. In the **trait mixture** the ten personas vary on perspective-taking, cognitive empathy and justice sensitivity; in the **irrelevant mixture** they vary on drink, leisure and evening preferences. Parser `final_marker_tolerant_v1`, settings as Study 1. Responses were collected 2026-10-12 17:08 to 2026-10-12 20:31 UTC.

### Coverage

| Arm | Planned | Recorded | Valid | Failures by status |
| --- | ---: | ---: | ---: | --- |
| trait mixture (`trait_mixture`) | 600 | 600 | 574 | `request_error` 26 |
| irrelevant mixture (`irrelevant_mixture`) | 600 | 600 | 569 | `request_error` 30, `invalid_label_format` 1 |

### Primary comparison

| Comparison | n | Mean JSD, left | Mean JSD, right | Mean difference | 95% CI | Closer / farther / tied | Pre-registered verdict |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| P3: trait mixture − irrelevant mixture | 60 | 0.2759 | 0.2760 | -0.0001 | [-0.0357, +0.0357] | 22 / 25 / 13 | Not distinguished (interval includes zero) |

### S1: complete cases

| Comparison | n | Mean JSD, left | Mean JSD, right | Mean difference | 95% CI | Closer / farther / tied | Pre-registered verdict |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| P3: trait mixture − irrelevant mixture | 25 | 0.2996 | 0.2731 | +0.0266 | [-0.0402, +0.0928] | 7 / 12 / 6 | Not distinguished (interval includes zero) |

### S2: strict parser

Reparsed under `exact_label_or_final_marker_v3`. Coverage under that parser:

| Arm | Planned | Recorded | Valid | Failures by status |
| --- | ---: | ---: | ---: | --- |
| trait mixture (`trait_mixture`) | 600 | 600 | 574 | `request_error` 26 |
| irrelevant mixture (`irrelevant_mixture`) | 600 | 600 | 569 | `request_error` 30, `invalid_label_format` 1 |

| Comparison | n | Mean JSD, left | Mean JSD, right | Mean difference | 95% CI | Closer / farther / tied | Pre-registered verdict |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| P3: trait mixture − irrelevant mixture | 60 | 0.2759 | 0.2760 | -0.0001 | [-0.0357, +0.0357] | 22 / 25 / 13 | Not distinguished (interval includes zero) |

### Descriptive

Not pre-registered as tests. **Run-time caveat:** the Study 1 direct-judgment arm was sampled 2026-10-11 22:44 to 2026-10-12 09:43 UTC and Study 2 2026-10-12 17:08 to 2026-10-12 20:31 UTC, so differences between them combine the persona effect with any change in the provider or model between the runs.

Each mixture minus the Study 1 direct-judgment arm, per-item JSD, paired over items:

| Comparison | n | Mean JSD, mixture | Mean JSD, Study 1 direct | Mean difference | 95% CI | Closer / farther / tied |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| trait mixture − Study 1 direct | 60 | 0.2759 | 0.2558 | +0.0201 | [-0.0186, +0.0575] | 16 / 29 / 15 |
| irrelevant mixture − Study 1 direct | 60 | 0.2760 | 0.2558 | +0.0202 | [-0.0176, +0.0579] | 21 / 27 / 12 |

Verdict shares (each item's distribution averaged with equal weight) and mean per-item entropy:

| Source | n | Author | Other | Everybody | Nobody | Mean entropy (bits) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| trait mixture | 60 | 0.3407 | 0.4995 | 0.0313 | 0.1285 | 0.7812 |
| irrelevant mixture | 60 | 0.3419 | 0.5075 | 0.0244 | 0.1261 | 0.7000 |
| Study 1 direct judgment | 60 | 0.2846 | 0.5563 | 0.0374 | 0.1217 | 0.6908 |
| humans | 60 | 0.2117 | 0.6233 | 0.0581 | 0.1070 | 0.7789 |

Figure: [figures/fig4_study2.png](../figures/fig4_study2.png).

## Pre-registered disagreements

Both pre-registrations require that a primary result and a sensitivity analysis be reported as disagreeing when their signs differ or when one interval excludes zero and the other does not, and that the disagreement not be resolved by choosing between them. Every primary comparison was checked against S1 and S2:

| Study | Comparison | Sensitivity | Primary: mean, 95% CI | Sensitivity: mean, 95% CI | Result |
| --- | --- | --- | --- | --- | --- |
| Study 1 | P1 | S1 | -0.0059 [-0.0494, +0.0371] | -0.0160 [-0.0768, +0.0445] | Agrees |
| Study 1 | P1 | S2 | -0.0059 [-0.0494, +0.0371] | -0.0008 [-0.0458, +0.0428] | Agrees |
| Study 1 | P2 | S1 | +0.0441 [+0.0156, +0.0717] | +0.0378 [-0.0073, +0.0765] | **Disagreement**: one interval excludes zero, the other includes it |
| Study 1 | P2 | S2 | +0.0441 [+0.0156, +0.0717] | +0.0432 [+0.0143, +0.0714] | Agrees |
| Study 2 | P3 | S1 | -0.0001 [-0.0357, +0.0357] | +0.0266 [-0.0402, +0.0928] | **Disagreement**: sign differs |
| Study 2 | P3 | S2 | -0.0001 [-0.0357, +0.0357] | -0.0001 [-0.0357, +0.0357] | Agrees |

- **Study 1, P2 vs S1.** The primary P2 interval excludes zero (generic appraisal farther from humans than direct judgment, n = 60); the complete-case interval includes zero (n = 29). Both means are positive. Reported as a disagreement and not resolved, as pre-registered.
- **Study 2, P3 vs S1.** The primary P3 mean is negative (-0.0001, n = 60) and the complete-case mean positive (+0.0266, n = 25); both intervals include zero, so neither distinguishes the two mixtures. Reported as a disagreement and not resolved, as pre-registered.

## Development history

Before Study 1, the three prompts were compared on 20 items from a development pool that had been inspected by hand (run `results/pilot_v4/32fa0ec867b00d0c`, 10 samples per item and prompt, `max_tokens` 4096, parser `exact_label_or_final_marker_v3`). Valid responses were 200/200 direct judgment, 190/200 generic appraisal, 180/200 moral-cognitive appraisal; the failures were 28 label-format failures and 2 truncations. That run was not pre-registered and its results are exploratory; they appear as hollow markers in [figures/fig2_results.png](../figures/fig2_results.png). Inspecting its format failures led to the parser `final_marker_tolerant_v1`, which was fixed before any held-out response was requested and is the declared parser of both studies; the strict parser is kept as sensitivity analysis S2. See [preregistration.md](preregistration.md), section 4.

## Provenance

Commits in this repository, from `git log`. In each study the pre-registration was committed before the raw responses, and the raw responses before the analysis.

| Record | Commit | Date | Subject |
| --- | --- | --- | --- |
| Study 1 pre-registration | `4e87c7b` | 2026-10-11 23:43 +0100 | Pre-register held-out evaluation (protocol 7edf899cb4bf44f4) |
| Study 1 raw responses | `339fca5` | 2026-10-12 10:46 +0100 | Held-out run 7edf899cb4bf44f4: raw responses, complete (1800 attempts), before analysis |
| Study 1 analysis (primary, S1, S2) | `1192808` | 2026-10-12 10:48 +0100 | Held-out analysis: primary + S1 complete-case + S2 strict-parser reparse, per preregistration |
| Exploratory analyses (post hoc) | `977d2cf` | 2026-10-12 12:32 +0100 | Exploratory (post-hoc): dispersion, disjoint 10-human ceiling, verdict shift, modal agreement |
| Study 2 pre-registration | `fc43a8b` | 2026-10-12 14:59 +0100 | Pre-register Study 2 (protocol 2e2b551529945ff6): trait-mixture vs irrelevant-mixture judges; refactor runner without changing Study 1/dev hashes |
| Study 2 pre-registration clarification (before execution) | `eee975a` | 2026-10-12 15:01 +0100 | Study 2 preregistration: clarify persona-composition effect of missingness (before execution) |
| Study 2 raw responses | `fe36e1b` | 2026-10-12 21:33 +0100 | Study 2 run 2e2b551529945ff6: raw responses, complete (1200 attempts), before analysis |
| Study 2 analysis (P3, S1, S2) | `927f744` | 2026-10-12 21:36 +0100 | Study 2 analysis: P3 + S1 + S2 per preregistration |

Configuration hashes: Study 1 `7edf899cb4bf44f4…`, Study 2 `2e2b551529945ff6…`, development `32fa0ec867b00d0c…`. Each covers every rendered prompt, item, human score, parser version and sampling setting of its run.
