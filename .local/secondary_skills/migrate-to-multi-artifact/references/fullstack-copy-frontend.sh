#!/bin/bash
# Copy frontend files from backup to artifact and handle Tailwind/theme setup.
# Usage: bash fullstack-copy-frontend.sh <app-name> [--client-dir <dir>] [--tw-version v3|v4] [--has-theme]
#
# Run AFTER createArtifact has created the artifact directory.
# If flags are omitted, auto-detects from .migration-backup/.

set -euo pipefail

BACKUP=".migration-backup"

if [ $# -lt 1 ]; then
  echo "Usage: bash fullstack-copy-frontend.sh <app-name> [--client-dir <dir>] [--tw-version v3|v4] [--has-theme]"
  exit 1
fi

APP_NAME="$1"; shift
CLIENT_DIR=""
TW_VERSION=""
HAS_THEME="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --client-dir) CLIENT_DIR="$2"; shift 2 ;;
    --tw-version) TW_VERSION="$2"; shift 2 ;;
    --has-theme) HAS_THEME="true"; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

# --- Auto-discover client dir ---
if [ -z "$CLIENT_DIR" ]; then
  if [ -d "$BACKUP/client/src" ]; then
    CLIENT_DIR="client"
  elif [ -d "$BACKUP/src/components" ] || [ -d "$BACKUP/src/pages" ] || [ -f "$BACKUP/src/App.tsx" ] || [ -f "$BACKUP/src/main.tsx" ]; then
    CLIENT_DIR="src"
  else
    echo "ERROR: Could not find client directory. Pass --client-dir explicitly."
    exit 1
  fi
fi

# --- Auto-detect Tailwind version ---
if [ -z "$TW_VERSION" ]; then
  TW_VERSION="v4"
  CSS_FILE="$BACKUP/$CLIENT_DIR/src/index.css"
  [ "$CLIENT_DIR" = "src" ] && CSS_FILE="$BACKUP/src/index.css"
  if [ -f "$CSS_FILE" ] && grep -q '@tailwind base' "$CSS_FILE" 2>/dev/null; then
    TW_VERSION="v3"
  fi
fi

# --- Auto-detect theme.json ---
if [ "$HAS_THEME" = "false" ] && [ -f "$BACKUP/theme.json" ]; then
  HAS_THEME="true"
fi

ARTIFACT_DIR="artifacts/$APP_NAME"

if [ ! -d "$ARTIFACT_DIR" ]; then
  echo "ERROR: $ARTIFACT_DIR does not exist. Run createArtifact first."
  exit 1
fi

echo "==== FRONTEND COPY ===="
echo "App: $APP_NAME | Client: $CLIENT_DIR | Tailwind: $TW_VERSION | Theme: $HAS_THEME"

# --- Copy source files ---
SRC_DIR="$BACKUP/$CLIENT_DIR/src"
if [ "$CLIENT_DIR" = "src" ]; then
  SRC_DIR="$BACKUP/src"
fi

