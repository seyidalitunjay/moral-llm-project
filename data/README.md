# Data

Neither file in this directory is tracked by git. The Scruples corpus is
third-party data released by its own authors, and the archive alone is 72 MB.

## What belongs here

| File | Size | SHA-256 |
| --- | ---: | --- |
| `anecdotes.tar` | 72 MB | `946eeb83ba2a1f30a3d70d1f906d507a069e3e57e6b6badebaa4a0499b9f75b6` |
| `dev.scruples-anecdotes.jsonl` | 5.4 MB | `23e49279fed593bbeccf64cd9b6224465e90c5aa9fd62511a92b9182e136e944` |

The loose JSONL is the dev split extracted from the archive. Only the legacy
`run_batch.py` needs it as a separate file; `run_control_pilot.py` and
`audit_results.py` read the archive directly, so a fresh setup needs the tar alone.

## Obtaining it

The Anecdotes subset of Scruples, from Lourie, Le Bras and Choi, *Scruples: A
Corpus of Community Ethical Judgments on 32,000 Real-Life Anecdotes* (AAAI 2021).
The corpus and its download instructions are published at
<https://github.com/allenai/scruples>.

Place the archive at `data/anecdotes.tar` and confirm the checksum before running
anything:

```bash
shasum -a 256 data/anecdotes.tar
```

The checksum matters beyond ordinary caution here. Run selection is a seeded draw
from the first 60 rows of the dev split, so a differently ordered or differently
versioned copy of the corpus would silently select different anecdotes while
producing an identical-looking command line.

## Expected structure

The archive holds three members, read by name and never extracted to disk:

```
anecdotes/train.scruples-anecdotes.jsonl
anecdotes/dev.scruples-anecdotes.jsonl
anecdotes/test.scruples-anecdotes.jsonl
```

Each row carries an `id`, the anecdote `text`, and `label_scores`, the count of
annotators choosing each of AUTHOR, OTHER, EVERYBODY, NOBODY and INFO. Those
counts are the human distribution every comparison in this repository is made
against.
