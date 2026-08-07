#!/bin/bash
# Copy backend files from backup to workspace and fix known import patterns.
# Usage: bash fullstack-copy-backend.sh [--schema-path <path>] [--route-layout single|directory]
#
# If flags are omitted, the script auto-discovers from .migration-backup/.
# Prints a summary of what was copied and what needs agent attention.

set -euo pipefail

BACKUP=".migration-backup"
SCHEMA_PATH=""
ROUTE_LAYOUT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --schema-path) SCHEMA_PATH="$2"; shift 2 ;;
    --route-layout) ROUTE_LAYOUT="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

echo "==== BACKEND COPY ===="

# --- Auto-discover if not specified ---
if [ -z "$SCHEMA_PATH" ]; then
  for candidate in \
    "$BACKUP/shared/schema.ts" \
    "$BACKUP/shared/schema/index.ts" \
    "$BACKUP/db/schema.ts" \
    "$BACKUP/server/db/schema.ts" \
    "$BACKUP/src/shared/schema.ts"; do
    if [ -f "$candidate" ]; then
      SCHEMA_PATH="${candidate#"$BACKUP/"}"
      break
    fi
  done
  # Fallback: broader search (matches fullstack-detect.sh behavior)
  if [ -z "$SCHEMA_PATH" ]; then
    FOUND=$(find "$BACKUP" -name "schema.ts" -not -path "*/node_modules/*" -not -path "*/.git/*" 2>/dev/null | head -1)
    if [ -n "$FOUND" ]; then
      SCHEMA_PATH="${FOUND#"$BACKUP/"}"
    fi
  fi
fi

if [ -z "$ROUTE_LAYOUT" ]; then
  if [ -d "$BACKUP/server/routes" ]; then
    ROUTE_LAYOUT="directory"
  elif [ -f "$BACKUP/server/routes.ts" ]; then
    ROUTE_LAYOUT="single"
  else
    ROUTE_LAYOUT="none"
  fi
fi

# --- Copy schema ---
if [ -n "$SCHEMA_PATH" ] && [ -f "$BACKUP/$SCHEMA_PATH" ]; then
  # Handle both single file and directory schemas
  SCHEMA_DIR=$(dirname "$BACKUP/$SCHEMA_PATH")
  SCHEMA_BASENAME=$(basename "$SCHEMA_PATH")

  if [ "$SCHEMA_BASENAME" = "index.ts" ]; then
    # Directory-style schema — copy entire directory
    cp -r "$SCHEMA_DIR"/* lib/db/src/schema/
    echo "COPIED: $SCHEMA_PATH (directory) → lib/db/src/schema/"
  else
    cp "$BACKUP/$SCHEMA_PATH" lib/db/src/schema/
    echo "COPIED: $SCHEMA_PATH → lib/db/src/schema/"

    # Update the barrel export so @workspace/db re-exports the schema
    SCHEMA_MODULE=$(basename "$SCHEMA_PATH" .ts)
    if [ -f lib/db/src/schema/index.ts ]; then
      # Replace the empty `export {}` with an actual export
      if grep -q 'export {}' lib/db/src/schema/index.ts; then
        sed -i "s|export {}|export * from \"./$SCHEMA_MODULE\";|" lib/db/src/schema/index.ts
      elif ! grep -q "from \"./$SCHEMA_MODULE\"" lib/db/src/schema/index.ts; then
        echo "export * from \"./$SCHEMA_MODULE\";" >> lib/db/src/schema/index.ts
      fi
      echo "UPDATED: lib/db/src/schema/index.ts → exports $SCHEMA_MODULE"
    fi
  fi

  # Fix zod imports in all copied schema files
  find lib/db/src/schema/ -name "*.ts" -exec sed -i 's/from "zod"/from "zod\/v4"/g' {} + 2>/dev/null || true
  find lib/db/src/schema/ -name "*.ts" -exec sed -i "s/from 'zod'/from 'zod\/v4'/g" {} + 2>/dev/null || true
  # Fix zod v4 API changes
  find lib/db/src/schema/ -name "*.ts" -exec sed -i 's/z\.record(z\.any())/z.record(z.string(), z.any())/g' {} + 2>/dev/null || true
  find lib/db/src/schema/ -name "*.ts" -exec sed -i 's/\.errors/\.issues/g' {} + 2>/dev/null || true
  echo "FIXED: zod → zod/v4 imports + API compat in schema files"
else
  echo "WARNING: No schema file found — agent must locate and copy manually"
fi

# --- Copy routes ---
COPIED_ROUTES=0
case "$ROUTE_LAYOUT" in
  single)
    cp "$BACKUP/server/routes.ts" artifacts/api-server/src/routes/routes.ts
    echo "COPIED: server/routes.ts → artifacts/api-server/src/routes/routes.ts"
    # Fix relative imports — routes.ts moved from server/ to server/routes/,
    # so sibling imports like ./storage need to become ../storage
    sed -i 's|from "\./|from "../|g' artifacts/api-server/src/routes/routes.ts 2>/dev/null || true
    sed -i "s|from '\./|from '../|g" artifacts/api-server/src/routes/routes.ts 2>/dev/null || true
    echo "FIXED: relative imports in routes.ts (adjusted for routes/ subdirectory)"
    COPIED_ROUTES=1
    ;;
  directory)
    cp -r "$BACKUP/server/routes/"* artifacts/api-server/src/routes/
    echo "COPIED: server/routes/* → artifacts/api-server/src/routes/"
    COPIED_ROUTES=1
    ;;
  none)
    echo "WARNING: No routes found — agent must locate and copy manually"
    ;;
esac

# --- Copy storage ---
if [ -f "$BACKUP/server/storage.ts" ]; then
  cp "$BACKUP/server/storage.ts" artifacts/api-server/src/storage.ts
  echo "COPIED: server/storage.ts → artifacts/api-server/src/storage.ts"
fi

# --- Copy remaining server files and directories ---
if [ -d "$BACKUP/server" ]; then
  # Copy top-level .ts files (skip already-copied and infrastructure)
  for f in "$BACKUP/server/"*.ts; do
    [ -f "$f" ] || continue
    basename=$(basename "$f")
    case "$basename" in
      routes.ts|storage.ts|index.ts|main.ts|vite.ts) continue ;;
    esac
    cp "$f" artifacts/api-server/src/
    echo "COPIED: server/$basename → artifacts/api-server/src/$basename"
  done
  # Copy nested directories (middleware, lib, utils, integrations, etc.)
  # Skip routes/ (already copied), node_modules, and dist/build output
  for dir in "$BACKUP/server"/*/; do
    [ ! -d "$dir" ] && continue
    dirname=$(basename "$dir")
    case "$dirname" in
      routes|node_modules|dist|build|__tests__|__mocks__) continue ;;
    esac
    cp -r "$dir" "artifacts/api-server/src/$dirname"
    echo "COPIED: server/$dirname/ → artifacts/api-server/src/$dirname/"
  done
