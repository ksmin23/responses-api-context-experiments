import json
from pathlib import Path
 
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = sorted((PROJECT_ROOT / "pricing").glob("*.json"))
 
 
def test_pricing_snapshots_are_present_and_consistent() -> None:
    assert SNAPSHOTS, "No pricing snapshots found"
 
    for snapshot_path in SNAPSHOTS:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        assert snapshot["currency"] == "USD"
        assert snapshot["unit"] == "per_1m_tokens"
 
        for prices in snapshot["models"].values():
            expected_cache_write = prices["input"] * prices["cache_write_multiplier"]
            assert prices["cache_write_input"] == expected_cache_write
            assert prices["cached_input"] < prices["input"]
