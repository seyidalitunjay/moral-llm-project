"""Legacy metric summary over the 60-item results file.

Superseded by `audit_results.py`, which validates the results against the dev
split and reports uncertainty. This script is kept because the figures quoted in
the earlier write-up came from it, and it remains the shortest way to reproduce
them. It reads its input and writes nothing.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

# Lets the script run straight from a clone, with or without an editable install.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from moral_judgment.io import read_jsonl
from moral_judgment.metrics import LABELS, distribution, js

DEFAULT_RESULTS = Path(__file__).resolve().parent.parent / 'results' / 'legacy' / 'results_v2.jsonl'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('results', nargs='?', default=str(DEFAULT_RESULTS))
    args = p.parse_args()

    baseline_scores = []
    intervention_scores = []
    skipped = 0

    for r in read_jsonl(args.results):
        # Human counts are normalised over the four verdict labels only, and model
        # samples over the ones that parsed, so both sides are conditional
        # distributions on the same support.
        h_dist = distribution(r['human_scores'])
        b_dist = distribution(Counter(s for s in r['baseline_samples'] if s in LABELS))
        i_dist = distribution(Counter(s for s in r['intervention_samples'] if s in LABELS))

        if h_dist is None or b_dist is None or i_dist is None:
            skipped += 1
            continue

        baseline_scores.append(js(h_dist, b_dist))
        intervention_scores.append(js(h_dist, i_dist))

    print(f"Items used: {len(baseline_scores)} (skipped: {skipped})")
    print(f"Average JS divergence (baseline vs human):     {sum(baseline_scores)/len(baseline_scores):.4f}")
    print(f"Average JS divergence (intervention vs human):  {sum(intervention_scores)/len(intervention_scores):.4f}")
    print()
    print("(Lower divergence = closer to human distribution = better)")

    # Counted per item rather than read off the two means, because a difference in
    # means can be produced by a few large shifts while most items are unmoved.
    improved = sum(1 for b, i in zip(baseline_scores, intervention_scores) if i < b)
    worsened = sum(1 for b, i in zip(baseline_scores, intervention_scores) if i > b)
    same = len(baseline_scores) - improved - worsened
    print(f"\nPer-item comparison: intervention closer to human in {improved} items, farther in {worsened}, tied in {same}")


if __name__ == '__main__':
    main()
