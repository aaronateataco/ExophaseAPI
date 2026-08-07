#!/bin/bash
# Discover the shape of a fullstack_js project before migration.
# Usage: bash fullstack-detect.sh
#
# Outputs key=value pairs describing the project structure.
# The agent reads this output to decide what to pass to the copy scripts.

set -euo pipefail

BACKUP=".migration-backup"

if [ ! -d "$BACKUP" ]; then
  echo "ERROR: $BACKUP directory not found"
  exit 1
fi

echo "==== PROJECT DETECTION ===="

# --- Tailwind version ---
# v3 uses @tailwind directives; v4 uses @import "tailwindcss"
TW_VERSION="v4"
for css in "$BACKUP"/client/src/index.css "$BACKUP"/src/index.css "$BACKUP"/index.css; do
  if [ -f "$css" ] && grep -q '@tailwind base' "$css" 2>/dev/null; then
    TW_VERSION="v3"
    break
  fi
done
echo "TAILWIND_VERSION=$TW_VERSION"

# --- Theme system ---
HAS_THEME_JSON="false"
if [ -f "$BACKUP/theme.json" ]; then
  HAS_THEME_JSON="true"
fi
echo "HAS_THEME_JSON=$HAS_THEME_JSON"

# --- Client directory ---
# Most fullstack_js projects use client/, but some use src/ or root
CLIENT_DIR=""
if [ -d "$BACKUP/client/src" ]; then
  CLIENT_DIR="client"
elif [ -d "$BACKUP/src/components" ] || [ -d "$BACKUP/src/pages" ] || [ -f "$BACKUP/src/App.tsx" ] || [ -f "$BACKUP/src/main.tsx" ]; then
  CLIENT_DIR="src"
fi
echo "CLIENT_DIR=$CLIENT_DIR"

# --- Route layout ---
ROUTE_LAYOUT="none"
if [ -d "$BACKUP/server/routes" ]; then
  ROUTE_LAYOUT="directory"
elif [ -f "$BACKUP/server/routes.ts" ]; then
  ROUTE_LAYOUT="single"
fi
echo "ROUTE_LAYOUT=$ROUTE_LAYOUT"

# --- Schema discovery ---
# Try common locations in order of likelihood
SCHEMA_PATH=""
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
if [ -z "$SCHEMA_PATH" ]; then
  # Broader search: any file named schema.ts outside node_modules
  FOUND=$(find "$BACKUP" -name "schema.ts" -not -path "*/node_modules/*" -not -path "*/.git/*" 2>/dev/null | head -1)
  if [ -n "$FOUND" ]; then
    SCHEMA_PATH="${FOUND#"$BACKUP/"}"
  fi
fi
echo "SCHEMA_PATH=$SCHEMA_PATH"

# --- Storage file ---
HAS_STORAGE="false"
if [ -f "$BACKUP/server/storage.ts" ]; then
  HAS_STORAGE="true"
fi
echo "HAS_STORAGE=$HAS_STORAGE"

# --- Attached assets ---
HAS_ATTACHED_ASSETS="false"
if [ -d "$BACKUP/attached_assets" ]; then
  HAS_ATTACHED_ASSETS="true"
fi
echo "HAS_ATTACHED_ASSETS=$HAS_ATTACHED_ASSETS"

# --- Custom queryClient ---
HAS_CUSTOM_QUERYCLIENT="false"
for candidate in \
  "$BACKUP/client/src/lib/queryClient.ts" \
  "$BACKUP/client/src/lib/queryClient.tsx" \
  "$BACKUP/client/src/queryClient.ts" \
  "$BACKUP/src/lib/queryClient.ts" \
  "$BACKUP/src/queryClient.ts"; do
  if [ -f "$candidate" ]; then
    HAS_CUSTOM_QUERYCLIENT="true"
    break
  fi
done
echo "HAS_CUSTOM_QUERYCLIENT=$HAS_CUSTOM_QUERYCLIENT"

# --- Server files ---
echo ""
echo "SERVER_FILES:"
if [ -d "$BACKUP/server" ]; then
  find "$BACKUP/server" -maxdepth 2 -name "*.ts" -not -path "*/node_modules/*" 2>/dev/null | sort | while read -r f; do
    echo "  ${f#"$BACKUP/"}"
  done
fi

# --- Client directories ---
echo ""
echo "CLIENT_DIRS:"
if [ -n "$CLIENT_DIR" ] && [ -d "$BACKUP/$CLIENT_DIR/src" ]; then
  for entry in "$BACKUP/$CLIENT_DIR/src/"*; do
    [ -e "$entry" ] || continue
    echo "  $CLIENT_DIR/src/$(basename "$entry")"
  done
fi

