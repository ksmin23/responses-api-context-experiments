# Responses API Context Experiments

This project contains reproducible Jupyter notebooks and reusable Python code
for experimenting with reasoning context, retained reasoning, response
continuation, and Compaction in the OpenAI Responses API.

## Project structure

```text
responses-api-context-experiments/
├── .env.local.example            # Template for local API credentials
├── docs/                         # Interpretations and developer guidance
├── fixtures/                     # Canonical deterministic fixtures
├── notebooks/                    # Ordered, executable examples
├── outputs/                      # Human-readable reports derived from saved artifacts
├── pricing/                      # Dated token-pricing snapshots
├── src/responses_lab/            # Python package shared by notebooks
├── tests/                        # Unit tests without network calls
├── artifacts/                    # Generated experiment results; excluded from Git
├── traces/                       # Local JSONL traces; excluded from Git
└── pyproject.toml                # Dependencies and test configuration
```

Name new notebooks sequentially, such as `notebooks/02_<topic>.ipynb`. Move logic used by more than one notebook into `src/responses_lab/`, and add corresponding tests under `tests/test_<module>.py`.

## Notebooks

- `01_responses_api_tutorial_gpt_5_6.ipynb` is a focused GPT-5.6 Responses API tutorial using a deterministic deployment-health workflow to demonstrate typed response items, `previous_response_id`, function calling, tool-result handling, protocol assertions, and Trace.
- `02_retained_reasoning_all_turns_gpt_5_6.ipynb` compares `current_turn` and `all_turns` with stored `previous_response_id` chaining across five paired Support Policy v2 profiles. Its labeled learning and boundary phases lead to a feedback-free blind evaluation, allowing quality, reasoning tokens, latency, and cost per success to be assessed separately. Compaction is reserved for Notebook 03.
- `03_compaction_break_even_gpt_5_6.ipynb` keeps `all_turns`, `previous_response_id`, Fast mode, and tool-output representation fixed while comparing no Compaction with calibrated early, middle, and late Compaction thresholds over a 30-turn invoice-reconciliation investigation. It records the effective service tier and reports Fast-priced, quality-gated, sustained cumulative-cost break-even. See the [August 28 experiment result interpretation](docs/03_compaction_break_even_interpretation_20260828.md) for the saved run's metadata, evidence, and limitations.

For a combined interpretation of the Notebook 02 retained-reasoning results and the Notebook 03 Compaction break-even results, including developer recommendations and comparison with OpenAI's official guidance, see [GPT-5.6 Retained Reasoning and Compaction: Developer Guidance](docs/retained_reasoning_developer_guidance_20260829.md).

Human-readable reports generated from saved JSON artifacts are stored under
`outputs/`. See the [Notebook 02 result report](outputs/02_retained_reasoning_results_20260829.md)
and [Notebook 03 experiment report](outputs/03_compaction_break_even_experiment_report_20260828.md).
These reports use stored results and do not re-run the API.

## Setup

Store your API key in `.env.local` at the project root.

```dotenv
OPENAI_API_KEY=your-key-here

# Optional: mirror local traces to the OpenAI Trace Dashboard
OPENAI_TRACING_API_KEY=your-tracing-key-here
# OPENAI_TRACING_ORG_ID=org_...
# OPENAI_TRACING_PROJECT_ID=proj_...
# OPENAI_LOCAL_TRACE_PATH=/absolute/path/to/local_traces.jsonl
```

Install the dependencies and start JupyterLab.

```bash
uv sync
uv run jupyter lab
```

Open a notebook under `notebooks/` in JupyterLab. It will use the project's `.venv` environment and the package under `src/`.

Tracing is local-first. `configure_tracing()` from `src/responses_lab/tracing.py` appends every trace and completed span to `traces/local_traces.jsonl`; the directory is excluded from Git. The shared function can be reused by future notebooks and scripts.

When `OPENAI_TRACING_API_KEY` is set, the same trace is also mirrored to the [OpenAI Traces dashboard](https://platform.openai.com/traces). This key must belong to a policy-approved project that permits trace ingestion; ZDR projects reject it. `OPENAI_TRACING_ORG_ID` and `OPENAI_TRACING_PROJECT_ID` can disambiguate the destination when needed.

Known generation input and output fields are omitted from local JSONL by default, while usage, timing, IDs, and custom span metadata remain available. Avoid placing secrets or prompt content in custom span metadata. Pass `include_sensitive_data=True` to `configure_tracing()` only when local capture of generation input/output is intentional and permitted.

Cost estimates use the dated JSON snapshot under `pricing/`. Treat each snapshot as point-in-time reference data rather than a live price feed; its official source URLs and any derived rates are recorded in the file.

Runtime results are stored under `artifacts/`. Newly generated files are ignored
by Git. The notebooks recreate the required subdirectories when their live
experiment stages run:

- Retained-reasoning results: `artifacts/02_retained_reasoning/`
- Compaction results and accepted calibration records: `artifacts/03_compaction/`

## Testing

```bash
uv run pytest
```

The unit tests do not call the OpenAI API. Running a notebook end to end consumes API usage, so do so only when explicitly needed.

## References

### Responses API and stateful tool use

- [GPT-5.6 model guidance](https://developers.openai.com/api/docs/guides/latest-model) — model-specific guidance for retained reasoning and `reasoning.context`.
- [Conversation state](https://developers.openai.com/api/docs/guides/conversation-state) — stateful continuation with `previous_response_id`.
- [Function calling](https://developers.openai.com/api/docs/guides/function-calling) — the tool-call and `function_call_output` loop used by the notebooks.
- [Reasoning models](https://developers.openai.com/api/docs/guides/reasoning) — reasoning behavior, token budgeting, and context considerations.

### Compaction, execution, and evaluation

- [Compaction](https://developers.openai.com/api/docs/guides/compaction) — `context_management`, Compaction items, and long-running response chains.
- [Fast mode](https://developers.openai.com/api/docs/guides/fast-mode) — the processing mode held fixed in the paired experiments.
- [GPT-5.6 model limits](https://developers.openai.com/api/docs/models/gpt-5.6) — task-model capabilities and limits used by the experiments.
- [GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna) — evaluator model used by the Compaction benchmark.
- [Grader Models API](https://developers.openai.com/api/reference/ruby/resources/graders/subresources/grader_models) — semantic grading used for benchmark calibration and quality gates.

## Related Projects

- [explicit-prompt-caching-demo](https://github.com/ksmin23/explicit-prompt-caching-demo) — notebook experiments measuring implicit and explicit prompt caching, cache reads and writes, and latency with the Responses API.
- [tool-search-prompt-caching-benchmarks](https://github.com/ksmin23/tool-search-prompt-caching-benchmarks) — benchmarks comparing eager tool loading with hosted tool search and explicit prompt caching across tool catalog sizes.
- [direct-vs-programmatic-tool-calling](https://github.com/ksmin23/direct-vs-programmatic-tool-calling) — benchmarks comparing Direct and Programmatic Tool Calling on deterministic workflows, measuring quality, token usage, latency, and estimated cost.
