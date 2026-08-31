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

`reasoning.context=\
