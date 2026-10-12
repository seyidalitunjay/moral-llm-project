"""Write docs/results.md from the result files and the git history.

Every number in the document is read here from an analysis.json, a manifest.json,
a responses.jsonl or the exploratory dispersion.json; every commit is read from
`git log`. Nothing is retyped. Result files are only read, and no request is sent.

Statements that depend on the numbers (each pre-registered verdict, which pairs
disagree, the commit order) are derived here and checked, so the prose cannot
drift from the files it describes.
"""
import json
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from moral_judgment.metrics import LABELS

DEV = ROOT / 'results' / 'pilot_v4' / '32fa0ec867b00d0c'
S1 = ROOT / 'results' / 'heldout' / '7edf899cb4bf44f4'
S2 = ROOT / 'results' / 'study2' / '2e2b551529945ff6'
OUT = ROOT / 'docs' / 'results.md'

NAMES = {'baseline': 'direct judgment', 'generic': 'generic appraisal', 'original': 'moral-cognitive appraisal',
         'trait_mixture': 'trait mixture', 'irrelevant_mixture': 'irrelevant mixture', 'human': 'humans',
         'study1_baseline': 'Study 1 direct judgment'}
VERDICT_NAMES = {'AUTHOR': 'Author', 'OTHER': 'Other', 'EVERYBODY': 'Everybody', 'NOBODY': 'Nobody'}

# Provenance rows: label, and the start of the commit subject that identifies it.
COMMITS = (('Study 1 pre-registration', 'Pre-register held-out evaluation'),
           ('Study 1 raw responses', 'Held-out run 7edf899cb4bf44f4'),
           ('Study 1 analysis (primary, S1, S2)', 'Held-out analysis'),
           ('Exploratory analyses (post hoc)', 'Exploratory (post-hoc)'),
           ('Study 2 pre-registration', 'Pre-register Study 2'),
           ('Study 2 pre-registration clarification (before execution)', 'Study 2 preregistration: clarify'),
           ('Study 2 raw responses', 'Study 2 run 2e2b551529945ff6'),
           ('Study 2 analysis (P3, S1, S2)', 'Study 2 analysis'))


def load(path):
    return json.loads(Path(path).read_text())


def f(x, d=4):
    return f'{x:+.{d}f}'


def ci(pair, d=4):
    return f'[{pair[0]:+.{d}f}, {pair[1]:+.{d}f}]'


def verdict(s):
    """The pre-registered inference rule, applied to one summary."""
    lo, hi = s['exploratory_paired_item_bootstrap_95_percent']
    return 'closer' if hi < 0 else 'farther' if lo > 0 else 'not distinguished'


def verdict_text(s, left, right):
    v = verdict(s)
    if v == 'not distinguished':
        return 'Not distinguished (interval includes zero)'
    return (f'{NAMES[left].capitalize()} {v} {"to" if v == "closer" else "from"} humans than {NAMES[right]} '
            f'(interval excludes zero)')


def excludes_zero(pair):
    return pair[0] > 0 or pair[1] < 0


def coverage_table(cov):
    rows = ['| Arm | Planned | Recorded | Valid | Failures by status |', '| --- | ---: | ---: | ---: | --- |']
    for arm, c in cov.items():
        fails = ', '.join(f'`{k}` {v}' for k, v in c['statuses'].items() if k != 'valid') or 'none'
        rows.append(f'| {NAMES[arm]} (`{arm}`) | {c["planned"]} | {c["recorded"]} | {c["valid"]} | {fails} |')
    return '\n'.join(rows)


def comparison_table(comparisons, pairs, suffix, with_verdict=True):
    head = '| Comparison | n | Mean JSD, left | Mean JSD, right | Mean difference | 95% CI | Closer / farther / tied |'
    sep = '| --- | ---: | ---: | ---: | ---: | --- | --- |'
    if with_verdict:
        head += ' Pre-registered verdict |'
        sep += ' --- |'
    rows = [head, sep]
    for label, left, right in pairs:
        s = comparisons[f'{left}_minus_{right}{suffix}']
        row = (f'| {label}: {NAMES[left]} − {NAMES[right]} | {s["n"]} | {s["intervention_js"]:.4f} | '
               f'{s["baseline_js"]:.4f} | {f(s["difference"])} | '
               f'{ci(s["exploratory_paired_item_bootstrap_95_percent"])} | '
               f'{s["closer"]} / {s["farther"]} / {s["tied"]} |')
        if with_verdict:
            row += f' {verdict_text(s, left, right)} |'
        rows.append(row)
    return '\n'.join(rows)


