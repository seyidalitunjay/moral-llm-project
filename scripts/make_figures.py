"""Build the three poster figures from existing result files only.

Every number drawn is read from an analysis.json, a manifest.json or the
exploratory dispersion.json; nothing is retyped and no request is sent. Result
files are only read. Output goes to figures/ as vector PDF and 300 dpi PNG at the
physical size each figure occupies on the A1 poster, so the font sizes below are
printed sizes.

fig1 takes the plotted distributions from exploratory/dispersion.json and is checked
against the primary analysis: its JSD is recomputed from the plotted bars and must
equal the value in analysis.json. fig3 is exploratory and its caption says so. The
fig2 caption's claim about the strict-parser sensitivity analysis (S2) is checked
against analysis_reparsed.json each time the script runs, not assumed.
"""
import json
import math
import statistics
import sys
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.transforms import blended_transform_factory

# Lets the script run straight from a clone, with or without an editable install.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from moral_judgment.metrics import LABELS, js

DEV = ROOT / 'results' / 'pilot_v4' / '32fa0ec867b00d0c'
HELDOUT = ROOT / 'results' / 'heldout' / '7edf899cb4bf44f4'
OUT = ROOT / 'figures'

MM = 1 / 25.4
TEXT, AXIS, GRID = '#0A2D50', '#5A6469', '#CDD7DC'
COLOURS = {'baseline': '#0A2D50', 'generic': '#00B9E1', 'original': '#FF5F05', 'human': '#5A6469'}
NAMES = {'baseline': 'Direct judgment', 'generic': 'Generic appraisal',
         'original': 'Moral-cognitive appraisal', 'human': 'Humans'}
VERDICTS = {'AUTHOR': 'Author at fault', 'OTHER': 'Other party at fault',
            'EVERYBODY': 'Everybody', 'NOBODY': 'Nobody'}
TICK_PT, LABEL_PT, INPLOT_PT = 20, 20, 22

# fig1 draws its example only from items with enough votes for the human
# distribution to be more than a handful of individual opinions.
FIG1_MIN_VOTES = 20

# Left condition, right condition, group label, whether greyed as descriptive.
GROUPS = (('original', 'generic', 'Moral-cognitive vs generic (P1)', False),
          ('generic', 'baseline', 'Generic appraisal vs direct (P2)', False),
          ('original', 'baseline', 'Moral-cognitive vs direct (descriptive)', True))

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans', 'sans-serif'],
    'font.size': TICK_PT,
    'text.color': TEXT, 'axes.labelcolor': TEXT,
    'axes.edgecolor': AXIS, 'xtick.color': AXIS, 'ytick.color': AXIS,
    'xtick.labelcolor': TEXT, 'ytick.labelcolor': TEXT,
    'xtick.labelsize': TICK_PT, 'ytick.labelsize': TICK_PT, 'axes.labelsize': LABEL_PT,
    'axes.spines.top': False, 'axes.spines.right': False,
    'axes.linewidth': 1.2, 'xtick.major.width': 1.2, 'ytick.major.width': 1.2,
    'grid.color': GRID, 'grid.linewidth': 1.0,
    # Embed TrueType rather than Type 3 so the PDF text stays editable for layout.
    'pdf.fonttype': 42, 'ps.fonttype': 42,
})


def load(path):
    return json.loads(Path(path).read_text())


def save(fig, name):
    for ext in ('pdf', 'png'):
        fig.savefig(OUT / f'{name}.{ext}', dpi=300)
    plt.close(fig)


def header(name, size):
    print('\n' + '=' * 78)
    print(f'{name}  ({size[0]} x {size[1]} mm)  -> figures/{name}.pdf, figures/{name}.png')
    print('=' * 78)


def signed(x, digits=3):
    return f'{x:+.{digits}f}'.replace('-', '−')


