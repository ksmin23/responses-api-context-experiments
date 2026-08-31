## Technical summary

The completed 30-run paired pilot provides workload-specific evidence that
`all_turns + previous_response_id` can reach the same quality level with less
reasoning and lower decision latency than `current_turn + previous_response_id`.

- Both arms completed 15 runs with 100% protocol validity, 100% context-linkage
  validity, and 100% task success.
- `all_turns` reduced median evaluation-decision reasoning from 111 to 19 tokens
  and median total reasoning from 5,716 to 2,170 tokens.
- Median evaluation-decision latency decreased from 3.52 seconds to 2.32
  seconds.
- Quality did not show a meaningful paired improvement: the paired median
  evaluation-accuracy and strategy-consistency deltas were both zero.
- Estimated cost per success was nearly unchanged. The experiment therefore
  supports a thinking-efficiency claim, not a general quality or cost claim.

The predeclared combined claim was not supported because the strategy-learning
gate failed and evaluation accuracy was already near the ceiling.

## Quality remained high in both arms

| Metric | `current_turn` | `all_turns` | Interpretation |
| --- | ---: | ---: | --- |
| Runs | 15 | 15 | Complete paired design |
| Protocol success rate | 100% | 100% | Harness valid |
| Context-linkage validity | 100% | 100% | Continuations valid |
| Learning accuracy, mean | 45.33% | 46.00% | Similar |
| Boundary accuracy, mean | 56.67% | 58.33% | Similar |
| Blind evaluation accuracy, mean | 95.67% | 96.67% | Aggregate difference +1 percentage point |
| Evaluation errors, median | 1 | 1 | No median difference |
| Strategy consistency, median | 0.95 | 0.95 | No median difference |
| Task success rate | 100% | 100% | Safe-quality gate passed |

The evaluation phase contained 20 feedback-free cases per run. Accuracy is the
share of those cases receiving the hidden expected action. Strategy consistency
uses the same evaluation decisions to measure whether the learned latent policy
was applied coherently.

## `all_turns` used less reasoning and returned decisions faster

| Metric | `current_turn` | `all_turns` | Arm-level change |
| --- | ---: | ---: | ---: |
| Evaluation-decision reasoning tokens, median | 111 | 19 | -82.9% |
| Total reasoning tokens, median | 5,716 | 2,170 | -62.0% |
| Evaluation-decision latency, median | 3,519.1 ms | 2,322.6 ms | -34.0% |
| Estimated standard-rate cost per success | $0.454744 | $0.452099 | -0.6% |

Across the 15 matched profile/trial pairs, the paired medians for
`all_turns - current_turn` were:

| Paired metric | Median delta |
| --- | ---: |
| Evaluation accuracy | 0.00 |
| Evaluation errors | 0 |
| Strategy consistency | 0.00 |
| Evaluation-decision reasoning | -2,121 tokens |
| Evaluation-decision latency | -20,544.1 ms |
| Estimated standard-rate task cost | -$0.003650 |

The paired latency delta is accumulated over the evaluation decisions in a run;
it is not the same denominator as the per-decision arm-level latency median.

## Predeclared gates separate the supported and unsupported claims

| Gate | Result |
| --- | --- |
| Pilot complete | Passed |
| Harness valid | Passed |
| Safe quality | Passed |
| Thinking-efficiency signal | Passed |
| Latency corroboration | Passed |
| Strategy-learning signal | Failed |
| No ceiling | Failed |
| No floor | Passed |
| Combined claim supported | No |

The result supports using retained reasoning as a continuity and
thinking-efficiency mechanism for this stable-goal workflow. It does not prove
that retained reasoning always increases accuracy, improves learning, or lowers
total cost.

## Scope and methodology

- Workload: synthetic hidden support-policy learning and feedback-free transfer
- Profiles: 5
- Trials per profile: 3
- Arms: `current_turn` and `all_turns`
- Tickets per run: 38 across learning, boundary, and blind-evaluation phases
- Continuation: stored responses linked through `previous_response_id`
- Treatment variable: `reasoning.context`
- Service request: Fast processing; the effective tier was reported as
  `priority`
- Cost: estimated from the dated pricing snapshot used by the notebook

The policy mapping and grading criteria were hidden from the solver. Learning
and boundary phases returned labels, while evaluation feedback revealed only
that a decision had been recorded.

## Limitations and next step

- Blind evaluation accuracy was already 95.7–96.7%, creating a ceiling that
  limited the ability to detect strategy-quality improvements.
- Fifteen pairs are sufficient for a pilot but not for a universal performance
  claim.
- Cost estimates depend on the experiment pricing snapshot, cache behavior, and
  workload token mix.
- Reasoning tokens are an observable usage measure, not a direct measurement of
  the model's private wall-clock thinking process.

A follow-up seeking a strategy-learning effect should increase transfer
distance and policy ambiguity while preserving the current blind-evaluation,
paired-randomization, and safe-quality controls.

## Source

- [Canonical Notebook 02](../notebooks/02_retained_reasoning_all_turns_gpt_5_6.ipynb)
- [Combined developer guidance](../docs/retained_reasoning_developer_guidance_20260829.md)
