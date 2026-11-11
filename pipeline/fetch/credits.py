"""Each fetch module records what it downloaded in CREDITS.md (CLAUDE.md "Data sources", item 4)."""
from pathlib import Path

HEADING = "## Data fetched by the pipeline"


def ensure_credit(path, line):
    """Add `line` under HEADING unless it is already there. Returns True if the file changed."""
    path = Path(path)
    lines = path.read_text().splitlines() if path.exists() else []
    if line in lines:
        return False
    if HEADING not in lines:
        lines += ["", HEADING, ""]
    start = lines.index(HEADING)
    end = next((k for k in range(start + 1, len(lines)) if lines[k].startswith("## ")), len(lines))
    insert_at = end
    while insert_at > start + 1 and not lines[insert_at - 1].strip():
        insert_at -= 1
    if insert_at == start + 1:
        lines.insert(insert_at, "")
        insert_at += 1
    lines.insert(insert_at, line)
    if insert_at + 1 < len(lines) and lines[insert_at + 1].startswith("## "):
        lines.insert(insert_at + 1, "")
    path.write_text("\n".join(lines) + "\n")
    return True
