"""config/rules.yaml: every threshold carries its value and its source (CLAUDE.md: never invent numbers)."""
import pytest
import yaml

from pipeline.fetch.rules import RULES_PATH, RulesError, load_rules


def _leaves(node, path=()):
    if isinstance(node, dict) and "value" in node:
        yield path, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from _leaves(v, path + (k,))


def test_every_rule_has_a_value_and_a_source():
    raw = yaml.safe_load(RULES_PATH.read_text())
    leaves = list(_leaves(raw))
    assert leaves
    for path, leaf in leaves:
        assert str(leaf.get("source", "")).strip(), f"{'.'.join(path)} has no source"


def test_loader_returns_plain_values():
    r = load_rules()
    assert r["rain_spike"]["min_mm"] == 50 and r["rain_spike"]["ratio"] == 5
    assert r["power_rain"]["never_fill_years"] == [2001, 2002, 2003]
    assert r["day_alignment"]["lags_days"] == [-1, 0, 1]


def test_a_rule_without_a_source_fails(tmp_path):
    p = tmp_path / "rules.yaml"
    p.write_text("x:\n  y: {value: 3}\n")
    with pytest.raises(RulesError, match="x.y"):
        load_rules(p)
