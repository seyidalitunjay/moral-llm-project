> Written during development and kept as a record. Current results: [results.md](results.md).

# Open methodological issues

Unresolved problems with the current design and data. Nothing here is settled, and
none of it should be treated as having been addressed elsewhere in these docs.

## 1. Parse failures are not evenly distributed across conditions

Status: open. Affects any comparison computed from `results/pilot_v4/32fa0ec867b00d0c`.

In the completed 20-item run, the rate at which responses failed to yield a usable
label rises monotonically with how much written appraisal the condition asked for:

| Condition | Valid | Planned | Failure rate | Items with all 10 valid |
| --- | ---: | ---: | ---: | ---: |
| Baseline, no written appraisal | 200 | 200 | 0% | 20 of 20 |
| Generic factual appraisal | 190 | 200 | 5% | 12 of 20 |
| Original intervention content | 180 | 200 | 10% | 8 of 20 |

Failures are 28 `invalid_label_format` and 2 `truncated`, the latter only in the
original-content arm.

### Why this threatens the comparison

Each item's model distribution is built from whichever of its 10 responses parsed.
Where an arm lost responses, its distribution for that item rests on fewer draws
than the baseline's. The loss is not plausibly independent of the condition. The
baseline lost nothing, and the two appraisal arms lost progressively more as the
requested appraisal grew. The missingness is therefore associated with the
treatment, and in that case dropping incomplete observations is not safe.

Two distinct problems follow, and they are worth keeping apart:

1. Unequal precision. An arm estimated from 6 draws has a noisier empirical
   distribution than one estimated from 10. Jensen-Shannon divergence from a fixed
   human distribution does not average out under that noise in a neutral way. A
   coarser empirical distribution places mass in fewer cells and tends to sit
   further from a spread-out human distribution. Part of any gap between arms could
   be an artefact of how many draws survived rather than of what the model judged.

2. Possible selection on the outcome. Responses may fail to parse for reasons
   related to what the model was going to conclude. For instance, genuinely
   ambiguous items may provoke longer, hedged appraisals that overrun the token cap
   or drift from the output format. If so, the surviving responses are a biased
   sample of the responses the model would have given. The verdicts that went missing would
   not be missing at random, and the distribution computed from what remains would
   be systematically wrong rather than merely imprecise.

The second possibility is untested. The 2 truncations and the largest share of
format violations both fall in the arm that asks for the most reasoning, which is
at least consistent with it.

### What would need to be done

- Report the complete-case sensitivity analysis alongside every available-pairs
  result. `analyze_control_pilot.py` already computes both, under the
  `_complete_all_arms` and `_available_pairs` keys. Agreement between them is weak
  evidence against the missingness driving the result; disagreement is a reason to
  distrust it.
- Note the severity of the complete-case restriction here: only 4 of 20 items
  have all 10 planned responses valid in all three arms. That subset is too small to
  settle the question, so the sensitivity analysis will be suggestive at best and
  cannot currently be used to dismiss the concern.
- Inspect the failing responses rather than only counting them.
  `diagnose_responses.py` carries the closing line of every response for this
  purpose. Determining whether failures cluster on particular anecdotes, or on
  anecdotes with a particular human judgment profile, would distinguish problem 1
  from problem 2.
- Consider whether a future confirmatory run should resample failed slots to a
  fixed count per cell, which would remove the unequal-precision problem. It would
  not remove the selection problem. Resampling until success is itself a form of
  selection unless the number of attempts is recorded and reported.

### What must not be done

Failures must not be quietly dropped, and a condition's distribution must not be
presented without the count it was computed from. Raising the token cap or loosening
the parser after seeing the results would be a post-hoc change to the measurement
instrument, and any such change has to be disclosed as one, in the way the earlier
parser revisions are disclosed in `protocol.md`.

## 2. Legacy labels cannot be rechecked

Status: open, and not fixable.

The raw response text from the 60-item legacy runs was never saved, and labels were
extracted at request time by a permissive search that cannot distinguish a stated
verdict from one merely mentioned in passing. Those results can be audited for
internal consistency, which `audit_results.py` does, but their label accuracy cannot
be reconstructed. See `provenance.md`. The current pipeline stores complete response
bodies specifically so that this cannot recur.

## 3. The development pool is not naive

Status: open by design; constrains what can be claimed.

All runs so far draw from the same first 60 rows of the dev split, which have been
inspected by hand across several iterations of prompt and parser design. Sample
sizes were not chosen against any target precision, and no analysis plan was fixed
before looking at results. Nothing produced from this pool can serve as a
confirmatory result, and the remaining items should be preserved untouched for a
later study with a frozen protocol.
