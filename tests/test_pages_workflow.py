"""GitHub Pages publishes only the repository root or /docs from a branch, so a GitHub Actions workflow
publishes site/ (owner review of d34fa93, item 5: the simpler choice; nothing moves). It must publish
site/ and nothing else (data/ and the pipeline stay out), on pushes to main or by hand, with the
permissions deploy-pages needs."""
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
WF = REPO / ".github" / "workflows" / "pages.yml"


def _wf():
    doc = yaml.safe_load(WF.read_text())
    doc["on"] = doc.get("on", doc.pop(True, None))   # PyYAML reads the bare key `on` as True
    return doc


def _steps(doc):
    return [s for job in doc["jobs"].values() for s in job["steps"]]


def test_workflow_publishes_the_site_folder_only():
    up = [s for s in _steps(_wf()) if s.get("uses", "").startswith("actions/upload-pages-artifact@")]
    assert len(up) == 1, "exactly one Pages artifact upload"
    assert up[0]["with"]["path"].rstrip("/") == "site"


def test_workflow_runs_on_main_and_by_hand_and_deploys():
    doc = _wf()
    assert doc["on"]["push"]["branches"] == ["main"]
    assert "workflow_dispatch" in doc["on"]
    assert doc["permissions"] == {"contents": "read", "pages": "write", "id-token": "write"}
    assert any(s.get("uses", "").startswith("actions/deploy-pages@") for s in _steps(doc))
    deploy = next(j for j in doc["jobs"].values() if any("deploy-pages" in s.get("uses", "") for s in j["steps"]))
    assert deploy["environment"]["name"] == "github-pages"
