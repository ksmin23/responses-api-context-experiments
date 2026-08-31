## Executive conclusion

This experiment provides workload-specific evidence that server-side Compaction can recover its own cost while preserving final-task quality in a long, stateful GPT-5.6 Responses API workflow.

- The **Early** arm passed every predeclared quality gate and reached sustained median break-even at turn 8, one turn after its first Compaction event. Its paired final task cost was 43.39% lower than baseline.
- The **Late** arm also passed every quality gate. It reached sustained median break-even at turn 22. A more conservative interpretation that requires the entire 95% bootstrap interval to be below zero places the crossing at turn 25. Its paired final task cost was 30.20% lower than baseline.
- The **Middle** arm reduced raw cost but failed the quality gate because one of ten trials violated a critical no-rollback constraint. Its cost reduction must therefore not be reported as quality-preserving savings.

The savings came from processing much less accumulated input context after Compaction. The experiment did **not** show lower output tokens, reasoning tokens, or latency. It therefore supports an input-context cost-amortization claim, not a general claim that Compaction reduces thinking time or output generation.

## Experiment question and scope

The notebook asks:

> In a long, stateful GPT-5.6 Responses API workflow, when does server-side Compaction recover its own cost without reducing task quality?

The workload is a synthetic 30-turn invoice-reconciliation incident investigation. The model must integrate observations, corrections, constraints, and rejected hypotheses before producing a final diagnosis and recommendation.

The experiment holds the following settings constant across all arms:

- GPT-5.6 with medium reasoning effort
- `reasoning.context="all_turns"`
- `store=True`
- continuation through the latest `previous_response_id`
- Fast service tier
- identical tool-output representation, prompts, checkpoints, grader, and pricing snapshot

The only treatment variable is whether Compaction is disabled or triggered at the calibrated Early, Middle, or Late threshold. This experiment does not compare `current_turn` with `all_turns`, manual history replay, rolling truncation, different tool-output sizes, or different service tiers.

## Protocol and calibration validity

The saved run is suitable for interpretation:

- 40 of 40 planned arms completed: 4 arms × 10 paired trials.
- Every arm completed 60 core Responses API calls over 30 turns.
- Every post-initial request linked to the immediately preceding response: 59 of 59 expected links per arm.
- All task responses completed; there were no incomplete responses or Compaction continuation calls.
- All responses passed the notebook's Fast-mode service check. The API returned `priority` as the effective service tier for the requests classified as Fast.
- No failure log was created for this run.
- All semantic grader evaluations were valid and non-empty.
- Grader calibration was accepted with 4/4 expected decisions matched and agreement 1.0.
- Threshold calibration was accepted with 21K, 41K, and 61K thresholds all within tolerance and with zero suggested delta.

The benchmark observed $162.611924 in task-arm cost. Calibration and grader evaluation are experiment overhead and are not included in the task-arm break-even curves.

## Quality results

| Arm | Successful trials | Median final score | Median checkpoint score | Critical violations | Quality gate |
| --- | ---: | ---: | ---: | ---: | --- |
| Baseline | 10/10 | 97.5 | 100 | 0 | Reference |
| Early | 10/10 | 97.5 | 100 | 0 | Passed |
| Middle | 9/10 | 96.5 | 100 | 1 | Failed |
| Late | 10/10 | 97.0 | 100 | 0 | Passed |

Early and Late preserved both final semantic quality and checkpoint continuity relative to baseline. Their cost results are therefore eligible for quality-gated interpretation.

Middle trial 1 correctly diagnosed the worker-scoped idempotency-key problem, but its recommendation contained a contradiction. It said not to roll back during the active ledger migration while also recommending a “p95 rollback gate.” The blind Luna grader classified this as a critical violation of the no-rollback constraint and assigned a score of 82. The predeclared success-rate and no-critical-violation gates therefore rejected the Middle arm.

This single failure does not establish that the Middle threshold inherently harms quality. It establishes only that this run did not demonstrate quality preservation for that arm.

## Efficiency results

The following values are medians over ten trials. Percentage changes are relative to baseline.

