"""Study 2 runner: trait-varied vs irrelevant-varied persona mixtures.

Dry run by default; --execute makes paid calls. The design is fixed by
docs/preregistration_study2.md, so nothing about it is a command-line option: the
only inputs are the corpus, which is read to confirm the items, and whether to
execute.

The items are not drawn again. They are the 60 items of the held-out run
7edf899cb4bf44f4, taken from its manifest in its order with its human scores, and
checked against the corpus byte for byte. Everything else about request handling,
logging, resumption and stopping is `run_control_pilot.execute`, unchanged.
"""
import argparse
import hashlib
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from moral_judgment.prompts import PERSONA_PROFILES, STUDY2_ARMS, personas, persona_prompt, prompt
from moral_judgment.parsing import TOLERANT_PARSER_VERSION
from run_control_pilot import RESULTS_ROOT, execute, load_items

PROTOCOL = 'study2_persona_mixture_v1'

STUDY1_HASH = '7edf899cb4bf44f43bfadcdacbe1ebcd387dd72ddeec2e0cbb998d65674c7bbd'
STUDY1_DIR = RESULTS_ROOT / 'heldout' / STUDY1_HASH[:16]

ORDER_SEED = 20261012
SAMPLES = len(PERSONA_PROFILES)

# Identical to the held-out run, which is what lets the two studies share a
# baseline descriptively. Any change here changes the hash.
SETTINGS = {'parser_version': TOLERANT_PARSER_VERSION,
            'extra_body': {'provider': {'only': ['parasail'], 'allow_fallbacks': False,
                                        'require_parameters': True}},
            'model': 'openai/gpt-oss-20b',
            'temperature': 0.8,
            'top_p': 1,
            'max_tokens': 16384,
            'request_timeout_seconds': 600.0}


def sha256(text):
    return hashlib.sha256(text.encode()).hexdigest()


def study1_items(data):
    """The held-out items, in Study 1's order, verified against the corpus.

    Study 1's manifest is rehashed first, so an edited manifest cannot supply the
    items. Each item's human scores must equal the corpus row's, and its anecdote
    must be exactly the text Study 1 placed between the delimiters.
    """
    cfg = json.loads((STUDY1_DIR / 'manifest.json').read_text())
    if sha256(json.dumps(cfg, sort_keys=True)) != STUDY1_HASH:
        raise SystemExit('Study 1 manifest does not reproduce its hash')
    rows, split_sha256 = load_items(data, 'test')
    if split_sha256 != cfg['split_sha256']:
        raise SystemExit('Corpus test split differs from the one Study 1 recorded')
    by_id = {x['id']: x for x in rows}
    items = []
    for ident, scores in cfg['human_scores'].items():
        x = by_id[ident]
        shown = cfg['prompts'][ident]['baseline'].split('<SITUATION>\n', 1)[1].rsplit('\n</SITUATION>', 1)[0]
        if x['label_scores'] != scores or x['text'] != shown:
            raise SystemExit(f'Item {ident} does not match Study 1')
        items.append(x)
    return items, cfg


def build_config(items, study1_cfg):
    labels = study1_cfg['labels']
    persona_table = {arm: [{'sample': i, 'profile': code, 'person': p}
                           for i, (code, p) in enumerate(zip(PERSONA_PROFILES, personas(arm)))]
                     for arm in STUDY2_ARMS}
    templates = {arm: [sha256(persona_prompt('{TEXT}', p['person'], labels)) for p in persona_table[arm]]
                 for arm in STUDY2_ARMS}
    return {'protocol': PROTOCOL,
            **SETTINGS,
            'seed_for_order_only': ORDER_SEED,
            'samples': SAMPLES,
            'labels': list(labels),
            'conditions': list(STUDY2_ARMS),
            'persona_assignment': 'sample i is judged by persona i of its arm',
            'personas': persona_table,
            'template_sha256': templates,
            'baseline_template_sha256_study1': sha256(prompt('{TEXT}', 'baseline', labels)),
            'prompts': {x['id']: {arm: [persona_prompt(x['text'], p['person'], labels)
                                        for p in persona_table[arm]] for arm in STUDY2_ARMS}
                        for x in items},
            'human_scores': {x['id']: x['label_scores'] for x in items},
            'items_source': {'study1_config_hash': STUDY1_HASH, 'study1_run': 'results/heldout/' + STUDY1_HASH[:16],
                             'split': 'test', 'split_sha256': study1_cfg['split_sha256']},
            'provider_policy': study1_cfg['provider_policy'],
            'retry_policy': study1_cfg['retry_policy']}


