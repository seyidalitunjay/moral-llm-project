"""The first-generation pipeline, preserved so its published numbers stay readable.

Nothing here should be used for new measurements, and none of it is shared with
`parsing.py` or `prompts.py`. It is kept because `results.jsonl` and
`results_v2.jsonl` were produced by exactly this code, and the audit of those
files only means anything if the code that wrote them is still on record.

Two differences from the current pipeline are substantive rather than cosmetic,
and collapsing either one would misrepresent what the historical numbers measure:

  * `extract_label` searches the whole response for a label, so it can return a
    verdict the model only mentioned in passing. The current parser refuses that.
  * The prompts below ask for a bare one-word answer with no dedicated final
    marker, which is what made the loose search necessary in the first place.
"""
LABELS = ['AUTHOR', 'OTHER', 'EVERYBODY', 'NOBODY']
N_SAMPLES = 5


def extract_label(text):
    """Return the last label mentioned anywhere in `text`, or None if none appears.

    Taking the last occurrence was a pragmatic choice for prompts that requested a
    one-word answer but often received a short preamble first. Note what it cannot
    distinguish: a response reasoning about OTHER before concluding AUTHOR, and a
    response concluding OTHER, both yield whichever label happens to sit later in
    the text. Substring matching also means AUTHORSHIP counts as AUTHOR. The
    resulting labels cannot be re-derived or checked, because the raw response text
    was never saved in these runs.
    """
    if not text or not text.strip():
        return None
    text_upper = text.upper()
    if not any(l in text_upper for l in LABELS):
        return None
    last_positions = {l: text_upper.rfind(l) for l in LABELS if l in text_upper}
    return max(last_positions, key=last_positions.get)


def build_baseline_prompt(anecdote_text):
    return f"""Read the following situation and judge who is in the wrong: the author (AUTHOR), the other person (OTHER), everybody (EVERYBODY), or nobody (NOBODY).

Situation: {anecdote_text}

Answer with one word."""


def build_intervention_prompt(anecdote_text):
    return f"""Consider the following situation from multiple perspectives before making a judgment.

Situation: {anecdote_text}

Step 1 - Perspective-taking: Consider this situation from the perspective of the author, and separately from the perspective of the other person. For each, describe what they likely believed and felt.

Step 2 - Cognitive empathy: For each party, explain what they were trying to achieve and why their action made sense to them at the time.

Step 3 - Justice sensitivity: Consider whether the outcome was proportionate, and whether either party's actions violated a reasonable expectation of fairness toward the other.

Now, given the above reasoning, judge who is in the wrong: the author (AUTHOR), the other person (OTHER), everybody (EVERYBODY), or nobody (NOBODY).

End your answer with just the single word judgment on its own line."""