| Arm | Task cost | Cost change | Input tokens | Cached tokens | Output tokens | Reasoning tokens | Latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | $5.520442 | — | 3,030,165 | 2,702,107 | 3,305 | 1,077 | 137.5 s |
| Early | $3.038160 | -44.97% | 718,781 (-76.28%) | 456,706 (-83.10%) | 10,107 (+205.86%) | 7,801 (+624.66%) | 160.1 s (+16.40%) |
| Middle | $3.674140 | -33.44% | 1,209,828 (-60.07%) | 921,951 (-65.88%) | 7,397 (+123.83%) | 5,201 (+383.14%) | 155.4 s (+13.00%) |
| Late | $3.859152 | -30.09% | 1,652,990 (-45.45%) | 1,381,443 (-48.88%) | 5,261 (+59.21%) | 2,931 (+172.22%) | 145.4 s (+5.74%) |

Compaction substantially reduced the accumulated input context processed on later calls. At the same time, generating Compaction items added output and reasoning tokens. Early Compaction produced the largest input reduction and final cost saving, but also the largest output-token and latency increase.

The result should therefore be interpreted as follows:

> The long-tail input-context savings exceeded the cost of generating and applying Compaction. The experiment does not show that Compaction itself is free or that it reduces every token class.

## Prompt-cache interaction explains much of the saving

`cached_tokens` is the cache-read quantity in the response usage record. `cache_write_tokens` is the portion written as a reusable prompt prefix. The notebook partitions every request's input into three mutually exclusive classes:

```text
uncached input = input tokens - cached tokens - cache-write tokens
```

Its dated GPT-5.6 Sol pricing snapshot uses $4.00 per million uncached input tokens, $0.40 per million cached-input tokens, and $5.00 per million cache-write tokens. The $5.00 cache-write rate is the complete 1.25× write price, not a surcharge added on top of the $4.00 input rate. The notebook then applies its 2× Fast-mode multiplier to each class. These are experiment-snapshot rates, not a live billing lookup.

### Compaction lowered total cache reads and writes

The values below are per-run medians over ten trials. “Cache read” means `cached_tokens`.

| Arm | Cache-read tokens | Change from baseline | Cache-write tokens | Change from baseline |
| --- | ---: | ---: | ---: | ---: |
| Baseline | 2,702,107 | — | 296,868 | — |
| Early | 456,706 | -83.10% | 140,486 | -52.68% |
| Middle | 921,951 | -65.88% | 165,121 | -44.38% |
| Late | 1,381,443 | -48.88% | 195,152 | -34.26% |

The initial hypothesis that every Compaction event would increase total cache-write volume is not supported by this run. Compaction invalidated or shortened the old reusable prefix, and some following requests wrote a new compact prefix. However, the replacement prefix was much shorter than the continuously growing baseline prefix. Across the full 30 turns, every Compaction arm therefore wrote fewer cache tokens in total.

### Cache-write savings were material, but not the only source of savings

For an additive decomposition, the following table uses the mean paired candidate-minus-baseline cost difference across the ten trials. Means are used here so the component rows sum exactly to the net difference. Negative values are savings; positive values are added cost.

| Arm | Cache-read cost | Cache-write cost | Uncached-input cost | Output cost | Net task-cost difference |
| --- | ---: | ---: | ---: | ---: | ---: |
| Early | -$1.795 | -$1.796 | +$0.901 | +$0.282 | -$2.409 |
| Middle | -$1.421 | -$1.544 | +$0.891 | +$0.167 | -$1.908 |
| Late | -$1.051 | -$1.206 | +$0.455 | +$0.072 | -$1.731 |

Early's cache reads and writes together reduced estimated cost by approximately $3.591 per trial. Compaction-related uncached input and output added approximately $1.182, leaving a net mean saving of $2.409. If cache-write savings are removed from this accounting counterfactual, Early still saves approximately $0.613 and Late approximately $0.525 on average. The observed cost advantage is therefore not solely a cache-write artifact, although cache-write avoidance substantially increases its magnitude.

