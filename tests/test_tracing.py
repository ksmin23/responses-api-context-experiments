import json
from pathlib import Path
 
import responses_lab.tracing as tracing_module
from responses_lab.tracing import LocalJSONLTraceExporter, default_local_trace_path
 
 
class FakeTraceItem:
    def __init__(self, payload):
        self.payload = payload
 
    def export(self):
        return self.payload
 
 
def test_local_exporter_redacts_known_sensitive_fields(tmp_path: Path) -> None:
    trace_path = tmp_path / "traces.jsonl"
    exporter = LocalJSONLTraceExporter(trace_path)
    exporter.export(
        [
            FakeTraceItem(
                {
                    "object": "trace.span",
                    "span_data": {
                        "type": "generation",
                        "input": "private prompt",
                        "output": "private answer",
                        "usage": {"input_tokens": 10, "output_tokens": 4},
                    },
                }
            )
        ]
    )
 
    record = json.loads(trace_path.read_text(encoding="utf-8"))
    assert "input" not in record["span_data"]
    assert "output" not in record["span_data"]
    assert record["span_data"]["usage"]["input_tokens"] == 10
 
 
def test_local_exporter_can_include_sensitive_fields(tmp_path: Path) -> None:
    trace_path = tmp_path / "traces.jsonl"
    exporter = LocalJSONLTraceExporter(trace_path, include_sensitive_data=True)
    exporter.export(
        [FakeTraceItem({"span_data": {"input": "prompt", "output": "answer"}})]
    )
 
    record = json.loads(trace_path.read_text(encoding="utf-8"))
    assert record["span_data"]["input"] == "prompt"
    assert record["span_data"]["output"] == "answer"
 
 
def test_default_path_uses_explicit_environment_path(monkeypatch, tmp_path: Path) -> None:
    expected = tmp_path / "custom.jsonl"
    monkeypatch.setenv("OPENAI_LOCAL_TRACE_PATH", str(expected))
    assert default_local_trace_path() == expected.resolve()
 
 
def test_configure_tracing_is_local_only_without_tracing_key(
    monkeypatch, tmp_path: Path
) -> None:
    captured = {}
    monkeypatch.delenv("OPENAI_TRACING_API_KEY", raising=False)
    monkeypatch.setattr(
        tracing_module,
        "set_trace_processors",
        lambda processors: captured.update(processors=processors),
    )
    monkeypatch.setattr(
        tracing_module,
        "set_tracing_disabled",
        lambda disabled: captured.update(disabled=disabled),
    )
 
    setup = tracing_module.configure_tracing(local_path=tmp_path / "local.jsonl")
 
    assert len(captured["processors"]) == 1
    assert captured["disabled"] is False
    assert setup.openai_dashboard_enabled is False
 
 
def test_configure_tracing_adds_openai_backend_when_key_is_present(
    monkeypatch, tmp_path: Path
) -> None:
    captured = {}
    backend_arguments = {}
 
    class FakeBackendExporter:
        def __init__(self, **kwargs):
            backend_arguments.update(kwargs)
 
    class FakeBatchProcessor:
        def __init__(self, exporter):
            self.exporter = exporter
 
    monkeypatch.setenv("OPENAI_TRACING_API_KEY", "test-tracing-key")
    monkeypatch.setenv("OPENAI_TRACING_PROJECT_ID", "project-for-traces")
    monkeypatch.setattr(tracing_module, "BackendSpanExporter", FakeBackendExporter)
    monkeypatch.setattr(tracing_module, "BatchTraceProcessor", FakeBatchProcessor)
    monkeypatch.setattr(
        tracing_module,
        "set_trace_processors",
        lambda processors: captured.update(processors=processors),
    )
    monkeypatch.setattr(tracing_module, "set_tracing_disabled", lambda disabled: None)
 
    setup = tracing_module.configure_tracing(local_path=tmp_path / "local.jsonl")
 
    assert len(captured["processors"]) == 2
    assert backend_arguments["api_key"] == "test-tracing-key"
    assert backend_arguments["project"] == "project-for-traces"
    assert setup.openai_dashboard_enabled is True
 
 
def test_reconfigure_shuts_down_previous_processors(monkeypatch, tmp_path: Path) -> None:
    shutdown_timeouts = []
 
    class FakeBatchProcessor:
        def __init__(self, exporter):
            self.exporter = exporter
 
        def shutdown(self, timeout=None):
            shutdown_timeouts.append(timeout)
 
    monkeypatch.delenv("OPENAI_TRACING_API_KEY", raising=False)
    monkeypatch.setattr(tracing_module, "BatchTraceProcessor", FakeBatchProcessor)
    monkeypatch.setattr(tracing_module, "set_trace_processors", lambda processors: None)
    monkeypatch.setattr(tracing_module, "set_tracing_disabled", lambda disabled: None)
 
    tracing_module.configure_tracing(local_path=tmp_path / "first.jsonl")
    tracing_module.configure_tracing(local_path=tmp_path / "second.jsonl")
 
    assert shutdown_timeouts[-1] == 5.0
