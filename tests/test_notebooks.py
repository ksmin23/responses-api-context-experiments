import ast
import json
from pathlib import Path
from types import SimpleNamespace
 
import nbformat
import pytest
 
PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = sorted((PROJECT_ROOT / "notebooks").glob("*.ipynb"))
ARCHIVE_DIR = PROJECT_ROOT / "notebooks" / "archive"
 
 
def notebook_id(path: Path) -> str:
    return path.stem
 
 
def test_notebook_collection_is_not_empty() -> None:
    assert NOTEBOOKS, "No notebooks found in the notebooks directory"
 
 
@pytest.mark.parametrize("notebook_path", NOTEBOOKS, ids=notebook_id)
def test_notebook_is_valid_clean_and_compilable(notebook_path: Path) -> None:
    notebook = nbformat.read(notebook_path, as_version=4)
    nbformat.validate(notebook)
 
    cell_ids = [cell.id for cell in notebook.cells]
    assert len(cell_ids) == len(set(cell_ids)), "Notebook cell IDs must be unique"
 
    notebook_text = "\n".join(cell.source for cell in notebook.cells)
    assert "sk-" not in notebook_text, "Notebook must not contain an embedded API key"
    allow_stored_outputs = bool(
        notebook.metadata.get("responses_lab", {}).get("allow_stored_outputs")
    )
 
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type != "code":
            continue
        ast.parse(cell.source, filename=f"{notebook_path.name}:cell-{index}")
        if not allow_stored_outputs:
            assert cell.execution_count is None
            assert cell.outputs == []
 
 
def test_archived_02a_supports_one_kernel_full_experiment_sequence() -> None:
    notebook_path = ARCHIVE_DIR / "02a_retained_reasoning_partner_api_gpt_5_6.ipynb"
    notebook = nbformat.read(notebook_path, as_version=4)
    code_text = "\n".join(
        cell.source for cell in notebook.cells if cell.cell_type == "code"
    )
    notebook_text = "\n".join(cell.source for cell in notebook.cells)
 
    assert "RUN_ALL_EXPERIMENTS = False" in code_text
    assert "RUN_GRADER_CALIBRATION_ONLY = False" in code_text
    assert "RUN_PAIRED_PILOT_ONLY = False" in code_text
    assert "RUN_GRADER_CALIBRATION = (" in code_text
    assert "RUN_PAIRED_PILOT = (" in code_text
    assert "RUN_ALL_EXPERIMENTS or RUN_GRADER_CALIBRATION_ONLY" in code_text
    assert "RUN_ALL_EXPERIMENTS or RUN_PAIRED_PILOT_ONLY" in code_text
    assert "GRADER_SDK_MAX_RETRIES = 2" in code_text
    assert "client = OpenAI(api_key=load_api_key(), max_retries=" in code_text
    assert "grader_client = client.with_options(" in code_text
    assert "max_retries=GRADER_SDK_MAX_RETRIES" in code_text
    assert code_text.count("grader_client.responses.create(") == 2
    assert "GRADER_CALIBRATION_TRANSCRIPT" in code_text
    assert "semantic_grader_payload(" in code_text
    assert "semantic_grader_schema(allowed_event_ids)" in code_text
    assert "normalize_semantic_grade(parse_json_object(" in code_text
    assert "candidate_summary" not in code_text
    assert "CALIBRATION_SCHEMA" not in code_text
    assert "assert sum((RUN_GRADER_CALIBRATION, RUN_PAIRED_PILOT)) <= 1" not in code_text
    assert "restart the kernel" not in notebook_text.lower()
    assert notebook.cells.index(next(cell for cell in notebook.cells if cell.id == "calibration-code")) < notebook.cells.index(next(cell for cell in notebook.cells if cell.id == "benchmark-code"))
 
 
