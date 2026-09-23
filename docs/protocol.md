# Research audit and development tools

The historical audit reproduced the uploaded 60-item results. The user subsequently completed a 30-call v3 smoke test. The user has also completed the provider-restricted v4 smoke test. Its 30 responses are usable after the documented post-hoc parsing correction below. The final parser revision has been tested against the saved responses and offline tests. Keep all original scripts and results unchanged.

## Verified historical findings

The uploaded results contain 60 unique anecdotes, matching the first 60 dev rows and their human scores. Five rows contain 10 attempts per condition; 55 contain five. There are 325 recorded attempts per condition, with 324 valid baseline labels and 322 intervention labels. Four nulls occur across three rows.

Mean base-2 JS divergence is 0.2728636171 for baseline and 0.3604473893 for intervention, with 8 closer, 25 farther, and 27 tied. Your metric calculation is correct. It conditions human judgments on non-INFO labels and model judgments on valid extracted labels. Twenty items have INFO counts, totaling 34 of 1,264 human judgments.

For the 53 rows with five valid labels in each condition, means are 0.2730919791 and 0.3742935314. This is a post-hoc sensitivity subset, not a replacement primary result or new confirmation experiment. The first five rows are already included in the 60; the larger batch is not independent replication of the initial pilot.

`results/reports/audit_report.json` includes all item-level values, input checksum, incomplete rows, and exploratory paired bootstrap intervals (10,000 resamples, seed 20260913). The bootstrap is over these convenience-sampled anecdotes, conditional on saved judgments. It does not recover the underlying model distribution or solve uncertainty in human labels.

The original parser can select a label mentioned in a rationale, example, or substring even without a valid final answer. Raw responses are absent from the uploaded results, so historical parse correctness cannot be reconstructed. The one-off `analyze.py` read the older `results.jsonl` schema and was never an audit of `results_v2.jsonl`; it has been removed, and `docs/provenance.md` records what the legacy files contain. That older file may contain useful original response text if you still have it; do not assume it contains all 60 cases.

## Run the historical audit on your Mac

Unzip this folder inside your existing project, then use your existing virtual environment. Place the corpus at `data/anecdotes.tar`; see `data/README.md`.

```bash
cd ~/Desktop/moral-llm-project
source venv/bin/activate
python3 scripts/audit_results.py results/legacy/results_v2.jsonl --archive data/anecdotes.tar --out audit_local.json
```

The script reads your originals and writes only the named new report. It needs no external Python packages. Compare its input checksum and output with the supplied report if your local file has changed.

## What the completed 30-call smoke test showed

There were **9 rejected responses, not 10**: five had correct labels wrapped in Markdown bold, two were truncated at the 2,048-token cap, and two used unsupported labels (`NO` and `ASSHOLE`). The old parser was too strict about presentation formatting.

The revised parser accepts paired bold/underline/backtick wrappers around an otherwise exact final field. It never derives a label from the rationale or translates unsupported labels. Truncated responses remain invalid even if a label appears in their text. One response's rationale conflicts with its final label; the explicitly emitted label remains the recorded judgment.

| Condition | Originally valid | Valid after format-only reparsing | Planned |
| --- | ---: | ---: | ---: |
| Baseline | 9 | 9 | 10 |
| Generic appraisal | 6 | 9 | 10 |
| Original intervention content | 6 | 8 | 10 |
| Total | 21 | 26 | 30 |

`results/reports/smoke_diagnostics.json` records the derivation, source checksum, and response-level reasons. Reparsing is a post-hoc measurement correction, not a new experiment. Nine providers appear in the original run. Five items with two samples per condition are sufficient for this technical check, not a reliable estimate of intervention effects.

To reproduce the correction without API calls:

```bash
python3 scripts/analyze_control_pilot.py results/pilot_v3/c677534c951c9525 --reparse
```

This writes `analysis_reparsed.json` and leaves the raw responses unchanged.

## Completed v4 smoke test and current next step

The run `results/pilot_v4/2968f02acc8e2d59` contains 30 responses, all returned by Parasail with `finish_reason=stop`. The six initially rejected baseline answers are exact standalone labels (four OTHER, one AUTHOR, one NOBODY) without a `FINAL_LABEL:` prefix. They contain unambiguous judgments.

Parser `exact_label_or_final_marker_v3` now accepts an exact whole-response label in every condition, or the existing unique final-marker form. It does not accept unmarked labels at the end of a rationale, synonyms, arbitrary substrings, or truncated responses. This is a post-hoc measurement correction and must be disclosed. All three conditions now have 10/10 usable responses. Raw records and manifests are unchanged.

The saved analysis is included as `results/reports/smoke_v4_analysis_reparsed.json`, and response-level provenance as `results/reports/smoke_v4_diagnostics.json`. Reproduce locally without API calls:

```bash
python3 scripts/analyze_control_pilot.py results/pilot_v4/2968f02acc8e2d59 --reparse
```

Mean base-2 JS divergence: baseline 0.2357, generic 0.1121, original content 0.1630. These five cases with two samples per condition are a technical smoke test, not evidence of a stable ranking. Do not interpret its small-sample bootstrap intervals as confirmatory significance or combine this run with the historical 60-item result.

The next development comparison uses 20 seeded cases from the previously inspected first 60 dev rows, 10 samples per condition, and the same prompt content, provider restriction, and token cap. Freeze the parser and these settings for that run. It schedules 600 paid calls. This run has since been completed; its coverage is recorded below.

