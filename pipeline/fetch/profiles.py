"""Country profiles (owner's item 3, 2026-11-14: "global core, local plug-ins"): config/countries/<ISO2>.yaml holds what is
country-specific (rain classes, dry day and dry spell, gauge sources, crop-calendar zone, calendar system, language, area
units, fertiliser notes, drought seasons, the monsoon-onset rule); config/countries/default.yaml holds a sourced global
default for every one of them, used by a field in a country with no profile. Every setting is {value, source}, as in
config/rules.yaml, and a setting without a source is refused.

    from pipeline.fetch.profiles import profile_for
    p = profile_for(load_field("demo"))      # Nepal's: p["_id"] == "NP"
    p = profile_for(load_field("ambohidratrimo"))   # no Madagascar profile: p["_id"] == "default"

A field picks the profile whose `country.names` holds its config's `country`, or whose `country.iso2` is its config's
`country_code`. A country profile may leave a setting out: it then takes the default's (`_from` says which file gave it).
"""
from pathlib import Path

import yaml

from pipeline.fetch.rules import RulesError, _NoDuplicateKeys, _values

COUNTRIES = Path(__file__).resolve().parents[2] / "config" / "countries"
SETTINGS = ("country", "language", "calendar_system", "area_units", "rain_classes", "dry_day", "dry_spell",
            "drought_seasons", "monsoon_onset", "gauges", "crop_calendar", "fertiliser_notes", "scorecard")


class ProfileError(ValueError):
    pass


def _read(path):
    raw = yaml.load(Path(path).read_text(), Loader=_NoDuplicateKeys) or {}
    try:
        vals = _values(raw, ())
    except RulesError as e:
        raise ProfileError(f"{Path(path).name}: {e}") from e
    unknown = sorted(set(vals) - set(SETTINGS))
    if unknown:
        raise ProfileError(f"{Path(path).name}: unknown settings {unknown}; the settings are {list(SETTINGS)}")
    return vals


def load_profiles(countries=COUNTRIES):
    """{'default': values, '<ISO2>': values, ...}. The default must hold every setting; a country file only some."""
    out = {}
    for p in sorted(Path(countries).glob("*.yaml")):
        vals = _read(p)
        key = "default" if p.stem == "default" else vals.get("country", {}).get("iso2")
        if key != p.stem:
            raise ProfileError(f"{p.name}: the file name must be the country's ISO2 code ({key!r}) or 'default'")
        out[key] = vals
    if "default" not in out:
        raise ProfileError(f"no default.yaml in {countries}")
    missing = [s for s in SETTINGS if s not in out["default"]]
    if missing:
        raise ProfileError(f"default.yaml lacks {missing}: every setting needs a sourced global default")
    return out


def profile_id(field, profiles):
    """The ISO2 code of the field's country profile, or 'default'. Pure."""
    name, code = field.get("country"), field.get("country_code")
    for key, vals in profiles.items():
        c = vals.get("country") or {}
        if key != "default" and (code == c.get("iso2") or (name and name in (c.get("names") or []))):
            return key
    return "default"


def profile_for(field, countries=COUNTRIES):
    """The field's settings: its country's profile over the default. `_id` is the profile used, `_from` each setting's file."""
    profiles = load_profiles(countries)
    pid = profile_id(field, profiles)
    own = profiles[pid] if pid != "default" else {}
    out = {s: own.get(s, profiles["default"][s]) for s in SETTINGS}
    out["_id"] = pid
    out["_from"] = {s: (pid if s in own else "default") for s in SETTINGS}
    return out


def events_rules(field, rules, countries=COUNTRIES):
    """rules.yaml `events` with the drought seasons (and, for the default's annual total, its wet-day floor) of the
    field's profile. For a Nepal field this equals rules['events'] (tests/test_profiles.py)."""
    ds = profile_for(field, countries)["drought_seasons"]
    out = {**rules["events"], "seasons": {k: list(v) for k, v in ds["seasons"].items()}}
    if ds.get("wet_day_mm") is not None:
        out["wet_day_mm"] = float(ds["wet_day_mm"])
    return out


def has_onset_rule(field, countries=COUNTRIES):
    """True when the field's profile names a monsoon-onset rule (Nepal: rules.yaml monsoon_onset). Without one the diary's
    onset trend is not exported (diary.shift_days null: no onset rule for this country yet)."""
    return profile_for(field, countries)["monsoon_onset"] is not None
