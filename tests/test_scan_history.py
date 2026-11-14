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


# ---------- REVIEW_2 H7 (owner's answer 14, 2026-11-13): the key shapes step 10b brings ----------
# Every secret-looking string is assembled at run time, so this file never matches the scan itself.
GKEY = "AI" + "za" + "SyA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q"                 # the shape of a Google / Firebase API key
JWT = "ey" + "JhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" + "." + "ey" + "JzdWIiOiIxMjM0NTY3ODkwIn0" + "." + "abcDEF123_-abcDEF123_-abc"

NEW_SHAPES = {
    "env_style_key": "FIREBASE_" + "API_KEY=" + GKEY,
    "json_api_key": '  "api' + 'Key": "' + GKEY + '",',
    "c_define_key": "#define API_" + 'KEY "' + GKEY + '"',
    "c_define_wifi": "#define WIFI_" + 'PASS "hunter2hunter2"',
    "bare_google_key": 'const k = "' + GKEY + '";',
    "url_key": "https://example.invalid/v1?ke" + "y=" + GKEY,
    "firebase_database_url": 'databaseURL: "https://some-project-default-rtdb.asia-southeast1.firebase' + 'database.app"',
    "jwt": "Authorization: Bearer " + JWT,
    "netrc_other_host": "machine appeears.example.invalid login someone pass" + "word hunter2hunter2",
    "wifi_camel_case": 'const char* wifiPass' + 'word = "hunter2hunter2";',
}


@pytest.mark.parametrize("name", sorted(NEW_SHAPES))
def test_finds_the_key_shapes_of_the_online_probe(repo, name):
    _commit(repo, "robot/firmware/khet_probe/config.h", NEW_SHAPES[name] + "\n")
    r = sh.scan(repo)
    assert r["content_hits"], name


@pytest.mark.parametrize("path", ["robot/firmware/khet_probe/secrets.h", "site/google-services.json",
                                  "serviceAccountKey.json", "keys/firebase-adminsdk-abc12.json"])
def test_finds_credential_file_names_of_firebase_and_firmware(repo, path):
    _commit(repo, path, "x\n")
    assert [h["file"] for h in sh.scan(repo)["file_hits"]] == [path]


def test_the_working_tree_is_scanned_too_before_it_is_committed(repo):
    """Golden rule 2: the scan runs before every push, so it must see what the next commit would take."""
    (repo / "site").mkdir()
    (repo / "site" / "app.js").write_text("const cfg = {" + NEW_SHAPES["json_api_key"] + "};\n")
    (repo / ".gitignore").write_text(".env\n")
    (repo / ".env").write_text(NEW_SHAPES["env_style_key"] + "\n")           # ignored: never committed, not a hit
    r = sh.scan(repo)
    assert [(h["commit"], h["file"]) for h in r["content_hits"]] == [("WORKTREE", "site/app.js")]
    assert r["file_hits"] == []


def test_the_website_key_is_let_through_by_its_sha256_only(repo):
    import hashlib
    _commit(repo, "site/firebase-config.js", "export const cfg = {" + NEW_SHAPES["json_api_key"] + "};\n")
    assert sh.scan(repo)["content_hits"]
    allowed = {hashlib.sha256(GKEY.encode()).hexdigest()}
    assert sh.scan(repo, allowed_sha256=allowed)["content_hits"] == []
    other = GKEY[:-1] + ("R" if GKEY[-1] != "R" else "S")                       # any other key is still a hit
    _commit(repo, "site/other.js", 'const k = "' + other + '";\n')
    hits = sh.scan(repo, allowed_sha256=allowed)["content_hits"]
    assert hits and all(h["file"] == "site/other.js" for h in hits)


def test_the_repository_never_holds_the_allowed_key_itself():
    """Only hashes are listed: 64 hex characters each, never a key."""
    assert all(len(h) == 64 and set(h) <= set("0123456789abcdef") for h in sh.ALLOWED_SHA256)


# ---------- 2026-11-14 evening (owner): a placeholder login template is not a secret; output is masked ----------
NETRC_HOST = "machine " + "urs.earthdata" + ".nasa.gov"


def test_a_login_template_with_your_placeholders_is_not_a_hit(repo):
    """The false alarm of 2026-11-14 (docs/DEPLOY_ANYWHERE.md line 24, never committed): both values are '<your ...>'."""
    _commit(repo, "docs/guide.md", "`" + NETRC_HOST + " login <your user name> password <your password>`\n")
    assert sh.scan(repo)["content_hits"] == []


@pytest.mark.parametrize("line", [
    NETRC_HOST + " login <your user name> password " + "Hunter2" + "Hunter2",        # a real-looking password
    NETRC_HOST + " login " + "jdoe" + "1984 password <your password>",               # a real-looking login
    NETRC_HOST,                                                                        # the host alone still counts
    "machine example.org login " + "jdoe" + " password " + "s3cr" + "etvalue",        # any host's netrc line
])
def test_any_login_line_with_a_real_looking_value_is_still_a_hit(repo, line):
    _commit(repo, "notes.txt", line + "\n")
    assert sh.scan(repo)["content_hits"]


def test_the_report_masks_every_value_and_gives_the_line(repo, capsys):
    _commit(repo, "a.txt", "one\n" + PW + "\n")
    hits = sh.scan(repo)["content_hits"]
    assert hits[0]["line"] == 2
    assert sh.main([str(repo)]) == 1
    out = capsys.readouterr().out
    assert "hunter2hunter2" not in out and "hun" in out and "a.txt:2" in out
    assert sh.mask("token = " + GH_TOKEN) == "tok** = gho" + "*" * (len(GH_TOKEN) - 3)


def test_the_pre_push_hook_blocks_a_push_when_the_scan_fails(repo):
    """Owner, 2026-11-14 evening: scripts/hooks/pre-push runs the scan and blocks EVERY push that fails it."""
    import os
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    (repo / ".venv").symlink_to(root / ".venv")
    (repo / "scripts").symlink_to(root / "scripts")
    (repo / ".gitignore").write_text(".venv\nscripts\n")
    _commit(repo, ".gitignore", ".venv\nscripts\n")
    hook = str(root / "scripts" / "hooks" / "pre-push")
    run = lambda: subprocess.run(["sh", hook], cwd=repo, capture_output=True, text=True,
                                 env={**os.environ, "GIT_DIR": str(repo / ".git")})
    ok = run()
    assert ok.returncode == 0 and "Push allowed" in ok.stderr
    (repo / "draft.txt").write_text("token: " + GH_TOKEN + "\n")        # not committed: the working tree is scanned
    bad = run()
    assert bad.returncode == 1 and "PUSH BLOCKED" in bad.stderr and GH_TOKEN not in bad.stderr


def test_the_installed_hook_is_the_tracked_one():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    installed = root / ".git" / "hooks" / "pre-push"
    if not installed.exists():                     # a fresh clone: scripts/install_hooks.sh has not been run yet
        pytest.skip("run scripts/install_hooks.sh")
    assert installed.read_text() == (root / "scripts" / "hooks" / "pre-push").read_text()
