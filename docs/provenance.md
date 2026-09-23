# Provenance of the legacy results files

This note records how `results/legacy/results.jsonl` and
`results/legacy/results_v2.jsonl` came to hold what they hold. It exists because
two throwaway scripts, `clean_results.py` and `clean_results2.py`, once rewrote
the second file in place and were then removed from the repository. Their effect
is no longer visible in the data, so without this note the history would be lost.
Everything below was reconstructed from the surviving files and verified against
the Scruples dev split.

## `results.jsonl`

Twenty items under the first schema, which stored a single answer per condition
(`baseline_answer`, `intervention_answer`) rather than a set of samples. Its ids
are exactly the first twenty of `results_v2.jsonl`, and every one of those items
was later rerun with repeated sampling. It is kept as the record of the first
pilot and is not read by any script.

## `results_v2.jsonl`

Sixty items under the sampled schema, holding `baseline_samples` and
`intervention_samples` per item. The file matches the first sixty rows of the
Scruples dev split exactly, in order, which `audit_results.py` reconfirms on every
run through its `first_dev_rows_exact_match` field.

It was built up over several sittings, and two interventions were made to it by
hand along the way:

1. An early run covered five items at ten samples per condition. `clean_results.py`
   then truncated the file to exactly those five ids. They are rows 1 to 5 of the
   final file and are still the only rows with ten attempts; every later row has
   five. This is the origin of the uneven attempt counts, and the reason the audit
   reports attempt-matched subsets alongside the full sixty.

2. Later, three items at rows 18 to 20 were judged corrupted and deleted by
   `clean_results2.py`. All three were subsequently rerun and are present in the
   final file with five valid samples per condition and no nulls. No trace of the
   deletion survives in the data.

Both scripts rewrote the file in place with no backup. Had either been run again
after the batch was complete, the first would have reduced the sixty-item file to
five rows. Neither is preserved, and the current pipeline does not modify its
inputs: `run_control_pilot.py` only ever appends, and every analysis script writes
to a separate output path and refuses to overwrite what it read.

## Missing samples that remain

Four samples across three items failed to yield a label and are recorded as nulls
rather than dropped:

| Row | Item | Nulls |
| --- | --- | ---: |
| 2 | `P96wm6qNDeGdaHy25VrNmYPWbtyTAxDN` | 2 intervention |
| 17 | `trQhUewlqGqFHuILFrCk6g8cLlTfCP6g` | 1 intervention |
| 21 | `wsHKrTPSiBGttaJiPpoJlgJ5nsF4h7Og` | 1 baseline |

These are the rows behind the 324 and 322 valid counts against 325 attempts per
condition. `audit_results.py` lists them under `incomplete_rows`.

## A limit worth stating plainly

The raw response text from these runs was never saved. Labels were extracted at
request time by the permissive search now isolated in `moral_judgment/legacy.py`,
which returns the last label appearing anywhere in the response and therefore
cannot distinguish a stated verdict from one merely discussed. Because the text is
gone, those extractions cannot be rechecked or reparsed. This is the specific
defect the current pipeline was built to avoid, and it is why `run_control_pilot.py`
stores the complete response body for every call.