fi

# --- Fix import patterns in all copied server files (recursive) ---
# Only rewrite schema imports to @workspace/db. Leave other @shared/ imports
# (auth, models, utils) for the agent — they need to go to different packages.
find artifacts/api-server/src/ -name "*.ts" -exec sed -i 's|from "../../shared/schema"|from "@workspace/db"|g' {} + 2>/dev/null || true
find artifacts/api-server/src/ -name "*.ts" -exec sed -i "s|from '../../shared/schema'|from '@workspace/db'|g" {} + 2>/dev/null || true
find artifacts/api-server/src/ -name "*.ts" -exec sed -i 's|from "@shared/schema"|from "@workspace/db"|g' {} + 2>/dev/null || true
find artifacts/api-server/src/ -name "*.ts" -exec sed -i "s|from '@shared/schema'|from '@workspace/db'|g" {} + 2>/dev/null || true
# Flag any remaining @shared/ or ../../shared/ imports the agent needs to fix
REMAINING_SHARED=$(find artifacts/api-server/src/ -name "*.ts" -exec grep -l "@shared/\|../../shared/" {} + 2>/dev/null || true)
if [ -n "$REMAINING_SHARED" ]; then
  echo "WARNING: non-schema @shared/ imports found — agent must relocate these manually:"
  echo "$REMAINING_SHARED" | while read -r f; do echo "  $f"; done
fi
# Fix zod v4 in server files too (routes may use zod for validation)
find artifacts/api-server/src/ -name "*.ts" -exec sed -i 's/from "zod"/from "zod\/v4"/g' {} + 2>/dev/null || true
find artifacts/api-server/src/ -name "*.ts" -exec sed -i "s/from 'zod'/from 'zod\/v4'/g" {} + 2>/dev/null || true
find artifacts/api-server/src/ -name "*.ts" -exec sed -i 's/z\.record(z\.any())/z.record(z.string(), z.any())/g' {} + 2>/dev/null || true
echo "FIXED: schema imports → @workspace/db + zod v4 compat in server files"

# --- Copy attached assets ---
if [ -d "$BACKUP/attached_assets" ]; then
  cp -r "$BACKUP/attached_assets" .
  echo "COPIED: attached_assets/"
fi

echo ""
echo "==== BACKEND COPY COMPLETE ===="
echo ""
echo "AGENT TODO:"
echo "  1. Convert route signature (registerRoutes → Express router)"
echo "  2. Write OpenAPI spec based on routes"
echo "  3. Add @workspace/api-zod imports where needed"
if [ $COPIED_ROUTES -eq 0 ]; then
  echo "  4. Locate and copy route files manually"
fi
