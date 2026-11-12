"""Owner decision H: before the repository goes public, scan EVERY commit on every branch for secrets.

    .venv/bin/python scripts/scan_history.py            # exit 1 if anything is found

Looks at every line ever added (git log --all -p) for secret-shaped text, and at every file name ever
committed for .env, .netrc, private keys and credential files. Prose that merely mentions passwords or
tokens is not a hit; values assigned to such names, and known token formats, are.
"""
import re
import subprocess
import sys
from pathlib import Path

PATTERNS = [
    ("assignment", re.compile(r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key)\b\s*[:=]\s*['\"]?[^\s'\"]{8,}")),
    ("github token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("aws access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("earthdata netrc line", re.compile(r"(?i)machine\s+urs\.earthdata\.nasa\.gov")),
    ("slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
]
BAD_FILES = re.compile(r"(^|/)(\.env(\..*)?|\.netrc|_netrc|[^/]*\.pem|[^/]*\.key|id_rsa[^/]*|credentials[^/]*\.json)$")


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True,
                          errors="replace").stdout


def scan(repo="."):
    commits = [c for c in _git(repo, "rev-list", "--all").split() if c]
    content, files = [], {}
    commit, path = None, None
    for line in _git(repo, "log", "--all", "-p", "--no-color", "--format=COMMIT %H").splitlines():
        if line.startswith("COMMIT "):
            commit = line.split()[1]
        elif line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("+") and not line.startswith("+++") and path:
            for kind, rx in PATTERNS:
                if rx.search(line):
                    content.append({"commit": commit, "file": path, "kind": kind, "text": line[1:].strip()[:120]})
    for block in _git(repo, "log", "--all", "--name-only", "--format=COMMIT %H").split("COMMIT ")[1:]:
        lines = block.strip().splitlines()
        for name in lines[1:]:
            if name and BAD_FILES.search(name):
                files.setdefault(name, lines[0])
    return {"commits_scanned": len(commits), "content_hits": content,
            "file_hits": [{"file": f, "commit": c} for f, c in sorted(files.items())]}


def main(argv=None):
    repo = Path(argv[0] if argv else ".")
    r = scan(repo)
    print(f"commits scanned: {r['commits_scanned']} (all branches)")
    print(f"secret-shaped lines ever added: {len(r['content_hits'])}")
    for h in r["content_hits"]:
        print(f"  {h['commit'][:10]} {h['file']} [{h['kind']}] {h['text']}")
    print(f"sensitive file names ever committed: {len(r['file_hits'])}")
    for h in r["file_hits"]:
        print(f"  {h['commit'][:10]} {h['file']}")
    return 1 if (r["content_hits"] or r["file_hits"]) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
