# GPT-5.6 Retained Reasoning과 Compaction 실험에서 배운 점

## 결론

이번 실험에서 얻은 결과는 두 개의 제한된 workload와 실험 조건에서 관찰한 **lesson learned**다. 모든 agent workflow에서 동일한 품질·비용·지연시간 개선이 재현된다는 결론이 아니라, 유사한 작업을 설계하고 검증할 때 출발점으로 삼을 수 있는 경험적 근거로 해석해야 한다.

이번 실험을 통해 배운 점은 다음과 같다.

- Retained reasoning은 정확도나 비용을 자동으로 개선하는 옵션이라기보다, 같은 목표가 이어지는 작업에서 모델의 재해석 부담을 줄이는 연속성 메커니즘에 가깝다. Notebook 02에서는 `all_turns`가 품질을 유지하면서 reasoning tokens와 지연시간을 줄였지만, 명확한 정확도·전략 향상이나 유의미한 총비용 절감까지 입증하지는 못했다.
- Compaction은 즉시 지연시간을 낮추는 기능이 아니라, 길어지는 context의 반복 처리 비용을 줄이기 위해 선행 비용을 지불하는 방식이다. Notebook 03에서는 일부 threshold가 품질을 유지하며 비용을 절감했지만, 다른 threshold는 중요한 제약 조건을 위반했다. 따라서 적용 시점은 고정된 규칙이 아니라 품질 게이트와 손익분기점으로 판단해야 한다.
- 품질, reasoning tokens, 지연시간, input context와 총비용은 서로 독립적으로 움직일 수 있다. 하나의 지표가 개선됐다는 이유로 전체 효율성이 향상됐다고 일반화해서는 안 된다.

따라서 이번 결과와 유사한 연속형 workflow에서는 `all_turns + previous_response_id`를 우선 검토할 수 있다. 다만 이를 보편적인 정답으로 간주하지 말고, 대표성 있는 자체 workload에서 품질과 비용을 다시 측정해야 한다. 대화 context가 길어지는 경우에도 Compaction은 품질 게이트를 통과하고 후속 turn에서 비용을 회수할 수 있을 때만 채택하는 것이 이번 실험에서 얻은 실무적 교훈이다.

## 실험별 핵심 결과

| 관점 | Notebook 02 | Notebook 03 | 개발자에게 주는 의미 |
| --- | --- | --- | --- |
| 주요 treatment | `current_turn`과 `all_turns` 비교 | Compaction 없음과 Early/Middle/Late 비교 | Retained reasoning과 Compaction은 서로 다른 최적화 축이다. |
| Retained reasoning | `all_turns`가 같은 수준의 품질을 더 적은 reasoning으로 달성 | 모든 arm에서 `all_turns` 고정 | 같은 목표가 이어지면 reasoning context를 유지하는 것이 합리적이다. |
| 품질 향상 | 명확한 paired 품질 향상은 입증하지 못함 | Early/Late는 품질 유지, Middle은 품질 게이트 실패 | 품질 향상을 기본 전제로 삼으면 안 된다. |
| 지연시간 | `all_turns`에서 감소 | Compaction arm에서 증가 가능 | Retained reasoning과 Compaction이 지연시간에 미치는 영향은 다르다. |
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

> 같은 작업을 계속 수행할 때 retained reasoning을 사용하면 모델이 기존 상황을 다시 해석하는 데 사용하는 reasoning tokens와 지연시간을 줄일 수 있다.

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

Early에서는 누적 input tokens가 baseline보다 약 76%, Late에서는 약 45% 감소했다. 반면 output tokens, reasoning tokens와 지연시간은 증가했다.

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

Middle arm은 비용이 감소했어도 중요한 no-rollback 제약 조건을 위반했다. 따라서 비용 비교는 반드시 품질 게이트를 통과한 arm 사이에서만 수행해야 한다.

## 두 실험을 합친 해석

### 1. Retained reasoning은 단기 연속성 최적화다

같은 목표, 가정, 정책이 여러 tool call과 turn에 걸쳐 유지된다면 `all_turns`는 모델이 매번 상황을 재구성하는 부담을 줄일 수 있다. Notebook 02는 이 효과를 reasoning tokens와 지연시간에서 확인했다.

이 결과만으로 정확도나 총비용이 항상 개선된다고 주장해서는 안 된다. 특히 cached input, cache write, output, reasoning의 가격 비중에 따라 reasoning 감소가 전체 청구 비용에 미치는 영향은 작을 수 있다.

### 2. Compaction은 긴 작업에서 누적되는 context 비용을 줄인다

대화 context가 계속 성장하는 workflow에서는 retained reasoning만 유지하면 매 요청에서 처리되는 history가 커진다. Compaction은 이 장기 비용을 줄이지만 자체 호출 비용과 새 reasoning/output 비용을 발생시킨다.

따라서 Compaction은 고정 turn마다 무조건 실행하는 기능이 아니라 다음을 고려하는 threshold 정책이어야 한다.

- 현재 context 크기
- 예상되는 남은 turn 수
- Compaction 호출 및 cache-write 비용
- 최종 품질과 제약 조건 유지 여부
- Compaction 이후 누적 절감액

### 3. 품질, reasoning, 지연시간, 비용은 서로 다른 지표다

두 실험은 이 지표들이 같은 방향으로 움직이지 않을 수 있음을 보여준다.

