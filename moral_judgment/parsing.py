"""Strict reading of a verdict out of a model response.

The parser is deliberately unwilling to guess. It accepts a judgment only where
the model committed to one through the requested output interface, and otherwise
records why the response could not be read. Recovering a label from surrounding
prose would let the analysis credit the model with a verdict it never actually
stated, which is the failure mode the legacy parser in `legacy.py` exhibits and
the reason the two are kept apart.
"""
import re

# Written into every manifest and diagnostics report, so a saved run can be tied
# to the exact parser that produced its labels. Change the string whenever the
# accepted forms change, and never reinterpret an old run under a new version
# without saying so.
PARSER_VERSION = 'exact_label_or_final_marker_v3'


def unwrap(text):
    """Strip paired Markdown or backtick wrappers, leaving the inner text intact.

    Only symmetric pairs are removed, and never enough to reach inside a word, so
    a label is judged on its spelling rather than on how the provider chose to
    decorate it. Three passes cover nesting such as bold inside a code span.
    """
    text = text.strip()
    for _ in range(3):
        for token in ('**', '__', '`'):
            if text.startswith(token) and text.endswith(token) and len(text) > 2 * len(token):
                text = text[len(token):-len(token)].strip()
                break
        else:
            break
    return text


def parse_label(text, labels):
    """Return the committed label, or None if the response does not state one.

    Two forms are accepted. A response consisting of nothing but an allowed label
    is taken at face value, which is what the direct condition tends to produce.
    Otherwise the label must arrive through a single FINAL_LABEL marker on the
    closing line. The marker is required to be unique because a response that
    emits it twice has not committed to one verdict, and reading only the final
    line stops a label quoted mid-rationale from being mistaken for the verdict.
    """
    if not isinstance(text, str) or not text.strip():
        return None
    if text.strip() in labels:
        return text.strip()
    if len(re.findall(r'\bFINAL_LABEL\s*:', text)) != 1:
        return None
    line = unwrap(text.strip().splitlines()[-1])
    # Handles the common variant where the provider bolds the marker but not the
    # label that follows it, which unwrap cannot reach because the pair is closed
    # before the value begins.
    for token in ('**', '__', '`'):
        prefix = token + 'FINAL_LABEL:' + token
        if line.startswith(prefix):
            line = 'FINAL_LABEL:' + line[len(prefix):]
            break
    if not line.startswith('FINAL_LABEL:'):
        return None
    value = unwrap(line[len('FINAL_LABEL:'):])
    return value if value in labels else None


# The declared parser for the held-out run. It differs from `parse_label` only in
# where the marker may sit and how it is punctuated, never in what counts as a
# label, and it is kept as a separate function so that runs recorded under v3 keep
# meaning exactly what they meant.
TOLERANT_PARSER_VERSION = 'final_marker_tolerant_v1'

_MARKER = re.compile(r'\bFINAL_LABEL\b')


def parse_label_tolerant(text, labels):
    """Like `parse_label`, but tolerant of the marker's position and punctuation.

    The 28 format failures in the 20-item development run were all one of three
    shapes: the marker run on at the end of a prose line instead of starting its
    own, the colon omitted, or the colon placed outside a bolded marker. Each one
    states its verdict unambiguously, so all three are accepted here. What is
    still required is a single marker in the whole response and, after it,
    nothing but one exactly spelled label, optionally wrapped. A label therefore
    still cannot be lifted out of the rationale, and a response that names two
    verdicts after the marker, or that writes the marker twice, is still refused.
    """
    if not isinstance(text, str) or not text.strip():
        return None
    if text.strip() in labels:
        return text.strip()
    found = _MARKER.findall(text)
    if len(found) != 1:
        return None
    rest = text[_MARKER.search(text).end():]
    # Wrapper characters and the optional colon between marker and label, then
    # any closing wrapper after the label. The label itself is not touched.
    value = rest.lstrip(' \t\r\n*_`:').rstrip(' \t\r\n*_`')
    return value if value in labels else None


def classify_response(response, labels, parse=parse_label):
    """Map a raw API response to (label, status), with status naming any failure.

    The completion is inspected before its text is. A response cut off at the
    token cap is rejected even when a well-formed label happens to sit in what
    survived, since the label the model was still writing cannot be known. The
    distinct status strings exist so that coverage reporting can separate a
    refusal or a transport failure from a genuine formatting violation, which
    bear on the results in quite different ways. `parse` selects the text
    parser; every completion check above applies whichever one is used.
    """
    choices = response.get('choices') or []
    if len(choices) != 1:
        return None, 'missing_or_multiple_choices'
    c = choices[0]
    finish = c.get('finish_reason')
    if finish == 'length':
        return None, 'truncated'
    if finish != 'stop':
        return None, 'unexpected_finish_reason'
    message = c.get('message') or {}
    if message.get('refusal'):
        return None, 'refusal'
    text = message.get('content')
    if not isinstance(text, str) or not text.strip():
        return None, 'missing_content'
    label = parse(text, labels)
    return (label, 'valid') if label else (None, 'invalid_label_format')

