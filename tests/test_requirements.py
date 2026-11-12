"""requirements.txt must install what we test with: every pin there equals the version in
requirements-lock.txt (pip freeze of the working .venv). A pin the lock disagrees with breaks a fresh
install or tests a different library (pandas 3.1.1 was pinned while pyet 1.5.0 needs pandas<3 and the
lock held 2.3.3; owner review of d34fa93)."""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _pins(path):
    out = {}
    for line in path.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        m = re.fullmatch(r"([A-Za-z0-9_.\-]+)==([^\s;]+)", line)
        if m:
            out[re.sub(r"[-_.]+", "-", m.group(1)).lower()] = m.group(2)
    return out


def test_every_requirement_pin_matches_the_lock_file():
    req, lock = _pins(REPO / "requirements.txt"), _pins(REPO / "requirements-lock.txt")
    assert req, "requirements.txt has no pins"
    missing = sorted(set(req) - set(lock))
    differ = {k: (req[k], lock[k]) for k in req if k in lock and req[k] != lock[k]}
    assert not missing, f"pinned but not in the lock: {missing}"
    assert not differ, f"requirements.txt vs requirements-lock.txt: {differ}"


def test_pandas_pin_satisfies_pyet():
    """pyet 1.5.0 declares pandas<3 (its package metadata)."""
    req = _pins(REPO / "requirements.txt")
    assert int(req["pandas"].split(".")[0]) < 3, f"pandas {req['pandas']}: pyet {req.get('pyet')} needs pandas<3"
