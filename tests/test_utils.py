from pathlib import Path
 
import pytest
 
from responses_lab.utils import load_api_key
 
 
def test_load_api_key_finds_env_file_in_parent_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env.local"
    env_file.write_text("OPENAI_API_KEY=test-key\n")
    nested_directory = tmp_path / "notebooks" / "nested"
    nested_directory.mkdir(parents=True)
    monkeypatch.chdir(nested_directory)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
 
    assert load_api_key() == "test-key"
 
 
def test_load_api_key_rejects_missing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
 
    with pytest.raises(FileNotFoundError, match="Could not find .env.local"):
        load_api_key()
 
 
def test_load_api_key_rejects_missing_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env.local"
    env_file.write_text("OTHER_SETTING=value\n")
    nested_directory = tmp_path / "notebooks"
    nested_directory.mkdir()
    monkeypatch.chdir(nested_directory)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
 
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is not set"):
        load_api_key()
