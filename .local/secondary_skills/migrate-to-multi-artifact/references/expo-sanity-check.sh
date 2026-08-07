#!/bin/bash
# Expo migration sanity check.
# Usage: bash expo-sanity-check.sh <app-name> <prefix>
#   app-name: the artifact slug (e.g. "my-app")
#   prefix:   the code prefix detected in Phase 1 ("client" or ".")

set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: bash expo-sanity-check.sh <app-name> <prefix>"
  exit 1
fi

APP="$1"
PREFIX="$2"

echo "==== MIGRATION SANITY CHECK ===="
echo "App: $APP | Prefix: $PREFIX"
FAIL=0

# 1. app.json preserved
if diff -q .migration-backup/app.json "artifacts/$APP/app.json" >/dev/null 2>&1; then
  echo "PASS: app.json matches original"
else
  echo "FAIL: app.json differs from original"
  diff .migration-backup/app.json "artifacts/$APP/app.json" || true
  FAIL=1
fi

# 2. No app.config.ts
if [ -f "artifacts/$APP/app.config.ts" ]; then
  echo "FAIL: app.config.ts exists — remove it and use static app.json"
  FAIL=1
else
  echo "PASS: no app.config.ts"
fi

# 3. Routing paradigm
if [ -f "artifacts/$APP/app/_layout.tsx" ]; then
  echo "PASS: expo-router layout found"
else
  echo "FAIL: app/_layout.tsx missing"
  FAIL=1
fi

# 4. All source directories copied
# Skip directories that are migrated elsewhere (not into the expo artifact):
#   node_modules — not copied
#   server/      — migrated to artifacts/api-server (Phase 2)
#   shared/      — migrated to lib/db (Phase 2)
SKIP_DIRS="node_modules server shared"
DIR_FAIL=0
for dir in .migration-backup/"$PREFIX"/*/; do
  [ ! -d "$dir" ] && continue
  name=$(basename "$dir")
  echo "$SKIP_DIRS" | grep -qw "$name" && continue
  if [ ! -d "artifacts/$APP/$name" ]; then
    echo "FAIL: directory $name was NOT copied"
    DIR_FAIL=1
    FAIL=1
  fi
done
[ $DIR_FAIL -eq 0 ] && echo "PASS: all source directories copied"

# 5. No broken @/ imports
BROKEN_IMPORTS=$({ grep -rn "from ['\"]@/" "artifacts/$APP/" --include="*.ts" --include="*.tsx" 2>/dev/null || true; } | while IFS= read -r line; do
  file=$(echo "$line" | cut -d: -f1)
  import_path=$(echo "$line" | sed -n "s/.*from ['\"]@\/\([^'\"]*\)['\"].*/\1/p")
  base="artifacts/$APP/$import_path"
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

# 6. Design tokens copied
for f in constants/colors.ts constants/typography.ts; do
  if [ -f ".migration-backup/$PREFIX/$f" ] || [ -f ".migration-backup/$f" ]; then
    if [ -f "artifacts/$APP/$f" ]; then
      echo "PASS: $f copied"
    else
      echo "FAIL: $f missing from artifact"
      FAIL=1
    fi
  fi
done

# 7. Font loading pattern preserved
if grep -q "useFonts\|SplashScreen" "artifacts/$APP/app/_layout.tsx" 2>/dev/null; then
  echo "PASS: font loading pattern present"
else
  echo "FAIL: useFonts/SplashScreen missing from _layout.tsx"
  FAIL=1
fi

# 8. No stale imports
if grep -rq "@shared/\|from ['\"]\.\.\/.*shared" "artifacts/$APP/" --include="*.ts" --include="*.tsx" 2>/dev/null; then
  echo "FAIL: old @shared/ imports still present"
  grep -rn "@shared/\|from ['\"]\.\.\/.*shared" "artifacts/$APP/" --include="*.ts" --include="*.tsx"
  FAIL=1
else
  echo "PASS: no old shared imports"
fi
if grep -rq "from ['\"]@workspace/db['\"]" "artifacts/$APP/" --include="*.ts" --include="*.tsx" 2>/dev/null; then
  echo "FAIL: @workspace/db imported in frontend"
  FAIL=1
else
  echo "PASS: no server code imports in frontend"
fi

# 9. Native package versions — flag mismatches
for pkg in react-native-reanimated react-native-gesture-handler react-native-keyboard-controller; do
  ART_VER=$(grep -o "\"$pkg\": *\"[^\"]*\"" "artifacts/$APP/package.json" 2>/dev/null || echo "")
  ORIG_VER=$(grep -o "\"$pkg\": *\"[^\"]*\"" .migration-backup/package.json 2>/dev/null || echo "")
  if [ -n "$ART_VER" ] && [ -n "$ORIG_VER" ]; then
    if [ "$ART_VER" != "$ORIG_VER" ]; then
      echo "FAIL: $pkg version mismatch — artifact has $ART_VER, original has $ORIG_VER. Use the original version."
      FAIL=1
    else
      echo "PASS: $pkg version matches"
    fi
  elif [ -n "$ORIG_VER" ] && [ -z "$ART_VER" ]; then
    echo "FAIL: $pkg present in original but missing from artifact"
    FAIL=1
  fi
done

# 10. Assets copied
if [ -d ".migration-backup/$PREFIX/assets" ] || [ -d ".migration-backup/assets" ]; then
  MISSING_ASSETS=0
  SOURCE_ASSETS=".migration-backup/$PREFIX/assets"
  [ ! -d "$SOURCE_ASSETS" ] && SOURCE_ASSETS=".migration-backup/assets"
  while IFS= read -r f; do
    REL="${f#"$SOURCE_ASSETS"/}"
    if [ ! -f "artifacts/$APP/assets/$REL" ]; then
      echo "FAIL: missing asset assets/$REL"
      MISSING_ASSETS=1
      FAIL=1
    fi
  done < <(find "$SOURCE_ASSETS" -type f 2>/dev/null)
  [ $MISSING_ASSETS -eq 0 ] && echo "PASS: all assets copied"
else
  echo "PASS: no assets directory in original (skipped)"
fi

echo "==== END SANITY CHECK ===="
if [ $FAIL -ne 0 ]; then
  echo "SANITY CHECK FAILED — fix all FAIL lines above before building."
  exit 1
else
  echo "ALL CHECKS PASSED"
fi
