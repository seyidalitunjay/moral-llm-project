"""EXPLORATORY dispersion analysis of the held-out run, defined after its results were seen.

Nothing here is pre-registered. These quantities were chosen after the primary
and sensitivity results of run 7edf899cb4bf44f4 had been read, to ask whether the
arms differ in how spread out their verdicts are, how close a model could be
expected to get given only ten draws, and whether the arm differences concentrate
on contested items. A second pass (log entry E2) replaced the panel ceiling with a
disjoint version and added the mean verdict shift and modal agreement. Every figure
is descriptive and must not be read as a test of the pre-registered comparisons.
See docs/exploratory_log.md.

Analysis only: no requests are sent and no existing file is written. Labels and
statuses are used as recorded (no reparse), and the per-item divergences come from
the same functions as the main analysis.
"""
import argparse
import json
import math
import random
import statistics
import sys
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

# Lets the script run straight from a clone, with or without an editable install.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import moral_judgment.metrics as metrics
from analyze_control_pilot import item_rows, load_cells
from moral_judgment.metrics import distribution, js, quantile, summarize

SEED = 20261012
BOOT = 10000
PANEL_SIZE = 10
PANEL_MIN_VOTES = 20
PANEL_DRAWS = 1000

DEFAULT_RUN = Path(__file__).resolve().parent.parent / 'results' / 'heldout' / '7edf899cb4bf44f4'

STATUS = 'EXPLORATORY'
NOTE = ('EXPLORATORY: defined after the primary results were seen, not pre-registered. '
        'Descriptive only; not a test of the pre-registered comparisons.')

ARM_PAIRS = (('generic', 'baseline'), ('original', 'generic'))
SHIFT_PAIRS = ARM_PAIRS + (('baseline', 'human'), ('generic', 'human'))
MODAL_PAIRS = ARM_PAIRS + (('original', 'baseline'),)

# Probabilities from small integer counts; a tolerance keeps equal shares equal.
TIE_TOL = 1e-12


@contextmanager
def bootstrap_seed(seed):
    """Run the main analysis's `summarize` unchanged, but under this script's seed.

    `summarize` reads the module-level seed at call time, so swapping it here keeps
    the resampling procedure identical to the main analysis without editing it.
    """
    saved = metrics.BOOTSTRAP_SEED
    metrics.BOOTSTRAP_SEED = seed
    try:
        yield
    finally:
        metrics.BOOTSTRAP_SEED = saved


def entropy(p):
    return -sum(x * math.log2(x) for x in p if x)


def paired(values, left, right):
    """Paired-item summary of values[left] - values[right], keyed for a dispersion measure."""
    rows = [{'baseline_js': v[right], 'intervention_js': v[left], 'difference': v[left] - v[right]}
            for v in values if v[left] is not None and v[right] is not None]
    with bootstrap_seed(SEED):
        s = summarize(rows, boot=BOOT)
    if not s['n']:
        return {'n': 0}
    return {'n': s['n'], f'mean_{left}': s['intervention_js'], f'mean_{right}': s['baseline_js'],
            'mean_difference': s['difference'],
            f'{left}_lower': s['closer'], f'{left}_higher': s['farther'], 'tied': s['tied'],
            'paired_item_bootstrap_95_percent': s['exploratory_paired_item_bootstrap_95_percent']}


def ranks(xs):
    """Average ranks, so tied values (common under resampling) share a rank."""
    order = sorted(range(len(xs)), key=xs.__getitem__)
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(xs, ys):
    """Pearson correlation of average ranks; None when either side is constant."""
    rx, ry = ranks(xs), ranks(ys)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    return sxy / math.sqrt(sxx * syy) if sxx and syy else None


