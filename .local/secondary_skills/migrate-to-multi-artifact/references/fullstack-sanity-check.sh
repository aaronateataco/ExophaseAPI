#!/bin/bash
# Post-migration sanity check for fullstack_js projects.
# Usage: bash fullstack-sanity-check.sh <app-name>
#
# Verifies the mechanical migration was done correctly.
# Run this BEFORE the visual verification step.

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: bash fullstack-sanity-check.sh <app-name>"
  exit 1
fi

APP="$1"
BACKUP=".migration-backup"

echo "==== MIGRATION SANITY CHECK ===="
echo "App: $APP"
FAIL=0

# 1. Artifact directory exists
if [ -d "artifacts/$APP/src" ]; then
  echo "PASS: artifact src/ exists"
else
  echo "FAIL: artifacts/$APP/src/ missing"
  FAIL=1
fi

# 2. index.html copied
if [ -f "artifacts/$APP/index.html" ]; then
  echo "PASS: index.html present"
else
  echo "FAIL: index.html missing — fonts/favicons/meta tags will be lost"
  FAIL=1
fi

# 3. All client source directories copied
if [ -d "$BACKUP/client/src" ]; then
  CLIENT_SRC="$BACKUP/client/src"
elif [ -d "$BACKUP/src" ]; then
  CLIENT_SRC="$BACKUP/src"
else
  CLIENT_SRC=""
fi

if [ -n "$CLIENT_SRC" ]; then
  DIR_FAIL=0
  for dir in "$CLIENT_SRC"/*/; do
    [ ! -d "$dir" ] && continue
    name=$(basename "$dir")
    # Skip node_modules and build output
    case "$name" in
      node_modules|dist|build|.next) continue ;;
    esac
    if [ ! -d "artifacts/$APP/src/$name" ]; then
      echo "FAIL: client directory $name was NOT copied"
      DIR_FAIL=1
      FAIL=1
    fi
  done
  [ $DIR_FAIL -eq 0 ] && echo "PASS: all client source directories copied"
fi

# 4. Schema file present with zod/v4
SCHEMA_OK=0
for f in lib/db/src/schema/*.ts; do
  [ -f "$f" ] || continue
  SCHEMA_OK=1
  # Match 'from "zod"' or "from 'zod'" exactly (not 'from "zod/v4"')
  if grep -qE "from ['\"]zod['\"]" "$f" 2>/dev/null; then
    echo "FAIL: $f still imports from 'zod' instead of 'zod/v4'"
    FAIL=1
  fi
done
if [ $SCHEMA_OK -eq 1 ]; then
  echo "PASS: schema files present in lib/db/src/schema/"
else
  echo "FAIL: no schema files in lib/db/src/schema/"
  FAIL=1
fi

# 5. Route files present
ROUTE_FILES=$(find "artifacts/api-server/src/routes/" -name "*.ts" ! -name "health.ts" ! -name "index.ts" 2>/dev/null | head -1)
if [ -f "artifacts/api-server/src/routes/routes.ts" ] || [ -n "$ROUTE_FILES" ]; then
  echo "PASS: route files present"
else
  echo "FAIL: no route files in artifacts/api-server/src/routes/"
  FAIL=1
fi

# 6. No stale @shared/ imports in server files
if grep -rq "@shared/\|from ['\"]\.\.\/.*shared\|from ['\"]\.\.\/\.\.\/shared" artifacts/api-server/src/ --include="*.ts" 2>/dev/null; then
  echo "FAIL: old @shared/ or ../../shared/ imports still present in server files:"
  grep -rn "@shared/\|from ['\"]\.\.\/.*shared\|from ['\"]\.\.\/\.\.\/shared" artifacts/api-server/src/ --include="*.ts" 2>/dev/null || true
  FAIL=1
else
  echo "PASS: no old shared imports in server files"
fi

# 7. No stale @shared/ imports in frontend
if grep -rq "@shared/\|from ['\"]\.\.\/.*shared" "artifacts/$APP/src/" --include="*.ts" --include="*.tsx" 2>/dev/null; then
  echo "FAIL: old @shared/ imports still present in frontend:"
  grep -rn "@shared/\|from ['\"]\.\.\/.*shared" "artifacts/$APP/src/" --include="*.ts" --include="*.tsx" 2>/dev/null || true
  FAIL=1
else
  echo "PASS: no old shared imports in frontend"
fi

# 8. No server code imported in frontend
if grep -rq "from ['\"]@workspace/db['\"]" "artifacts/$APP/src/" --include="*.ts" --include="*.tsx" 2>/dev/null; then
  echo "FAIL: @workspace/db imported in frontend — use generated hooks instead"
  FAIL=1
else
  echo "PASS: no server code imports in frontend"
fi

# 9. No broken @/ imports
BROKEN_IMPORTS=$({ grep -rn "from ['\"]@/" "artifacts/$APP/src/" --include="*.ts" --include="*.tsx" 2>/dev/null || true; } | while IFS= read -r line; do
  file=$(echo "$line" | cut -d: -f1)
  import_path=$(echo "$line" | sed -n "s/.*from ['\"]@\/\([^'\"]*\)['\"].*/\1/p")
  [ -z "$import_path" ] && continue
  base="artifacts/$APP/src/$import_path"
  if [ ! -f "$base.ts" ] && [ ! -f "$base.tsx" ] && [ ! -f "$base/index.ts" ] && [ ! -f "$base/index.tsx" ] && [ ! -f "$base" ]; then
    echo "$file → @/$import_path"
  fi
