"""mock.py writes a valid demo field and index so the UI teammate can build against the contract."""
import json

from pipeline.export import mock
from pipeline.export.validate import main as validate_main


def test_write_all_creates_field_and_index(tmp_path):
    mock.write_all(tmp_path)
    assert (tmp_path / "fields" / "demo.json").is_file()
    assert (tmp_path / "index.json").is_file()


def test_written_files_validate_through_the_cli(tmp_path):
    mock.write_all(tmp_path)
    assert validate_main(["--data-dir", str(tmp_path)]) == 0


def test_cli_fails_when_index_lists_a_field_with_no_file(tmp_path):
    mock.write_all(tmp_path)
    index = json.loads((tmp_path / "index.json").read_text())
    index["fields"].append({"id": "kenya", "name": "Kenya field", "country": "Kenya",
                            "lat": 0.5, "lon": 37.5, "bbox": [37.4, 0.4, 37.6, 0.6]})
    (tmp_path / "index.json").write_text(json.dumps(index))
    assert validate_main(["--data-dir", str(tmp_path)]) == 1


def test_cli_fails_when_field_sits_outside_its_index_bbox(tmp_path):
    mock.write_all(tmp_path)
    field = json.loads((tmp_path / "fields" / "demo.json").read_text())
    field["field"]["lat"] = 28.5
    (tmp_path / "fields" / "demo.json").write_text(json.dumps(field))
    assert validate_main(["--data-dir", str(tmp_path)]) == 1


def test_mock_is_labelled_so_it_cannot_pass_for_real_data():
    d = mock.build_field()
    assert "MOCK" in d["field"]["name"]
    assert all("MOCK" in s["name"] for s in d["sources"])
    assert all(t.startswith("MOCK") for p in d["plans"] for t in p["tabs"].values())


def test_index_uses_the_demo_bbox_from_claude_md():
    (entry,) = mock.build_index()["fields"]
    assert entry["id"] == "demo"
    assert entry["bbox"] == [85.42, 27.66, 85.44, 27.68]


def test_mock_has_current_plus_two_plans_with_full_replay():
    d = mock.build_field()
    ids = [p["id"] for p in d["plans"]]
    assert ids[0] == "current" and len(ids) == 3
    for pid in ids:
        assert [r["year"] for r in d["replay"][pid]] == list(range(2001, 2026))


def test_mock_future_gives_a_range_around_each_value():
    for series in mock.build_field()["future"].values():
        if isinstance(series, dict):
            for lo, mid, hi in zip(series["harvest_low"], series["harvest"], series["harvest_high"]):
                assert lo <= mid <= hi and lo < hi


def test_mock_has_groundwater():
    gw = mock.build_field()["diary"]["groundwater"]
    assert set(gw) == {"trend_cm_per_year", "direction", "confidence"}


def test_mock_sections_aim_for_ten_to_forty():
    assert 10 <= len(mock.build_field()["field"]["sections"]) <= 40