def fig1_example(heldout, dispersion, manifest):
    size = (280, 140)
    labels = manifest['labels']
    votes = {i: sum(s.get(k, 0) for k in labels) for i, s in manifest['human_scores'].items()}
    pool = [r for r in heldout['items'] if r['js']['baseline'] is not None and votes[r['id']] >= FIG1_MIN_VOTES]
    median = statistics.median(r['js']['baseline'] for r in pool)
    # Ties on distance go to the first item in manifest order, which is the order
    # analysis.json lists them in.
    chosen = min(pool, key=lambda r: abs(r['js']['baseline'] - median))
    item = next(r for r in dispersion['items'] if r['id'] == chosen['id'])
    h, q = item['distribution']['human'], item['distribution']['baseline']
    value = chosen['js']['baseline']
    if abs(js(h, q) - value) > 1e-12:
        raise ValueError('Plotted distributions do not reproduce the analysis.json JSD')

    fig, ax = plt.subplots(figsize=(size[0] * MM, size[1] * MM), layout='constrained')
    x = range(len(labels))
    w = 0.38
    ax.bar([i - w / 2 for i in x], h, w, facecolor='white', edgecolor=COLOURS['human'], linewidth=2.5)
    ax.bar([i + w / 2 for i in x], q, w, color=COLOURS['baseline'])
    ax.set_xticks(list(x), [VERDICTS[k] for k in labels])
    ax.set_ylabel('Share of judgments')
    # Headroom above 1 so a label over a near-unanimous bar stays inside the axes.
    ax.set_ylim(0, 1.1)
    ax.set_yticks([0, .25, .5, .75, 1])
    ax.spines['left'].set_bounds(0, 1)
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    ax.tick_params(axis='x', length=0)
    # Direct labels over the tallest group. Each is anchored at the outer edge of its
    # own bar and runs away from the pair, so the two labels cannot overlap.
    top = max(x, key=lambda i: max(h[i], q[i]))
    ax.annotate(NAMES['human'], (top, h[top]), xytext=(-4, 8), textcoords='offset points',
                ha='right', va='bottom', fontsize=INPLOT_PT, color=TEXT)
    ax.annotate(NAMES['baseline'], (top, q[top]), xytext=(4, 8), textcoords='offset points',
                ha='left', va='bottom', fontsize=INPLOT_PT, color=TEXT)
    ax.text(0.98, 0.92, f'JSD = {value:.2f}', transform=ax.transAxes, ha='right', va='top',
            fontsize=INPLOT_PT, color=TEXT)
    save(fig, 'fig1_example')

    header('fig1_example', size)
    print(f'Item selection rule: among held-out items with a baseline JSD and at least {FIG1_MIN_VOTES} '
          f'non-INFO human votes, the item whose baseline JSD is closest to the median baseline JSD of '
          f'that subset (ties: first in manifest order).')
    print(f'  qualifying items = {len(pool)}; median baseline JSD over them = {median:.4f}')
    print(f'  chosen item id = {chosen["id"]}  baseline JSD = {value:.4f}')
    print(f'  human non-INFO votes = {votes[chosen["id"]]}, direct-judgment valid responses = '
          f'{item["valid_n"]["baseline"]} of {manifest["samples"]}')
    print(f'  {"verdict":<22}{"humans":>8}{"direct":>8}')
    for k, a, b in zip(labels, h, q):
        print(f'  {VERDICTS[k]:<22}{a:>8.3f}{b:>8.3f}')
    print(f'\nCaption: How the measure works, on one held-out item chosen by rule: among the {len(pool)} '
          f'items with at least {FIG1_MIN_VOTES} human votes, the one whose divergence is closest to their '
          f'median. Hollow bars: the share of {votes[chosen["id"]]} human annotators giving each verdict '
          f'(INFO excluded). Filled bars: the model\'s verdicts over {item["valid_n"]["baseline"]} '
          f'sampled responses with direct judgment. Jensen-Shannon divergence (base 2, 0 = identical, '
          f'1 = disjoint) between the two is {value:.2f}.')


def comparison(analysis, left, right):
    s = analysis['comparisons'][f'{left}_minus_{right}_available_pairs']
    lo, hi = s['exploratory_paired_item_bootstrap_95_percent']
    return {'mean': s['difference'], 'lo': lo, 'hi': hi, 'n': s['n'],
            'closer': s['closer'], 'farther': s['farther'], 'tied': s['tied']}


def conclusion(c):
    """The pre-registered inference rule: a direction only if the interval excludes zero."""
    return 'closer' if c['hi'] < 0 else 'farther' if c['lo'] > 0 else 'not distinguished'


def check_s2(heldout, reparsed):
    """Whether the strict-parser reanalysis reaches the same P1 and P2 conclusions."""
    out = []
    for left, right, label, grey in GROUPS:
        if grey:
            continue
        a, b = comparison(heldout, left, right), comparison(reparsed, left, right)
        out.append((label, a, b, conclusion(a) == conclusion(b) and (a['mean'] > 0) == (b['mean'] > 0)))
    return out


