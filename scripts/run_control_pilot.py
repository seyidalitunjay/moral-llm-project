"""Three-arm runner for the development pilots and the held-out evaluation.

Dry run by default; --execute makes paid calls.

Every scheduled call is recorded, including the ones that fail. A run is addressed
by the SHA-256 of its own configuration, so a changed model, prompt, sample count
or label set lands in a new directory instead of quietly joining an existing one,
and two incompatible sets of responses can never be pooled by accident.

By default the runner draws only from the first 60 dev items, the pool already
inspected during development. `--split test` draws instead from the whole test
split for the frozen held-out evaluation, and refuses to start if any drawn item
already appears anywhere under results/.
"""
import argparse
import hashlib
import json
import os
import random
import re
import sys
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path

# Lets the script run straight from a clone, with or without an editable install.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from moral_judgment.io import read_jsonl
from moral_judgment.metrics import LABELS
from moral_judgment.parsing import (PARSER_VERSION, TOLERANT_PARSER_VERSION, classify_response,
                                    parse_label, parse_label_tolerant)
from moral_judgment.prompts import CONDITIONS, prompt

PROTOCOL = 'development_control_v4'
HELDOUT_PROTOCOL = 'heldout_frozen_v1'

PARSERS = {PARSER_VERSION: parse_label, TOLERANT_PARSER_VERSION: parse_label_tolerant}

# Where every earlier run and report lives. A held-out item found anywhere in here
# has been seen before and is not held out.
RESULTS_ROOT = Path(__file__).resolve().parent.parent / 'results'

# The development pool. Held at 60 so the selection stays inside the items already
# looked at by hand, which is what keeps the remainder of the split naive.
POOL_SIZE = 60

# Three consecutive failures, or any of these HTTP statuses, ends the run. The
# status codes signal a bad key, an exhausted balance or a refused request, none of
# which a retry can fix, and continuing would burn the schedule on certain errors.
FATAL_HTTP_STATUS = (401, 402, 403)
MAX_CONSECUTIVE_FAILURES = 3


def load_items(path, split='dev'):
    """Read one split from the distributed tar, or a plain dev JSONL file.

    Also returns the SHA-256 of the split's raw bytes, which the held-out
    configuration records so that a reordered or re-versioned corpus cannot
    silently select different anecdotes under the same seed.
    """
    if tarfile.is_tarfile(path):
        with tarfile.open(path) as t:
            raw = t.extractfile(f'anecdotes/{split}.scruples-anecdotes.jsonl').read()
    elif split == 'dev':
        raw = Path(path).read_bytes()
    else:
        raise SystemExit('The test split is read from anecdotes.tar only.')
    return [json.loads(l) for l in raw.splitlines() if l.strip()], hashlib.sha256(raw).hexdigest()


def ids_already_used(exclude):
    """Every 32-character token in any file under results/, outside `exclude`.

    Deliberately crude: it does not parse any schema, so an item recorded under
    any past format, report or manifest is caught. Scruples ids are 32
    alphanumeric characters, and false positives can only exclude, never admit.
    """
    used = set()
    for f in RESULTS_ROOT.rglob('*'):
        if f.is_file() and exclude not in f.parents:
            used |= set(re.findall(r'[A-Za-z0-9]{32}', f.read_text(errors='ignore')))
    return used


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', required=True, help='anecdotes.tar or dev JSONL')
    p.add_argument('--split', choices=['dev', 'test'], default='dev',
                   help='dev: first 60 development rows. test: the whole held-out test split')
    p.add_argument('--parser', choices=sorted(PARSERS), default=PARSER_VERSION)
    p.add_argument('--timeout', type=float, default=120.0, help='Per-request client timeout, seconds')
    p.add_argument('--items', type=int, default=20)
    p.add_argument('--samples', type=int, default=10)
    p.add_argument('--seed', type=int, default=20260913)
    p.add_argument('--model', default='openai/gpt-oss-20b')
    p.add_argument('--temperature', type=float, default=.8)
    p.add_argument('--max-tokens', type=int, default=2048)
    p.add_argument('--provider', help='OpenRouter provider slug; restricts routing to it, with fallback disabled')
    p.add_argument('--reasoning-effort', choices=['low', 'medium', 'high'], help='Optional; requires provider support')
    p.add_argument('--include-info', action='store_true')
    p.add_argument('--out')
    p.add_argument('--execute', action='store_true')
    args = p.parse_args()
    if args.out is None:
        args.out = 'pilot_v4' if args.split == 'dev' else str(RESULTS_ROOT / 'heldout')
    if args.split == 'dev' and not args.items <= POOL_SIZE:
        p.error('Require at most 60 development items')
    if args.items < 1 or args.samples < 1 or args.max_tokens < 1 or args.timeout <= 0 or not 0 <= args.temperature <= 2:
        p.error('Require positive items/samples/token cap/timeout, temperature 0-2')
    return args