def spearman_bootstrap(pairs, rng):
    xs, ys = zip(*pairs)
    stats, degenerate = [], 0
    for _ in range(BOOT):
        sample = rng.choices(pairs, k=len(pairs))
        rho = spearman(*zip(*sample))
        if rho is None:
            degenerate += 1
        else:
            stats.append(rho)
    return {'n': len(pairs), 'spearman_rho': spearman(xs, ys),
            'item_bootstrap_95_percent': [quantile(stats, .025), quantile(stats, .975)],
            'bootstrap_resamples': BOOT, 'degenerate_resamples_dropped': degenerate}


def vote_pool(scores, labels):
    return [k for k in labels for _ in range(scores.get(k, 0))]


def panel_overlapping(scores, labels, rng):
    """Mean JSD between a random 10-vote panel and the full human distribution.

    Biased low: the panel's own votes are part of the reference it is scored
    against. Kept only so the first-pass figure stays traceable; see panel_disjoint.
    """
    pool = vote_pool(scores, labels)
    full = distribution(scores, labels)
    total = 0.0
    for _ in range(PANEL_DRAWS):
        total += js(distribution(Counter(rng.sample(pool, PANEL_SIZE)), labels), full)
    return total / PANEL_DRAWS


def panel_disjoint(scores, labels, rng):
    """Mean JSD between a random 10-vote panel and the remaining votes only."""
    pool = vote_pool(scores, labels)
    total = 0.0
    for _ in range(PANEL_DRAWS):
        order = rng.sample(range(len(pool)), len(pool))
        panel = Counter(pool[j] for j in order[:PANEL_SIZE])
        rest = Counter(pool[j] for j in order[PANEL_SIZE:])
        total += js(distribution(panel, labels), distribution(rest, labels))
    return total / PANEL_DRAWS


def modal_set(p, labels):
    top = max(p)
    return {k for k, x in zip(labels, p) if top - x <= TIE_TOL}


