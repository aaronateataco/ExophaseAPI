#!/bin/bash
# Verify all source directories were copied to the artifact.
# Usage: bash expo-verify-copy.sh <app-name> <prefix>

set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: bash expo-verify-copy.sh <app-name> <prefix>"
  exit 1
fi

APP="$1"
PREFIX="$2"
MISSING=0

# Skip directories that are migrated elsewhere (not into the expo artifact):
#   node_modules — not copied
#   server/      — migrated to artifacts/api-server (Phase 2)
#   shared/      — migrated to lib/db (Phase 2)
SKIP_DIRS="node_modules server shared"

for dir in .migration-backup/"$PREFIX"/*/; do
  [ ! -d "$dir" ] && continue
  name=$(basename "$dir")
  echo "$SKIP_DIRS" | grep -qw "$name" && continue
  if [ ! -d "artifacts/$APP/$name" ]; then
    echo "WARNING: $name was NOT copied"
    MISSING=1
  fi
done

if [ $MISSING -ne 0 ]; then
  echo "Fix missing directories before proceeding."
  exit 1
else
  echo "All source directories copied."
fi