if [ -d "$SRC_DIR" ]; then
  cp -r "$SRC_DIR"/* "$ARTIFACT_DIR/src/"
  echo "COPIED: $CLIENT_DIR/src/* → $ARTIFACT_DIR/src/"
else
  echo "WARNING: $SRC_DIR not found — agent must copy source files manually"
fi

# --- Copy public assets ---
PUBLIC_DIR="$BACKUP/$CLIENT_DIR/public"
if [ "$CLIENT_DIR" = "src" ]; then
  PUBLIC_DIR="$BACKUP/public"
fi

if [ -d "$PUBLIC_DIR" ]; then
  cp -r "$PUBLIC_DIR"/* "$ARTIFACT_DIR/public/" 2>/dev/null || true
  echo "COPIED: public/* → $ARTIFACT_DIR/public/"
fi

# --- Copy index.html ---
INDEX_HTML="$BACKUP/$CLIENT_DIR/index.html"
if [ "$CLIENT_DIR" = "src" ]; then
  INDEX_HTML="$BACKUP/index.html"
fi

if [ -f "$INDEX_HTML" ]; then
  cp "$INDEX_HTML" "$ARTIFACT_DIR/index.html"
  echo "COPIED: index.html → $ARTIFACT_DIR/index.html"

  # Warn about meta image paths that reference source assets instead of public/
  for meta_attr in "og:image" "twitter:image"; do
    META_PATH=$(grep -oE "property=\"$meta_attr\"[^>]*content=\"[^\"]+\"" "$ARTIFACT_DIR/index.html" 2>/dev/null | grep -oE 'content="[^"]+"' | sed 's/content="//;s/"$//' || true)
    if [ -n "$META_PATH" ] && echo "$META_PATH" | grep -qv "^http"; then
      # Check if the referenced file exists in public/
      if [ ! -f "$ARTIFACT_DIR/public${META_PATH}" ] && [ ! -f "$ARTIFACT_DIR/public/$META_PATH" ]; then
        echo "WARNING: $meta_attr references $META_PATH which is not in public/ — social previews may break"
      fi
    fi
  done
else
  echo "WARNING: index.html not found at $INDEX_HTML — check if fonts/meta tags need manual copy"
fi

# --- Copy local Vite plugin files ---
# If the old vite.config imports local files (./vite-plugin-foo), copy them
VITE_CFG=""
for candidate in "$BACKUP/vite.config.ts" "$BACKUP/client/vite.config.ts" "$BACKUP/vite.config.js" "$BACKUP/client/vite.config.js"; do
  [ -f "$candidate" ] && VITE_CFG="$candidate" && break
done
if [ -n "$VITE_CFG" ]; then
  LOCAL_IMPORTS=$(grep -oE "from ['\"]\\./[^'\"]+['\"]" "$VITE_CFG" 2>/dev/null | sed "s/from [\"']//;s/[\"']//" || true)
  for imp in $LOCAL_IMPORTS; do
    # Resolve relative to the vite config's directory
    VITE_DIR=$(dirname "$VITE_CFG")
    SRC_FILE="$VITE_DIR/$imp"
    # Try with .ts extension if no extension
    [ ! -f "$SRC_FILE" ] && SRC_FILE="${SRC_FILE}.ts"
    [ ! -f "$SRC_FILE" ] && SRC_FILE="${VITE_DIR}/${imp}.js"
    if [ -f "$SRC_FILE" ]; then
      cp "$SRC_FILE" "$ARTIFACT_DIR/"
      echo "COPIED: local Vite plugin $(basename "$SRC_FILE") → $ARTIFACT_DIR/"
    fi
  done
fi

# --- Tailwind v3 handling ---
VITE_EDITS_NEEDED=""
if [ "$TW_VERSION" = "v3" ]; then
  echo ""
  echo "--- Tailwind v3 setup ---"

  # Copy tailwind config
  TW_CONFIG_COPIED="false"
  for candidate in \
    "$BACKUP/tailwind.config.ts" \
    "$BACKUP/tailwind.config.js" \
    "$BACKUP/tailwind.config.cjs" \
    "$BACKUP/$CLIENT_DIR/tailwind.config.ts" \
    "$BACKUP/$CLIENT_DIR/tailwind.config.js"; do
    if [ -f "$candidate" ]; then
      cp "$candidate" "$ARTIFACT_DIR/"
      echo "COPIED: $(basename "$candidate") → $ARTIFACT_DIR/"
      TW_CONFIG_COPIED="true"
      break
    fi
  done
  if [ "$TW_CONFIG_COPIED" = "false" ]; then
    echo "WARNING: No tailwind config found — agent may need to create one"
  else
    # Fix content paths — old configs reference ./client/src/**, ./app/**, etc.
    # After migration, source lives at ./src/** relative to artifact root.
    for tw_file in "$ARTIFACT_DIR"/tailwind.config.*; do
      [ -f "$tw_file" ] || continue
      sed -i 's|"\./client/src/|"./src/|g' "$tw_file" 2>/dev/null || true
      sed -i "s|'./client/src/|'./src/|g" "$tw_file" 2>/dev/null || true
      sed -i 's|"\./client/|"./|g' "$tw_file" 2>/dev/null || true
      sed -i "s|'./client/|'./|g" "$tw_file" 2>/dev/null || true
      sed -i 's|"\./app/|"./src/|g' "$tw_file" 2>/dev/null || true
      sed -i "s|'./app/|'./src/|g" "$tw_file" 2>/dev/null || true
    done
    echo "FIXED: tailwind content paths updated for artifact structure"
  fi

  # Install v3 deps, remove v4 plugin
  pnpm --filter "@workspace/$APP_NAME" add -D tailwindcss@3 postcss autoprefixer 2>&1 || true
  pnpm --filter "@workspace/$APP_NAME" remove @tailwindcss/vite 2>&1 || true
  echo "INSTALLED: tailwindcss@3 postcss autoprefixer"
  echo "REMOVED: @tailwindcss/vite"

  VITE_EDITS_NEEDED="$VITE_EDITS_NEEDED
  - Remove @tailwindcss/vite import and plugin entry
  - Add css.postcss.plugins with autoprefixer + tailwindcss"
fi

# --- Theme.json handling ---
if [ "$HAS_THEME" = "true" ]; then
  echo ""
  echo "--- Theme setup ---"

  cp "$BACKUP/theme.json" "$ARTIFACT_DIR/theme.json"
  echo "COPIED: theme.json → $ARTIFACT_DIR/theme.json"

  pnpm --filter "@workspace/$APP_NAME" add -D @replit/vite-plugin-shadcn-theme-json 2>&1 || true
  echo "INSTALLED: @replit/vite-plugin-shadcn-theme-json"

  VITE_EDITS_NEEDED="$VITE_EDITS_NEEDED
  - Add: import themePlugin from \"@replit/vite-plugin-shadcn-theme-json\"
  - Add: themePlugin() to plugins array"
fi

# --- Copy postcss config only for Tailwind v3 ---
# For v4, the scaffold uses @tailwindcss/vite — a v3 postcss config would conflict.
if [ "$TW_VERSION" = "v3" ]; then
  for candidate in "$BACKUP/postcss.config.js" "$BACKUP/postcss.config.cjs" "$BACKUP/postcss.config.mjs"; do
    if [ -f "$candidate" ]; then
      cp "$candidate" "$ARTIFACT_DIR/"
      echo "COPIED: $(basename "$candidate") → $ARTIFACT_DIR/"
      break
    fi
  done
else
  # Flag if old postcss config exists but we're skipping it
  for candidate in "$BACKUP/postcss.config.js" "$BACKUP/postcss.config.cjs" "$BACKUP/postcss.config.mjs"; do
    if [ -f "$candidate" ]; then
      echo "SKIPPED: $(basename "$candidate") — conflicts with @tailwindcss/vite (Tailwind v4)"
      break
    fi
  done
fi

# --- Fix Vite fs.strict for @assets alias ---
# The scaffold sets fs.strict: true, which blocks access to attached_assets/ outside the artifact root.
# If attached_assets exist, the agent needs to flip fs.strict to false.
if [ -d "$BACKUP/attached_assets" ] || [ -d "attached_assets" ]; then
  VITE_EDITS_NEEDED="$VITE_EDITS_NEEDED
  - Set server.fs.strict to false (attached_assets lives outside artifact root)"
fi

# --- Auto-patch fonts from index.html into index.css ---
FONT_PATCHED="false"
if [ -f "$ARTIFACT_DIR/index.html" ] && [ -f "$ARTIFACT_DIR/src/index.css" ]; then
  # Extract font family names from Google Fonts URL
  FONT_FAMILIES=$(grep -oE 'family=[^&"]+' "$ARTIFACT_DIR/index.html" 2>/dev/null | sed 's/family=//g; s/+/ /g; s/:.*//g' | head -3 || true)
  if [ -n "$FONT_FAMILIES" ]; then
    PRIMARY_FONT=$(echo "$FONT_FAMILIES" | head -1)
    if [ -n "$PRIMARY_FONT" ]; then
      # Try to update --app-font-sans or --font-sans in index.css
      if grep -q "\-\-app-font-sans:" "$ARTIFACT_DIR/src/index.css" 2>/dev/null; then
        sed -i "s/--app-font-sans:.*$/--app-font-sans: '$PRIMARY_FONT', sans-serif;/" "$ARTIFACT_DIR/src/index.css" 2>/dev/null && FONT_PATCHED="true"
      elif grep -q "\-\-font-sans:" "$ARTIFACT_DIR/src/index.css" 2>/dev/null; then
        sed -i "s/--font-sans:.*$/--font-sans: '$PRIMARY_FONT', sans-serif;/" "$ARTIFACT_DIR/src/index.css" 2>/dev/null && FONT_PATCHED="true"
      fi
      if [ "$FONT_PATCHED" = "true" ]; then
        echo "PATCHED: index.css — updated font-sans to '$PRIMARY_FONT'"
      else
        echo "FONT DETECTED: '$PRIMARY_FONT' in index.html — agent must update CSS variable manually"
      fi
    fi
  fi
