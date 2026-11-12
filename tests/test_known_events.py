"""Owner decision E: a sourced list of documented drought, flood and frost years for the Kathmandu
valley and central Nepal since 2001 (validation layer 4.1). Every confirmed event cites at least one
opened source; anything unsourced is TODO-VERIFY."""
from pathlib import Path

import yaml

PATH = Path(__file__).resolve().parents[1] / "config" / "known_events.yaml"
CATEGORIES = {"drought", "flood", "frost"}
KV = {"yes", "partly", "indirect", "no", "not_stated"}


def _load():
    return yaml.safe_load(PATH.read_text())


def test_every_confirmed_event_is_complete_and_sourced():
    events = _load()["events"]
    assert len(events) >= 8
    ids = [e["id"] for e in events]
    assert len(ids) == len(set(ids))
    for e in events:
        assert e["category"] in CATEGORIES, e["id"]
        assert e["kathmandu_valley"] in KV, e["id"]
        assert e["years"] and all(2001 <= y <= 2025 for y in e["years"]), e["id"]
        assert e["summary"].strip(), e["id"]
        assert e["sources"], e["id"]
        for s in e["sources"]:
            assert s["url"].startswith("http") and s["title"].strip(), e["id"]


def test_the_owner_named_events_are_present():
    events = {e["id"]: e for e in _load()["events"]}
    assert events["winter_drought_2008_09"]["category"] == "drought"
    assert events["kathmandu_floods_2024_09"]["kathmandu_valley"] == "yes"


def test_unconfirmed_items_are_marked_todo_verify_with_a_reason():
    for u in _load()["unconfirmed"]:
        assert u["status"] == "TODO-VERIFY" and u["reason"].strip()


def test_negative_controls_are_sourced():
    for n in _load()["negative_controls"]:
        assert n["sources"] and all(s["url"].startswith("http") for s in n["sources"])


def test_the_2010_cold_night_checks_the_frost_band_not_the_replay():
    """Owner, 2026-11-12: Kathmandu -0.2 C on 12 Jan 2010 is a check for the frost risk band (January 2010
    should show high frost risk), not a replay event."""
    e = {x["id"]: x for x in _load()["events"]}["cold_night_2010_01"]
    assert e["category"] == "frost" and e["years"] == [2010]
    assert e["check"] == "frost_risk_band" and e["expect"] == {"month": "2010-01", "frost": "high"}
    assert e["replay_event"] is False


def test_excluded_items_carry_the_owners_reason():
    ex = {x["item"]: x for x in _load()["excluded"]}
    jure = next(v for k, v in ex.items() if "Jure" in k)
    assert "owner" in jure["reason"].lower() and "landslide" in jure["reason"]
    assert not any("Jure" in u["item"] for u in _load()["unconfirmed"])
    assert not any("-0.2 C on 12 Jan 2010" in u["item"] for u in _load()["unconfirmed"])