# --- Tailwind config location ---
TW_CONFIG=""
for candidate in \
  "$BACKUP/tailwind.config.ts" \
  "$BACKUP/tailwind.config.js" \
  "$BACKUP/tailwind.config.cjs" \
  "$BACKUP/client/tailwind.config.ts" \
  "$BACKUP/client/tailwind.config.js"; do
  if [ -f "$candidate" ]; then
    TW_CONFIG="${candidate#"$BACKUP/"}"
    break
  fi
done
echo ""
echo "TAILWIND_CONFIG=$TW_CONFIG"

# --- Vite plugins in use ---
# Known scaffold plugins that don't need manual porting
SCAFFOLD_PLUGINS="@vitejs/plugin-react @tailwindcss/vite @replit/vite-plugin-runtime-error-modal @replit/vite-plugin-cartographer @replit/vite-plugin-dev-banner"

echo ""
echo "VITE_PLUGINS:"
VITE_CONFIG=""
for candidate in "$BACKUP/vite.config.ts" "$BACKUP/client/vite.config.ts" "$BACKUP/vite.config.js" "$BACKUP/client/vite.config.js"; do
  if [ -f "$candidate" ]; then
    VITE_CONFIG="$candidate"
    break
  fi
done
ALL_PLUGINS=""
if [ -n "$VITE_CONFIG" ]; then
  ALL_PLUGINS=$(sed -n 's/.*from ["\x27]\([^"\x27]*\)["\x27].*/\1/p' "$VITE_CONFIG" 2>/dev/null | grep -iv "^vite$\|^path$\|^express\|^http\|^url" || true)
  echo "$ALL_PLUGINS" | while read -r p; do
    [ -z "$p" ] && continue
    echo "  $p"
  done
fi

# --- Custom Vite plugins (not in scaffold) ---
echo ""
echo "CUSTOM_VITE_PLUGINS:"
if [ -n "$ALL_PLUGINS" ]; then
  echo "$ALL_PLUGINS" | while read -r p; do
    [ -z "$p" ] && continue
    IS_SCAFFOLD="false"
    for sp in $SCAFFOLD_PLUGINS; do
      if [ "$p" = "$sp" ]; then
        IS_SCAFFOLD="true"
        break
      fi
    done
    if [ "$IS_SCAFFOLD" = "false" ]; then
      echo "  $p"
    fi
  done
fi
# Also detect local/relative plugin imports
if [ -n "$VITE_CONFIG" ]; then
  LOCAL_PLUGINS=$(grep -oE 'from ["\x27]\./[^"\x27]+["\x27]' "$VITE_CONFIG" 2>/dev/null | sed "s/from [\"']//;s/[\"']//" || true)
  if [ -n "$LOCAL_PLUGINS" ]; then
    echo "$LOCAL_PLUGINS" | while read -r p; do
      [ -z "$p" ] && continue
      echo "  $p (local file)"
    done
  fi
fi

# --- Potential conflicts ---
echo ""
echo "CONFLICTS:"
HAS_CONFLICTS="false"

# PostCSS config + Tailwind v4 = build failure
if [ "$TW_VERSION" = "v4" ]; then
  for candidate in "$BACKUP/postcss.config.js" "$BACKUP/postcss.config.cjs" "$BACKUP/postcss.config.mjs"; do
    if [ -f "$candidate" ]; then
      echo "  WARNING: $(basename "$candidate") exists but Tailwind v4 detected — will conflict with @tailwindcss/vite"
      HAS_CONFLICTS="true"
      break
    fi
  done
fi

# Old vite plugins that won't exist in the scaffold
if [ -n "$VITE_CONFIG" ]; then
  if grep -q "vite-plugin-shadcn-theme-json" "$VITE_CONFIG" 2>/dev/null && [ "$HAS_THEME_JSON" = "false" ]; then
    echo "  WARNING: vite.config uses shadcn-theme-json plugin but no theme.json found"
    HAS_CONFLICTS="true"
  fi
fi

# Custom Vite plugins that will be silently dropped
# Note: avoid piped while loops — they run in subshells and can't update HAS_CONFLICTS
if [ -n "$ALL_PLUGINS" ]; then
  while read -r p; do
    [ -z "$p" ] && continue
    IS_SCAFFOLD="false"
    for sp in $SCAFFOLD_PLUGINS; do
      if [ "$p" = "$sp" ]; then IS_SCAFFOLD="true"; break; fi
    done
    if [ "$IS_SCAFFOLD" = "false" ]; then
      echo "  WARNING: custom Vite plugin '$p' will be DROPPED unless manually ported"
      HAS_CONFLICTS="true"
    fi
  done <<< "$ALL_PLUGINS"
fi
if [ -n "${LOCAL_PLUGINS:-}" ]; then
  while read -r p; do
    [ -z "$p" ] && continue
    echo "  WARNING: local Vite plugin '$p' will be DROPPED unless manually ported"
    HAS_CONFLICTS="true"
  done <<< "$LOCAL_PLUGINS"
fi

[ "$HAS_CONFLICTS" = "false" ] && echo "  none"

echo ""
echo "==== END DETECTION ===="