def build_config(args, chosen, labels, split_sha256=None, pool=()):
    """Assemble the configuration that both defines the run and identifies it.

    The rendered prompts and the human scores are part of the configuration, not
    merely logged alongside it, so the hash changes if either the wording or the
    selected items change. `labels` and `conditions` are stored as lists because
    the manifest-conflict check compares this object against the parsed manifest,
    where a tuple would not compare equal to the array it was written as.

    The held-out fields are added only for a test-split run, and the timeout only
    when it departs from the old fixed value, so a development configuration
    still hashes exactly as it did before they existed.
    """
    extra = {}
    if args.provider:
        extra['provider'] = {'only': [args.provider], 'allow_fallbacks': False, 'require_parameters': True}
    if args.reasoning_effort:
        extra['reasoning'] = {'effort': args.reasoning_effort}
    config = {'protocol': PROTOCOL if args.split == 'dev' else HELDOUT_PROTOCOL,
            'parser_version': args.parser,
            'extra_body': extra,
            'model': args.model,
            'temperature': args.temperature,
            'top_p': 1,
            'max_tokens': args.max_tokens,
            # The seed fixes which items are drawn and the order calls are issued.
            # It does not make the model's own sampling reproducible.
            'seed_for_selection_and_order_only': args.seed,
            'samples': args.samples,
            'labels': list(labels),
            'conditions': list(CONDITIONS),
            'prompts': {x['id']: {c: prompt(x['text'], c, labels) for c in CONDITIONS} for x in chosen},
            'human_scores': {x['id']: x['label_scores'] for x in chosen},
            'provider_policy': ('Restricted to requested provider slug; no fallback; verify returned provider.'
                                if args.provider else
                                'Automatic routing; provider recorded when returned.'),
            'retry_policy': ('SDK retries disabled; one attempted request per scheduled sample; '
                             'failed slots retained')}
    if args.split == 'test':
        config['split'] = 'test'
        config['split_sha256'] = split_sha256
        config['selection'] = (f'random.Random(seed).sample over the {len(pool)} test-split rows with '
                               f'non-empty text, in file order, k={args.items}; no stratification')
    if args.timeout != 120.0:
        config['request_timeout_seconds'] = args.timeout
    return config


def completed_samples(records_path, config_hash):
    """Identify already-attempted slots so a resumed run does not repeat them.

    Any record written under a different configuration hash, or any repeated slot,
    aborts rather than being tolerated: both mean the directory holds responses
    that cannot be treated as one run.
    """
    done = set()
    if not records_path.exists():
        return done
    for r in read_jsonl(records_path):
        if r['config_hash'] != config_hash:
            raise ValueError('Config mismatch')
        identity = (r['id'], r['condition'], r['sample'])
        if identity in done:
            raise ValueError('Duplicate sample identity')
        done.add(identity)
    return done


def request_one(client, args, prompt_text, extra):
    return client.chat.completions.create(model=args.model,
                                          messages=[{'role': 'user', 'content': prompt_text}],
                                          temperature=args.temperature,
                                          top_p=1,
                                          max_tokens=args.max_tokens,
                                          extra_body=extra)