def mean_or_none(xs):
    return statistics.mean(xs) if xs else None


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('run_directory', nargs='?', default=str(DEFAULT_RUN))
    args = p.parse_args()

    root = Path(args.run_directory)
    cfg = json.loads((root / 'manifest.json').read_text())
    labels, arms = cfg['labels'], cfg['conditions']
    cells = load_cells(root, cfg, reparse=False)
    js_by_item = {r['id']: r['js'] for r in item_rows(cells, cfg)}

    # Per-item dispersion. Model cells use valid labels only, filtered exactly as in
    # item_rows; humans use non-INFO counts renormalised over the four labels.
    items = []
    for i, scores in cfg['human_scores'].items():
        h = distribution(scores, labels)
        row = {'id': i, 'human_non_info_votes': sum(scores.get(k, 0) for k in labels),
               'entropy': {'human': entropy(h) if h else None},
               'modal_share': {'human': max(h) if h else None},
               'valid_n': {}, 'js': js_by_item[i], 'distribution': {'human': h}}
        for c in arms:
            valid = [r['label'] for r in cells[(i, c)] if r['status'] == 'valid' and r['label'] in labels]
            q = distribution(Counter(valid), labels)
            row['valid_n'][c] = len(valid)
            row['distribution'][c] = q
            row['entropy'][c] = entropy(q) if q else None
            row['modal_share'][c] = max(q) if q else None
        items.append(row)

    dispersion = {'note': NOTE, 'status': STATUS, 'units': 'entropy in bits (max 2 over four labels)'}
    for measure in ('entropy', 'modal_share'):
        vals = [r[measure] for r in items]
        dispersion[measure] = {
            'means': {k: {'n': sum(v[k] is not None for v in vals),
                          'mean': mean_or_none([v[k] for v in vals if v[k] is not None])}
                      for k in arms + ['human']},
            'paired_differences': {f'{l}_minus_{r}': paired(vals, l, r)
                                   for l, r in ARM_PAIRS + (('baseline', 'human'),)}}

    # Ceiling: how far a 10-vote human panel lands from other humans on the same item.
    # The overlapping draws run first on the shared stream so that the first-pass
    # figures, including the Spearman intervals below, reproduce exactly; the
    # disjoint draws get their own stream under the same seed.
    rng = random.Random(SEED)
    eligible = [r for r in items if r['human_non_info_votes'] >= PANEL_MIN_VOTES]
    for r in eligible:
        r['panel_overlapping_biased_low_js'] = panel_overlapping(cfg['human_scores'][r['id']], labels, rng)
    disjoint_rng = random.Random(SEED)
    for r in eligible:
        r['panel_ceiling_js'] = panel_disjoint(cfg['human_scores'][r['id']], labels, disjoint_rng)
    votes = [r['human_non_info_votes'] for r in eligible]
    ceiling = {
        'note': NOTE, 'status': STATUS,
        'definition': (f'per item, mean over {PANEL_DRAWS} draws of base-2 JSD between {PANEL_SIZE} non-INFO '
                       f'votes drawn without replacement and the remaining non-INFO votes of that item '
                       f'(disjoint); items with at least {PANEL_MIN_VOTES} non-INFO votes'),
        'items_total': len(items), 'items_qualifying': len(eligible),
        'qualifying_vote_count_range': [min(votes), max(votes)] if votes else None,
        'qualifying_vote_count_median': statistics.median(votes) if votes else None,
        'mean_panel_ceiling_js': mean_or_none([r['panel_ceiling_js'] for r in eligible]),
        'overlapping_biased_low': {
            'definition': ('first-pass version: panel scored against the full distribution, which includes '
                           'the panel itself, so the divergence is biased low; superseded, kept for the record'),
            'mean_panel_js': mean_or_none([r['panel_overlapping_biased_low_js'] for r in eligible])},
        'model_mean_js_same_items': {
            c: {'n': sum(r['js'][c] is not None for r in eligible),
                'mean': mean_or_none([r['js'][c] for r in eligible if r['js'][c] is not None])}
            for c in arms}}

    # Contested vs consensus: does the arm difference track human disagreement?
    contested = {'note': NOTE, 'status': STATUS}
    defined = [r['entropy']['human'] for r in items if r['entropy']['human'] is not None]
    median = statistics.median(defined)
    contested['median_human_entropy'] = median
    contested['split_rule'] = 'low: human entropy <= median; high: human entropy > median'
    for l, r in ARM_PAIRS:
        pairs = [(row['entropy']['human'], row['js'][l] - row['js'][r]) for row in items
                 if row['entropy']['human'] is not None and row['js'][l] is not None and row['js'][r] is not None]
        halves = {}
        for name, keep in (('low_entropy_half', lambda e: e <= median), ('high_entropy_half', lambda e: e > median)):
            ds = [d for e, d in pairs if keep(e)]
            halves[name] = {'n': len(ds), 'mean_delta_js': mean_or_none(ds)}
        contested[f'{l}_minus_{r}'] = {'spearman_human_entropy_vs_delta_js': spearman_bootstrap(pairs, rng),
                                       **halves}

    # Verdict shift: where the mass sits, label by label, averaged over items.
    sources = arms + ['human']
    shift = {'note': NOTE, 'status': STATUS,
             'definition': ('per label, mean over items of each per-item distribution (model: valid labels; '
                            'human: non-INFO renormalised); paired differences are per label, over items '
                            'where both sides are defined'),
             'mean_distribution': {}, 'paired_differences': {}}
    for s in sources:
        ds = [r['distribution'][s] for r in items if r['distribution'][s] is not None]
        shift['mean_distribution'][s] = {'n': len(ds),
                                         **{k: statistics.mean(d[j] for d in ds) for j, k in enumerate(labels)}}
    for l, r in SHIFT_PAIRS:
        shift['paired_differences'][f'{l}_minus_{r}'] = {
            k: paired([{s: (row['distribution'][s][j] if row['distribution'][s] is not None else None)
                        for s in (l, r)} for row in items], l, r)
            for j, k in enumerate(labels)}

    # Modal agreement: does the model's most frequent verdict match the humans'?
    modal = {'note': NOTE, 'status': STATUS,
             'definition': ('per item, 1 if the model modal set and the human modal set share a label, else 0. '
                            'Human ties count as a match if the model mode is any tied label, as specified; '
                            'model ties are handled the same way (match if any tied model label is a human '
                            'modal label), which was not specified and is reported separately'),
             'human_tied_items': 0, 'model_tied_items': {}, 'matches_relying_on_model_tie': {},
             'agreement': {}, 'paired_differences': {}}
    hits = [{} for _ in items]
    for n, row in enumerate(items):
        h = row['distribution']['human']
        hm = modal_set(h, labels) if h is not None else None
        row['modal'] = {'human': sorted(hm) if hm else None}
        modal['human_tied_items'] += bool(hm and len(hm) > 1)
        for c in arms:
            q = row['distribution'][c]
            qm = modal_set(q, labels) if q is not None else None
            row['modal'][c] = sorted(qm) if qm else None
            hits[n][c] = float(bool(qm & hm)) if qm and hm else None
        row['modal_match'] = hits[n]
    for c in arms:
        xs = [h[c] for h in hits if h[c] is not None]
        modal['model_tied_items'][c] = sum(len(r['modal'][c] or ()) > 1 for r in items)
        modal['matches_relying_on_model_tie'][c] = sum(
            bool(r['modal_match'][c]) and len(r['modal'][c]) > 1 for r in items)
        modal['agreement'][c] = {'n': len(xs), 'share': mean_or_none(xs)}
    for l, r in MODAL_PAIRS:
        modal['paired_differences'][f'{l}_minus_{r}'] = paired(hits, l, r)

    report = {'status': STATUS, 'note': NOTE, 'run': cfg['protocol'], 'run_directory': str(root),
              'seed': SEED,
              'seed_note': ('All resampling uses this seed. Paired differences use '
                            'moral_judgment.metrics.summarize unchanged, with its module seed '
                            'temporarily set to this value (main analysis used 20260913); each '
                            'summarize call restarts from it. The overlapping panel draws and the '
                            'Spearman bootstraps share one Random(seed) stream, in that order; the '
                            'disjoint panel draws use a separate Random(seed).'),
              'labels_used': 'valid labels and statuses as recorded; no reparse',
              'human_support': 'INFO excluded, renormalised over ' + '/'.join(labels),
              'dispersion': dispersion, 'panel_ceiling': ceiling, 'contested_vs_consensus': contested,
              'verdict_shift': shift, 'modal_agreement': modal, 'items': items}

    out_dir = root / 'exploratory'
    out_dir.mkdir(exist_ok=True)
    out = out_dir / 'dispersion.json'
    out.write_text(json.dumps(report, indent=2) + '\n')
    print_summary(report, arms, out)


