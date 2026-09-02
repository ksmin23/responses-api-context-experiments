## 결론

개발자에게 전달할 핵심 메시지는 다음과 같다.

> GPT-5.6의 retained reasoning은 항상 더 저렴하고 더 정확하게 만드는 옵션이 아니라, 같은 목표가 이어지는 작업에서 모델이 매번 문제를 다시 해석하지 않도록 하는 기본적인 연속성 메커니즘이다. 짧고 연속적인 작업에서는 `all_turns + previous_response_id`를 기본으로 사용하고, context가 길어지면 품질 게이트와 손익분기점을 측정해 Compaction을 적용해야 한다.

이 메시지는 OpenAI의 공식 권장 사항과 대체로 일치한다. 다만 ARC-AGI-3 사례의 성능 향상을 모든 workload에서 재현할 수 있다는 의미로 확대해서는 안 된다.

## 실험별 핵심 결과

| 관점 | Notebook 02 | Notebook 03 | 개발자에게 주는 의미 |
| --- | --- | --- | --- |
| 주요 treatment | `current_turn`과 `all_turns` 비교 | Compaction 없음과 Early/Middle/Late 비교 | Retained reasoning과 Compaction은 서로 다른 최적화 축이다. |
| Retained reasoning | `all_turns`가 같은 수준의 품질을 더 적은 reasoning으로 달성 | 모든 arm에서 `all_turns` 고정 | 같은 목표가 이어지면 reasoning context를 유지하는 것이 합리적이다. |
| 품질 향상 | 명확한 paired 품질 향상은 입증하지 못함 | Early/Late는 품질 유지, Middle은 품질 게이트 실패 | 품질 향상을 기본 전제로 삼으면 안 된다. |
| 지연시간 | `all_turns`에서 감소 | Compaction arm에서 증가 가능 | Retained reasoning과 Compaction의 latency 효과는 다르다. |
| 비용 | 성공당 비용이 약 0.6% 감소해 사실상 유사 | 장기 실행에서 품질을 유지한 Early/Late가 약 30–43% 절감 | Reasoning 감소가 곧바로 총비용 감소를 뜻하지 않는다. |
| 장기 전략 | Ceiling effect로 학습·전략 향상 입증 실패 | 긴 context의 비용 상각 효과를 측정 | 전략 학습 효과를 보려면 더 어려운 적응형 workload가 필요하다. |

## Notebook 02 해석

Notebook 02는 Support Policy v2 workload를 사용하며, 5개 profile, profile당 3개 paired trial, arm당 38개 ticket으로 구성된다. 전체 30개 실행이 완료되었다.

### 관찰된 효과

| 지표 | `current_turn` | `all_turns` | 해석 |
| --- | ---: | ---: | --- |
| Blind evaluation accuracy | 95.67% | 96.67% | Aggregate 기준 1%p 차이지만 paired median 차이는 0이다. |
| Strategy consistency | 0.95 | 0.95 | 전략 일관성 향상은 관찰되지 않았다. |
| Evaluation-decision reasoning tokens 중앙값 | 111 | 19 | 약 83% 감소했다. |
| 전체 reasoning tokens 중앙값 | 5,716 | 2,170 | 약 62% 감소했다. |
| Evaluation-decision latency 중앙값 | 3.52초 | 2.32초 | 약 34% 감소했다. |
| 성공당 추정 비용 | $0.4547 | $0.4521 | 약 0.6% 차이로, 일반적인 비용 절감을 주장하기에는 작다. |

이 결과는 다음 주장을 지원한다.

> 같은 작업을 계속 수행할 때 retained reasoning을 사용하면 모델이 기존 상황을 다시 해석하는 데 사용하는 reasoning tokens와 latency를 줄일 수 있다.

그러나 다음 주장은 입증하지 못했다.

> Retained reasoning이 항상 더 높은 정확도나 더 나은 학습·전략을 만든다.

정확도의 paired median 차이가 없고 strategy consistency도 같았다. 실험의 `claim_supported=false`는 전체 결합 가설을 기각한 올바른 판정이다. 즉, thinking-efficiency 신호는 관찰됐지만 strategy-learning 신호는 ceiling effect로 확인하지 못했다.

## Notebook 03 해석

Notebook 03은 30-turn invoice-reconciliation incident investigation에서 `all_turns`, `previous_response_id`, model, reasoning effort, tool-output representation을 고정하고 Compaction threshold만 변경했다.

### 품질과 비용 결과