done)
if [ -n "$BROKEN_IMPORTS" ]; then
  echo "FAIL: broken @/ imports found:"
  echo "$BROKEN_IMPORTS"
  FAIL=1
else
  echo "PASS: all @/ imports resolve"
fi

# 10. Theme.json carried over if applicable
if [ -f "$BACKUP/theme.json" ]; then
  if [ -f "artifacts/$APP/theme.json" ]; then
    echo "PASS: theme.json copied"
  else
    echo "FAIL: theme.json exists in backup but not in artifact — colors will be broken"
    FAIL=1
  fi
fi

# 11. Attached assets
if [ -d "$BACKUP/attached_assets" ]; then
  if [ -d "attached_assets" ]; then
    echo "PASS: attached_assets present"
  else
    echo "FAIL: attached_assets directory missing"
    FAIL=1
  fi
fi

# 12. Wouter base path
APP_TSX="artifacts/$APP/src/App.tsx"
if [ -f "$APP_TSX" ]; then
  if grep -q "from ['\"]wouter['\"]" "$APP_TSX" 2>/dev/null; then
    if grep -q "BASE_URL\|base=" "$APP_TSX" 2>/dev/null; then
      echo "PASS: wouter has BASE_URL base path"
    else
      echo "FAIL: App.tsx uses wouter but missing BASE_URL base path — routing will break"
      FAIL=1
    fi
  fi
fi

# 13. Font consistency
if [ -f "artifacts/$APP/index.html" ] && [ -f "artifacts/$APP/src/index.css" ]; then
  LOADED_FONTS=$(grep -oE 'family=[^&"]+' "artifacts/$APP/index.html" 2>/dev/null | sed 's/family=//g; s/+/ /g; s/:.*//g' || true)
  if [ -n "$LOADED_FONTS" ]; then
    echo "$LOADED_FONTS" | while read -r font; do
      [ -z "$font" ] && continue
      if grep -qi "$font" "artifacts/$APP/src/index.css" 2>/dev/null; then
        echo "PASS: font '$font' referenced in index.css"
      else
        echo "WARN: font '$font' loaded in index.html but not referenced in index.css — may render with fallback"
      fi
    done
  fi
fi

echo ""
echo "==== END SANITY CHECK ===="
if [ $FAIL -ne 0 ]; then
  echo "SANITY CHECK FAILED — fix all FAIL lines above before proceeding."
  exit 1
else
  echo "ALL CHECKS PASSED"
fi
