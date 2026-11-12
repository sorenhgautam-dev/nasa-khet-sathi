"""Load config/rules.yaml: returns plain values; refuses any entry without a source."""
from pathlib import Path

import yaml

RULES_PATH = Path(__file__).resolve().parents[2] / "config" / "rules.yaml"


class RulesError(ValueError):
    pass


def _values(node, path):
    if isinstance(node, dict) and "value" in node:
        if not str(node.get("source", "")).strip():
            raise RulesError(f"rule {'.'.join(path)} has no source")
        return node["value"]
    if isinstance(node, dict):
        return {k: _values(v, path + (k,)) for k, v in node.items()}
    raise RulesError(f"rule {'.'.join(path)} must be a mapping with value and source")


def load_rules(path=RULES_PATH):
    return _values(yaml.safe_load(Path(path).read_text()) or {}, ())