def test_archived_02a_persists_and_resumes_completed_pilot_runs() -> None:
    notebook_path = ARCHIVE_DIR / "02a_retained_reasoning_partner_api_gpt_5_6.ipynb"
    notebook = nbformat.read(notebook_path, as_version=4)
    code_text = "\n".join(
        cell.source for cell in notebook.cells if cell.cell_type == "code"
    )
    notebook_text = "\n".join(cell.source for cell in notebook.cells)
 
    assert 'PILOT_RESUME_PATH = None' in code_text
    assert 'GRADER_CALIBRATION_RESULTS_PATH = "latest"' in code_text
    assert 'grader-calibration-{run_id}.json' in code_text
    assert 'results-{run_id}.json' in code_text
    assert "def atomic_write_json(" in code_text
    assert "def persist_pilot_results(" in code_text
    assert "def append_failure_log(" in code_text
    assert "validate_pilot_resume_payload(" in code_text
    assert 'status="interrupted"' in code_text
    assert "completed_runs = {" in code_text
    assert "if run_key in completed_runs:" in code_text
    assert "skip completed trial=" in code_text
    assert "except BaseException as exc:" in code_text
    assert "pilot_failure_recovery_guidance(" in code_text
    assert 'error_code = error_body.get("code")' in code_text
    assert '"status_code": status_code' in code_text
    assert '"error_code": error_code' in code_text
    assert '"request_id": request_id' in code_text
    assert '"recovery_guidance": recovery_guidance' in code_text
    assert "final_input_items = build_action_budget_final_input(input_items)" in code_text
    assert "input_items=final_input_items" in code_text
    assert 'row["action_budget_exhausted"] = True' in code_text
    assert '"harness_version": PARTNER_API_HARNESS_VERSION' in code_text
    assert '"artifact_schema_version": 2' in code_text
    assert '"analysis_complete": False' in code_text
    assert '"expected_run_count"' in code_text
    assert '"completed_run_count"' in code_text
    assert "def build_interpretation(" in code_text
    assert "def finalize_pilot_artifact(" in code_text
    assert '"summary_rows": summary' in code_text
    assert '"paired_deltas": deltas' in code_text
    assert '"interpretation": interpretation' in code_text
    assert 'print("Final analysis saved:", pilot_artifact_path)' in code_text
    assert "PILOT_RESUME_PATH=\"latest\"" in notebook_text
    assert "interrupted unit starts" in notebook_text
    assert "employee_api_key_requires_corporate_network" in notebook_text
 
 
def test_archived_02b_support_policy_experiment_contract() -> None:
    notebook_path = ARCHIVE_DIR / "02b_retained_reasoning_support_policy_gpt_5_6.ipynb"
    notebook = nbformat.read(notebook_path, as_version=4)
    code_text = "\n".join(
        cell.source for cell in notebook.cells if cell.cell_type == "code"
    )
    notebook_text = "\n".join(cell.source for cell in notebook.cells)
 
    assert 'MODEL = "gpt-5.6"' in code_text
    assert 'SERVICE_TIER = "fast"' in code_text
    assert "MAX_TOOL_OUTPUT_TOKENS = 1_500" in code_text
    assert "MAX_FINAL_OUTPUT_TOKENS = 300" in code_text
    assert "service_tier=SERVICE_TIER" in code_text
    assert '"requested_service_tier": SERVICE_TIER' in code_text
    assert '"effective_service_tier"' in code_text
    assert "RUN_PAIRED_PILOT =" in code_text
    assert "PILOT_RESUME_PATH = None" in code_text
    assert 'reasoning_context": "current_turn"' in code_text
    assert 'reasoning_context": "all_turns"' in code_text
    assert "previous_response_id=previous_response_id" in code_text
    assert '"store": True' in code_text
    assert "def atomic_write_json(" in code_text
    assert "def persist_results(" in code_text
    assert "def resolve_resume_path(" in code_text
    assert "if run_key in completed_runs:" in code_text
    assert 'status="interrupted"' in code_text
    assert 'results-{run_id}.json' in code_text
    assert 'failures-{run_id}.jsonl' in code_text
    assert '"artifact_schema_version": 1' in code_text
    assert '"analysis_complete": False' in code_text
    assert "finalize_artifact(" in code_text
    assert "SupportPolicySimulator" in code_text
    assert "transfer_accuracy" in code_text
    assert "decision_reasoning_tokens" in code_text
    assert "require_completed_response(" in code_text
    assert "parse_tool_call(" in code_text
    assert '"solver_incomplete_reason"' in code_text
    assert "external scratchpad" in notebook_text
 
 
