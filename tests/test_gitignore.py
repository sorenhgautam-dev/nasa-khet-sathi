"""The owner's single final commit must be safe: .gitignore keeps data and secrets out.

Uses `git check-ignore` in a throwaway repo in tmp_path (no commit is made anywhere)."""
import shutil
import subprocess
from pathlib import Path

import pytest

GITIGNORE = Path(__file__).resolve().parents[1] / ".gitignore"

MUST_IGNORE = ["data/raw/imerg.nc4", "data/clean/power.parquet", "data/cards/power.json", ".env",
               ".env.local", "robot/.env", ".netrc", "keys/server.pem", ".venv/bin/python",
               "pipeline/__pycache__/x.pyc", "review_pack.zip", "review_pack/DATA_AUDIT.md",
               # REVIEW_2 H7 and L7 (owner's answers 14 and 19, 2026-11-13): firmware and Firebase secrets, the live probe file
               "robot/firmware/khet_probe/secrets.h", "site/google-services.json", "serviceAccountKey.json",
               "keys/firebase-adminsdk-abc12.json", "site/data/live.json", "site/data/.live.json.tmp"]
MUST_KEEP = ["site/data/fields/demo.json", "site/data/index.json", "pipeline/export/schema.json",
             "config/crops.json", "records/credits.txt", "scripts/backup.sh", "README.md"]


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
