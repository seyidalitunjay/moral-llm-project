"""Read-only audit of the legacy 60-item results file.

The audit recomputes every reported quantity from the results file itself, checks
it against the Scruples dev split where the archive is supplied, and refuses to
proceed on any inconsistency rather than reporting a number it cannot stand
behind. It writes one new report and never touches its inputs.

Standard library only, so it can be rerun by a reader who has the results file
but not the project environment.
"""
import argparse
import hashlib
import json
import statistics
import tarfile
from collections import Counter
from pathlib import Path
import sys

# Lets the script run straight from a clone, with or without an editable install.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from moral_judgment.io import read_jsonl
from moral_judgment.metrics import LABELS, BOOTSTRAP_SEED, distribution, js, summarize

CONDITIONS = ('baseline', 'intervention')

METRIC_NOTE = ('Mean base-2 Jensen-Shannon divergence; human labels conditional on '
               'non-INFO; model labels conditional on valid parse')
BOOTSTRAP_NOTE = (f'Exploratory percentile bootstrap over paired items, seed {BOOTSTRAP_SEED}, '
                  '10000 resamples. Convenience sample; not a confirmatory population interval '
                  'and not a separate estimate of model-sampling or human-annotation uncertainty.')


def _load_dev_split(archive):
    """Return the dev items keyed by id, plus the row count of each split.

    Only the three known member paths are read. Nothing is extracted to disk and
    no member name comes from the archive's own table of contents, which keeps a
    crafted archive from writing outside the working directory.
    """
    dataset = {}
    counts = {}
    with tarfile.open(archive) as t:
        for split in ('train', 'dev', 'test'):
            name = f'anecdotes/{split}.scruples-anecdotes.jsonl'
            if split == 'dev':
                dev = [json.loads(line) for line in t.extractfile(name) if line.strip()]
                dataset = {r['id']: r for r in dev}
                counts[split] = len(dev)
            else:
                counts[split] = sum(bool(line.strip()) for line in t.extractfile(name))
    return dataset, counts


def _audit_row(index, r, dataset):
    """Recompute one item's distributions, divergences and attempt counts."""
    if dataset and (r['id'] not in dataset or r['human_scores'] != dataset[r['id']]['label_scores']):
        raise ValueError('Result ID or human scores do not match dev dataset')
    unknown = set(r['human_scores']) - set(LABELS) - {'INFO'}
    if unknown:
        raise ValueError(f'Unexpected human labels: {unknown}')

    sampled = {c: Counter(s for s in r[c + '_samples'] if s in LABELS) for c in CONDITIONS}
    h = distribution(r['human_scores'])
    model = {c: distribution(sampled[c]) for c in CONDITIONS}
    if h is None or any(v is None for v in model.values()):
        # An item with no mass on the four labels has no distribution to compare,
        # and dropping it here would shrink the denominator without saying so.
        raise ValueError(f'Undefined distribution at row {index + 1}; do not silently exclude')

    row = {'row': index + 1,
           'id': r['id'],
           'human_scores': r['human_scores'],
           'human_non_info_distribution': dict(zip(LABELS, h)),
           'baseline_counts': dict(sampled['baseline']),
           'intervention_counts': dict(sampled['intervention']),
           'baseline_js': js(h, model['baseline']),
           'intervention_js': js(h, model['intervention'])}
    for c in CONDITIONS:
        samples = r[c + '_samples']
        # Attempts and valid parses are tracked apart so that a condition losing
        # more responses to parse failure than the other stays visible.
        row[c + '_attempts'] = len(samples)
        row[c + '_valid'] = sum(s in LABELS for s in samples)
    row['difference'] = row['intervention_js'] - row['baseline_js']
    if dataset:
        row['title'] = dataset[r['id']]['title']
    return row


def audit(path, archive=None):
    source = Path(path)
    raw = read_jsonl(source)
    ids = [r['id'] for r in raw]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate IDs: resolve before treating rows as independent items')

    dataset, counts = _load_dev_split(archive) if archive else ({}, {})
    rows = [_audit_row(i, r, dataset) for i, r in enumerate(raw)]

    # The batch was assembled over several sittings and rows differ in how many
    # attempts they received, so the primary figure is reported beside subsets
    # holding attempt count fixed. These are post-hoc sensitivity checks on one
    # convenience sample, not independent confirmations of the primary result.
    groups = {
        'all_60_rows_as_uploaded': rows,
        'ten_attempt_rows': [r for r in rows if r['baseline_attempts'] == r['intervention_attempts'] == 10],
        'five_attempt_rows': [r for r in rows if r['baseline_attempts'] == r['intervention_attempts'] == 5],
        'five_valid_each': [r for r in rows
                            if r['baseline_attempts'] == r['intervention_attempts']
                            == r['baseline_valid'] == r['intervention_valid'] == 5],
    }

    return {'input_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'metric': METRIC_NOTE,
            'bootstrap_note': BOOTSTRAP_NOTE,
            'groups': {k: summarize(v) for k, v in groups.items()},
            'attempts': {c: sum(r[c + '_attempts'] for r in rows) for c in CONDITIONS},
            'valid': {c: sum(r[c + '_valid'] for r in rows) for c in CONDITIONS},
            'incomplete_rows': [r for r in rows
                                if any(r[c + '_valid'] != r[c + '_attempts'] for c in CONDITIONS)],
            'human_info_items': sum(r['human_scores'].get('INFO', 0) > 0 for r in rows),
            'human_info_count': sum(r['human_scores'].get('INFO', 0) for r in rows),
            'human_count': sum(sum(r['human_scores'].values()) for r in rows),
            'human_count_median': statistics.median(sum(r['human_scores'].values()) for r in rows),
            'split_sizes': counts,
            # Confirms the batch is the first 60 dev rows in order, which is the
            # selection the write-up describes. None when no archive was given.
            'first_dev_rows_exact_match': ids == list(dataset)[:len(ids)] if dataset else None,
            'items': rows}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('results')
    p.add_argument('--archive', help='anecdotes.tar, for cross-checking against the dev split')
    p.add_argument('--out', default='audit_report.json')
    args = p.parse_args()

    dest = Path(args.out)
    if dest.resolve() == Path(args.results).resolve():
        raise ValueError('Output cannot overwrite input')
    report = audit(args.results, args.archive)
    dest.write_text(json.dumps(report, indent=2) + '\n')
    # Item-level detail goes to the file; the console shows only the summary.
    print(json.dumps({k: v for k, v in report.items() if k not in ('items', 'incomplete_rows')}, indent=2))
    print('Full audit saved to', dest)


if __name__ == '__main__':
    main()
