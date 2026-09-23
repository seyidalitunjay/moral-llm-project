"""Legacy two-condition batch runner, kept for provenance.

This is the script that produced `results/legacy/results_v2.jsonl`. It is not the
current experiment: it has no control arm, discards the raw response text, and
relies on the permissive label search in `moral_judgment.legacy`. Use
`run_control_pilot.py` for new measurements.

It is left runnable because the historical results are only interpretable against
the code that generated them, and it appends rather than overwrites, so an
interrupted batch resumes without re-paying for completed items.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from openai import OpenAI

# Lets the script run straight from a clone, with or without an editable install.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from moral_judgment.legacy import (N_SAMPLES, build_baseline_prompt,
                                   build_intervention_prompt, extract_label)

MODEL = 'openai/gpt-oss-20b'
TEMPERATURE = 0.8

# The batch was drawn from the head of the dev split rather than sampled, which is
# why the audit checks the results against the first 60 rows in order.
POOL_SIZE = 60

_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA = _ROOT / 'data' / 'dev.scruples-anecdotes.jsonl'
DEFAULT_OUT = _ROOT / 'results' / 'legacy' / 'results_v2.jsonl'


def sample_judgments(client, prompt, n=N_SAMPLES):
    """Draw `n` independent judgments for one prompt.

    Sampling is repeated rather than taken once because a single decode at
    temperature 0.8 is one draw from the model's distribution, not the
    distribution itself, and the quantity being compared against the spread of
    human annotators is that distribution. A failed call contributes None, so the
    slot stays in the record and the loss is visible downstream rather than
    shortening the sample silently.
    """
    labels_collected = []
    for i in range(n):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=TEMPERATURE
            )
            text = response.choices[0].message.content
            label = extract_label(text)
            labels_collected.append(label)
        except Exception as e:
            print(f"  Error on sample {i}: {e}")
            labels_collected.append(None)
        time.sleep(1)
    return labels_collected


def completed_ids(path):
    """Ids already written, so a resumed run skips them."""
    ids = set()
    try:
        with open(path) as f:
            for line in f:
                ids.add(json.loads(line)["id"])
    except FileNotFoundError:
        pass
    return ids


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', default=str(DEFAULT_DATA))
    p.add_argument('--out', default=str(DEFAULT_OUT))
    args = p.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("Set OPENROUTER_API_KEY in the environment; do not write the key into this file.")
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

    done = completed_ids(args.out)
    print(f"Already completed: {len(done)} items")

    with open(args.data) as f:
        lines = f.readlines()[:POOL_SIZE]

    with open(args.out, "a") as out:
        for line in lines:
            item = json.loads(line)
            if item["id"] in done:
                continue

            print(f"Processing {item['id']}...")
            baseline_samples = sample_judgments(client, build_baseline_prompt(item["text"]))
            intervention_samples = sample_judgments(client, build_intervention_prompt(item["text"]))

            result = {
                "id": item["id"],
                "human_scores": item["label_scores"],
                "baseline_samples": baseline_samples,
                "intervention_samples": intervention_samples
            }
            # Flushed per item so an interrupted batch keeps everything paid for.
            out.write(json.dumps(result) + "\n")
            out.flush()
            print(f"  Done: {item['id']}")

    print("All done for this run.")


if __name__ == '__main__':
    main()