| Arm | 품질 결과 | Paired final task cost | 손익분기점 |
| --- | --- | ---: | --- |
| Baseline | 기준 arm | 기준 | 해당 없음 |
| Early | 10/10 성공, 품질 게이트 통과 | 약 43.4% 감소 | 중앙값 기준 turn 8 |
| Middle | 9/10 성공, critical violation 1건 | 원시 비용은 감소 | 품질 게이트 실패로 절감 성공이라 할 수 없음 |
| Late | 10/10 성공, 품질 게이트 통과 | 약 30.2% 감소 | 중앙값 turn 22, 보수적 bootstrap 기준 turn 25 |

Early에서는 누적 input tokens가 baseline보다 약 76%, Late에서는 약 45% 감소했다. 반면 output tokens, reasoning tokens, latency는 증가했다.

따라서 Notebook 03은 다음을 보여준다.

> Compaction은 모델을 즉시 더 빠르게 생각하게 만드는 기능이 아니라, 선행 비용을 지불하고 이후 반복적으로 처리되는 장기 context를 줄이는 투자다.

실무적인 Compaction 조건은 다음과 같이 표현할 수 있다.

```text
예상되는 이후 context 절감액
    >
Compaction 호출 비용
+ 추가 reasoning/output 비용
+ 품질 저하 위험
```

Middle arm은 비용이 감소했어도 중요한 no-rollback constraint를 위반했다. 따라서 비용 비교는 반드시 품질 게이트를 통과한 arm 사이에서만 수행해야 한다.

## 두 실험을 합친 해석

### 1. Retained reasoning은 단기 연속성 최적화다

같은 목표, 가정, 정책이 여러 tool call과 turn에 걸쳐 유지된다면 `all_turns`는 모델이 매번 상황을 재구성하는 부담을 줄일 수 있다. Notebook 02는 이 효과를 reasoning tokens와 latency에서 확인했다.

이 결과만으로 정확도나 총비용이 항상 개선된다고 주장해서는 안 된다. 특히 cached input, cache write, output, reasoning의 가격 비중에 따라 reasoning 감소가 전체 청구 비용에 미치는 영향은 작을 수 있다.

### 2. Compaction은 장기 context 비용 상각이다

Context가 계속 성장하는 workflow에서는 retained reasoning만 유지하면 매 요청에서 처리되는 history가 커진다. Compaction은 이 장기 비용을 줄이지만 자체 호출 비용과 새 reasoning/output 비용을 발생시킨다.

따라서 Compaction은 고정 turn마다 무조건 실행하는 기능이 아니라 다음을 고려하는 threshold 정책이어야 한다.

- 현재 context 크기
- 예상되는 남은 turn 수
- Compaction 호출 및 cache-write 비용
- 최종 품질과 constraint 유지 여부
- Compaction 이후 누적 절감액

### 3. 품질, reasoning, latency, 비용은 서로 다른 지표다

두 실험은 이 지표들이 같은 방향으로 움직이지 않을 수 있음을 보여준다.

- Notebook 02: reasoning과 latency는 크게 감소했지만 총비용은 거의 같았다.
- Notebook 03: input context와 총비용은 감소했지만 reasoning, output, latency는 증가했다.

따라서 “토큰 감소”, “thinking time 감소”, “latency 감소”, “비용 감소”, “품질 향상”을 하나의 효율성 주장으로 묶어서는 안 된다.

## 개발자 권장 운영 원칙

### 같은 목표와 가정이 유지되는 작업

`reasoning.context="all_turns"`와 `previous_response_id`를 기본으로 사용한다.

적합한 예:

- 동일한 incident를 여러 tool로 조사하는 작업
- 동일한 고객 정책을 여러 ticket에 반복 적용하는 작업
- 하나의 코드 변경을 탐색, 구현, 테스트하는 agent workflow
- 장기 분석에서 새로운 관찰값을 계속 반영하는 작업

### 목표나 가정이 크게 바뀌는 작업

새 response chain을 시작하거나 `current_turn`을 사용한다. 이전 reasoning이 새 목표와 무관하거나 잘못된 가정에 고정되어 있다면 이를 계속 유지하는 것이 오히려 방해가 될 수 있다.

### 긴 작업

고정된 turn 수만으로 Compaction을 실행하지 말고, input-context 성장과 남은 작업 길이를 기준으로 threshold를 정한다. Compaction 비용을 회수할 만큼 후속 turn이 남아 있어야 한다.

### 품질 우선 평가

다음 순서로 실험 결과를 판정한다.

1. 정확도, 안전성, 필수 constraint를 평가한다.
2. 사전에 정한 품질 게이트를 통과했는지 확인한다.
3. 통과한 arm 사이에서 latency와 비용을 비교한다.
4. 실패한 시도의 비용까지 포함한 `cost_per_success`를 계산한다.

### 관측해야 할 지표

