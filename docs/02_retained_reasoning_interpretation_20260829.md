## Technical summary

Notebook 02 partially achieved its original objective. On the Support Policy v2
workload, `all_turns + previous_response_id` preserved the quality reached by
`current_turn + previous_response_id` while using materially fewer reasoning
tokens and returning evaluation decisions faster.

- Both arms completed all 15 runs with 100% protocol validity, context-linkage
  validity, and task success.
- Median reasoning per evaluation decision fell from 111 to 19 tokens, an
  82.9% reduction.
- Median total reasoning per run fell from 5,716 to 2,170 tokens, a 62.0%
  reduction.
- Median evaluation-decision latency fell from 3.52 seconds to 2.32 seconds, a
  34.0% reduction.
- Blind-evaluation accuracy was 95.67% for `current_turn` and 96.67% for
  `all_turns`, but the paired median accuracy difference was zero.
- Median strategy consistency was 95% in both arms.
- Estimated standard-rate cost per successful run differed by only 0.58%, and
  the pair-level cost direction was nearly evenly split.

The experiment therefore provides strong workload-specific evidence for a
**thinking-efficiency effect**. It does not establish a retained-reasoning
improvement in learning quality, strategy consistency, or total cost. The
notebook's final `claim_supported: false` result is correct because the
predeclared combined claim required both an efficiency benefit and a
strategy-learning benefit.

## Experimental design isolates reasoning retention within a stateful workflow

The experiment compares two reasoning-context policies while holding the rest
of the workflow constant.

| Dimension | Design |
| --- | --- |
| Workload | Hidden Support Policy v2 learning and feedback-free evaluation |
| Profiles | 5 independently parameterized policy profiles |
| Trials | 3 paired trials per profile |
| Arms | `current_turn` and `all_turns` |
| Continuation | `store=True` with `previous_response_id` |
| Tickets per run | 10 learning, 8 boundary, and 20 blind-evaluation tickets |
| Model configuration | GPT-5.6 with medium reasoning effort |
| Processing request | `fast`; responses reported `priority` |
| Primary treatment | `reasoning.context` |

Both arms receive the same profile-specific ticket sequence. Learning and
boundary tickets return labels after each decision. Blind-evaluation tickets
only confirm that the decision was recorded; they do not reveal the expected
action. Evaluation accuracy therefore measures transfer of the previously
learned policy rather than additional learning from evaluation feedback.

The preflight enumerates 2,880 candidate mapping and precedence
parameterizations and verifies that the 18 labeled cases identify exactly one
behavior signature. This removes ambiguity about whether the target policy can
be learned. It also contributes to the ceiling effect discussed below.

### Metric definitions

- **Blind-evaluation accuracy** is the share of 20 feedback-free evaluation
  tickets per run that received the hidden expected action.
- **Strategy consistency** measures whether tickets governed by the same
  decisive rule received the corresponding learned action consistently.
- **Evaluation-decision reasoning** counts reasoning tokens generated for the
  action decision in the blind-evaluation phase.
- **Evaluation-decision latency** measures the elapsed time of those decision
  responses. It includes service and network variation.
- **Cost per success** includes the estimated standard-rate cost of all runs in
  an arm divided by successful runs. Because both arms achieved 100% task
  success, it equals mean estimated task cost in this experiment.

## `all_turns` preserved quality while using substantially less reasoning

| Metric | `current_turn` | `all_turns` | Interpretation |
| --- | ---: | ---: | --- |
| Blind-evaluation accuracy | 95.67% (287/300) | 96.67% (290/300) | Aggregate difference of +1 percentage point; paired median difference was 0 |
| Median strategy consistency | 95% | 95% | No median improvement |
| Median reasoning per evaluation decision | 111 tokens | 19 tokens | 82.9% lower |
| Median evaluation-phase reasoning per run | 2,682 tokens | 622 tokens | 76.8% lower |
| Median total reasoning per run | 5,716 tokens | 2,170 tokens | 62.0% lower |
| Median evaluation-decision latency | 3.52 seconds | 2.32 seconds | 34.0% lower |
| Task success | 100% | 100% | Safe-quality gate passed |
| Estimated standard-rate cost per success | $0.454744 | $0.452099 | 0.58% lower; not a robust cost effect |

The pair-level directions show that the reasoning result was consistent across
profiles and trials rather than being driven by one outlier.

