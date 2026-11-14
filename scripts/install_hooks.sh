#!/bin/sh
# Install the repository's git hooks (owner, 2026-11-14 evening): the pre-push secrets scan.
set -e
cd "$(git rev-parse --show-toplevel)"
hooks="$(git rev-parse --git-common-dir)/hooks"
cp scripts/hooks/pre-push "$hooks/pre-push"
chmod +x "$hooks/pre-push" scripts/hooks/pre-push
echo "installed $hooks/pre-push"
