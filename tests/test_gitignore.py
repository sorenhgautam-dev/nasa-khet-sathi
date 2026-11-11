"""The owner's single final commit must be safe: .gitignore keeps data and secrets out.

Uses `git check-ignore` in a throwaway repo in tmp_path (no commit is made anywhere)."""
import shutil
import subprocess
from pathlib import Path

import pytest

GITIGNORE = Path(__file__).resolve().parents[1] / ".gitignore"

MUST_IGNORE = ["data/raw/imerg.nc4", "data/clean/power.parquet", "data/cards/power.json", ".env",
               ".env.local", "robot/.env", ".netrc", "keys/server.pem", ".venv/bin/python",
               "pipeline/__pycache__/x.pyc", "review_pack.zip", "review_pack/DATA_AUDIT.md"]
MUST_KEEP = ["site/data/fields/demo.json", "site/data/index.json", "pipeline/export/schema.json",
             "config/crops.json", "CREDITS.md", "scripts/backup.sh", "requirements.txt"]


@pytest.fixture(scope="module")
def ignored(tmp_path_factory):
    if shutil.which("git") is None:
        pytest.skip("git not installed")
    repo = tmp_path_factory.mktemp("gitcheck")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    shutil.copy(GITIGNORE, repo / ".gitignore")
    paths = MUST_IGNORE + MUST_KEEP
    res = subprocess.run(["git", "-C", str(repo), "check-ignore", "--no-index", *paths],
                         capture_output=True, text=True)
    return set(res.stdout.split())


@pytest.mark.parametrize("path", MUST_IGNORE)
def test_ignored(ignored, path):
    assert path in ignored


@pytest.mark.parametrize("path", MUST_KEEP)
def test_kept(ignored, path):
    assert path not in ignored