| Paired metric (`all_turns - current_turn`) | Favors `all_turns` | Tie | Favors `current_turn` | Paired median |
| --- | ---: | ---: | ---: | ---: |
| Evaluation accuracy | 3 | 11 | 1 | 0 |
| Evaluation errors | 3 | 11 | 1 | 0 |
| Strategy consistency | 3 | 11 | 1 | 0 |
| Evaluation-decision reasoning | 15 | 0 | 0 | -2,121 tokens per run |
| Evaluation-decision latency | 14 | 0 | 1 | -20.54 seconds per run |
| Estimated standard-rate cost | 8 | 0 | 7 | -$0.003650 per run |

Evaluation-decision reasoning favored `all_turns` in all 15 pairs, and latency
favored it in 14 of 15 pairs. The most defensible interpretation is that
`all_turns` reused policy reasoning formed earlier in the response chain,
reducing the amount of newly generated reasoning required for each subsequent
decision.

Reasoning tokens are observable API usage, not direct access to the model's
private reasoning process. Latency provides an independent operational signal,
but it is also affected by service and network variation. Together, the two
measures support a thinking-efficiency conclusion within this workload.

## The experiment did not identify a learning or strategy-quality advantage

Quality was already near the maximum in both arms:

- `current_turn` produced 287 correct decisions out of 300.
- `all_turns` produced 290 correct decisions out of 300.
- Eleven of the 15 pairs tied on evaluation accuracy and strategy consistency.
- The paired median accuracy, error, and strategy-consistency differences were
  all zero.

Both arms improved from mean learning accuracy of roughly 45–46% and mean
boundary accuracy of roughly 57–58% to more than 95% blind-evaluation accuracy.
This shows that the workflow enabled the model to learn and apply the hidden
policy. It does not show that retaining reasoning caused better learning than
the control condition.

The quality difference remained unresolved for four related reasons:

1. **The labeled evidence fully identifies the policy.** Once the model has
   processed the 18 labeled cases, both arms can reconstruct the only policy
   consistent with the evidence.
2. **`current_turn` retains observable conversation state.** Both arms use
   `previous_response_id`, so prior tickets, tool outputs, and accepted actions
   remain available. `current_turn` can reconstruct the policy by reasoning
   over that visible history even when older reasoning items are not retained.
3. **Transfer distance is limited.** Evaluation requires new combinations of a
   static mapping and precedence policy, but not a mid-run policy change,
   delayed dependency, or reconciliation of conflicting new evidence.
4. **Strategy consistency is closely coupled to accuracy.** In a static policy,
   applying the correct action for each decisive rule is nearly the same as
   rule-level accuracy, so the metric does not independently capture strategy
   formation, revision, or long-horizon transfer.

The result should therefore be described as **unresolved under a ceiling**, not
as evidence that retained reasoning has no learning benefit.

## Lower reasoning did not produce a reliable total-cost reduction

| Mean usage per run | `current_turn` | `all_turns` | Direction |
| --- | ---: | ---: | --- |
| Input tokens | 327,955 | 436,819 | Higher |
| Cached-input tokens | 289,683 | 392,760 | Higher |
| Cache-write tokens | 23,854 | 31,249 | Higher |
| Output tokens | 8,097 | 4,376 | Lower |
| Reasoning tokens | 5,962 | 2,241 | Lower |

`all_turns` substantially reduced output and reasoning tokens but processed
more input, cached-input, and cache-write tokens. These movements largely
offset one another in the notebook's dated standard-rate estimate. Estimated
cost per success declined from $0.454744 to $0.452099, but cost favored
`all_turns` in only 8 of 15 pairs and favored `current_turn` in 7.

The experiment therefore does not support a general cost-saving claim. The
estimate uses the notebook's August 25, 2026 pricing snapshot rather than an
invoice-level reconstruction of Fast Processing charges. The design also lacks
a cache-disabled control, so it cannot isolate retained reasoning from
prompt-cache behavior in the cost result.

## The original objective was only partially achieved

| Objective | Result | Evidence |
| --- | --- | --- |
| Validate the protocol and response chain | Achieved | 30/30 runs completed; protocol and linkage validity were 100% |
| Preserve quality on a blind workload | Achieved | Both arms had 100% task success and more than 95% evaluation accuracy |
| Reduce newly generated reasoning | Strongly achieved | All 15 pairs favored `all_turns` |
| Reduce decision latency | Achieved | 14 of 15 pairs favored `all_turns` |
| Improve learning quality | Not demonstrated | Paired accuracy median was 0 under a quality ceiling |
| Improve strategy consistency | Not demonstrated | Both medians were 95%; paired median was 0 |
| Reduce total cost | Not demonstrated | Aggregate difference was 0.58%; pair direction was 8 versus 7 |
| Establish an overall retained-reasoning advantage | Not demonstrated | The predeclared combined gate required both efficiency and strategy-learning signals |