- Input tokens
- Cached-input tokens
- Cache-write tokens
- Uncached-input tokens
- Output tokens
- Reasoning tokens
- End-to-end latency와 decision latency
- Retry와 tool-call error
- Quality score와 critical violation
- Total cost와 cost per successful task
- Effective reasoning context와 response ID chain
- Compaction 발생 turn과 cumulative break-even turn

### `store=false` 환경

`store=false`라고 retained reasoning을 포기할 필요는 없다. Opaque한 `reasoning.encrypted_content`를 포함한 전체 output item sequence를 순서대로 보존하고 다음 요청에 다시 전달할 수 있다.

Codex 소스 조사에서도 `store:false`, `reasoning.context: all_turns`, encrypted reasoning, 로컬 `ConversationHistory`를 조합하는 구현이 확인되었다. 조건이 맞는 WebSocket continuation에서는 `previous_response_id`와 incremental suffix를 사용하고, 그렇지 않으면 전체 logical input을 재생한다. 이는 `previous_response_id`가 retained reasoning의 유일한 구현 방식이 아니라는 점을 보여준다.

## OpenAI 공식 권장 사항과의 비교

### 일치하는 부분

이번 종합 메시지는 다음 공식 권장 사항과 일치한다.

- GPT-5.6에서는 `all_turns`가 기본 reasoning context다.
- 목표, 가정, 우선순위가 유지되는 작업에는 `all_turns`가 적합하다.
- 연속 호출은 `previous_response_id`로 연결할 수 있다.
- 이전 reasoning이 더 이상 관련 없으면 `current_turn` 또는 새 chain이 적합하다.
- 장기 workflow에는 Compaction을 사용해 유용한 상태를 보존하면서 context를 줄일 수 있다.
- 대표성 있는 workload와 최종 품질 기준으로 최적화 효과를 평가해야 한다.
- `store=false` 또는 ZDR 환경에서는 encrypted reasoning items를 수동으로 전달할 수 있다.

### 주의해서 표현해야 하는 부분

OpenAI의 ARC-AGI-3 사례는 retained reasoning과 Compaction을 사용했을 때 더 적은 재해석, 더 일관된 장기 전략, 높은 score, 적은 output tokens를 관찰했다. 이것은 해당 장기 게임 workload에서 얻은 강한 사례이지만 모든 workload에 대한 보장은 아니다.

이번 실험에서 재현된 범위는 다음과 같다.

- **재현됨:** 같은 목표가 이어질 때 reasoning tokens와 latency 감소
- **재현됨:** 긴 workflow에서 품질을 유지한 Compaction의 input-context 비용 회수
- **재현되지 않음:** Retained reasoning으로 인한 명확한 전략 학습 또는 paired 품질 향상
- **재현되지 않음:** Compaction으로 인한 reasoning/output/latency 감소
- **일반화할 수 없음:** 모든 workload에서의 총비용 절감률과 보편적인 Compaction threshold

## 최종 권장 메시지

> GPT-5.6에서 동일한 목표가 이어지는 agent workflow라면 retained reasoning을 기본으로 사용하라. 하지만 품질, reasoning, latency, 비용의 개선 폭은 workload에 따라 다르므로 각각 측정해야 한다. 장기 context에는 품질 게이트를 통과하는 범위에서 Compaction을 적용하고, Compaction 비용을 회수할 만큼 충분한 후속 작업이 있을 때만 비용 절감으로 평가하라.

Retained reasoning은 benchmark 결과가 좋을 때만 켜는 실험적 최적화라기보다 작업 연속성을 위한 권장 기본값이다. 반면 Compaction 시점과 비용 절감 주장은 workload별 실험으로 결정해야 한다.

## 근거 자료

### 이 프로젝트의 실험 자료

- [Notebook 02](../notebooks/02_retained_reasoning_all_turns_gpt_5_6.ipynb)
- [Notebook 02 detailed result interpretation](02_retained_reasoning_interpretation_20260829.md)
- [Notebook 03](../notebooks/03_compaction_break_even_gpt_5_6.ipynb)
- [Notebook 03 detailed result interpretation](03_compaction_break_even_interpretation_20260828.md)

### OpenAI 공식 자료

- [GPT-5.6 model guidance](https://developers.openai.com/api/docs/guides/latest-model)
- [Conversation state guide](https://developers.openai.com/api/docs/guides/conversation-state)
- [Compaction guide](https://developers.openai.com/api/docs/guides/compaction)
- [Responses API Compaction reference](https://developers.openai.com/api/reference/resources/responses/methods/compact)
- [Responses API Create Response reference](https://developers.openai.com/api/reference/cli/resources/responses/methods/create)
