"""Owner decision H and golden rule 2: before EVERY push, scan every commit on every branch AND the working tree
(what the next commit would take) for secrets.

    .venv/bin/python scripts/scan_history.py                      # exit 1 if anything is found
    .venv/bin/python scripts/scan_history.py --hash-env NAME      # print the SHA-256 of one .env value (never the value)

Looks at every line ever added (git log --all -p), at every line of every file a commit would take now (tracked, and
untracked but not ignored), and at every such file name, for secret-shaped text and for .env, .netrc, private keys and
credential files. Prose that merely mentions passwords or tokens is not a hit; values assigned to such names, and
known token formats, are.

Extended 2026-11-13 (REVIEW_2 H7; owner's answer 14) for what the online probe (build step 10b) brings: Google and
Firebase API keys in any position, C `#define` secrets, Wi-Fi passwords, Firebase database addresses, JWTs, netrc
lines for any host, and the firmware and Firebase credential file names.

The website's Firebase web API key is public by Firebase's design (CLAUDE.md, build step 10b; owner, 2026-11-12). It
is let through BY ITS SHA-256 ONLY: ALLOWED_SHA256 holds hashes, never a key. Any other key is a hit. To allow a
value, run --hash-env and add the printed hash below; that is the owner's decision each time.
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

# SHA-256 of values that may appear in the public repository (owner, 2026-11-13, REVIEW_2 answer 14):
ALLOWED_SHA256 = {
    # the website's Firebase web API key (.env FIREBASE_API_KEY on 2026-11-13); the probe's own key is never listed
    "0948f81eb64d68029168639d3e3c3fc64613b21e345e0167965c12797e9d0873",
}
ALLOWED_SHA256 = {h for h in ALLOWED_SHA256 if len(h) == 64}

_VALUE = r"['\"]?(?=[^\s'\"]*[0-9])(?=[^\s'\"]*[A-Za-z])[^\s'\"]{8,}"      # 8+ characters with a letter and a digit
PATTERNS = [
    ("assignment", re.compile(r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key)\b\s*[:=]\s*['\"]?[^\s'\"]{8,}")),
    # names with a prefix or in camelCase or quoted (FIREBASE_API_KEY=, "apiKey": "...", wifiPassword = "..."):
    ("assignment (prefixed or quoted name)", re.compile(
        r"(?i)(password|passwd|secret|token|api[_-]?key|access[_-]?key|wifi[_-]?pass)[A-Za-z_]{0,12}['\"]?\s*[:=]\s*" + _VALUE)),
    ("c define", re.compile(r"(?i)#\s*define\s+\w*(pass|pwd|secret|token|key)\w*\s+\"[^\"]{8,}\"")),
    ("google api key", re.compile(r"AIza[0-9A-Za-z_\-]{30,}")),
    ("firebase database address", re.compile(r"https://[a-z0-9-]+\.(?:[a-z0-9-]+\.firebasedatabase\.app|firebaseio\.com)")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("github token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("aws access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("earthdata netrc line", re.compile(r"(?i)machine\s+urs\.earthdata\.nasa\.gov")),
    ("netrc line", re.compile(r"(?i)\bmachine\s+\S+\s+login\s+\S+\s+password\s+\S+")),
    ("slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
]
# tokens that may be let through by hash: the same shapes as the three "value" patterns above
_TOKENS = re.compile(r"AIza[0-9A-Za-z_\-]{30,}|https://[a-z0-9-]+\.(?:[a-z0-9-]+\.firebasedatabase\.app|firebaseio\.com)")
BAD_FILES = re.compile(r"(^|/)(\.env(\..*)?|\.netrc|_netrc|[^/]*\.pem|[^/]*\.key|id_rsa[^/]*|credentials[^/]*\.json|"
                       r"secrets\.h|google-services\.json|GoogleService-Info\.plist|serviceAccount[^/]*\.json|"
                       r"firebase-adminsdk[^/]*\.json)$")
MAX_FILE_BYTES = 5_000_000
# A login template whose two values are both "<your ...>" placeholders (owner, 2026-11-14 evening: the false alarm in an
# uncommitted draft of docs/DEPLOY_ANYWHERE.md). Only that exact shape is let through; any other value is still a hit.
_PLACEHOLDER = r"<your [a-z ]{1,30}>"
_NETRC_TEMPLATE = re.compile(rf"(?i)\bmachine\s+\S+\s+login\s+{_PLACEHOLDER}\s+password\s+{_PLACEHOLDER}")


def mask(text):
    """Every run of 4 or more non-space characters keeps its first 3; the rest become '*'. Reports never show a value."""
    return re.sub(r"\S{4,}", lambda m: m.group(0)[:3] + "*" * (len(m.group(0)) - 3), text)


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True,
                          errors="replace").stdout


def _line_hits(line, allowed):
    """Kinds of secret-shaped text in one line, after letting through the values whose SHA-256 is allowed."""
    line = _NETRC_TEMPLATE.sub("LOGIN_TEMPLATE", line)
    if allowed:
        line = _TOKENS.sub(lambda m: "ALLOWED" if hashlib.sha256(m.group(0).encode()).hexdigest() in allowed else m.group(0), line)
    return [kind for kind, rx in PATTERNS if rx.search(line)]


def scan(repo=".", allowed_sha256=None):
    allowed = ALLOWED_SHA256 if allowed_sha256 is None else set(allowed_sha256)
    commits = [c for c in _git(repo, "rev-list", "--all").split() if c]
    content, files = [], {}
    commit, path, n = None, None, 0
    for line in _git(repo, "log", "--all", "-p", "--no-color", "--format=COMMIT %H").splitlines():
        if line.startswith("COMMIT "):
            commit = line.split()[1]
        elif line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("@@ "):
            m = re.search(r"\+(\d+)", line)
            n = int(m.group(1)) if m else 0
        elif line.startswith("+") and not line.startswith("+++") and path:
            for kind in _line_hits(line, allowed)[:1]:
                content.append({"commit": commit, "file": path, "line": n, "kind": kind, "text": mask(line[1:].strip())[:120]})
            n += 1
        elif line.startswith(" "):
            n += 1
    for block in _git(repo, "log", "--all", "--name-only", "--format=COMMIT %H").split("COMMIT ")[1:]:
        lines = block.strip().splitlines()
        for name in lines[1:]:
            if name and BAD_FILES.search(name):
                files.setdefault(name, lines[0])
    # the working tree: every file the next commit would take (tracked, or untracked and not ignored)
    seen = {(h["file"], h["text"]) for h in content}
    tree = [n for n in _git(repo, "ls-files", "-co", "--exclude-standard", "-z").split("\0") if n]
    for name in tree:
        f = Path(repo) / name
        if not f.is_file():
            continue
        if BAD_FILES.search(name):
            files.setdefault(name, "WORKTREE")
        if f.stat().st_size > MAX_FILE_BYTES:
            continue
        try:
            text = f.read_text(errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for kind in _line_hits(line, allowed)[:1]:
                hit = {"commit": "WORKTREE", "file": name, "line": i, "kind": kind, "text": mask(line.strip())[:120]}
                if (hit["file"], hit["text"]) not in seen:
                    seen.add((hit["file"], hit["text"]))
                    content.append(hit)
    return {"commits_scanned": len(commits), "files_scanned": len(tree), "content_hits": content,
            "file_hits": [{"file": f, "commit": c} for f, c in sorted(files.items())]}


def hash_env(name, env_path=".env"):
    """SHA-256 of one KEY=value in a .env file. Prints the hash only, never the value."""
    for line in Path(env_path).read_text().splitlines():
        if line.startswith(name + "="):
            return hashlib.sha256(line.split("=", 1)[1].strip().strip("'\"").encode()).hexdigest()
    raise KeyError(f"{name} is not in {env_path}")


def main(argv=None):
    argv = list(argv or [])
    if argv[:1] == ["--hash-env"]:
        print(hash_env(argv[1], argv[2] if len(argv) > 2 else ".env"))
        return 0
    repo = Path(argv[0] if argv else ".")
    r = scan(repo)
    print(f"commits scanned: {r['commits_scanned']} (all branches); files in the working tree scanned: {r['files_scanned']}")
    print(f"secret-shaped lines (ever added, or in the working tree): {len(r['content_hits'])}")
    for h in r["content_hits"]:
        print(f"  {h['commit'][:10]} {h['file']}:{h['line']} [{h['kind']}] {h['text']}")
    print(f"sensitive file names (ever committed, or in the working tree): {len(r['file_hits'])}")
    for h in r["file_hits"]:
        print(f"  {h['commit'][:10]} {h['file']}")
    return 1 if (r["content_hits"] or r["file_hits"]) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
