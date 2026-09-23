"""Reading of the JSONL record files the pipelines write.

A run's records are appended one JSON object per line and flushed as they arrive,
so the file stays valid while a run is in progress and a run that dies partway
through remains analysable.
"""
import json
from pathlib import Path


def read_jsonl(path):
    """Parse a JSONL file into a list of objects, skipping only blank lines.

    A line that is present but unparseable raises, by design. A partial final line
    means a write was interrupted, and that is a fact about the run which the
    analyst needs to see and resolve; silently discarding it would quietly drop a
    scheduled observation and bias whatever coverage figure is computed next.
    """
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