fi

# --- Detect wouter usage and BASE_URL requirement ---
NEEDS_WOUTER_BASE="false"
APP_TSX="$ARTIFACT_DIR/src/App.tsx"
if [ -f "$APP_TSX" ]; then
  if grep -q "from ['\"]wouter['\"]" "$APP_TSX" 2>/dev/null; then
    if ! grep -q "BASE_URL\|base=" "$APP_TSX" 2>/dev/null; then
      NEEDS_WOUTER_BASE="true"
      # Auto-patch the import to include Router
      if ! grep -q "Router" "$APP_TSX" 2>/dev/null; then
        sed -i "s/from ['\"]wouter['\"]/from 'wouter'/" "$APP_TSX" 2>/dev/null || true
        # Add Router import if Switch or Route is imported
        sed -i "s/import { \(.*\) } from 'wouter'/import { \1, Router as WouterRouter } from 'wouter'/" "$APP_TSX" 2>/dev/null || true
        echo "PATCHED: App.tsx — added WouterRouter import"
      fi
    fi
  fi
fi

# --- Detect custom queryClient ---
HAS_QC="false"
for qc in "$ARTIFACT_DIR/src/lib/queryClient.ts" "$ARTIFACT_DIR/src/lib/queryClient.tsx" "$ARTIFACT_DIR/src/queryClient.ts"; do
  if [ -f "$qc" ]; then
    HAS_QC="true"
    break
  fi