def execute(args, config, config_hash, dest, jobs):
    key = os.environ.get('OPENROUTER_API_KEY')
    if not key:
        raise SystemExit('Set OPENROUTER_API_KEY locally; do not paste it into chat.')
    from openai import OpenAI
    # Retries are disabled at the SDK level so that one scheduled sample means one
    # attempted request. A silent retry would make the recorded failure rate, and
    # therefore the coverage figures, understate what the provider actually did.
    client = OpenAI(base_url='https://openrouter.ai/api/v1', api_key=key, max_retries=0, timeout=args.timeout)
    parse = PARSERS[config['parser_version']]

    prompts = config['prompts']
    extra = config['extra_body']
    import fcntl  # POSIX advisory lock; covers the macOS and Linux targets.
    with (dest / 'run.lock').open('w') as lock:
        # Non-blocking, so a second runner aimed at this directory fails at once
        # rather than interleaving writes into the same response log.
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        records = dest / 'responses.jsonl'
        done = completed_samples(records, config_hash)
        failures = 0
        with records.open('a') as f:
            for ident, c, k in jobs:
                if (ident, c, k) in done:
                    continue
                r = {'config_hash': config_hash, 'id': ident, 'condition': c, 'sample': k,
                     'timestamp': datetime.now(timezone.utc).isoformat(), 'label': None}
                try:
                    response = request_one(client, args, prompts[ident][c], extra)
                    # The whole response is kept, not just the parsed label, so the
                    # parser can be revised later and rerun over the same records.
                    r['response'] = response.model_dump(mode='json')
                    r['label'], r['status'] = classify_response(r['response'], config['labels'], parse)
                    r['parser_version'] = config['parser_version']
                    failures = 0
                except Exception as e:
                    r['status'] = 'request_error'
                    r['error_type'] = type(e).__name__
                    r['http_status'] = getattr(e, 'status_code', None)
                    failures += 1
                # Flushed and fsynced per record, so an interrupted run leaves a
                # complete log of everything already paid for.
                f.write(json.dumps(r) + '\n')
                f.flush()
                os.fsync(f.fileno())
                print(ident, c, k, r['status'])
                if failures >= MAX_CONSECUTIVE_FAILURES or r.get('http_status') in FATAL_HTTP_STATUS:
                    raise SystemExit('Stopped after request errors. Failed attempts remain recorded; '
                                     'resuming skips them.')
                time.sleep(1)
    print('Scheduled attempts completed. Analyze coverage before interpreting distributions.')


def main():
    args = parse_args()
    pool, split_sha256 = load_items(args.data, args.split)
    if args.split == 'dev':
        pool = pool[:POOL_SIZE]
    else:
        # A row with an empty body gives the model an empty situation while its
        # annotators saw the title, so it would not measure the same judgment.
        # Filtered before the draw, on the text alone, never on any label.
        pool = [x for x in pool if x['text'].strip()]
    chosen = random.Random(args.seed).sample(pool, args.items)
    # INFO makes a five-label configuration whose scores are not comparable with
    # four-label results, which is why it changes the hash and the directory.
    labels = list(LABELS) + (['INFO'] if args.include_info else [])

    config = build_config(args, chosen, labels, split_sha256, pool)
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    dest = Path(args.out) / config_hash[:16]
    if args.split == 'test' and not (dest / 'responses.jsonl').exists():
        seen = {x['id'] for x in chosen} & ids_already_used(dest.resolve())
        if seen:
            raise SystemExit(f'{len(seen)} drawn items already appear under results/: {sorted(seen)}')
        print('Overlap check: none of the', len(chosen), 'drawn items appears under', RESULTS_ROOT)
    dest.mkdir(parents=True, exist_ok=True)
    manifest = dest / 'manifest.json'
    if manifest.exists() and json.loads(manifest.read_text()) != config:
        raise ValueError('Manifest conflict')
    manifest.write_text(json.dumps(config, indent=2) + '\n')

    # Conditions are interleaved and shuffled rather than run arm by arm, so that
    # provider-side drift over the run cannot land disproportionately on one arm.
    jobs = [(x['id'], c, k) for x in chosen for k in range(args.samples) for c in CONDITIONS]
    random.Random(args.seed).shuffle(jobs)
    print('Protocol:', config_hash, '\nScheduled calls:', len(jobs), '\nOutput:', dest)
    if not args.execute:
        print('DRY RUN: no API calls. Review manifest and cost before adding --execute.')
        return
    execute(args, config, config_hash, dest, jobs)


if __name__ == '__main__':
    main()
