#!/usr/bin/env bash
# Copy the project to a dated folder OUTSIDE the repository (CLAUDE.md rule 3). No git involved.
# Leaves out data/, secrets (.env*, .netrc, *.pem, *.key) and the virtualenv.
#
#   scripts/backup.sh                          -> ~/khet-sathi-backups/khet-sathi_YYYY-MM-DD_HHMMSS/
#   BACKUP_ROOT=/Volumes/usb scripts/backup.sh -> /Volumes/usb/khet-sathi_YYYY-MM-DD_HHMMSS/
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
ROOT="${BACKUP_ROOT:-$HOME/khet-sathi-backups}"

# Physical absolute path of a directory that may not exist yet (resolves /var -> /private/var etc.)
abs_dir() {
  local p="$1" rest=""
  while [ ! -d "$p" ]; do rest="/$(basename "$p")$rest"; p="$(dirname "$p")"; done
  echo "$(cd "$p" && pwd -P)$rest"
}

ROOT_ABS="$(abs_dir "$ROOT")"
case "$ROOT_ABS/" in
  "$REPO"/*) echo "backup.sh: refusing to back up into the repository itself ($ROOT_ABS)" >&2; exit 1 ;;
esac

DEST="$ROOT_ABS/khet-sathi_$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$DEST"
rsync -a \
  --exclude '/data/' \
  --exclude '.env' --exclude '.env.*' --exclude '.netrc' --exclude '*.pem' --exclude '*.key' \
  --exclude '/.venv/' --exclude '__pycache__/' --exclude '.pytest_cache/' --exclude '.DS_Store' \
  "$REPO/" "$DEST/"

echo "Backup written to $DEST ($(du -sh "$DEST" | cut -f1))"
