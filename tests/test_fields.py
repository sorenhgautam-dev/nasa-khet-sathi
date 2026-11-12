"""config/fields/<id>.yaml loader."""
import pytest

from pipeline.fetch.fields import FieldConfigError, load_field


def test_demo_is_a_labelled_placeholder_inside_the_box_around_the_old_point():
    """Owner, 2026-11-12: 27.67 N, 85.43 E is Bhaktapur's old city, so it is only the box centre."""
    f = load_field("demo")
    assert f["id"] == "demo" and f["placeholder"] is True and "PLACEHOLDER" in f["name"]
    assert (f["origin_point"]["lat"], f["origin_point"]["lon"]) == (27.67, 85.43)
    assert (f["lat"], f["lon"]) != (27.67, 85.43)
    b = f["fetch_box"]
    assert b[0] < f["lon"] < b[2] and b[1] < f["lat"] < b[3] and f["bbox"] == b
    assert len(f["polygon"]) == 4 and all(b[0] < x < b[2] and b[1] < y < b[3] for x, y in f["polygon"])
    assert f["current_rotation"] == ["rice", "potato"] and "PLACEHOLDER" in f["current_rotation_source"]


def _write(tmp_path, text, name="x"):
    (tmp_path / f"{name}.yaml").write_text(text)
    return tmp_path


def test_missing_lat_fails(tmp_path):
    with pytest.raises(FieldConfigError, match="lat"):
        load_field("x", _write(tmp_path, "id: x\nlon: 85.4\n"))


def test_id_must_match_the_file_name(tmp_path):
    with pytest.raises(FieldConfigError, match="id"):
        load_field("x", _write(tmp_path, "id: y\nlat: 27.6\nlon: 85.4\n"))


def test_lat_out_of_range_fails(tmp_path):
    with pytest.raises(FieldConfigError, match="lat"):
        load_field("x", _write(tmp_path, "id: x\nlat: 127.6\nlon: 85.4\n"))


def test_unknown_field_fails_clearly(tmp_path):
    with pytest.raises(FieldConfigError, match="nope"):
        load_field("nope", tmp_path)
