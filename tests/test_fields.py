"""config/fields/<id>.yaml loader."""
import pytest

from pipeline.fetch.fields import FieldConfigError, load_field


def test_demo_config_loads_with_the_claude_md_point():
    f = load_field("demo")
    assert (f["id"], f["lat"], f["lon"]) == ("demo", 27.67, 85.43)


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
