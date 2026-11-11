"""scripts/backup.sh copies the project outside the repo and never copies data/ or secrets."""
import re
import shutil
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "backup.sh"


def _fake_repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    shutil.copy(SCRIPT, repo / "scripts" / "backup.sh")
    (repo / "keep.txt").write_text("keep")
    for secret_or_bulk in ["data/raw/x.nc", ".env", "sub/.env.local", ".netrc", ".venv/bin/python",
                           "certs/server.pem"]:
        p = repo / secret_or_bulk
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("do not copy")
    return repo


def _run(repo, root):
    return subprocess.run(["bash", str(repo / "scripts" / "backup.sh")], env={"BACKUP_ROOT": str(root),
                          "PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "HOME": str(root.parent)},
                          capture_output=True, text=True)


def test_backup_copies_project_to_a_dated_folder(tmp_path):
    repo = _fake_repo(tmp_path)
    res = _run(repo, tmp_path / "backups")
    assert res.returncode == 0, res.stderr
    (dest,) = list((tmp_path / "backups").iterdir())
    assert re.fullmatch(r"khet-sathi_\d{4}-\d{2}-\d{2}_\d{6}", dest.name)
    assert (dest / "keep.txt").read_text() == "keep"
    assert (dest / "scripts" / "backup.sh").is_file()


def test_backup_leaves_out_data_secrets_and_virtualenv(tmp_path):
    repo = _fake_repo(tmp_path)
    assert _run(repo, tmp_path / "backups").returncode == 0
    (dest,) = list((tmp_path / "backups").iterdir())
    for left_out in ["data", ".env", "sub/.env.local", ".netrc", ".venv", "certs/server.pem"]:
        assert not (dest / left_out).exists(), left_out


def test_backup_refuses_a_destination_inside_the_repo(tmp_path):
    repo = _fake_repo(tmp_path)
    res = _run(repo, repo / "backups")
    assert res.returncode != 0
    assert not (repo / "backups").exists()
