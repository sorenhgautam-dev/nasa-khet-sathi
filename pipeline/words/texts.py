"""Load, check and fill the plain-word files in pipeline/words/.

Pure functions apart from reading the JSON files next to this module and the two read-only inputs the
registry points at (pipeline/export/schema.json, config/crops.json, config/fields/*.yaml).

A *text node* is any JSON object with an "en" string: it must also carry "ne" (Devanagari) and
"ne_review", which is NE_REVIEW until a person has read the Nepali, then "reviewed by <name>, <YYYY-MM-DD>".
Placeholders are written {name}; the pipeline fills them (registry: fill_registry.json).
"""
import json
import re
from datetime import date
from functools import lru_cache
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SCHEMA_PATH = REPO / "pipeline" / "export" / "schema.json"
CROPS_PATH = REPO / "config" / "crops.json"
FIELDS_DIR = REPO / "config" / "fields"

WORD_FILES = ("screens", "tabs", "glossary", "crop_explainers")
NE_REVIEW = "needs native-speaker review"
REVIEWED = re.compile(r"reviewed by (?P<name>[^\[\]{}<>,]+), (?P<date>\d{4}-\d{2}-\d{2})")
MAX_WORDS_SCREEN = 8      # CLAUDE.md "Site rules": sentences of eight words or fewer
MAX_WORDS_GLOSSARY = 15   # Claude's choice: one plain sentence per term; the glossary is where science words live

PLACEHOLDER = re.compile(r"\{([a-z0-9_]+)\}")
NE_DIGITS = str.maketrans("0123456789", "०१२३४५६७८९")


class PlaceholderError(KeyError):
    """A text needs a value the caller did not supply."""


def is_review_mark(mark):
    """True for NE_REVIEW, or for "reviewed by <name>, <YYYY-MM-DD>" with a real name (not blank, no
    [template brackets]) and a real calendar date."""
    if mark == NE_REVIEW:
        return True
    m = REVIEWED.fullmatch(mark) if isinstance(mark, str) else None
    if not m or not m["name"].strip():
        return False
    try:
        date.fromisoformat(m["date"])
    except ValueError:
        return False
    return True


@lru_cache(maxsize=None)
def _load_cached(name):
    return json.loads((HERE / f"{name}.json").read_text(encoding="utf-8"))


def load(name):
    """One word file (screens, tabs, glossary, crop_explainers) or the fill registry."""
    return _load_cached(name)


