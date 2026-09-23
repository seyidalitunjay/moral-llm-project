"""Construction of judgment distributions and the divergence used to compare them.

A Scruples item carries a spread of annotator verdicts rather than a single gold
label, and sampling the model repeatedly yields a spread of its own. The unit of
comparison here is therefore a categorical distribution on each side, not a point
prediction, and the quantities below exist to put those two spreads on one
footing.
"""
import math
import random
import statistics

# INFO is left out of the support on purpose. An annotator choosing it is saying
# the account is too thin to rule on, which is a claim about the account rather
# than a verdict against either party, and the model is never offered the option
# in the four-label configuration. Normalising over these four alone keeps both
# sides defined on the same support; leaving INFO in would compare a five-outcome
# human distribution against a four-outcome model one.
LABELS = ('AUTHOR', 'OTHER', 'EVERYBODY', 'NOBODY')

# Fixed so that the interval reported for a given results file is reproducible
# across machines and reruns.
BOOTSTRAP_SEED = 20260913


def distribution(counts, labels=LABELS):
    """Normalise `counts` over `labels`, returning None when no mass is present.

    Mass on labels outside `labels` is discarded before the total is taken, so
    the result is conditional on the requested support. Returning None rather
    than a zero vector keeps an empty item distinguishable from a genuine one,
    which matters because callers are expected to report such items as missing
    instead of letting them enter a mean.
    """
    values = [counts.get(k, 0) for k in labels]
    if any(not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in values):
        raise ValueError('Invalid count')
    total = sum(values)
    return [v / total for v in values] if total else None


def js(p, q):
    """Base-2 Jensen-Shannon divergence between two distributions on one support.

    Divergence, not the square-root distance. What is reported is an amount of
    information, in bits, and taking base 2 over a shared support bounds it on
    [0, 1], so figures are directly comparable across conditions and items. The
    square root would buy the triangle inequality, which no step of this analysis
    uses. Plain KL is unusable here because either side can place zero mass on a
    label the other uses, which the mixture term removes.
    """
    m = [(a + b) / 2 for a, b in zip(p, q)]
    return (sum(a * math.log2(a / c) / 2 if a else 0 for a, c in zip(p, m))
            + sum(b * math.log2(b / c) / 2 if b else 0 for b, c in zip(q, m)))


def quantile(xs, p):
    """Linear-interpolated quantile, matching the usual percentile-bootstrap cut."""
    xs = sorted(xs)
    index = (len(xs) - 1) * p
    lo = math.floor(index)
    hi = math.ceil(index)
    return xs[lo] + (xs[hi] - xs[lo]) * (index - lo)


def summarize(rows, boot=10000):
    """Mean divergences plus a paired-item percentile bootstrap over `rows`.

    Resampling is over items, holding each item's paired baseline and
    intervention values together, because the two conditions see the same
    anecdote and their errors are not independent. The interval that results
    describes this convenience sample of anecdotes only: it carries no
    information about sampling error in the model's own generation or in the
    human annotations, and it is not a confirmatory test.

    The tie bands use 1e-12 rather than exact equality because the two
    divergences are separate floating-point reductions, so an item on which the
    conditions agreed can still differ in the last bits.
    """
    if not rows:
        return {'n': 0}
    diffs = [r['difference'] for r in rows]
    rng = random.Random(BOOTSTRAP_SEED)
    means = [statistics.mean(rng.choices(diffs, k=len(diffs))) for _ in range(boot)]
    return {'n': len(rows),
            'baseline_js': statistics.mean(r['baseline_js'] for r in rows),
            'intervention_js': statistics.mean(r['intervention_js'] for r in rows),
            'difference': statistics.mean(diffs),
            'closer': sum(d < -1e-12 for d in diffs),
            'farther': sum(d > 1e-12 for d in diffs),
            'tied': sum(abs(d) <= 1e-12 for d in diffs),
            'exploratory_paired_item_bootstrap_95_percent': [quantile(means, .025), quantile(means, .975)]}
