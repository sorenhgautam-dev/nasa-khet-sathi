"""Owner decision F: FAOSTAT national yields for Nepal (rice, wheat, maize) from 2001, for validation
layer 4.3 only (year-to-year ups and downs). Never shown to farmers as mass per area (rule 11).
Rows below are SYNTHETIC, in FAOSTAT's normalized bulk-file layout."""
import csv
import io
import json
import zipfile
from pathlib import Path

import pytest

from pipeline.fetch import faostat as fs
from pipeline.fetch.guards import CARD_FIELDS, DataGuardError

HEADER = ["Area Code", "Area Code (M49)", "Area", "Item Code", "Item Code (CPC)", "Item", "Element Code",
          "Element", "Year Code", "Year", "Unit", "Value", "Flag", "Note"]


def _row(area=149, item=27, name="Rice", element="Yield", year=2001, unit="kg/ha", value=2700.0, flag="A"):
    return {"Area Code": str(area), "Area Code (M49)": "'524", "Area": "Nepal", "Item Code": str(item),
            "Item Code (CPC)": "'0113", "Item": name, "Element Code": "5412", "Element": element,
            "Year Code": str(year), "Year": str(year), "Unit": unit, "Value": str(value), "Flag": flag, "Note": ""}


ROWS = [
    _row(),
    _row(item=15, name="Wheat", value=2100.0),
    _row(item=56, name="Maize (corn)", value=1900.0, flag="E"),
    _row(year=2002, value=2650.0),
    _row(area=100, value=9999.0),                    # another country
    _row(element="Production", value=1.0),           # another element
    _row(item=44, name="Barley", value=1.0),         # another crop
    _row(year=2000, value=1.0),                      # before 2001
]


def test_keeps_nepal_rice_wheat_maize_yields_from_2001():
    df, _ = fs.parse(ROWS)
    assert sorted(map(tuple, df[["year", "crop"]].values.tolist())) == [
        (2001, "maize"), (2001, "rice"), (2001, "wheat"), (2002, "rice")]
    assert df.set_index(["year", "crop"]).loc[(2001, "rice"), "yield_kg_ha"] == 2700.0


def test_converts_hg_per_ha():
    df, _ = fs.parse([_row(unit="hg/ha", value=27000.0)])
    assert df["yield_kg_ha"].iloc[0] == pytest.approx(2700.0)


def test_unknown_unit_fails_loudly():
    with pytest.raises(DataGuardError, match="unit"):
        fs.parse([_row(unit="t/ha")])


def test_flags_are_kept_and_counted():
    df, info = fs.parse(ROWS)
    assert "flag" in df.columns and info["flags"] == {"A": 3, "E": 1}


def test_a_repeated_year_and_crop_fails():
    with pytest.raises(DataGuardError, match="repeated"):
        fs.parse([_row(), _row()])


def _zip(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=HEADER, quoting=csv.QUOTE_ALL)
    w.writeheader()
    w.writerows(rows)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr(fs.MEMBER, buf.getvalue().encode("latin-1"))
    return out.getvalue()


def test_fetch_reads_the_bulk_zip_and_writes_table_and_card(tmp_path):
    calls = []

    def fake(url):
        calls.append(url)
        return _zip(ROWS)

    out = fs.fetch({"id": "demo"}, data_dir=tmp_path, get_bytes=fake)
    assert Path(out["table"]) == tmp_path / "clean" / "demo" / "faostat_yields.parquet"
    card = json.loads(Path(out["card"]).read_text())
    assert set(CARD_FIELDS) <= set(card)
    fs.fetch({"id": "demo"}, data_dir=tmp_path, get_bytes=fake)
    assert len(calls) == 1