def iter_text_nodes(obj, path=""):
    """Yield (path, node) for every object holding an English text."""
    if isinstance(obj, dict):
        if isinstance(obj.get("en"), str):
            yield path, obj
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                yield from iter_text_nodes(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from iter_text_nodes(v, f"{path}[{i}]")


def sentences(text, lang):
    """Split a text into sentences: . ! ? in English; the danda । and ? ! in Nepali."""
    ends = r"(?<=[.!?])\s+" if lang == "en" else r"(?<=[।?!])\s*"
    return [s.strip() for s in re.split(ends, text.strip()) if s.strip()]


def word_count(sentence):
    """Words in one sentence; a {placeholder} counts as one word, punctuation alone as none."""
    return sum(1 for tok in sentence.split() if re.search(r"[\w{]", tok))


def placeholders(text):
    return set(PLACEHOLDER.findall(text))


def _value(v, lang):
    if isinstance(v, dict):
        v = v[lang]
    s = str(v)
    return s.translate(NE_DIGITS) if lang == "ne" else s


def fill(node, values, lang):
    """The node's text in `lang` with every {placeholder} replaced. Names may be {"en":..,"ne":..}.
    Digits become Devanagari digits in Nepali. A missing value raises PlaceholderError."""
    text = node[lang]
    missing = sorted(placeholders(text) - set(values))
    if missing:
        raise PlaceholderError(f"no value for {', '.join(missing)} in {text!r}")
    return PLACEHOLDER.sub(lambda m: _value(values[m.group(1)], lang), text)


def render_tab(lines, conditions, values, lang):
    """Join the tab's sentences whose conditions all hold ("always" always holds). A line with
    "repeat": key is rendered once per entry of values[key]. If nothing is chosen, the fallback
    lines are used, so a tab is never empty."""
    held = set(conditions) | {"always"}
    out = []
    for line in lines:
        when = set(line["when"])
        if "fallback" in when or not when <= held:
            continue
        if "repeat" in line:
            out += [fill(line, {**values, **each}, lang) for each in values[line["repeat"]]]
        else:
            out.append(fill(line, values, lang))
    if not out:
        out = [fill(l, values, lang) for l in lines if "fallback" in l["when"]]
    return " ".join(out)


# ---------- science words ----------

def science_words():
    """Words that may appear only in the glossary: every term and alias, plus the extra lists."""
    g = load("glossary")
    en, ne = [], []
    for t in g["terms"]:
        en += [t["term"]["en"]] + t.get("aliases_en", [])
        ne += t.get("ne_block", [])
    en += g["never_on_screens"]["en"]
    ne += g["never_on_screens"]["ne"]
    return {"en": sorted(set(w.lower() for w in en)), "ne": sorted(set(ne))}


def science_hits(text, lang, words):
    """Science words found in a text (placeholders are skipped). English: whole words or phrases,
    any case, space or hyphen between words, an optional plural s. Nepali: any occurrence."""
    text = PLACEHOLDER.sub(" ", text)
    hits = []
    for w in words[lang]:
        if lang == "en":
            body = r"[\s-]+".join(re.escape(p) for p in re.split(r"[\s-]+", w))
            if re.search(rf"(?<![A-Za-z]){body}(?:s|es)?(?![A-Za-z])", text, re.IGNORECASE):
                hits.append(w)
        elif w in text:
            hits.append(w)
    return hits


# ---------- where each placeholder comes from ----------

@lru_cache(maxsize=None)
def _schema():
    return json.loads(SCHEMA_PATH.read_text())


def _deref(node, schema):
    """Follow $ref, and in "X or null" (anyOf with a null branch: a value that may be missing) take X."""
    while isinstance(node, dict) and ("$ref" in node or "anyOf" in node):
        if "$ref" in node:
            node = schema["$defs"][node["$ref"].split("/")[-1]]
        else:
            alts = [a for a in node["anyOf"] if a.get("type") != "null"]
            if len(alts) != 1:
                return node
            node = alts[0]
    return node


def _contract_path_exists(path):
    """'diary.bare_days', 'plans[].score.harvest', 'replay.*[].year' in pipeline/export/schema.json."""
    schema = _schema()
    node = schema
    for seg in path.split("."):
        is_array = seg.endswith("[]")
        name = seg[:-2] if is_array else seg
        node = _deref(node, schema)
        if name == "*":
            node = node.get("additionalProperties")
        else:
            node = node.get("properties", {}).get(name)
        if not isinstance(node, dict):
            return False
        node = _deref(node, schema)
        if is_array:
            node = node.get("items")
            if not isinstance(node, dict):
                return False
    return True


def _crops_path_exists(path):
    """'*.legume': the key is present on at least one crop in config/crops.json."""
    crops = json.loads(CROPS_PATH.read_text())["crops"]
    first, _, rest = path.partition(".")
    pool = list(crops.values()) if first == "*" else [crops.get(first)]
    return bool(rest) and any(_has_key(crop, rest) for crop in pool)


def _has_key(obj, dotted):
    for key in dotted.split("."):
        if not isinstance(obj, dict) or key not in obj:
            return False
        obj = obj[key]
    return True


def _field_key_exists(key):
    """A top-level key in at least one config/fields/*.yaml (its value may be null: not known yet)."""
    return any(key in (yaml.safe_load(p.read_text()) or {}) for p in FIELDS_DIR.glob("*.yaml"))


def _words_path_exists(path):
    name, _, rest = path.partition(".")
    if name not in WORD_FILES:
        return False
    return _has_key(load(name), rest)


def _code_name_exists(path):
    """'pipeline/twin/soil_water.py:run_bucket': the file exists and defines that name."""
    rel, _, name = path.rpartition(":")
    src = REPO / rel
    if not (rel and name and src.is_file()):
        return False
    return bool(re.search(rf"^(def|class)\s+{re.escape(name)}\b|^{re.escape(name)}\s*=", src.read_text(), re.M))


def resolve_ref(ref):
    """True if a registry 'from' reference points at something that exists:
    contract:<schema path> | crops:<crop or *>.<key> | field:<yaml key> | words:<file>.<key path>
    | code:<repo file>:<function>  (a value the twin computes but the contract does not carry)."""
    kind, _, path = ref.partition(":")
    try:
        return {"contract": _contract_path_exists, "crops": _crops_path_exists,
                "field": _field_key_exists, "words": _words_path_exists,
                "code": _code_name_exists}[kind](path)
    except KeyError:
        return False