- Notebook 02: reasoning과 지연시간은 크게 감소했지만 총비용은 거의 같았다.
- Notebook 03: input context와 총비용은 감소했지만 reasoning, output과 지연시간은 증가했다.

따라서 “토큰 감소”, “thinking time 감소”, “지연시간 감소”, “비용 감소”, “품질 향상”을 하나의 효율성 주장으로 묶어서는 안 된다.

## 관련 공개 자료와 이번 실험 결과의 비교

### 공개 문서에서 확인되는 운영 기준

OpenAI Docs의 [GPT-5.6 model guidance](https://developers.openai.com/api/docs/guides/latest-model), [Conversation state guide](https://developers.openai.com/api/docs/guides/conversation-state), [Compaction guide](https://developers.openai.com/api/docs/guides/compaction)에서는 다음과 같은 운영 기준을 확인할 수 있다.

- GPT-5.6은 `all_turns`를 기본 reasoning context로 사용한다. 여러 turn에 걸쳐 같은 작업을 계속하며 앞서 정한 목표, 전제와 우선순위를 다음 요청에서도 활용해야 한다면 `previous_response_id`로 호출을 연결한다. 반대로 새 작업으로 전환했거나 이전 reasoning이 더 이상 도움이 되지 않으면 `current_turn`을 사용하거나 새로운 response chain을 시작한다.
- 장기 workflow에서는 Compaction으로 증가하는 context를 관리할 수 있다.
- `store=false` 또는 ZDR 환경에서는 encrypted reasoning items를 다음 요청에 다시 전달할 수 있다.
- 각 설정의 효과는 실제 서비스에서 자주 발생하는 작업과 비슷한 테스트로 확인해야 한다. 먼저 결과가 정확하고 필수 조건을 지켰는지 확인한 뒤, 그 기준을 통과한 설정끼리 사용한 tokens, 지연시간과 비용을 비교한다.

이 내용은 기능의 사용 방법과 평가 기준에 관한 설명이며, 특정 workload의 정확도, 지연시간 또는 비용 개선을 보장하지 않는다. 이번 실험의 관찰값은 앞 절의 두 Notebook 결과를 기준으로 해석한다.

### 공개 사례와 비교할 때의 해석 범위

다음 비교는 결과의 보편성을 주장하기 위한 것이 아니라, 서로 다른 workload에서 관찰된 공통점과 차이점을 구분하기 위한 것이다.

- **공통점:** [ARC-AGI-3 사례 보고](https://openai.com/index/how-two-settings-tripled-our-arc-agi-3-scores/)와 이번 실험 모두 같은 목표가 이어지는 작업에서 재해석 부담을 줄일 수 있다는 신호를 관찰했다. 이번 실험에서는 이 신호가 reasoning tokens와 지연시간 감소로 나타났다.
- **차이점:** ARC-AGI-3 사례에서는 장기 전략의 일관성과 score 향상이 보고됐지만, 이번 실험에서는 명확한 전략 학습이나 paired 품질 향상을 확인하지 못했다. 또한 이번 실험의 Compaction은 input-context 비용을 줄였지만 reasoning, output과 지연시간까지 줄이지는 않았다.
- **해석의 한계:** 두 결과는 서로 다른 workload와 평가 조건에서 얻은 독립적인 관찰이다. 효과의 크기, 재현 가능성, 비용 절감률과 적절한 Compaction threshold는 다른 workload에 그대로 적용할 수 없다.

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

1. 정확도, 안전성, 필수 제약 조건을 평가한다.
2. 사전에 정한 품질 게이트를 통과했는지 확인한다.
3. 통과한 arm 사이에서 지연시간과 비용을 비교한다.
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

## 실무 적용 체크리스트

- 다음 turn에서도 같은 목표, 전제와 우선순위를 사용하는가?
- 이전 reasoning이 다음 판단에 실제로 도움이 되는가?
- 정확도와 필수 제약 조건을 먼저 검증했는가?
- Compaction 비용을 회수할 만큼 후속 작업이 남았는가?
- 품질 게이트를 통과한 설정끼리 지연시간과 비용을 비교했는가?
- 실패 비용을 포함한 `cost_per_success`를 계산했는가?

## 근거 자료

### 이 프로젝트의 실험 자료

- [Notebook 02](../notebooks/02_retained_reasoning_all_turns_gpt_5_6.ipynb)
- [Notebook 02 detailed result interpretation](02_retained_reasoning_interpretation_20260829.md)
- [Notebook 03](../notebooks/03_compaction_break_even_gpt_5_6.ipynb)
- [Notebook 03 detailed result interpretation](03_compaction_break_even_interpretation_20260828.md)

### OpenAI 공개 자료

#### 공식 문서

- [GPT-5.6 model guidance](https://developers.openai.com/api/docs/guides/latest-model)
- [Conversation state guide](https://developers.openai.com/api/docs/guides/conversation-state)
- [Compaction guide](https://developers.openai.com/api/docs/guides/compaction)
- [Responses API Compaction reference](https://developers.openai.com/api/reference/resources/responses/methods/compact)
- [Responses API Create Response reference](https://developers.openai.com/api/reference/cli/resources/responses/methods/create)

#### 사례 보고

- [How two settings tripled our ARC-AGI-3 scores (July 29, 2026)](https://openai.com/index/how-two-settings-tripled-our-arc-agi-3-scores/)
