"""scripts/make_review_pack.py gathers what exists, lists what is missing, and scans for secrets.
Clean tables and data cards live in per-field folders: data/clean/<field>/, data/cards/<field>/."""
import json
import zipfile

import pandas as pd

from scripts import make_review_pack as rp


def _fake_repo(tmp_path):
    (tmp_path / "data" / "cards" / "demo").mkdir(parents=True)
    (tmp_path / "data" / "cards" / "demo" / "power.json").write_text(json.dumps({"dataset": "power"}))
    (tmp_path / "data" / "clean" / "demo").mkdir(parents=True)
    pd.DataFrame({"date": pd.date_range("2001-01-01", periods=15), "rain_mm": range(15),
                  "tmax_c": [20.0] * 14 + [None]}).to_parquet(tmp_path / "data" / "clean" / "demo" / "power.parquet")
    (tmp_path / "data" / "checks" / "demo").mkdir(parents=True)
    (tmp_path / "data" / "checks" / "demo" / "layer3_power.json").write_text("{}")
    (tmp_path / "data" / "raw").mkdir(parents=True)
    (tmp_path / "data" / "raw" / "secret.nc").write_text("raw")
    (tmp_path / "DATA_AUDIT.md").write_text("# audit")
    return tmp_path


def test_pack_copies_cards_checks_and_audit(tmp_path):
    pack = rp.build(_fake_repo(tmp_path), run_tests=False)
    assert (pack / "cards" / "demo" / "power.json").is_file()
    assert (pack / "checks" / "demo" / "layer3_power.json").is_file()
    assert (pack / "DATA_AUDIT.md").is_file()


def test_pack_summarises_each_clean_table(tmp_path):
    pack = rp.build(_fake_repo(tmp_path), run_tests=False)
    head = pd.read_csv(pack / "clean_tables" / "demo__power_head.csv")
    summary = pd.read_csv(pack / "clean_tables" / "demo__power_summary.csv", index_col=0)
    assert len(head) == 10
    assert summary.loc["tmax_c", "missing"] == 1
    assert float(summary.loc["rain_mm", "max"]) == 14  # column mixes dates and numbers, reads back as text
    assert {"count", "min", "max", "mean", "missing"} <= set(summary.columns)


def test_pack_plots_each_variable_over_time(tmp_path):
    pack = rp.build(_fake_repo(tmp_path), run_tests=False)
    assert (pack / "timeseries" / "demo__power__rain_mm.png").is_file()


def test_pack_never_contains_raw_data(tmp_path):
    pack = rp.build(_fake_repo(tmp_path), run_tests=False)
    assert not any("raw" in p.parts for p in pack.rglob("*"))


def test_pack_lists_what_is_missing(tmp_path):
    pack = rp.build(_fake_repo(tmp_path), run_tests=False)
    missing = (pack / "MISSING.md").read_text()
    assert "config/crops.json" in missing and "config/rules.yaml" in missing


def test_secret_scan_reports_each_hit_with_file_and_line(tmp_path):
    (tmp_path / "a.txt").write_text("fine\nmy password is hunter2\n")
    (tmp_path / "b.json").write_text('{"api_key": "x"}')
    hits = rp.scan_for_secrets(tmp_path)
    assert ("a.txt", 2, "password") in [(h["file"], h["line"], h["word"]) for h in hits]
    assert any(h["file"] == "b.json" and h["word"] == "key" for h in hits)


def test_zip_contains_the_pack(tmp_path):
    pack = rp.build(_fake_repo(tmp_path), run_tests=False)
    z = rp.zip_pack(pack)
    with zipfile.ZipFile(z) as f:
        assert "review_pack/cards/demo/power.json" in f.namelist()