def fig2_results(dev, heldout, d_manifest, h_manifest):
    size = (270, 170)
    d_items, h_items = len(d_manifest['human_scores']), len(h_manifest['human_scores'])
    rows = (('dev', dev, f'Development ({d_items} items)', True),
            ('heldout', heldout, f'Held-out, pre-registered ({h_items} items)', False))
    data = []
    for left, right, label, grey in GROUPS:
        colour = AXIS if grey else TEXT
        data.append((label, colour, [(name, tick, hollow, comparison(a, left, right))
                                     for name, a, tick, hollow in rows]))

    lo = min(c['lo'] for _, _, rs in data for *_, c in rs)
    hi = max(c['hi'] for _, _, rs in data for *_, c in rs)
    xlim = (round(min(lo, 0) - 0.03, 2), round(hi + 0.07, 2))
    step = 0.05
    xticks = [round(k * step, 2) for k in range(math.ceil(xlim[0] / step), math.floor(xlim[1] / step) + 1)]

    fig, ax = plt.subplots(figsize=(size[0] * MM, size[1] * MM), layout='constrained')
    # Group headers start at the figure's left edge, above the row labels, so they
    # are not crossed by the grid or the zero line; those are drawn per group,
    # spanning only that group's two rows.
    left_edge = blended_transform_factory(fig.transFigure, ax.transData)
    ticks, ticklabels = [], []
    y = 0
    for label, colour, rs in data:
        ax.text(0.004, y + 0.55, label, ha='left', va='bottom', fontsize=INPLOT_PT, color=TEXT,
                transform=left_edge)
        top, bottom = y + 0.45, y - len(rs) + 0.55
        for t in xticks:
            ax.plot([t, t], [bottom, top], color=AXIS if t == 0 else GRID,
                    linewidth=1.5 if t == 0 else 1.0, zorder=1.5 if t == 0 else 0.5)
        for name, tick, hollow, c in rs:
            ax.plot([c['lo'], c['hi']], [y, y], color=colour, linewidth=4, solid_capstyle='butt')
            ax.plot(c['mean'], y, 'o', markersize=14, color=colour, markeredgewidth=2.5,
                    markerfacecolor='white' if hollow else colour, zorder=3)
            ax.text(c['hi'], y, '  ' + signed(c['mean']), ha='left', va='center',
                    fontsize=INPLOT_PT, color=TEXT)
            ticks.append(y)
            ticklabels.append(tick)
            y -= 1
        y -= 1.1
    ax.set_yticks(ticks, ticklabels)
    ax.tick_params(axis='y', length=0)
    ax.spines['left'].set_visible(False)
    ax.set_xlim(*xlim)
    ax.set_xticks(xticks)
    ax.set_ylim(y + 1.6, 1.3)
    ax.set_xlabel('Δ JSD (negative = closer to humans)')
    save(fig, 'fig2_results')
    return size, data, xlim


def print_fig2(size, data, xlim, dev, heldout, d_manifest, h_manifest, reparsed):
    header('fig2_results', size)
    d_parser, h_parser = d_manifest['parser_version'], h_manifest['parser_version']
    print(f'Development: run {DEV.name}, protocol {d_manifest["protocol"]}, parser {d_parser} '
          f'({dev["parser_used"]}), keys *_available_pairs')
    print(f'Held-out:    run {HELDOUT.name}, protocol {h_manifest["protocol"]}, parser {h_parser} '
          f'({heldout["parser_used"]}), keys *_available_pairs')
    print(f'  x-axis limits: [{xlim[0]:.3f}, {xlim[1]:.3f}]')
    print(f'  {"group / row":<44}{"n":>4}{"mean":>9}{"95% CI":>20}  closer/farther/tied')
    for label, _, rs in data:
        print(f'  {label}')
        for name, tick, _, c in rs:
            print(f'    {tick:<42}{c["n"]:>4}{c["mean"]:>+9.4f}   [{c["lo"]:+.4f}, {c["hi"]:+.4f}]'
                  f'  {c["closer"]}/{c["farther"]}/{c["tied"]}')

    s2 = check_s2(heldout, reparsed)
    strict = reparsed['parser_used']
    print(f'\nS2 check, held-out under {strict} (analysis_reparsed.json):')
    for label, a, b, same in s2:
        print(f'  {label:<36} primary {a["mean"]:+.4f} [{a["lo"]:+.4f}, {a["hi"]:+.4f}] {conclusion(a)}'
              f' | strict {b["mean"]:+.4f} [{b["lo"]:+.4f}, {b["hi"]:+.4f}] {conclusion(b)}'
              f'  -> {"same" if same else "DISAGREES"}')
    if strict != d_parser:
        raise ValueError(f'analysis_reparsed.json used {strict}, not the development parser {d_parser}')
    s2_sentence = ('Reparsing the held-out responses with the strict parser leaves both pre-registered '
                   'conclusions unchanged (sensitivity analysis S2).' if all(x[3] for x in s2) else
                   'Reparsing the held-out responses with the strict parser changes at least one '
                   'pre-registered conclusion (sensitivity analysis S2); see the S2 check above.')
    d_items, h_items = len(d_manifest['human_scores']), len(h_manifest['human_scores'])
    print(f'\nCaption: Paired mean difference in Jensen-Shannon divergence from the human distribution, '
          f'with 95% paired-item bootstrap intervals (10,000 resamples). Negative values mean closer to '
          f'humans. Hollow markers: development run ({d_items} items), not pre-registered, parsed with '
          f'{d_parser}. Filled markers: held-out evaluation ({h_items} items), pre-registered, parsed with '
          f'the pre-registered {h_parser}. P1 and P2 are the pre-registered comparisons; moral-cognitive '
          f'vs direct is descriptive. {s2_sentence}')