Middle remains descriptive only because its quality gate failed. Its token and cost movements must not be presented as quality-preserving savings.

### A Compaction event can temporarily increase cache misses and later writes

The first Early event illustrates the request-level sequence:

| Window | Cache-read difference | Cache-write difference | Task-cost difference |
| --- | ---: | ---: | ---: |
| Turn 7 Compaction response | -20,216 tokens | -3,281 tokens | +$0.180 |
| Next request | -23,442 tokens | -31 tokens | -$0.011 |
| Entire next turn | -23,442 tokens | -22,498 tokens | -$0.235 |

On the turn-7 Compaction response itself, the Early arm reported zero cache-read and zero cache-write tokens and processed a median 24.2k tokens as uncached input. The response also generated a median 893 output tokens. That request was therefore approximately $0.180 more expensive than its paired baseline request.

The replacement cache appeared over subsequent requests rather than uniformly on the Compaction response. At turn 8, the Early arm wrote a median 4.4k-token prefix on the tool-output request, while the paired baseline wrote approximately 26.9k tokens. The next turn saved approximately $0.235 and recovered the first event's cost.

Later events did not all have the same pattern. At the Early turn-13 event, cache-write tokens were approximately 984 higher than baseline on the event request and 1,712 higher on the following request. The much larger cache-read reduction still made both requests cheaper overall. Therefore, `cache_write_tokens=0` on one Compaction response must not be interpreted as proof that no replacement cache was created; usage needs to be followed across subsequent requests.

### Implicit caching affects the measured break-even point

The benchmark used a unique `prompt_cache_key` for every trial and arm, preventing cross-arm cache contamination, but it used `prompt_cache_options={"mode": "implicit"}`. GPT-5.6 therefore selected the cache breakpoint automatically.

Two discontinuities materially affect the reported economics:

- Immediately after the first Early Compaction, baseline wrote approximately 26.9k tokens at turn 8 while Early wrote approximately 4.4k. This cache-write difference is the main reason the first event was repaid by the next turn.
- At the final turn, baseline wrote a median 101.2k-token prefix. Nine Early trials emitted a turn-30 Compaction item, and the Early arm wrote a median 9.8k tokens on that final tool-output request. The paired task-cost difference moved from -$1.486 at turn 29 to -$2.382 at turn 30. Approximately $0.8–$0.9 of the final difference is associated with this terminal-request cache-write and Compaction interaction.

The second point deserves caution. A cache write on the final request has no opportunity to generate a later cache hit inside this fixed 30-turn workload. Avoiding that write is still a real billed saving under the observed implicit-cache behavior, but it inflates the final percentage relative to a workflow that continues for more turns or controls cache breakpoints explicitly. It does not invalidate the Early turn-8 crossing, which occurred much earlier.

Late provides the cleaner robustness check: it had no terminal Compaction event, passed the quality gate, and still produced a mean paired saving of $1.731. Its result shows that the overall Compaction saving is not dependent on the turn-30 Early event.

### Recommended cache-focused follow-up

The next experiment should separate Compaction from the implicit cache policy:

1. Add paired `implicit` and `explicit` prompt-cache modes while keeping the Compaction threshold fixed.
2. Predeclare explicit breakpoints so baseline and treatment write comparable stable prefixes.
3. Continue for a fixed number of turns after the last Compaction event instead of ending on a possible Compaction turn.
4. Report cumulative cache-read, cache-write, uncached-input, and output costs as separate curves.
5. Report both the observed total cost and a diagnostic counterfactual with cache-write cost removed. The counterfactual is an attribution tool, not a billing claim.
6. Retain the unique per-trial and per-arm `prompt_cache_key` isolation already used by the notebook.

This follow-up would answer two distinct questions: whether Compaction reduces the amount of context processed, and whether its apparent dollar break-even depends on the automatic cache-write schedule.

## Cost per successful task

`cost_per_success` includes the cost of failed attempts in the numerator and is therefore the safer economic metric when quality differs.

