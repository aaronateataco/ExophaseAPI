#!/bin/bash
# Verify all @/ imports in the artifact resolve to real files.
# Usage: bash expo-verify-imports.sh <app-name>

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: bash expo-verify-imports.sh <app-name>"
  exit 1
fi

APP="$1"

BROKEN_IMPORTS=$({ grep -rn "from ['\"]@/" "artifacts/$APP/" --include="*.ts" --include="*.tsx" 2>/dev/null || true; } | while IFS= read -r line; do
  file=$(echo "$line" | cut -d: -f1)
  import_path=$(echo "$line" | sed -n "s/.*from ['\"]@\/\([^'\"]*\)['\"].*/\1/p")
  base="artifacts/$APP/$import_path"
  if [ ! -f "$base.ts" ] && [ ! -f "$base.tsx" ] && [ ! -f "$base/index.ts" ] && [ ! -f "$base/index.tsx" ] && [ ! -f "$base" ]; then
    echo "BROKEN: $file → @/$import_path"
  fi
done)

if [ -n "$BROKEN_IMPORTS" ]; then
  echo "$BROKEN_IMPORTS"
  echo "Fix every broken import before proceeding."
  exit 1
else
  echo "All @/ imports resolve."
fi
