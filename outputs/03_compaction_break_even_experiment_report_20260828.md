## Technical summary

The completed benchmark shows that Compaction can recover its own cost in a
long, stateful GPT-5.6 workflow when enough turns remain after the Compaction
event and final-task quality is preserved.

- Early Compaction passed every quality gate, reached sustained median
  break-even at turn 8, and reduced paired final task cost by 43.39%.
- Late Compaction passed every quality gate, reached median break-even at turn
  22 and full-interval break-even at turn 25, and reduced paired final task cost
  by 30.20%.
- Middle Compaction reduced raw cost but failed the quality gate because one of
  ten trials violated a critical no-rollback constraint.
- Savings came from processing much less accumulated input context. Output
  tokens, reasoning tokens, and latency increased in the Compaction arms.

The result supports an input-context cost-amortization claim. It does not show
that Compaction always reduces thinking time, output generation, or latency.

## Quality determines which cost comparisons are eligible

| Arm | Successful trials | Median final score | Critical violations | Quality gate |
| --- | ---: | ---: | ---: | --- |
| Baseline | 10/10 | 97.5 | 0 | Reference |
| Early | 10/10 | 97.5 | 0 | Passed |
| Middle | 9/10 | 96.5 | 1 | Failed |
| Late | 10/10 | 97.0 | 0 | Passed |

Middle remains useful diagnostic evidence, but its lower cost cannot be called
quality-preserving savings.

## Early and Late recovered their Compaction investment

| Arm | Median task cost | Raw change from baseline | Paired final task-cost change | Break-even result |
| --- | ---: | ---: | ---: | --- |
| Baseline | $5.520442 | — | — | Reference |
| Early | $3.038160 | -44.97% | -43.39% | Sustained median and interval crossing at turn 8 |
| Middle | $3.674140 | -33.44% | Not quality-eligible | Quality gate failed |
| Late | $3.859152 | -30.09% | -30.20% | Median turn 22; full 95% interval turn 25 |

Cost per successful task, which charges failed attempts to the numerator, was:

| Arm | Cost per success | Change from baseline | Interpretation |
| --- | ---: | ---: | --- |
| Baseline | $5.577412 | — | Reference |
| Early | $3.168323 | approximately -43.2% | Quality-eligible |
| Middle | $4.077158 | approximately -26.9% | Descriptive only |
| Late | $3.846015 | approximately -31.0% | Quality-eligible |

## Input-context savings outweighed additional generation

Values below are medians over ten trials.

| Arm | Input tokens | Cached tokens | Output tokens | Reasoning tokens | Latency |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baseline | 3,030,165 | 2,702,107 | 3,305 | 1,077 | 137.5 s |
| Early | 718,781 (-76.28%) | 456,706 (-83.10%) | 10,107 (+205.86%) | 7,801 (+624.66%) | 160.1 s (+16.40%) |
| Middle | 1,209,828 (-60.07%) | 921,951 (-65.88%) | 7,397 (+123.83%) | 5,201 (+383.14%) | 155.4 s (+13.00%) |
| Late | 1,652,990 (-45.45%) | 1,381,443 (-48.88%) | 5,261 (+59.21%) | 2,931 (+172.22%) | 145.4 s (+5.74%) |

Compaction shortened later prefixes enough to reduce cache reads and cache
writes over the complete workflow. The Compaction request itself could be more
expensive, and replacement cache behavior appeared over subsequent requests.

## Scope and methodology

- Workload: synthetic 30-turn invoice-reconciliation incident investigation
- Arms: Baseline, Early, Middle, and Late
- Trials: 10 paired trials per arm
- Core Responses calls: 60 per arm run
- Fixed settings: GPT-5.6, medium reasoning effort, `all_turns`, `store=True`,
  `previous_response_id`, Fast service request, identical tool representation
- Treatment variable: Compaction disabled or triggered at calibrated 21k, 41k,
  or 61k thresholds
- Quality evaluation: calibrated GPT-5.6 Luna semantic grader
- Break-even requirement: cumulative paired savings remain below zero for the
  required post-crossing horizon

The benchmark completed all 40 planned arm runs. Every post-initial request had
the expected previous-response linkage, and calibration checks passed before
the benchmark.

## Limitations and next step

- Implicit prompt caching materially affected the measured break-even point.
- A terminal Early Compaction/cache-write interaction increased the final Early
  percentage; Late is the cleaner robustness check.
- The Middle quality failure does not prove that its threshold is inherently
  harmful, only that this run did not establish quality preservation.
- Thresholds are workload-specific and should not be copied as universal
  production settings.
- The experiment does not compare `current_turn` with `all_turns`; Notebook 02
  owns that question.

The next experiment should pair implicit and explicit cache policies, freeze
comparable cache breakpoints, and continue for a fixed horizon after the final
Compaction event.

## Source

- [Canonical Notebook 03](../notebooks/03_compaction_break_even_gpt_5_6.ipynb)
- [Detailed result interpretation](../docs/03_compaction_break_even_interpretation_20260828.md)
