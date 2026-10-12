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
import math
import sys
from collections import Counter
from pathlib import Path

# Lets the script run straight from a clone, with or without an editable install.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from moral_judgment.io import read_jsonl
from moral_judgment.metrics import distribution, js, summarize
from moral_judgment.parsing import (PARSER_VERSION, TOLERANT_PARSER_VERSION, classify_response,
                                    parse_label, parse_label_tolerant)

PARSERS = {PARSER_VERSION: parse_label, TOLERANT_PARSER_VERSION: parse_label_tolerant}

# Left against right, where right plays the baseline role in each summary. The
# third pair is the one the design exists to answer: whether the empathy content
# does anything a content-free appraisal of similar shape does not.
COMPARISONS = (('original', 'baseline'), ('generic', 'baseline'), ('original', 'generic'))

# Study 2 has one primary comparison, P3 in docs/preregistration_study2.md. Its
# baseline comparisons are against another run and are computed separately, as
# descriptives, by `study2_descriptives`.
STUDY2_PROTOCOL = 'study2_persona_mixture_v1'
STUDY2_COMPARISONS = (('trait_mixture', 'irrelevant_mixture'),)

MISSINGNESS_NOTE = ('Exploratory development results; available-valid distributions may be '
                    'biased by missingness.')
HELDOUT_NOTE = ('Held-out evaluation under docs/preregistration.md; available-valid distributions '
                'may be biased by missingness.')
STUDY2_NOTE = ('Study 2 under docs/preregistration_study2.md; available-valid distributions may be '
               'biased by missingness. Comparisons with the Study 1 baseline are descriptive only.')


def load_cells(root, cfg, reparse, parser=PARSER_VERSION):
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
            r['label'], r['status'] = classify_response(r['response'], cfg['labels'], PARSERS[parser])
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


def comparisons(items, pairs=COMPARISONS):
    report = {}
    for left, right in pairs:
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


def valid_distribution(rows, cfg):
    valid = [r['label'] for r in rows if r['status'] == 'valid' and r['label'] in cfg['labels']]
    return distribution(Counter(valid), cfg['labels'])


def entropy(p):
    return -sum(x * math.log2(x) for x in p if x)


def per_arm_descriptives(dists, labels):
    """Verdict shares and entropy of one arm, each the mean over items.

    Each item counts once, whatever its number of valid draws or human votes;
    items with no distribution are left out and counted in `n`.
    """
    ds = [d for d in dists if d is not None]
    return {'n': len(ds),
            'verdict_shares': {k: sum(d[j] for d in ds) / len(ds) for j, k in enumerate(labels)},
            'mean_entropy_bits': sum(entropy(d) for d in ds) / len(ds)}


def study2_descriptives(cells, cfg, items, reparse, parser):
    """Each arm against Study 1's baseline, and per-arm verdict shares and entropy.

    Study 1's baseline was sampled at a different time, so its differences from
    the Study 2 arms mix the persona effect with any provider drift between the
    runs. The Study 1 run is loaded through `load_cells`, which revalidates its
    hash, and reparsed with the same parser whenever this analysis is.
    """
    root = Path(__file__).resolve().parent.parent / cfg['items_source']['study1_run']
    cfg1 = json.loads((root / 'manifest.json').read_text())
    if hashlib.sha256(json.dumps(cfg1, sort_keys=True).encode()).hexdigest() != cfg['items_source']['study1_config_hash']:
        raise ValueError('Study 1 manifest does not match the recorded hash')
    if cfg1['human_scores'] != cfg['human_scores'] or cfg1['labels'] != cfg['labels']:
        raise ValueError('Study 1 items, human scores or labels differ')
    cells1 = load_cells(root, cfg1, reparse, parser)
    baseline = {i: valid_distribution(cells1[(i, 'baseline')], cfg1) for i in cfg['human_scores']}
    report = {'note': 'Descriptive only. Study 1 baseline from a different run time.',
              'arm_minus_study1_baseline': {}, 'per_arm': {}}
    for arm in cfg['conditions']:
        rows = []
        for r in items:
            h = distribution(cfg['human_scores'][r['id']], cfg['labels'])
            b = js(h, baseline[r['id']]) if h is not None and baseline[r['id']] is not None else None
            if b is not None and r['js'][arm] is not None:
                rows.append({'baseline_js': b, 'intervention_js': r['js'][arm], 'difference': r['js'][arm] - b})
        report['arm_minus_study1_baseline'][f'{arm}_minus_study1_baseline_available_pairs'] = summarize(rows)
    for arm in cfg['conditions']:
        report['per_arm'][arm] = per_arm_descriptives(
            [valid_distribution(cells[(i, arm)], cfg) for i in cfg['human_scores']], cfg['labels'])
    report['per_arm']['study1_baseline'] = per_arm_descriptives(list(baseline.values()), cfg['labels'])
    report['per_arm']['human'] = per_arm_descriptives(
        [distribution(s, cfg['labels']) for s in cfg['human_scores'].values()], cfg['labels'])
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run_directory')
    p.add_argument('--reparse', action='store_true',
                   help='Reparse saved raw content into a separate derived analysis; never overwrite responses')
    p.add_argument('--parser', choices=sorted(PARSERS), default=PARSER_VERSION,
                   help='Parser used by --reparse')
    args = p.parse_args()

    root = Path(args.run_directory)
    cfg = json.loads((root / 'manifest.json').read_text())
    cells = load_cells(root, cfg, args.reparse, args.parser)

    study2 = cfg['protocol'] == STUDY2_PROTOCOL
    note = (STUDY2_NOTE if study2 else
            HELDOUT_NOTE if cfg['protocol'].startswith('heldout') else MISSINGNESS_NOTE)
    report = {'note': note, 'coverage': {}, 'comparisons': {}, 'items': []}
    report['coverage'] = coverage(cells, cfg)
    report['items'] = item_rows(cells, cfg)
    report['comparisons'] = comparisons(report['items'], STUDY2_COMPARISONS if study2 else COMPARISONS)
    if study2:
        report['descriptive'] = study2_descriptives(cells, cfg, report['items'], args.reparse, args.parser)
    # Records which parser produced the labels being summarised, so a reparsed
    # analysis can never be mistaken for the run's original measurement.
    report['parser_used'] = args.parser if args.reparse else 'labels and statuses as recorded'
    report['posthoc_reparse'] = args.reparse

    out = root / (f'analysis_reparsed_{args.parser}.json' if args.reparse and args.parser != PARSER_VERSION
                  else 'analysis_reparsed.json' if args.reparse else 'analysis.json')
    out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'items'}, indent=2))


if __name__ == '__main__':
    main()