def ids_seen_elsewhere(ids, dest):
    """Item ids found under results/ anywhere except Study 1's run and this one.

    The same crude 32-character scan as the held-out runner. These items are meant
    to appear in Study 1; appearing anywhere else (a pilot, a report) would mean
    they were used in development.
    """
    found = set()
    for f in RESULTS_ROOT.rglob('*'):
        if f.is_file() and STUDY1_DIR not in f.parents and dest not in f.parents:
            found |= set(re.findall(r'[A-Za-z0-9]{32}', f.read_text(errors='ignore')))
    return ids & found


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', required=True, help='anecdotes.tar')
    p.add_argument('--show-prompts', action='store_true',
                   help='Print the rendered prompt for every arm and persona on the first item')
    p.add_argument('--execute', action='store_true')
    args = p.parse_args()

    items, study1_cfg = study1_items(args.data)
    config = build_config(items, study1_cfg)
    config_hash = sha256(json.dumps(config, sort_keys=True))
    dest = (RESULTS_ROOT / 'study2' / config_hash[:16]).resolve()

    if not (dest / 'responses.jsonl').exists():
        ids = {x['id'] for x in items}
        elsewhere = ids_seen_elsewhere(ids, dest)
        if elsewhere:
            raise SystemExit(f'{len(elsewhere)} items appear under results/ outside Study 1: {sorted(elsewhere)}')
        print(f'Overlap check: all {len(ids)} items are Study 1\'s ({STUDY1_HASH[:16]}), verified against the '
              f'corpus; none appears anywhere else under {RESULTS_ROOT}')
    dest.mkdir(parents=True, exist_ok=True)
    manifest = dest / 'manifest.json'
    if manifest.exists() and json.loads(manifest.read_text()) != config:
        raise ValueError('Manifest conflict')
    manifest.write_text(json.dumps(config, indent=2) + '\n')

    # Interleaved and shuffled across arms, as in Study 1, so drift during the run
    # cannot fall on one arm.
    jobs = [(x['id'], arm, k) for x in items for k in range(SAMPLES) for arm in STUDY2_ARMS]
    random.Random(ORDER_SEED).shuffle(jobs)
    print('Protocol:', config_hash, '\nScheduled calls:', len(jobs), '\nOutput:', dest)
    print('Template SHA-256 (first 16), by sample:')
    for arm in STUDY2_ARMS:
        print(f'  {arm}:', ' '.join(h[:16] for h in config['template_sha256'][arm]))
    print('  Study 1 baseline:', config['baseline_template_sha256_study1'][:16])

    if args.show_prompts:
        first = items[0]['id']
        for arm in STUDY2_ARMS:
            for k, code in enumerate(PERSONA_PROFILES):
                print(f'\n===== {arm} | sample/persona {k} | {code} | item {first} =====')
                print(config['prompts'][first][arm][k])

    if not args.execute:
        print('\nDRY RUN: no API calls. Review manifest and cost before adding --execute.')
        return
    run_args = argparse.Namespace(model=config['model'], temperature=config['temperature'],
                                  max_tokens=config['max_tokens'], timeout=config['request_timeout_seconds'])
    execute(run_args, config, config_hash, dest, jobs,
            prompt_of=lambda ident, arm, k: config['prompts'][ident][arm][k])


if __name__ == '__main__':
    main()