def fmt(x, d=3):
    return 'n/a' if x is None else f'{x:.{d}f}'


def ci(pair):
    return f'[{fmt(pair[0])}, {fmt(pair[1])}]'


def print_summary(rep, arms, out):
    print('=' * 78)
    print(f'{STATUS}: defined after the primary results were seen, NOT pre-registered.')
    print(f'Run {rep["run_directory"]}  seed {rep["seed"]}  labels as recorded')
    print('=' * 78)
    for measure, title in (('entropy', 'Shannon entropy (bits, max 2)'), ('modal_share', 'Modal-label share')):
        d = rep['dispersion'][measure]
        print(f'\n{title}: per-item mean')
        for k, v in d['means'].items():
            print(f'  {k:<9} {fmt(v["mean"])}  (n={v["n"]})')
        print('  Paired differences (95% paired-item bootstrap, 10,000 resamples):')
        for k, v in d['paired_differences'].items():
            l = k.split('_minus_')[0]
            print(f'    {k:<22} {fmt(v["mean_difference"]):>7}  {ci(v["paired_item_bootstrap_95_percent"])}'
                  f'  n={v["n"]}  {l} lower/higher/tied {v[l + "_lower"]}/{v[l + "_higher"]}/{v["tied"]}')
    c = rep['panel_ceiling']
    lo, hi = c['qualifying_vote_count_range']
    print(f'\n10-human panel ceiling, disjoint ({c["items_qualifying"]} of {c["items_total"]} items have '
          f'>= {PANEL_MIN_VOTES} non-INFO votes; range {lo}-{hi}, median {fmt(c["qualifying_vote_count_median"], 1)})')
    print(f'  CEILING  panel vs remaining votes:      {fmt(c["mean_panel_ceiling_js"])}')
    print(f'  (superseded) overlapping_biased_low:    {fmt(c["overlapping_biased_low"]["mean_panel_js"])}')
    for k, v in c['model_mean_js_same_items'].items():
        print(f'  model {k:<9} mean JSD, same items:  {fmt(v["mean"])}  (n={v["n"]})')
    cv = rep['contested_vs_consensus']
    print(f'\nContested vs consensus (median human entropy {fmt(cv["median_human_entropy"])} bits)')
    for l, r in ARM_PAIRS:
        v = cv[f'{l}_minus_{r}']
        s = v['spearman_human_entropy_vs_delta_js']
        print(f'  dJSD {l} - {r}: Spearman rho {fmt(s["spearman_rho"])} {ci(s["item_bootstrap_95_percent"])}'
              f'  n={s["n"]}  (degenerate resamples dropped: {s["degenerate_resamples_dropped"]})')
        for h in ('low_entropy_half', 'high_entropy_half'):
            print(f'    {h:<18} mean dJSD {fmt(v[h]["mean_delta_js"]):>7}  n={v[h]["n"]}')
    sh = rep['verdict_shift']
    labels = [k for k in sh['mean_distribution']['human'] if k != 'n']
    print('\nVerdict shift: mean per-item distribution')
    print('  ' + ' ' * 10 + ''.join(f'{k:>10}' for k in labels))
    for s, v in sh['mean_distribution'].items():
        print(f'  {s:<10}' + ''.join(f'{fmt(v[k]):>10}' for k in labels) + f'   n={v["n"]}')
    print('  Per-label paired differences (95% paired-item bootstrap, 10,000 resamples):')
    for pair, per_label in sh['paired_differences'].items():
        print(f'    {pair}')
        for k, v in per_label.items():
            flag = '  *' if v['paired_item_bootstrap_95_percent'][0] > 0 or v['paired_item_bootstrap_95_percent'][1] < 0 else ''
            print(f'      {k:<10} {fmt(v["mean_difference"]):>7}  {ci(v["paired_item_bootstrap_95_percent"])}'
                  f'  n={v["n"]}{flag}')
    m = rep['modal_agreement']
    print(f'\nModal agreement (items with a human modal tie: {m["human_tied_items"]})')
    for c_, v in m['agreement'].items():
        print(f'  {c_:<9} {fmt(v["share"])}  (n={v["n"]}; model-mode ties {m["model_tied_items"][c_]}, '
              f'matches relying on a model tie {m["matches_relying_on_model_tie"][c_]})')
    print('  Paired differences (95% paired-item bootstrap, 10,000 resamples):')
    for k, v in m['paired_differences'].items():
        print(f'    {k:<22} {fmt(v["mean_difference"]):>7}  {ci(v["paired_item_bootstrap_95_percent"])}  n={v["n"]}')
    print('  (* in verdict shift = interval excludes zero; exploratory, unadjusted for the many intervals shown)')
    print(f'\nWritten to {out}')
    print(f'{STATUS}: descriptive only; not evidence for or against the pre-registered comparisons.')


if __name__ == '__main__':
    main()
