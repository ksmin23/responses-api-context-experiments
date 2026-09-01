import ast
from pathlib import Path
 
import nbformat
import pytest
 
PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = sorted((PROJECT_ROOT / "notebooks").glob("*.ipynb"))
 
 
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
