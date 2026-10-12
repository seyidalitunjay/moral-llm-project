# Exploratory analysis log

Every analysis recorded here was **defined after the pre-registered results of the
held-out run had been seen**. None of it is pre-registered, none of it is a test of
P1 or P2 in [preregistration.md](preregistration.md), and none of it changes how
those results are reported. Entries are added in the order they were run.

## E1. Dispersion, panel ceiling, contested vs consensus

- **When:** 2026-10-12, 12:25 BST. This was after the primary and sensitivity
  analyses were committed (`1192808`, 2026-10-12 10:48 +0100) and read.
- **Run analysed:** `results/heldout/7edf899cb4bf44f4` (protocol `heldout_frozen_v1`).
  Labels and statuses were used as recorded, with no reparse.
- **Command:** `python3 scripts/exploratory_dispersion.py`
- **Output:** `results/heldout/7edf899cb4bf44f4/exploratory/dispersion.json`. Every
  section is marked `EXPLORATORY`.
- **API calls:** none. No existing file was modified.
- **Seed:** 20261012 for all resampling. The paired differences use
  `moral_judgment.metrics.summarize` unchanged, with its module seed temporarily set
  to 20261012. The main analysis used 20260913.

**Why.** The primary results showed generic further from humans than baseline,
while original and generic were not distinguished. That raised questions the
pre-registered metric does not answer:

- whether the arms differ in how spread out their verdicts are, as distinct from
  where the mass falls;
- how far a model could be expected to get with ten draws;
- whether arm differences concentrate on items where humans disagree.

**What was computed.**

1. *Dispersion.* For each item and arm, the base-2 Shannon entropy and the
   modal-label share of the valid-label distribution, and the same for humans (INFO
   excluded, renormalised over the four labels). Per-arm and human means are
   reported, plus three paired differences: generic − baseline, original − generic
   and baseline − human. Each has a 95% paired-item bootstrap interval from 10,000
   resamples.
2. *10-human panel ceiling.* Only items with at least 20 non-INFO votes qualify. For
   each one, 10 votes are drawn without replacement from the non-INFO pool and the
   base-2 JSD to the full human distribution is computed. This is averaged over
   1,000 draws. The output reports the mean over qualifying items next to each
   arm's mean model JSD on the same items.
3. *Contested vs consensus.* Spearman correlation (average ranks) between human
   entropy and per-item ΔJSD for generic − baseline and original − generic, with
   95% item-bootstrap intervals from 10,000 resamples. Items are also split at the
   median human entropy (low = at or below the median) and the mean ΔJSD is
   reported for each half.

**Caveats.** These analyses were chosen after the outcome was known. The number of
analyses that could have been run is not controlled, and no interval here has
nominal coverage as a test. Only 14 of 60 items qualify for the panel ceiling, so
that comparison rests on a small subset that is not representative. Plug-in
entropy is biased downward at small n on both sides. Model cells have at most 10
valid draws. Human non-INFO vote counts range from 2 to 186, with a median of about
10, so baseline − human mixes a real difference with unequal sample sizes. Human
entropy is also too noisy to rank many items reliably, and that noise affects the
correlation and the median split.

## E2. Disjoint panel ceiling, verdict shift, modal agreement

- **When:** 2026-10-12, 12:30 BST. This was after E1 had been run and read, which
  means it also follows the pre-registered results.
- **Command:** `python3 scripts/exploratory_dispersion.py`. The E1 script was
  extended rather than a second script added, and the run directory and rules are
  the same as E1: labels as recorded, no API calls, no existing pre-registered
  output modified.
- **Output:** the same `exploratory/dispersion.json`, now holding the E1 sections
  plus `verdict_shift` and `modal_agreement`, all marked `EXPLORATORY`. The E1
  dispersion and contested-vs-consensus figures reproduce exactly. This was checked
  against the E1 file before it was overwritten.
- **Seed:** 20261012, unchanged. The E1 overlapping panel draws and the Spearman
  bootstraps still share one `Random(20261012)` stream, in the same order, which is
  why they reproduce. The new disjoint panel draws use a separate
  `Random(20261012)`. Every `summarize` call restarts from 20261012.

**Why.**

1. *The panel ceiling was biased.* In E1 each 10-vote panel was scored against the
   item's full human distribution. That distribution includes the panel's own 10
   votes, so the panel was partly compared with itself and the divergence came out
   too low. This made the human ceiling look tighter than it is. The ceiling is now
   the JSD between the 10-vote panel and the remaining votes only, which are
   disjoint from it, averaged over 1,000 draws per item. The E1 figure is kept in
   the JSON as `overlapping_biased_low` and is superseded. Qualifying items are
   unchanged (14 of 60, with at least 20 non-INFO votes), and their vote-count range
   and each arm's model JSD on those same items are reported.
2. *Verdict shift.* JSD says how far each arm is from humans but not in which
   direction. For each arm and for humans, the per-item distribution over the four
   labels is averaged across items. Per-label paired differences are reported for
   generic − baseline, original − generic, baseline − human and generic − human,
   each with a 95% paired-item bootstrap interval from 10,000 resamples.
3. *Modal agreement.* This is a coarser and more interpretable view: for each arm,
   the share of items where the model's most frequent label matches the humans'.
   - A tie for the human mode counts as a match if the model's mode is any of the
     tied labels.
   - A tie for the model's mode is handled the same way (a match if any tied model
     label is a human modal label). This rule was not specified in advance, so for
     each arm the output counts how many matches depend on it.
   - Paired differences are reported for generic − baseline, original − generic and
     original − baseline, with bootstrap intervals.

**Caveats.**

- Verdict shift produces 16 per-label intervals with no multiplicity adjustment.
  The four labels sum to one, so the differences within each pair are not
  independent.
- Modal agreement is a 0/1 quantity per item, and most items are tied between arms.
  Its bootstrap intervals are therefore coarse and discrete. For example, the
  original − baseline interval has an upper bound of exactly 0.
- The E1 caveats still apply.