The final experiment claim should be limited to the following:

> On this Support Policy v2 workload, `all_turns` preserved essentially the
> same blind-evaluation quality as `current_turn` while substantially reducing
> evaluation reasoning and usually returning decisions faster. Because both
> arms exceeded 95% accuracy, the experiment did not establish an improvement
> in learning quality or strategy consistency, and it did not show a reliable
> total-cost reduction.

## Use retained reasoning as a task-scoped default for stable goals

The absence of a measured quality uplift is not a reason to disable retained
reasoning. Notebook 02 shows a useful outcome for a continuous agent workflow:
the treatment preserved quality while reducing reasoning and latency.

Current [OpenAI GPT-5.6 model guidance](https://developers.openai.com/api/docs/guides/latest-model)
states that GPT-5.6 defaults to `all_turns`. It recommends `all_turns` when a
task's goals, assumptions, and priorities remain stable across turns, using
`previous_response_id` to make earlier reasoning available. It recommends
`current_turn` when earlier reasoning is no longer relevant.

This supports a **task-scoped default**, not a global rule that all reasoning
should always be retained.

| Workflow state | Recommended starting point |
| --- | --- |
| The same incident, coding task, or policy application continues | `all_turns` with `previous_response_id` |
| The same rules and assumptions are reused across tool calls | `all_turns` with `previous_response_id` |
| Context continues growing within the same task | Keep `all_turns`; evaluate Compaction separately |
| The goal, customer, ticket, or core assumptions change materially | Start a new response chain or use `current_turn` |
| Earlier reasoning is obsolete or actively interferes with the new task | Use `current_turn` or start a new chain |
| The request is independent and one-shot | Use an independent response or `current_turn` |

This recommendation does not assume that `all_turns` is always more accurate
or less expensive. Quality, latency, token classes, and cost should be measured
separately on representative application workloads.

## Limitations and robustness boundaries

- The result covers one synthetic hidden-policy workload, 15 runs per arm, and
  15 matched pairs.
- The quality ceiling left little statistical room to detect a
  strategy-learning benefit.
- No cache-disabled control separates prompt-cache effects from retained
  reasoning in the cost comparison.
- Reasoning tokens and latency are operational measures, not direct observation
  of the model's private reasoning process.
- The strategy-consistency metric is not sufficiently independent of accuracy
  for a static policy.
- The experiment used `store=True`; it did not compare server-managed state
  with manual encrypted-reasoning replay under `store=False`.

These limitations do not invalidate the observed 15-of-15 reasoning reduction.
They limit how far that result can be generalized and prevent broader claims
about quality, cost, or alternative state-management implementations.

## The next experiment should create room for strategy learning to differ

A follow-up should preserve the current identifiability and blind-evaluation
controls while increasing the need to retain and revise a strategy over time.

1. Calibrate control accuracy to approximately 80–90% to avoid both floor and
   ceiling effects.
2. Increase the transfer distance between labeled cases and evaluation cases.
3. Introduce a mid-run policy update, delayed rule interaction, or correction
   that requires reconciliation with earlier evidence.
4. Keep evaluation feedback-free and continue prohibiting an external
   rationale scratchpad that could leak the learned policy across arms.
5. Increase the number of profiles and repetitions, then report paired
   confidence intervals for quality, reasoning, latency, and cost.
6. Add a cache-policy control if the follow-up is intended to make an economic
   attribution claim.

## Further questions

- Does the reasoning reduction persist when evaluation requires policy revision
  rather than static-policy lookup?
- Can the workload expose a strategy-learning difference without pushing
  `current_turn` below the safe-quality floor?
- How much of the input-token and cost difference is attributable to retained
  reasoning versus prompt-cache behavior?
- Does the result persist across reasoning efforts, service tiers, and longer
  response chains?

## Sources

### Project evidence

- [Notebook 02 result summary](../outputs/02_retained_reasoning_results_20260829.md)
- [Notebook 02](../notebooks/02_retained_reasoning_all_turns_gpt_5_6.ipynb)
- [Retained Reasoning and Compaction developer guidance](retained_reasoning_developer_guidance_20260829.md)

### Official OpenAI documentation

- [GPT-5.6 model guidance](https://developers.openai.com/api/docs/guides/latest-model)
- [Responses API create reference](https://developers.openai.com/api/reference/cli/resources/responses/methods/create)