| Arm | Total successful trials | Cost per success | Change from baseline |
| --- | ---: | ---: | ---: |
| Baseline | 10 | $5.577412 | — |
| Early | 10 | $3.168323 | approximately -43.2% |
| Middle | 9 | $4.077158 | approximately -26.9% |
| Late | 10 | $3.846015 | approximately -31.0% |

Although Middle still has a lower cost per success than baseline, its quality gate failed. It remains economically descriptive but is not evidence of quality-preserving Compaction.

## Paired break-even analysis

### Early threshold

- Observed Compaction turns: 7, 13, 19, 25, and usually 30
- First-event incremental cost at turn 7: +$0.181220
- Predeclared sustained median break-even: turn 8
- Final paired task-cost delta: -$2.381821
- Final paired percentage delta: -43.39%
- 95% bootstrap interval for final percentage delta: -47.83% to -38.65%

The first Compaction event imposed an observable cost. The candidate recovered that cost on the next turn, and the paired incremental median and its 95% interval remained below zero through turn 30. Early is the strongest cost-amortization result in this experiment.

### Late threshold

- First Compaction turn: 18 or 19, depending on the trial
- Predeclared sustained median break-even: turn 22
- First turn whose full 95% bootstrap interval is below zero: turn 25
- Final paired task-cost delta: -$1.677218
- Final paired percentage delta: -30.20%
- 95% bootstrap interval for final percentage delta: -36.10% to -27.72%

The notebook's predeclared rule uses the paired median, requires all ten pairs, and requires at least four later turns that remain below zero. Turn 22 satisfies that rule. Its interval still crosses zero, however, so turn 25 is the more conservative statistically supported crossing.

### Middle threshold

- Observed Compaction turns: 13 and 25
- Median paired final raw-cost delta: approximately -$1.88
- Break-even conclusion: withheld

The arm failed the success non-inferiority and no-critical-violation gates. Calculating a raw cost difference is useful diagnostically, but reporting it as quality-preserving savings would violate the experiment protocol.

## Evaluation against the original purpose

The experiment successfully answers its narrow question for two thresholds:

> On this 30-turn invoice-reconciliation workload, Early and Late server-side Compaction recovered their treatment cost while preserving the predeclared final and checkpoint quality requirements.

It does not establish the following broader claims:

- Compaction always preserves quality.
- Early Compaction is optimal for every workload.
- Compaction reduces thinking time, output tokens, reasoning tokens, or latency.
- Compaction is better than rolling truncation.
- `all_turns` is better than `current_turn`.
- Retained reasoning itself caused the observed savings.

The experiment is a strong paired pilot for long-context cost amortization, but it remains one synthetic workload with ten paired trials and a dated pricing snapshot. Production recommendations require replication across workloads, context-growth patterns, tool-output sizes, model snapshots, and service tiers.

## Recommended reporting language

Use:

> In a 30-turn paired GPT-5.6 invoice-reconciliation workload using `all_turns` and `previous_response_id`, Early and Late server-side Compaction preserved the predeclared quality gates and reduced final paired task cost by median values of 43.39% and 30.20%, respectively. Early recovered its first Compaction cost by the next turn; Late crossed the predeclared median break-even criterion at turn 22 and the more conservative interval-based criterion at turn 25.

Avoid:

> Compaction universally makes GPT-5.6 faster, cheaper, and more accurate.

## Source artifacts

- [Notebook 03](../notebooks/03_compaction_break_even_gpt_5_6.ipynb)
- [Experiment improvement plan](notebook_01_03_improvement_plan.md)
- [GPT-5.6 model guidance: prompt caching](https://developers.openai.com/api/docs/guides/latest-model)
- [GPT-5.6 Sol pricing](https://developers.openai.com/api/docs/models/gpt-5.6-sol)
- [Responses API Compaction reference](https://developers.openai.com/api/reference/java/resources/responses/methods/compact)

The SHA-256 values in the document metadata identify the exact files used for this interpretation. The recorded Git commit is a repository baseline; the source worktree contained uncommitted modifications, so the notebook checksum is the authoritative identifier for the interpreted notebook state.
