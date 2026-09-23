# Moral judgment distributions in LLMs

Code and data for an evaluation of how closely a language model's distribution of
moral verdicts tracks the distribution of human verdicts on the same anecdote, and
whether prompting the model to reason about perspective, empathy and fairness
moves it closer.

## The question

Scruples anecdotes do not come with a gold verdict. Each carries a spread of
judgments from many annotators, and on a contested case that spread is the
interesting object: annotators genuinely disagree. Sampling the model repeatedly
gives a spread of its own, so each item yields two categorical distributions over
the same four verdict labels, and the quantity reported throughout is the base-2
Jensen-Shannon divergence between them. Lower means closer agreement with the
shape of human opinion, not closer agreement with a majority vote.

The intervention under study asks the model to work through perspective-taking,
cognitive empathy and justice sensitivity before judging. The obvious confound is
that any such instruction also makes the model deliberate at length, so the
current design runs a third arm: a generic factual appraisal of comparable
structure and length with no moral-psychological content. The question is whether
the empathy content does anything that generic deliberation does not.

## Status

Two generations of work are in this repository and their results are not poolable.

**Legacy, complete.** Sixty items, two arms, five samples each (ten for the first
five items), scored by a permissive label search over responses whose raw text was
not retained. Mean divergence 0.2729 baseline against 0.3604 intervention, with
the intervention closer to the human distribution on 8 items, farther on 25 and
tied on 27. The intervention was worse. See `docs/provenance.md` for how the files
were assembled and why those labels cannot be rechecked.

**Current, in progress.** Three arms, strict output parsing, full response bodies
retained, runs addressed by a hash of their own configuration. Two smoke tests are
complete and analysed. The main 20-item comparison at 10 samples per condition,
in `results/pilot_v4/32fa0ec867b00d0c`, has all 600 responses recorded but has not
yet been analysed. `docs/protocol.md` documents the design and the parser revisions
in detail, including a post-hoc parsing correction that must be disclosed in any
write-up.

**Read `docs/open-issues.md` before interpreting that run.** Responses failed to
parse at 0% in the baseline arm, 5% in the generic arm and 10% in the
original-content arm, so each arm's distributions rest on different numbers of
draws and the losses are associated with the treatment. Only 4 of the 20 items are
complete in all three arms. This is unresolved.

Nothing here is a confirmatory result. The items come from a 60-row development
pool that has been inspected by hand, sample sizes were not chosen for any target
precision, and the analysis plan was not fixed in advance.

## Layout

```
moral_judgment/     metric, prompts, parsers, IO. All shared logic lives here.
scripts/            command-line entry points; no analysis logic of their own
tests/              offline tests, no API calls and no data files
docs/               protocol, provenance, open issues, verification, meeting notes
data/               Scruples corpus, untracked; see data/README.md
results/
  legacy/           the 60-item results files
  pilot_v3/         first three-arm run, superseded prompt wording
  pilot_v4/         current runs, one directory per configuration hash
  reports/          generated audit and diagnostic reports
```

Two parsers and two prompt families are kept deliberately apart.
`moral_judgment/legacy.py` holds the permissive search and the original prompts
that produced the legacy results; `parsing.py` and `prompts.py` hold the current
strict versions. Merging them would change what the historical numbers mean, and
the difference between them is itself one of the findings.

## Setup

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

The analysis scripts and the tests use only the standard library, so every
reported figure can be recomputed without installing anything. `openai` is needed
only to make new API calls. Place the corpus at `data/anecdotes.tar` first, as
described in `data/README.md`.

## Reproducing the reported figures

None of these make network calls or modify their inputs.

```bash
# Legacy 60-item audit, cross-checked against the dev split
python3 scripts/audit_results.py results/legacy/results_v2.jsonl \
    --archive data/anecdotes.tar --out results/reports/audit_report.json

# The same headline numbers, via the original short script
python3 scripts/compute_metric.py

# Three-arm smoke run, reparsed under the current parser
python3 scripts/analyze_control_pilot.py results/pilot_v4/2968f02acc8e2d59 --reparse

# Response-level parser diagnosis
python3 scripts/diagnose_responses.py \
    results/pilot_v4/2968f02acc8e2d59/manifest.json \
    results/pilot_v4/2968f02acc8e2d59/responses.jsonl \
    --out results/reports/smoke_v4_diagnostics.json

python3 -m unittest discover -s tests -v
```

`docs/verification.html` records the byte-level comparison establishing that the
current code reproduces the outputs of the earlier, unrefactored scripts exactly.
It is a standalone file; open it directly in a browser.

## Making new measurements

`run_control_pilot.py` is a dry run unless given `--execute`, and prints the exact
number of calls it would make. Review that count and the manifest before spending
anything.

```bash
export OPENROUTER_API_KEY=...        # see .env.example
python3 scripts/run_control_pilot.py --data data/anecdotes.tar   # dry run
```

A run is identified by the SHA-256 of its configuration, prompts and item
selection included, and writes to a directory named after that hash. Changing any
of them produces a new directory rather than adding to an existing one, which is
what stops two incompatible sets of responses from being pooled. Reruns resume the
slots never attempted; failed attempts stay in the log rather than being retried.

## Citing the data

Lourie, N., Le Bras, R., and Choi, Y. *Scruples: A Corpus of Community Ethical
Judgments on 32,000 Real-Life Anecdotes.* AAAI 2021.