def paired_table(diffs, keys, label_of):
    """Exploratory paired differences, which use their own key layout."""
    rows = ['| Comparison | n | Mean difference | 95% CI | Lower / higher / tied | Interval excludes zero |',
            '| --- | ---: | ---: | --- | --- | --- |']
    for key in keys:
        d = diffs[key]
        left = key.split('_minus_')[0]
        c = d['paired_item_bootstrap_95_percent']
        rows.append(f'| {label_of(key)} | {d["n"]} | {f(d["mean_difference"])} | {ci(c)} | '
                    f'{d[left + "_lower"]} / {d[left + "_higher"]} / {d["tied"]} | '
                    f'{"yes" if excludes_zero(c) else "no"} |')
    return '\n'.join(rows)


def pair_name(key):
    left, right = key.split('_minus_')
    return f'{NAMES[left]} − {NAMES[right]}'


def mean_js(analysis, arm):
    vals = [r['js'][arm] for r in analysis['items'] if r['js'][arm] is not None]
    return len(vals), statistics.mean(vals)


def run_window(path):
    ts = [json.loads(line)['timestamp'] for line in path.read_text().splitlines() if line.strip()]
    return min(ts)[:16].replace('T', ' '), max(ts)[:16].replace('T', ' ')


def disagreement(a, b):
    """The pre-registered definition: signs differ, or exactly one interval excludes zero."""
    ca = a['exploratory_paired_item_bootstrap_95_percent']
    cb = b['exploratory_paired_item_bootstrap_95_percent']
    reasons = []
    if (a['difference'] > 0) != (b['difference'] > 0):
        reasons.append('sign differs')
    if excludes_zero(ca) != excludes_zero(cb):
        reasons.append('one interval excludes zero, the other includes it')
    return reasons


def commits():
    log = subprocess.run(['git', 'log', '--format=%h%x09%ad%x09%s', '--date=format:%Y-%m-%d %H:%M %z'],
                         cwd=ROOT, check=True, capture_output=True, text=True).stdout.splitlines()
    log = [line.split('\t', 2) for line in log]
    rows = []
    for label, prefix in COMMITS:
        hits = [c for c in log if c[2].startswith(prefix)]
        if len(hits) != 1:
            raise ValueError(f'{len(hits)} commits match {prefix!r}')
        rows.append((label, *hits[0]))
    # Each pre-registration precedes its raw responses, which precede the analysis.
    order = {label: i for i, (label, *_) in enumerate(rows)}
    position = {c[0]: i for i, c in enumerate(reversed(log))}
    for pre, raw, ana in ((0, 1, 2), (4, 6, 7), (5, 6, 7)):
        if not position[rows[pre][1]] < position[rows[raw][1]] < position[rows[ana][1]]:
            raise ValueError('Commit order does not match pre-registration, then responses, then analysis')
    if not position[rows[order['Study 1 analysis (primary, S1, S2)']][1]] < position[rows[3][1]]:
        raise ValueError('Exploratory commit precedes the Study 1 analysis')
    return rows


