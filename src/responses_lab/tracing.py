"""Local-first tracing configuration shared by notebooks and scripts."""
 
from __future__ import annotations
 
import copy
import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any
 
from agents.tracing import set_trace_processors, set_tracing_disabled
from agents.tracing.processor_interface import TracingExporter
from agents.tracing.processors import (
    BackendSpanExporter,
    BatchTraceProcessor,
)
from dotenv import find_dotenv
 
 
DEFAULT_TRACE_RELATIVE_PATH = Path("traces/local_traces.jsonl")
_CONFIGURATION_LOCK = threading.Lock()
_ACTIVE_PROCESSORS: list[Any] = []
 
 
@dataclass(frozen=True)
class TracingSetup:
    """Result of configuring local-first trace routing."""
 
    local_path: Path
    openai_dashboard_enabled: bool
 
 
class LocalJSONLTraceExporter(TracingExporter):
    """Append traces and completed spans to a local JSON Lines file."""
 
    def __init__(self, path: str | Path, *, include_sensitive_data: bool = False):
        self.path = Path(path).expanduser().resolve()
        self.include_sensitive_data = include_sensitive_data
        self._lock = threading.Lock()
 
    def export(self, items) -> None:
        records = []
        for item in items:
            exported = item.export()
            if not exported:
                continue
            record = copy.deepcopy(exported)
            if not self.include_sensitive_data:
                self._remove_known_sensitive_fields(record)
            records.append(json.dumps(record, ensure_ascii=False, default=str))
 
        if not records:
            return
 
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self.path.open("a", encoding="utf-8") as trace_file:
            for record in records:
                trace_file.write(record + "\n")
 
    @staticmethod
    def _remove_known_sensitive_fields(record: dict[str, Any]) -> None:
        span_data = record.get("span_data")
        if not isinstance(span_data, dict):
            return
        span_data.pop("input", None)
        span_data.pop("output", None)
 
 
def default_local_trace_path() -> Path:
    """Return a project-relative trace path when .env.local can be located."""
    configured_path = os.getenv("OPENAI_LOCAL_TRACE_PATH")
    if configured_path:
        return Path(configured_path).expanduser().resolve()
 
    env_file = find_dotenv(filename=".env.local", usecwd=True)
    project_root = Path(env_file).parent if env_file else Path.cwd()
    return (project_root / DEFAULT_TRACE_RELATIVE_PATH).resolve()
 
 
def configure_tracing(
    *,
    local_path: str | Path | None = None,
    include_sensitive_data: bool = False,
) -> TracingSetup:
    """Route every trace locally and optionally mirror it to OpenAI.
 
    Local JSONL export is always enabled. OpenAI export is added only when
    OPENAI_TRACING_API_KEY is set. Using set_trace_processors replaces the
    SDK's default backend processor, so the model API key is never used for
    trace ingestion implicitly.
    """
    resolved_path = (
        Path(local_path).expanduser().resolve()
        if local_path is not None
        else default_local_trace_path()
    )
    processors = [
        BatchTraceProcessor(
            LocalJSONLTraceExporter(
                resolved_path,
                include_sensitive_data=include_sensitive_data,
            )
        )
    ]
 
    tracing_api_key = os.getenv("OPENAI_TRACING_API_KEY")
    if tracing_api_key:
        processors.append(
            BatchTraceProcessor(
                BackendSpanExporter(
                    api_key=tracing_api_key,
                    organization=(
                        os.getenv("OPENAI_TRACING_ORG_ID")
                        or os.getenv("OPENAI_ORG_ID")
                    ),
                    project=(
                        os.getenv("OPENAI_TRACING_PROJECT_ID")
                        or os.getenv("OPENAI_PROJECT_ID")
                    ),
                )
            )
        )
 
    global _ACTIVE_PROCESSORS
    with _CONFIGURATION_LOCK:
        for processor in _ACTIVE_PROCESSORS:
            shutdown = getattr(processor, "shutdown", None)
            if callable(shutdown):
                shutdown(timeout=5.0)
        set_trace_processors(processors)
        set_tracing_disabled(False)
        _ACTIVE_PROCESSORS = processors
 
    return TracingSetup(
        local_path=resolved_path,
        openai_dashboard_enabled=bool(tracing_api_key),
    )