done

# --- Scan for missing dependencies ---
# Extract third-party imports from copied source, compare against package.json,
# and install anything missing in one batch.
ARTIFACT_PKG="$ARTIFACT_DIR/package.json"
if [ -f "$ARTIFACT_PKG" ]; then
  # Node built-ins to skip
  BUILTINS="assert buffer child_process cluster console crypto dgram dns domain events fs http http2 https inspector module net os path perf_hooks process punycode querystring readline repl stream string_decoder sys timers tls trace_events tty url util v8 vm worker_threads zlib"

  # Extract package names from imports. For scoped packages (@scope/name),
  # keep @scope/name. For unscoped (react, wouter), keep just the name.
  # Skip: relative imports, @/ aliases, @shared/ workspace refs, @workspace/
  MISSING_DEPS=$(find "$ARTIFACT_DIR/src" \( -name "*.ts" -o -name "*.tsx" \) -print0 2>/dev/null | \
    xargs -0 grep -ohE "from ['\"][^'\"./@][^'\"]*['\"]|from ['\"]@[a-z][^'\"]+['\"]" 2>/dev/null | \
    sed "s/from ['\"]//;s/['\"]$//" | \
    sed -E 's|^(@[^/]+/[^/]+)/.*|\1|; s|^([^@][^/]*)/.*|\1|' | \
    sort -u | \
    while read -r pkg; do
      [ -z "$pkg" ] && continue
      # Skip workspace/alias packages
      case "$pkg" in @workspace/*|@shared/*|@db/*|@assets/*) continue ;; esac
      # Skip node built-ins
      echo " $BUILTINS " | grep -q " $pkg " && continue
      # Skip if already in package.json
      grep -q "\"$pkg\"" "$ARTIFACT_PKG" 2>/dev/null && continue
      echo "$pkg"
    done || true)

  if [ -n "$MISSING_DEPS" ]; then
    DEP_LIST=$(echo "$MISSING_DEPS" | tr '\n' ' ')
    echo ""
    echo "--- Installing missing dependencies ---"
    echo "DETECTED: $DEP_LIST"
    # Intentional word splitting for package list
    # shellcheck disable=SC2086
    pnpm --filter "@workspace/$APP_NAME" add $DEP_LIST 2>&1 || true
    echo "INSTALLED: $DEP_LIST"
  fi
fi

echo ""
echo "==== FRONTEND COPY COMPLETE ===="

if [ -n "$VITE_EDITS_NEEDED" ]; then
  echo ""
  echo "AGENT TODO — edit $ARTIFACT_DIR/vite.config.ts:$VITE_EDITS_NEEDED"
fi
echo ""
echo "AGENT TODO:"
echo "  1. Fix frontend imports (@shared/ → generated hooks from @workspace/api-client-react)"
if [ "$NEEDS_WOUTER_BASE" = "true" ]; then
  echo "  2. REQUIRED: Wrap wouter Router with base path — add <WouterRouter base={import.meta.env.BASE_URL.replace(/\\/$/, '')}> around your routes in App.tsx. Navigation will silently break without this."
fi
if [ "$HAS_QC" = "true" ]; then
  echo "  3. Custom queryClient.ts was copied — verify App.tsx imports from it instead of creating a bare new QueryClient()"
fi