def fig3_shift(dispersion):
    size = (270, 150)
    md = dispersion['verdict_shift']['mean_distribution']
    labels = list(VERDICTS)
    order = ('human', 'baseline', 'generic', 'original')
    # Tighter than the row pitch, so the gap between verdicts is wider than the
    # gap within one, and each group of four reads as a unit.
    offsets = dict(zip(order, (0.27, 0.09, -0.09, -0.27)))
    fig, ax = plt.subplots(figsize=(size[0] * MM, size[1] * MM), layout='constrained')
    ys = dict(zip(labels, range(len(labels))[::-1]))
    for k in labels[::2]:
        ax.axhspan(ys[k] - 0.5, ys[k] + 0.5, color=GRID, alpha=0.35, linewidth=0, zorder=0)
    for k in labels:
        y = ys[k]
        for s in order:
            if s == 'human':
                ax.plot(md[s][k], y + offsets[s], 'o', markersize=15, markerfacecolor='white',
                        markeredgecolor=COLOURS[s], markeredgewidth=2.5, zorder=3)
            else:
                ax.plot(md[s][k], y + offsets[s], 'o', markersize=14, color=COLOURS[s], zorder=3)
    # The legend sits in the lower right, which the two rare verdicts leave empty.
    # Markers keep their condition colours; the text stays dark for contrast.
    handles = [Line2D([], [], linestyle='none', marker='o', markersize=15, markerfacecolor='white',
                      markeredgecolor=COLOURS['human'], markeredgewidth=2.5)]
    handles += [Line2D([], [], linestyle='none', marker='o', markersize=14, color=COLOURS[s])
                for s in order[1:]]
    ax.legend(handles, [NAMES[s] for s in order], loc='lower right', bbox_to_anchor=(1, 0.03),
              frameon=False, fontsize=INPLOT_PT, labelcolor=TEXT, handletextpad=0.4, borderaxespad=0)
    ax.set_yticks([ys[k] for k in labels], [VERDICTS[k] for k in labels])
    ax.tick_params(axis='y', length=0)
    ax.set_xlim(0, 0.7)
    ax.set_ylim(-0.5, len(labels) - 0.5)
    ax.xaxis.grid(True)
    ax.set_axisbelow(True)
    ax.set_xlabel('Mean share of judgments')
    save(fig, 'fig3_shift')

    header('fig3_shift', size)
    print(f'Source: {HELDOUT.relative_to(ROOT)}/exploratory/dispersion.json, verdict_shift.mean_distribution '
          f'(status: {dispersion["verdict_shift"]["status"]})')
    print(f'  {"verdict":<22}' + ''.join(f'{NAMES[s]:>27}' for s in order))
    for k in labels:
        print(f'  {VERDICTS[k]:<22}' + ''.join(f'{md[s][k]:>27.3f}' for s in order))
    print('  n items: ' + ', '.join(f'{NAMES[s]} {md[s]["n"]}' for s in order))
    print('\nCaption: Exploratory, defined after the pre-registered results were seen. Mean share of '
          'each verdict across the 60 held-out items: each item\'s distribution is averaged with equal '
          'weight per item. Hollow grey: human annotators (INFO excluded). Filled: the model under each '
          'prompt. Relative to direct judgment, the generic appraisal shifts judgments from "other party '
          'at fault" towards "nobody", and the moral-cognitive appraisal shifts them towards "author at '
          'fault".')


def main():
    OUT.mkdir(exist_ok=True)
    heldout, dev = load(HELDOUT / 'analysis.json'), load(DEV / 'analysis.json')
    reparsed = load(HELDOUT / 'analysis_reparsed.json')
    h_manifest, d_manifest = load(HELDOUT / 'manifest.json'), load(DEV / 'manifest.json')
    dispersion = load(HELDOUT / 'exploratory' / 'dispersion.json')
    assert tuple(h_manifest['labels']) == LABELS

    fig1_example(heldout, dispersion, h_manifest)
    size, data, xlim = fig2_results(dev, heldout, d_manifest, h_manifest)
    print_fig2(size, data, xlim, dev, heldout, d_manifest, h_manifest, reparsed)
    fig3_shift(dispersion)
    print(f'\nWrote 6 files to {OUT}')


if __name__ == '__main__':
    main()