```bash
python3 scripts/run_control_pilot.py --data data/anecdotes.tar --items 20 --samples 10 --max-tokens 4096 --provider parasail --execute
```

### Status of the 20-item run

Completed. `results/pilot_v4/32fa0ec867b00d0c` holds all 600 scheduled responses
under configuration hash `32fa0ec867b00d0c`, whose manifest the current code
reproduces byte for byte. Recorded coverage, before any reparsing:

| Condition | Valid | Planned | Failure statuses |
| --- | ---: | ---: | --- |
| Baseline | 200 | 200 | none |
| Generic appraisal | 190 | 200 | 10 `invalid_label_format` |
| Original intervention content | 180 | 200 | 18 `invalid_label_format`, 2 `truncated` |

Per item, all 20 items are complete in the baseline arm, 12 in the generic arm and
8 in the original arm. Only 4 items have all 10 planned responses valid in all
three arms.

No analysis has been run over this directory and no divergences are reported here.
The uneven failure rate across arms is an open methodological issue, recorded in
`docs/open-issues.md`; read it before interpreting any comparison computed from
this run. To produce the coverage table and the comparisons:

```bash
python3 scripts/analyze_control_pilot.py results/pilot_v4/32fa0ec867b00d0c
```

A changed sample size and parser version create a new configuration directory; do not edit the earlier manifest or pool runs. The new 20-item selection can be previewed without `--execute`. It is still exploratory development, with coarse empirical model distributions. Preserve untouched cases for a later study with a fixed analysis plan and sample size justified by the precision needed. Do not expand to another dataset yet.

## Preview the broader development control experiment

```bash
python3 scripts/run_control_pilot.py --data data/anecdotes.tar
```

This dry run creates a manifest under `results/pilot_v4/<configuration-hash>/` and makes no API calls. Defaults: 20 seeded-random cases from the first 60 dev items, three conditions, 10 attempts per condition, 600 calls if executed, temperature 0.8, top-p 1, maximum output 2,048 tokens per call. Input tokens are additional. Review current provider prices and your available balance before execution. A five-item smoke run can be previewed by adding `--items 5 --samples 2` (30 calls if executed).

Conditions are direct judgment, generic facts/sequence/review, and the original intervention's three content steps. Every condition uses a new final-label interface; generic and original request at most 180 words of appraisal. Therefore the original-content condition is not an exact replication of the historical prompt. New measurements must remain separate from old results.

Four-label evaluation remains the default for the immediate control study. This preserves the conditional moral-judgment target. Adding `--include-info` starts a distinct five-label configuration; do not pool its scores with four-label results. The final study's choice should be agreed before evaluation. Generic appraisal is an active control, and actual output lengths may differ. This runner does not implement the later P/J component ablations.

## Execute after reviewing the manifest

The runner uses the `openai` package already used by your project. Keep your key in the `OPENROUTER_API_KEY` environment variable. To enter it privately in your Mac's default zsh terminal without putting it in shell history:

```zsh
read -s 'OPENROUTER_API_KEY?OpenRouter API key: '
export OPENROUTER_API_KEY
```

Then run:

```bash
python3 scripts/run_control_pilot.py --data data/anecdotes.tar --execute
```

This makes real API calls and incurs provider charges. The user generated both supplied smoke tests. Parsing and analysis revisions were checked against their saved raw responses without new API calls here. Choose your own item/sample count after reviewing the cost; the runner prints the exact planned call count.

The runner logs each response and configuration, accepts an exact whole-response label or a unique final marker with exact label spelling and permitted presentation wrappers, rejects truncated outputs as valid labels, and retains failures. It stops on authentication/balance errors or three consecutive request errors. It does not retry failed slots or regenerate invalid labels until success. Re-running resumes unattempted slots; failed attempts remain part of the record. Actual provider identity is retained if returned. Use `--provider` to restrict routing; without it routing remains automatic. Optional `--reasoning-effort low|medium|high` is recorded in the configuration and requires provider support. The recommended immediate command leaves reasoning effort unspecified. Freeze these settings before a confirmatory run.

Do not run two copies on the same output directory. A file lock guards against this on macOS/Linux. A malformed partial final JSON line raises an error for manual inspection rather than being silently dropped. A changed configuration gets a different output directory.

## Analyze the new run

Use the run-directory path printed by the runner:

```bash
python3 scripts/analyze_control_pilot.py results/pilot_v4/CONFIGURATION_HASH
```

Replace `CONFIGURATION_HASH` with the actual printed directory name. Inspect coverage and invalid/truncated responses first. The script reports available-pair results and a sensitivity analysis limited to items with every planned response valid in all three conditions. Neither hides failures, and neither makes missingness harmless.

## Validation and research limits

```bash
python3 -m unittest discover -s tests -v
```

Tests cover metric identities, explicit conditioning, cosmetic-wrapper handling, unsupported labels, and truncation even when a final label is present. The supplied v4 run verifies that the provider-restricted request path returned 30 completed responses; this does not guarantee future availability or label compliance. The runner is for development and control diagnosis, not a claim of completed research. Preserve untouched data for the later frozen study. No additional dataset is needed to perform this immediate step.

Provider routing reference: [OpenRouter documentation](https://openrouter.ai/docs/guides/routing/provider-selection).
