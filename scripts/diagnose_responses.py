"""Response-level parser audit. Reads saved records only; makes no API calls.

Its purpose is to separate two things a coverage count conflates: responses that
carried no usable judgment, and responses that carried one the parser of the day
could not read. The report states both the status recorded during the run and the
status the current parser derives, so a revision's effect is visible response by
response rather than only in the totals.

Nothing here rewrites a record, and no label is ever inferred from a rationale or
from the human scores.
"""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

# Lets the script run straight from a clone, with or without an editable install.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from moral_judgment.parsing import PARSER_VERSION, classify_response

DERIVATION_NOTE = ('Post-hoc format-only reinterpretation of final labels. Original records remain '
                   'unchanged. No labels inferred from rationales or human judgments.')


def diagnose(manifest, responses):
    m = json.loads(Path(manifest).read_text())
    # Hashed as bytes so the report pins the exact file that was read, letting a
    # reader confirm the diagnosis was run against the records they hold.
    raw = Path(responses).read_bytes()
    records = [json.loads(l) for l in raw.decode().splitlines() if l.strip()]
    cfg_hash = hashlib.sha256(json.dumps(m, sort_keys=True).encode()).hexdigest()

    seen = set()
    rows = []
    for r in records:
        key = (r['id'], r['condition'], r['sample'])
        if (key in seen or r['config_hash'] != cfg_hash or r['id'] not in m['human_scores']
                or r['condition'] not in m['conditions'] or not 0 <= r['sample'] < m['samples']):
            raise ValueError('Duplicate or mismatched response identity')
        seen.add(key)

        response = r.get('response', {})
        # An absent response body means the request itself failed, which is a
        # transport outcome rather than anything the parser could have read.
        label, status = classify_response(response, m['labels']) if response else (None, 'request_error')
        choices = response.get('choices') or []
        choice = choices[0] if choices else {}
        text = (choice.get('message') or {}).get('content') or ''
        rows.append({'id': r['id'], 'condition': r['condition'], 'sample': r['sample'],
                     'recorded_status': r['status'], 'recorded_label': r.get('label'),
                     'derived_status': status, 'derived_label': label,
                     'provider': response.get('provider'),
                     'finish_reason': choice.get('finish_reason'),
                     'completion_tokens': (response.get('usage') or {}).get('completion_tokens'),
                     # The closing line is what the parser actually inspects, so it
                     # is carried through for inspection of any rejected response.
                     'last_content_line': text.strip().splitlines()[-1] if text.strip() else ''})

    summary = {c: {'recorded': dict(Counter(x['recorded_status'] for x in rows if x['condition'] == c)),
                   'reparsed': dict(Counter(x['derived_status'] for x in rows if x['condition'] == c))}
               for c in m['conditions']}
    return {'config_hash': cfg_hash,
            'responses_sha256': hashlib.sha256(raw).hexdigest(),
            'parser_version': PARSER_VERSION,
            'note': DERIVATION_NOTE,
            'coverage': summary,
            # Providers are tracked because routing varied across the earlier runs,
            # and label-format compliance turned out to differ between providers.
            'providers': dict(Counter(x['provider'] for x in rows)),
            'recovered_format_only': sum(x['recorded_status'] != 'valid' and x['derived_status'] == 'valid'
                                         for x in rows),
            'total_valid': sum(x['derived_status'] == 'valid' for x in rows),
            'records': rows}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest')
    p.add_argument('responses')
    p.add_argument('--out', default='smoke_diagnostics.json')
    args = p.parse_args()
    if Path(args.out).resolve() in (Path(args.manifest).resolve(), Path(args.responses).resolve()):
        raise ValueError('Output cannot overwrite input')
    report = diagnose(args.manifest, args.responses)
    Path(args.out).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'records'}, indent=2))


if __name__ == '__main__':
    main()
