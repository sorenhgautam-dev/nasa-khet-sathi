"""Owner decision H: before the repository goes public, scan EVERY commit (not just current files) for
keys, tokens, passwords, .netrc and .env. These tests build throwaway git repos in tmp_path.
Secret-looking strings are assembled at run time so this file itself never matches the scan."""
import subprocess

import pytest

from scripts import scan_history as sh

PW = "pass" + "word = " + "hunter2hunter2"
GH_TOKEN = "gh" + "o_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"


def _git(repo, *args):
    subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid",
                    "-c", "commit.gpgsign=false", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "README.md").write_text("hello\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "first")
    return tmp_path


def _commit(repo, path, text=None, delete=False):
    p = repo / path
    if delete:
        p.unlink()
    else:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", f"change {path}")


def test_clean_history_has_no_hits(repo):
    r = sh.scan(repo)
    assert r["content_hits"] == [] and r["file_hits"] == [] and r["commits_scanned"] == 1


def test_finds_a_password_deleted_in_a_later_commit(repo):
    _commit(repo, "config.txt", PW + "\n")
    _commit(repo, "config.txt", delete=True)
    hits = sh.scan(repo)["content_hits"]
    assert len(hits) == 1 and hits[0]["file"] == "config.txt" and hits[0]["kind"] == "assignment"
    assert len(hits[0]["commit"]) == 40


def test_finds_a_known_token_format(repo):
    _commit(repo, "x.py", f"T = '{GH_TOKEN}'\n")
    assert any(h["kind"] == "github token" for h in sh.scan(repo)["content_hits"])


def test_finds_env_and_netrc_files_ever_committed(repo):
    _commit(repo, ".env", "A=1\n")
    _commit(repo, "sub/.netrc", "x\n")
    _commit(repo, ".env", delete=True)
    files = {h["file"] for h in sh.scan(repo)["file_hits"]}
    assert {".env", "sub/.netrc"} <= files


def test_prose_about_passwords_is_not_a_hit(repo):
    _commit(repo, "notes.md", "Never commit a password, token or key. Keys live in .env.\n")
    assert sh.scan(repo)["content_hits"] == []