def test_archived_02b_reports_incomplete_tool_calls_before_json_parsing() -> None:
    notebook_path = ARCHIVE_DIR / "02b_retained_reasoning_support_policy_gpt_5_6.ipynb"
    notebook = nbformat.read(notebook_path, as_version=4)
    runner_cell = next(cell for cell in notebook.cells if cell.id == "runner-code")
    namespace = {"json": json}
    exec(runner_cell.source, namespace)
 
    response = SimpleNamespace(
        id="resp_incomplete",
        status="incomplete",
        incomplete_details=SimpleNamespace(reason="max_output_tokens"),
        output=[
            SimpleNamespace(
                type="function_call",
                name="submit_disposition",
                call_id="call_1",
                arguments="",
            )
        ],
    )
    error_type = namespace["SolverResponseContractError"]
    with pytest.raises(error_type, match="max_output_tokens") as captured:
        namespace["parse_tool_call"](response, "submit_disposition")
    assert captured.value.solver_response_id == "resp_incomplete"
    assert captured.value.solver_response_status == "incomplete"
    assert captured.value.solver_incomplete_reason == "max_output_tokens"
 
 
def test_02_retained_reasoning_blind_policy_experiment_contract() -> None:
    notebook_path = (
        PROJECT_ROOT
        / "notebooks"
        / "02_retained_reasoning_all_turns_gpt_5_6.ipynb"
    )
    notebook = nbformat.read(notebook_path, as_version=4)
    code_text = "\n".join(
        cell.source for cell in notebook.cells if cell.cell_type == "code"
    )
    notebook_text = "\n".join(cell.source for cell in notebook.cells)
 
    assert 'MODEL = "gpt-5.6"' in code_text
    assert 'SERVICE_TIER = "fast"' in code_text
    assert "RUN_PAIRED_PILOT = False" in code_text
    assert "PILOT_RESUME_PATH = None" in code_text
    assert "SupportPolicyV2Simulator" in code_text
    assert '"learning": 10' in code_text
    assert '"boundary": 8' in code_text
    assert '"evaluation": 20' in code_text
    assert '"candidate_parameterizations"] == 2_880' in code_text
    assert '"matching_behavior_signatures"] == 1' in code_text
    assert "ordered_tickets(" in code_text
    assert 'f"02b-v2:{scenario_id}:{trial}:{arm[\'name\']}"' in code_text
    assert "previous_response_id=previous_response_id" in code_text
    assert '"store": True' in code_text
    assert "service_tier=SERVICE_TIER" in code_text
    assert '"accepted": hidden_grade["accepted"]' in code_text
    assert "evaluation_accuracy" in code_text
    assert "strategy_consistency" in code_text
    assert "evaluation_decision_reasoning_delta" in code_text
    assert '"max_tool_output_tokens": MAX_TOOL_OUTPUT_TOKENS' in code_text
    assert 'ARTIFACT_DIR = PROJECT_ROOT / "artifacts" / "02_retained_reasoning"' in code_text
    assert "def atomic_write_json(" in code_text
    assert "def persist_results(" in code_text
    assert "if run_key in completed_runs:" in code_text
    assert 'status="interrupted"' in code_text
    assert "finalize_artifact(" in code_text
    assert "Blind evaluation" in notebook_text or "blind evaluation" in notebook_text
    assert "external scratchpad" in notebook_text
    assert "grader_client" not in code_text
