# OpenAI API model pricing

Checked: 2026-08-30 (Asia/Seoul)

Snapshot schema: `1.1.0`. Its `scope` metadata identifies these as OpenAI
Responses API text-token rates for Standard processing with at most 272K input
tokens. Fast and long-context adjustments are represented separately.

The notebooks use `gpt-5.6` and `gpt-5.6-luna`. The snapshot also includes
`gpt-5.6-terra` for direct comparison. The `gpt-5.6` alias routes to
`gpt-5.6-sol`.

## Standard pricing

Prices are USD per 1 million text tokens, for short-context requests (up to 272K input tokens).

| Notebook model | Underlying model | Input | Cached input | Cache write | Output |
|---|---|---:|---:|---:|---:|
| `gpt-5.6` | `gpt-5.6-sol` | $4.00 | $0.40 | $5.00 | $20.00 |
| `gpt-5.6-terra` | `gpt-5.6-terra` | $2.00 | $0.20 | $2.50 | $12.00 |
| `gpt-5.6-luna` | `gpt-5.6-luna` | $0.20 | $0.02 | $0.25 | $1.20 |

Cache writes cost 1.25× uncached input. Requests with more than 272K input tokens are charged, for the whole request, at 2× the short-context input/cached-input/cache-write price and 1.5× the short-context output price.

## Fast / Priority pricing

OpenAI renamed Priority processing to **Fast mode** on 2026-07-30. Both `service_tier: "priority"` and `service_tier: "fast"` remain accepted.

Fast mode costs 2× Standard for both models:

| Notebook model | Input | Cached input | Cache write | Output |
|---|---:|---:|---:|---:|
| `gpt-5.6` | $8.00 | $0.80 | $10.00 | $40.00 |
| `gpt-5.6-terra` | $4.00 | $0.40 | $5.00 | $24.00 |
| `gpt-5.6-luna` | $0.40 | $0.04 | $0.50 | $2.40 |

For long-context Fast requests, input-side prices are again 2× and output is
1.5× the short-context Fast price: `gpt-5.6` is $16.00 / $1.60 / $20.00 /
$60.00, `gpt-5.6-terra` is $8.00 / $0.80 / $10.00 / $36.00, and
`gpt-5.6-luna` is $0.80 / $0.08 / $1.00 / $3.60 (input / cached input /
cache write / output).

## Official sources

- [OpenAI API pricing](https://developers.openai.com/api/docs/pricing) — Standard, Batch, Flex, and Fast mode token rates; long-context rates; Priority-to-Fast rename.
- [GPT-5.6 Sol model page](https://developers.openai.com/api/docs/models/gpt-5.6-sol) — confirms that `gpt-5.6` aliases `gpt-5.6-sol`, Standard rates, long-context rule, cache-write rate, and promotional-price timing.
- [GPT-5.6 Terra model page](https://developers.openai.com/api/docs/models/gpt-5.6-terra) — Standard rates, long-context rule, and cache-write rate.
- [GPT-5.6 Luna model page](https://developers.openai.com/api/docs/models/gpt-5.6-luna) — Standard rates, long-context rule, and cache-write rate.

## Time-sensitive note

OpenAI states that GPT-5.6 Sol's current promotional pricing is available **at least through 2026-11-21**. Recheck the official pricing page before using these values after that date.