def main():
    dev, dev_m = load(DEV / 'analysis.json'), load(DEV / 'manifest.json')
    a1, r1, m1 = load(S1 / 'analysis.json'), load(S1 / 'analysis_reparsed.json'), load(S1 / 'manifest.json')
    a2, r2, m2 = load(S2 / 'analysis.json'), load(S2 / 'analysis_reparsed.json'), load(S2 / 'manifest.json')
    ex = load(S1 / 'exploratory' / 'dispersion.json')
    assert tuple(m1['labels']) == tuple(m2['labels']) == LABELS
    assert m1['human_scores'] == m2['human_scores']
    assert r1['parser_used'] == r2['parser_used'] == dev_m['parser_version']
    n_items = len(m1['human_scores'])
    provider = m1['extra_body']['provider']['only'][0]
    w1, w2 = run_window(S1 / 'responses.jsonl'), run_window(S2 / 'responses.jsonl')

    s1_pairs = (('P1', 'original', 'generic'), ('P2', 'generic', 'baseline'))
    s1_desc = (('Descriptive', 'original', 'baseline'),)
    s2_pairs = (('P3', 'trait_mixture', 'irrelevant_mixture'),)

    # Every primary result against each of its sensitivity analyses.
    checks = []
    for study, analysis, reparsed, pairs in (('Study 1', a1, r1, s1_pairs), ('Study 2', a2, r2, s2_pairs)):
        for label, left, right in pairs:
            p = analysis['comparisons'][f'{left}_minus_{right}_available_pairs']
            for sens, s in (('S1', analysis['comparisons'][f'{left}_minus_{right}_complete_all_arms']),
                            ('S2', reparsed['comparisons'][f'{left}_minus_{right}_available_pairs'])):
                checks.append((study, label, sens, p, s, disagreement(p, s)))
    found = {(c[0], c[1], c[2]) for c in checks if c[5]}
    if found != {('Study 1', 'P2', 'S1'), ('Study 2', 'P3', 'S1')}:
        raise ValueError(f'Disagreements differ from those this document describes: {sorted(found)}')

    o = []
    w = o.append
    w('# Results')
    w('')
    w('A factual record of every result in this repository: the two pre-registered studies, the exploratory '
      'analyses run after the first of them, and the development run that preceded both. Every number below '
      'is read from the result files named in each section by `scripts/make_results_doc.py`; nothing is '
      'retyped. Interpretation is limited to what the pre-registrations allow.')
    w('')
    w('## Overview')
    w('')
    w(f'The question is whether perspective-taking, cognitive-empathy and justice-sensitivity content brings '
      f'a language model\'s distribution of moral verdicts closer to the distribution of human verdicts than '
      f'a matched control does: in Study 1 an appraisal prompt of the same shape without that content, in '
      f'Study 2 a mixture of personas varied on morally irrelevant traits. The model is `{m1["model"]}`, '
      f'served through OpenRouter by `{provider}` only, at temperature {m1["temperature"]} and top-p '
      f'{m1["top_p"]}. The items are {n_items} anecdotes drawn at random from the Scruples Anecdotes test '
      f'split, each with a spread of human annotator verdicts over four labels (author, other party, '
      f'everybody, nobody at fault). The measure is the base-2 Jensen-Shannon divergence (JSD; 0 = identical, '
      f'1 = disjoint) between the model\'s verdicts over {m1["samples"]} samples and the human verdicts (INFO '
      f'excluded), compared between prompts item by item with 95% paired-item bootstrap intervals (10,000 '
      f'resamples); a negative difference means the first-named prompt is closer to humans.')
    w('')
    w('**Inference rule** (pre-registered, both studies): a comparison is reported as showing a direction only if '
      'its 95% interval excludes zero; otherwise it is reported as not distinguishing the conditions. The '
      'intervals cover variation over anecdotes only, not sampling error in the model\'s draws or uncertainty '
      'in the human labels.')
    w('')

    # Study 1
    w('## Study 1: held-out three-condition evaluation')
    w('')
    w(f'Run `{S1.relative_to(ROOT)}`, protocol `{m1["protocol"]}`, pre-registered in '
      f'[preregistration.md](preregistration.md). Three prompts on the same {n_items} items, '
      f'{m1["samples"]} samples per item and prompt: **direct judgment** (`baseline`), a **generic** factual '
      f'appraisal of similar structure and length (`generic`), and the **moral-cognitive** appraisal '
      f'(`original`). Parser `{m1["parser_version"]}`. Responses were collected {w1[0]} to {w1[1]} UTC.')
    w('')
    w('### Coverage')
    w('')
    w(coverage_table(a1['coverage']))
    w('')
    w('### Primary comparisons')
    w('')
    w(comparison_table(a1['comparisons'], s1_pairs, '_available_pairs'))
    w('')
    w('Left and right are the first- and second-named prompts. Each item enters when both of its cells have '
      'at least one valid label.')
    w('')
    w('### S1: complete cases')
    w('')
    w('Restricted to items with all planned responses valid in all three arms.')
    w('')
    w(comparison_table(a1['comparisons'], s1_pairs, '_complete_all_arms'))
    w('')
    w(f'### S2: strict parser')
    w('')
    w(f'The saved responses reparsed under `{r1["parser_used"]}` (`analysis_reparsed.json`). Coverage under '
      f'that parser:')
    w('')
    w(coverage_table(r1['coverage']))
    w('')
    w(comparison_table(r1['comparisons'], s1_pairs, '_available_pairs'))
    w('')
    w('### Moral-cognitive − direct (descriptive)')
    w('')
    w('Not a pre-registered comparison; it conflates the effects that P1 and P2 separate.')
    w('')
    rows = ['| Analysis | n | Mean difference | 95% CI | Closer / farther / tied |', '| --- | ---: | ---: | --- | --- |']
    for name, src, suffix in (('Primary', a1, '_available_pairs'), ('S1 complete cases', a1, '_complete_all_arms'),
                              ('S2 strict parser', r1, '_available_pairs')):
        s = src['comparisons']['original_minus_baseline' + suffix]
        rows.append(f'| {name} | {s["n"]} | {f(s["difference"])} | '
                    f'{ci(s["exploratory_paired_item_bootstrap_95_percent"])} | '
                    f'{s["closer"]} / {s["farther"]} / {s["tied"]} |')
    w('\n'.join(rows))
    w('')
    w('Mean JSD from humans per arm, over items with a defined distribution:')
    w('')
    rows = ['| Arm | n | Mean JSD |', '| --- | ---: | ---: |']
    for arm in m1['conditions']:
        n, m = mean_js(a1, arm)
        rows.append(f'| {NAMES[arm]} | {n} | {m:.4f} |')
    w('\n'.join(rows))
    w('')
    w('Figure: [figures/fig2_results.png](../figures/fig2_results.png) (filled markers; hollow markers are '
      'the development run).')
    w('')

    # Exploratory
    w('## Exploratory analyses (post hoc, not pre-registered)')
    w('')
    w(f'Defined after the Study 1 results had been seen, on the same run; see '
      f'[exploratory_log.md](exploratory_log.md) (entries E1 and E2) for when and why each was run. Source: '
      f'`{S1.relative_to(ROOT)}/exploratory/dispersion.json`, status `{ex["status"]}`. Labels as recorded, no '
      f'reparse; resampling seed {ex["seed"]}. None of these is a test of a pre-registered comparison, and no '
      f'interval below has nominal coverage as a test.')
    w('')
    disp = ex['dispersion']
    w('### Dispersion')
    w('')
    w('Per item, the base-2 Shannon entropy (bits; maximum 2) and the modal-label share of each '
      'distribution, averaged over items.')
    w('')
    rows = ['| Source | n | Mean entropy (bits) | Mean modal share |', '| --- | ---: | ---: | ---: |']
    for s in ('baseline', 'generic', 'original', 'human'):
        e, m = disp['entropy']['means'][s], disp['modal_share']['means'][s]
        rows.append(f'| {NAMES[s]} | {e["n"]} | {e["mean"]:.4f} | {m["mean"]:.4f} |')
    w('\n'.join(rows))
    w('')
    keys = ('generic_minus_baseline', 'original_minus_generic', 'baseline_minus_human')
    w('Entropy, paired differences:')
    w('')
    w(paired_table(disp['entropy']['paired_differences'], keys, pair_name))
    w('')
    w('Modal share, paired differences:')
    w('')
    w(paired_table(disp['modal_share']['paired_differences'], keys, pair_name))
    w('')
    cc = ex['contested_vs_consensus']
    w(f'Contested vs consensus items. Spearman correlation between human entropy and the per-item JSD '
      f'difference, and the mean difference in each half of a split at the median human entropy '
      f'({cc["median_human_entropy"]:.4f} bits; low half = at or below the median):')
    w('')
    rows = ['| Difference | n | Spearman ρ | 95% CI | Mean, low-entropy half | Mean, high-entropy half |',
            '| --- | ---: | ---: | --- | ---: | ---: |']
    for key in ('generic_minus_baseline', 'original_minus_generic'):
        c = cc[key]
        sp = c['spearman_human_entropy_vs_delta_js']
        rows.append(f'| {pair_name(key)} | {sp["n"]} | {f(sp["spearman_rho"])} | '
                    f'{ci(sp["item_bootstrap_95_percent"])} | {f(c["low_entropy_half"]["mean_delta_js"])} '
                    f'(n={c["low_entropy_half"]["n"]}) | {f(c["high_entropy_half"]["mean_delta_js"])} '
                    f'(n={c["high_entropy_half"]["n"]}) |')
    w('\n'.join(rows))
    w('')
    pc = ex['panel_ceiling']
    w('### Disjoint 10-human ceiling')
    w('')
    w(f'How close ten humans get to the rest of the human panel: per item, the mean over 1,000 draws of the '
      f'JSD between 10 non-INFO votes drawn without replacement and the item\'s remaining non-INFO votes. Only '
      f'items with at least 20 non-INFO votes qualify: {pc["items_qualifying"]} of {pc["items_total"]} '
      f'(votes {pc["qualifying_vote_count_range"][0]}–{pc["qualifying_vote_count_range"][1]}, median '
      f'{pc["qualifying_vote_count_median"]:g}). These items are not representative of the {pc["items_total"]}.')
    w('')
    rows = ['| Source, same items | n | Mean JSD |', '| --- | ---: | ---: |',
            f'| 10-human panel vs remaining humans | {pc["items_qualifying"]} | {pc["mean_panel_ceiling_js"]:.4f} |']
    for arm, v in pc['model_mean_js_same_items'].items():
        rows.append(f'| {NAMES[arm]} vs all humans | {v["n"]} | {v["mean"]:.4f} |')
    w('\n'.join(rows))
    w('')
    w(f'A first-pass version scored each panel against the full distribution, which contains the panel '
      f'itself; it is biased low ({pc["overlapping_biased_low"]["mean_panel_js"]:.4f}) and superseded.')
    w('')
    vs = ex['verdict_shift']
    w('### Verdict shift')
    w('')
    w('Mean share of each verdict, averaging each item\'s distribution with equal weight per item. Figure: '
      '[figures/fig3_shift.png](../figures/fig3_shift.png).')
    w('')
    rows = ['| Source | n | ' + ' | '.join(VERDICT_NAMES[k] for k in LABELS) + ' |',
            '| --- | ---: |' + ' ---: |' * len(LABELS)]
    for s in ('human', 'baseline', 'generic', 'original'):
        md = vs['mean_distribution'][s]
        rows.append(f'| {NAMES[s]} | {md["n"]} | ' + ' | '.join(f'{md[k]:.4f}' for k in LABELS) + ' |')
    w('\n'.join(rows))
    w('')
    w('Paired per-label differences (16 intervals, no multiplicity adjustment; within a comparison the four '
      'labels sum to zero, so they are not independent):')
    w('')
    rows = ['| Comparison | Verdict | n | Mean difference | 95% CI | Interval excludes zero |',
            '| --- | --- | ---: | ---: | --- | --- |']
    for key, per_label in vs['paired_differences'].items():
        for k in LABELS:
            d = per_label[k]
            c = d['paired_item_bootstrap_95_percent']
            rows.append(f'| {pair_name(key)} | {VERDICT_NAMES[k]} | {d["n"]} | {f(d["mean_difference"])} | '
                        f'{ci(c)} | {"yes" if excludes_zero(c) else "no"} |')
    w('\n'.join(rows))
    w('')
    ma = ex['modal_agreement']
    w('### Modal agreement')
    w('')
    w('Share of items on which the model\'s most frequent verdict matches the humans\' most frequent verdict. '
      'A tie on either side counts as a match if any tied label matches; the rule for model ties was not '
      'specified in advance, so the matches that depend on it are counted separately.')
    w('')
    rows = ['| Arm | n | Agreement | Items with a model tie | Matches relying on a model tie |',
            '| --- | ---: | ---: | ---: | ---: |']
    for arm, v in ma['agreement'].items():
        rows.append(f'| {NAMES[arm]} | {v["n"]} | {v["share"]:.4f} | {ma["model_tied_items"][arm]} | '
                    f'{ma["matches_relying_on_model_tie"][arm]} |')
    w('\n'.join(rows))
    w('')
    w(f'Items with a human tie: {ma["human_tied_items"]}. Paired differences (0/1 per item, so the intervals '
      f'are coarse):')
    w('')
    w(paired_table(ma['paired_differences'], list(ma['paired_differences']), pair_name))
    w('')

    # Study 2
    w('## Study 2: trait-varied vs irrelevant-varied persona mixtures')
    w('')
    w(f'Run `{S2.relative_to(ROOT)}`, protocol `{m2["protocol"]}`, pre-registered in '
      f'[preregistration_study2.md](preregistration_study2.md). The same {n_items} items and human scores as '
      f'Study 1, with the Study 1 direct-judgment prompt preceded by a persona; sample *i* of each item is '
      f'judged by persona *i*. In the **trait mixture** the ten personas vary on perspective-taking, cognitive '
      f'empathy and justice sensitivity; in the **irrelevant mixture** they vary on drink, leisure and evening '
      f'preferences. Parser `{m2["parser_version"]}`, settings as Study 1. Responses were collected {w2[0]} to '
      f'{w2[1]} UTC.')
    w('')
    w('### Coverage')
    w('')
    w(coverage_table(a2['coverage']))
    w('')
    w('### Primary comparison')
    w('')
    w(comparison_table(a2['comparisons'], s2_pairs, '_available_pairs'))
    w('')
    w('### S1: complete cases')
    w('')
    w(comparison_table(a2['comparisons'], s2_pairs, '_complete_all_arms'))
    w('')
    w('### S2: strict parser')
    w('')
    w(f'Reparsed under `{r2["parser_used"]}`. Coverage under that parser:')
    w('')
    w(coverage_table(r2['coverage']))
    w('')
    w(comparison_table(r2['comparisons'], s2_pairs, '_available_pairs'))
    w('')
    desc = a2['descriptive']
    w('### Descriptive')
    w('')
    w(f'Not pre-registered as tests. **Run-time caveat:** the Study 1 direct-judgment arm was sampled '
      f'{w1[0]} to {w1[1]} UTC and Study 2 {w2[0]} to {w2[1]} UTC, so differences between them combine the '
      f'persona effect with any change in the provider or model between the runs.')
    w('')
    w('Each mixture minus the Study 1 direct-judgment arm, per-item JSD, paired over items:')
    w('')
    rows = ['| Comparison | n | Mean JSD, mixture | Mean JSD, Study 1 direct | Mean difference | 95% CI | '
            'Closer / farther / tied |', '| --- | ---: | ---: | ---: | ---: | --- | --- |']
    for arm in m2['conditions']:
        s = desc['arm_minus_study1_baseline'][f'{arm}_minus_study1_baseline_available_pairs']
        rows.append(f'| {NAMES[arm]} − Study 1 direct | {s["n"]} | {s["intervention_js"]:.4f} | '
                    f'{s["baseline_js"]:.4f} | {f(s["difference"])} | '
                    f'{ci(s["exploratory_paired_item_bootstrap_95_percent"])} | '
                    f'{s["closer"]} / {s["farther"]} / {s["tied"]} |')
    w('\n'.join(rows))
    w('')
    w('Verdict shares (each item\'s distribution averaged with equal weight) and mean per-item entropy:')
    w('')
    rows = ['| Source | n | ' + ' | '.join(VERDICT_NAMES[k] for k in LABELS) + ' | Mean entropy (bits) |',
            '| --- | ---: |' + ' ---: |' * (len(LABELS) + 1)]
    for s, v in desc['per_arm'].items():
        rows.append(f'| {NAMES[s]} | {v["n"]} | ' + ' | '.join(f'{v["verdict_shares"][k]:.4f}' for k in LABELS)
                    + f' | {v["mean_entropy_bits"]:.4f} |')
    w('\n'.join(rows))
    w('')
    w('Figure: [figures/fig4_study2.png](../figures/fig4_study2.png).')
    w('')

    # Disagreements
    w('## Pre-registered disagreements')
    w('')
    w('Both pre-registrations require that a primary result and a sensitivity analysis be reported as '
      'disagreeing when their signs differ or when one interval excludes zero and the other does not, and '
      'that the disagreement not be resolved by choosing between them. Every primary comparison was checked '
      'against S1 and S2:')
    w('')
    rows = ['| Study | Comparison | Sensitivity | Primary: mean, 95% CI | Sensitivity: mean, 95% CI | Result |',
            '| --- | --- | --- | --- | --- | --- |']
    for study, label, sens, p, s, reasons in checks:
        rows.append(f'| {study} | {label} | {sens} | {f(p["difference"])} {ci(p["exploratory_paired_item_bootstrap_95_percent"])} '
                    f'| {f(s["difference"])} {ci(s["exploratory_paired_item_bootstrap_95_percent"])} | '
                    f'{"**Disagreement**: " + "; ".join(reasons) if reasons else "Agrees"} |')
    w('\n'.join(rows))
    w('')
    p2, p2s1 = a1['comparisons']['generic_minus_baseline_available_pairs'], a1['comparisons']['generic_minus_baseline_complete_all_arms']
    p3, p3s1 = a2['comparisons']['trait_mixture_minus_irrelevant_mixture_available_pairs'], a2['comparisons']['trait_mixture_minus_irrelevant_mixture_complete_all_arms']
    w(f'- **Study 1, P2 vs S1.** The primary P2 interval excludes zero (generic appraisal farther from humans '
      f'than direct judgment, n = {p2["n"]}); the complete-case interval includes zero (n = {p2s1["n"]}). '
      f'Both means are positive. Reported as a disagreement and not resolved, as pre-registered.')
    w(f'- **Study 2, P3 vs S1.** The primary P3 mean is negative ({f(p3["difference"])}, n = {p3["n"]}) and '
      f'the complete-case mean positive ({f(p3s1["difference"])}, n = {p3s1["n"]}); both intervals include '
      f'zero, so neither distinguishes the two mixtures. Reported as a disagreement and not resolved, as '
      f'pre-registered.')
    w('')

    # Development
    dc = dev['coverage']
    fmt = sum(c['statuses'].get('invalid_label_format', 0) for c in dc.values())
    trunc = sum(c['statuses'].get('truncated', 0) for c in dc.values())
    w('## Development history')
    w('')
    w(f'Before Study 1, the three prompts were compared on {len(dev_m["human_scores"])} items from a '
      f'development pool that had been inspected by hand (run `{DEV.relative_to(ROOT)}`, {dev_m["samples"]} '
      f'samples per item and prompt, `max_tokens` {dev_m["max_tokens"]}, parser `{dev_m["parser_version"]}`). '
      f'Valid responses were ' + ', '.join(f'{c["valid"]}/{c["planned"]} {NAMES[a]}' for a, c in dc.items())
      + f'; the failures were {fmt} label-format failures and {trunc} truncations. That run was not '
      f'pre-registered and its results are exploratory; they appear as hollow markers in '
      f'[figures/fig2_results.png](../figures/fig2_results.png). Inspecting its format failures led to the '
      f'parser `{m1["parser_version"]}`, which was fixed before any held-out response was requested and is '
      f'the declared parser of both studies; the strict parser is kept as sensitivity analysis S2. See '
      f'[preregistration.md](preregistration.md), section 4.')
    w('')

    # Provenance
    w('## Provenance')
    w('')
    w('Commits in this repository, from `git log`. In each study the pre-registration was committed before '
      'the raw responses, and the raw responses before the analysis.')
    w('')
    rows = ['| Record | Commit | Date | Subject |', '| --- | --- | --- | --- |']
    for label, h, date, subject in commits():
        rows.append(f'| {label} | `{h}` | {date} | {subject} |')
    w('\n'.join(rows))
    w('')
    w(f'Configuration hashes: Study 1 `{S1.name}…`, Study 2 `{S2.name}…`, development `{DEV.name}…`. Each '
      f'covers every rendered prompt, item, human score, parser version and sampling setting of its run.')
    w('')
    OUT.write_text('\n'.join(o))
    print(f'Wrote {OUT.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
