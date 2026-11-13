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


class _NoDuplicateKeys(yaml.SafeLoader):
    """YAML silently keeps the last of two equal keys; a rules file must never do that (2026-11-13: a repeated
    'groundwater' block replaced the owner's GRACE rules)."""


def _mapping(loader, node, deep=False):
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise RulesError(f"rules file repeats the key '{key}' (line {key_node.start_mark.line + 1})")
        seen.add(key)
    return loader.construct_mapping(node, deep=deep)


_NoDuplicateKeys.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def load_rules(path=RULES_PATH):
    return _values(yaml.load(Path(path).read_text(), Loader=_NoDuplicateKeys) or {}, ())
