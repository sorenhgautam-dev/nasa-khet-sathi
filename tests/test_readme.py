"""README.md and LICENSE (owner review of d34fa93): the README covers what Khet Sathi is, the NASA data,
why there is no backend, how to run a new field, and the credits; every command it names exists; the code
is MIT-licensed and the README says data and text keep their own licences."""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _readme():
    return (REPO / "README.md").read_text()


def test_readme_has_the_five_parts_the_owner_asked_for():
    heads = [h.lower() for h in re.findall(r"^##\s+(.+)$", _readme(), flags=re.M)]
    for want in ("what", "nasa data", "no backend", "new field", "credits"):
        assert any(want in h for h in heads), f"no README section about '{want}'; sections: {heads}"


def test_every_command_in_the_readme_exists():
    text = _readme()
    mods = set(re.findall(r"python -m (pipeline(?:\.\w+)+)", text))
    scripts = set(re.findall(r"\b(scripts/[\w./-]+\.(?:py|sh))", text))
    assert mods and scripts, "the README should show how to run the pipeline"
    for m in sorted(mods):
        assert (REPO / (m.replace(".", "/") + ".py")).is_file(), f"README names {m}, which does not exist"
    for s in sorted(scripts):
        assert (REPO / s).is_file(), f"README names {s}, which does not exist"


def test_code_is_mit_and_the_readme_says_data_keep_their_own_licences():
    lic = (REPO / "LICENSE").read_text()
    assert lic.startswith("MIT License")
    assert "Permission is hereby granted, free of charge" in lic
    text = _readme()
    assert "LICENSE" in text and "records/credits.txt" in text
    assert re.search(r"data[^.]*own licen[cs]e", text, flags=re.I), "say that data and text keep their own licences"
