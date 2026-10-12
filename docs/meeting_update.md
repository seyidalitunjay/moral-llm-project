> Historical record, left as written. Current results: [results.md](results.md).

# Meeting update: completed technical control pilot

A three-condition technical pilot was completed on five previously inspected Scruples dev anecdotes, with two independent API requests per anecdote and condition (30 requests total). Conditions were direct judgment without a requested written appraisal, generic factual appraisal, and the original perspective-taking/cognitive-empathy/justice-sensitivity content. All responses were returned by Parasail for openai/gpt-oss-20b, at temperature 0.8, top-p 1, and a 4,096-token output cap. All reported normal completion. The baseline did include provider-returned reasoning, so it must not be described as a model operating without reasoning.

Six baseline responses initially failed the output parser because they consisted solely of an exact allowed label rather than the requested FINAL_LABEL field. A documented post-hoc correction accepts exact whole-response labels in all conditions, alongside the existing final-marker format. No labels were inferred from rationales or human scores. The original response records are retained; after reparsing, all conditions have 10 usable judgments. This fixes measurement of the emitted judgments while retaining the fact that six responses did not follow the requested output interface.

| Condition | Mean base-2 Jensen–Shannon divergence | Usable requests |
| --- | ---: | ---: |
| Direct baseline | 0.2357 | 10/10 |
| Generic factual appraisal | 0.1121 | 10/10 |
| Original intervention content | 0.1630 | 10/10 |

Lower divergence means closer agreement with the observed human judgment distribution, conditional on the four non-INFO labels. Generic appraisal has the lowest observed mean in this small run. Five anecdotes and two responses per condition cannot establish a reliable ranking, an empathy-specific benefit, or a reversal of the historical 60-item result. The prompts and routing also differ from the historical batch. The scientific question remains whether the specific perspective-taking and justice content adds anything beyond generic appraisal.

The immediate next step is a fixed 20-item development comparison with 10 requests per condition, keeping the three prompts, corrected parser, provider, and token cap fixed. Its 600 requests are planned, not completed. Review coverage before comparing item-paired divergence; report uncertainty and failures. Use the results to decide whether component ablations or a literature-grounded prompt revision are justified. A later untouched evaluation with a frozen protocol and justified sample size is required before calling the research complete.

---

**Correction appended 2026-09-24.** The closing paragraph above states that the
600 requests for the 20-item comparison are "planned, not completed". That was true
when this note was written and is no longer. The run has since been executed and is
stored at `results/pilot_v4/32fa0ec867b00d0c`, with all 600 responses recorded.
Coverage is uneven across arms: baseline 200/200 valid, generic 190/200, original
180/200, and only 4 of 20 items are complete in all three arms. No analysis has been
run over it. The original text is left unedited as a record of what was reported at
the time; see `protocol.md` for current status and `open-issues.md` for why the
uneven coverage matters.
