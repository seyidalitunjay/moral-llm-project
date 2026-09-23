"""Analyse a logged pilot run, reporting coverage before any comparison.

Coverage is reported first and separately because the divergences that follow are
computed from whatever responses parsed successfully. If one arm lost more
responses than another, its distribution rests on fewer samples and the missingness
is not plausibly unrelated to the condition, so the comparison is only as sound as
the coverage table above it.

Each comparison therefore appears twice: over every item where both arms yielded a
distribution, and restricted to items where every planned response in all three
arms parsed. Agreement between the two is weak evidence that missingness is not
driving the result; disagreement is a reason to distrust it.
"""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

# Lets the script run straight from a clone, with or without an editable install.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from moral_judgment.io import read_jsonl
from moral_judgment.metrics import distribution, js, summarize
from moral_judgment.parsing import PARSER_VERSION, classify_response

# Left against right, where right plays the baseline role in each summary. The
# third pair is the one the design exists to answer: whether the empathy content
# does anything a content-free appraisal of similar shape does not.
COMPARISONS = (('original', 'baseline'), ('generic', 'baseline'), ('original', 'generic'))

MISSINGNESS_NOTE = ('Exploratory development results; available-valid distributions may be '
                    'biased by missingness.')


def load_cells(root, cfg, reparse):
    """Group responses by (item, condition), validating each record's identity.

    The manifest is rehashed and every record checked against it, so a directory
    holding responses from more than one configuration, a duplicated slot, or a
    sample index outside the planned range stops the analysis instead of silently
    contributing to a mean.
    """
    expected = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()
    n = cfg['samples']
    cells = {(i, c): [] for i in cfg['human_scores'] for c in cfg['conditions']}
    seen = set()
    for r in read_jsonl(root / 'responses.jsonl'):
        key = (r['id'], r['condition'], r['sample'])
        if r['config_hash'] != expected or key in seen or key[:2] not in cells or not 0 <= key[2] < n:
            raise ValueError('Invalid configuration, duplicate, or unexpected sample')
        seen.add(key)
        if reparse and 'response' in r:
            # Reparsing derives new labels from the saved raw text into a separate
            # report. The record on disk is never rewritten, so the originally
            # recorded status of each response stays recoverable.
            r = dict(r)
            r['label'], r['status'] = classify_response(r['response'], cfg['labels'])
        cells[key[:2]].append(r)
    return cells


def coverage(cells, cfg):
    """Planned, recorded and valid counts per condition, with failure reasons."""
    report = {}
    for c in cfg['conditions']:
        rs = [r for (_, cc), rows in cells.items() if cc == c for r in rows]
        report[c] = {'planned': len(cfg['human_scores']) * cfg['samples'],
                     'recorded': len(rs),
                     'valid': sum(r['status'] == 'valid' and r['label'] in cfg['labels'] for r in rs),
                     'statuses': dict(Counter(r['status'] for r in rs))}
    return report


def item_rows(cells, cfg):
    """Per-item divergence from the human distribution, in each condition."""
    rows = []
    for i, scores in cfg['human_scores'].items():
        h = distribution(scores, cfg['labels'])
        row = {'id': i, 'js': {}, 'complete_all_conditions': True}
        for c in cfg['conditions']:
            rs = cells[(i, c)]
            valid = [r['label'] for r in rs if r['status'] == 'valid' and r['label'] in cfg['labels']]
            q = distribution(Counter(valid), cfg['labels'])
            row['js'][c] = js(h, q) if h is not None and q is not None else None
            row['complete_all_conditions'] &= len(rs) == cfg['samples'] and len(valid) == cfg['samples']
        rows.append(row)
    return rows


def comparisons(items):
    report = {}
    for left, right in COMPARISONS:
        for complete in (False, True):
            rows = []
            for r in items:
                if complete and not r['complete_all_conditions']:
                    continue
                b = r['js'][right]
                i = r['js'][left]
                if b is not None and i is not None:
                    rows.append({'baseline_js': b, 'intervention_js': i, 'difference': i - b})
            key = f'{left}_minus_{right}' + ('_complete_all_arms' if complete else '_available_pairs')
            report[key] = summarize(rows)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run_directory')
    p.add_argument('--reparse', action='store_true',
                   help='Reparse saved raw content into a separate derived analysis; never overwrite responses')
    args = p.parse_args()

    root = Path(args.run_directory)
    cfg = json.loads((root / 'manifest.json').read_text())
    cells = load_cells(root, cfg, args.reparse)

    report = {'note': MISSINGNESS_NOTE, 'coverage': {}, 'comparisons': {}, 'items': []}
    report['coverage'] = coverage(cells, cfg)
    report['items'] = item_rows(cells, cfg)
    report['comparisons'] = comparisons(report['items'])
    # Records which parser produced the labels being summarised, so a reparsed
    # analysis can never be mistaken for the run's original measurement.
    report['parser_used'] = PARSER_VERSION if args.reparse else 'labels and statuses as recorded'
    report['posthoc_reparse'] = args.reparse

    out = root / ('analysis_reparsed.json' if args.reparse else 'analysis.json')
    out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'items'}, indent=2))


if __name__ == '__main__':
    main()
