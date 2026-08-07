#!/bin/bash
# Overlay the imported Figma (Anima) design onto the already-created
# `figma-design` artifact, keeping the design code verbatim.
#
# Run AFTER the agent has called createArtifact for this slug:
#
#   createArtifact({ artifactType: "react-vite", slug: "figma-design",
#                    previewPath: "/", title: "<design title>",
#                    description: "<short paragraph: what the design is and what it is for>" })
#
# createArtifact is what REGISTERS the artifact: it allocates a port, writes
# .replit-artifact/artifact.toml, generates the dev workflow, and wires the Run
# button. Dropping a folder + hand-written artifact.toml on disk does none of
# that — pid2's artifact watcher only scans for artifacts once at init and on
# explicit rescans (which createArtifact triggers), so a folder copied in later
# is never discovered and gets no workflow.
#
# This script then replaces the react-vite template's scaffolded files with the
# Anima design as-is, keeping the generated artifact.toml. There is NO
# Tailwind/JSX/react-day-picker conversion: the design ships its own
# package.json and vite.config that already match its own code.
#
#   bash figma-setup.sh
set -euo pipefail

SLUG="figma-design"
SRC=".migration-backup"
DEST="artifacts/$SLUG"
TOML="$DEST/.replit-artifact/artifact.toml"

if [ ! -d "$SRC" ]; then
  echo "ERROR: $SRC not found — the pnpm_workspace scaffold must run first."
  exit 1
fi
if [ ! -f "$SRC/package.json" ]; then
  echo "ERROR: $SRC/package.json not found — expected the imported design there."
  exit 1
fi
if [ ! -f "$TOML" ]; then
  echo "ERROR: $TOML not found. Call createArtifact for slug '$SLUG'"
  echo "       (artifactType react-vite) BEFORE running this script — that is"
  echo "       what registers the artifact + workflow."
  exit 1
fi

echo "==== FIGMA SETUP: overlay Anima design onto $DEST ===="

# 1. Replace the react-vite template files with the Anima design, but keep the
#    registered .replit-artifact/ (the generated artifact.toml + its port).
find "$DEST" -mindepth 1 -maxdepth 1 ! -name '.replit-artifact' -exec rm -rf {} +
cp -a "$SRC/." "$DEST/"
# Drop heavy/stale dirs and single-repl config the design carries; never the
# registered artifact.toml the scaffold copy can't contain anyway.
rm -rf "$DEST/node_modules" "$DEST/.git" "$DEST/dist" \
       "$DEST/package-lock.json" "$DEST/.replit" "$DEST/.config" \
       "$DEST/.upm" "$DEST/.cache"
echo "overlaid $SRC -> $DEST (kept .replit-artifact)"

# 2. Plumbing only — not a code change. The package must be the workspace member
#    the generated artifact.toml filters on, and its dev/build must run Vite
#    (the design is frontend-only; Anima ships `dev: tsx server/index.ts`, which
#    boots a server the design doesn't have).
node -e '
  const fs = require("fs");
  const p = process.argv[1];
  const j = JSON.parse(fs.readFileSync(p, "utf8"));
  j.name = "@workspace/figma-design";
  j.scripts = j.scripts || {};
  j.scripts.dev = "vite";
  j.scripts.build = "vite build";
  fs.writeFileSync(p, JSON.stringify(j, null, 2) + "\n");
  console.log("package -> " + j.name + " (dev: vite, build: vite build)");
' "$DEST/package.json"

# 2b. Make Vite honor the platform-assigned PORT and bind all interfaces, and
#     fail loudly on a busy port instead of silently moving (which desyncs the
#     proxy). Injects into the existing server block or adds one.
node -e '
  const fs = require("fs");
  (function (dir) {
    const cand = ["vite.config.ts", "vite.config.mts", "vite.config.js"]
      .map((f) => dir + "/" + f)
      .find((f) => fs.existsSync(f));
    if (!cand) { console.log("SKIP vite config: none found"); return; }
    let c = fs.readFileSync(cand, "utf8");
    if (/strictPort/.test(c)) { console.log("SKIP " + cand + ": already patched"); return; }
    const props = "port: parseInt(process.env.PORT || \"5000\", 10),\n    host: \"0.0.0.0\",\n    strictPort: true,\n    allowedHosts: true,";
    const serverOpen = c.match(/server\s*:\s*{/);
    if (serverOpen) {
      // Drop conflicting keys from the existing block (later keys would win
      // over the injected ones), then prepend ours.
      const start = serverOpen.index + serverOpen[0].length;
      let depth = 1;
      let end = start;
      while (end < c.length && depth > 0) {
        if (c[end] === "{") depth++;
        else if (c[end] === "}") depth--;
        end++;
      }
      const body = c
        .slice(start, end - 1)
        .split("\n")
        .filter((l) => !/^\s*(port|host|strictPort|allowedHosts)\s*:/.test(l))
        .join("\n");
      c = c.slice(0, start) + "\n    " + props + body + c.slice(end - 1);
    } else if (/defineConfig\s*\(\s*{/.test(c)) {
      // Insert as the FIRST property so we never depend on the existing last
      // property having a trailing comma.
      c = c.replace(
        /defineConfig\s*\(\s*{/,
        (s) => s + "\n  server: {\n    " + props + "\n  },",
      );
    } else {
      console.log("SKIP " + cand + ": unrecognized config shape, patch by hand");
      return;
    }
    fs.writeFileSync(cand, c);
    console.log("PATCHED " + cand + ": server reads PORT, host 0.0.0.0, strictPort, allowedHosts");
  })(process.argv[1]);
' "$DEST"

# 2c. CSS entry fixups, one pass: PostCSS requires @import to precede every
#     other statement (Anima emits the Google Fonts import after the @tailwind
#     directives — hard error), and Anima opens with a stray partial
#     `@tailwind components; @tailwind utilities;` block before the canonical
#     base/components/utilities triple, which double-applies the layers.
node -e '
  const fs = require("fs");
  (function (dir) {
    const cand = ["client/src/index.css", "src/index.css"]
      .map((f) => dir + "/" + f)
      .find((f) => fs.existsSync(f));
    if (!cand) { console.log("SKIP css entry: none found"); return; }
    const before = fs.readFileSync(cand, "utf8");
    const lines = before.split("\n");
    const firstBase = lines.findIndex((l) => /^\s*@tailwind\s+base\s*;/.test(l));
    const kept = lines.filter(
      (l, i) => !(firstBase > -1 && i < firstBase && /^\s*@tailwind\b/.test(l)),
    );
    const imports = kept.filter((l) => /^\s*@import\b/.test(l));
    const rest = kept.filter((l) => !/^\s*@import\b/.test(l));
    const after = imports.concat(rest).join("\n");
    if (after === before) { console.log("SKIP " + cand + ": already clean"); return; }
    fs.writeFileSync(cand, after);
    console.log("PATCHED " + cand + ": @import hoisted to top, pre-base @tailwind lines dropped");
  })(process.argv[1]);
' "$DEST"

# 2d. Anima generates CommonJS configs (module.exports + require()) but the
#     package is "type": "module", so Node treats them as ESM — "module is not
#     defined", Tailwind silently loads no config, and every custom class in
#     the design resolves to nothing. Rewrite require() calls to imports and
#     module.exports to export default. Gated on the package actually being
#     ESM: in a CJS package these configs are valid as-is and the rewrite
#     would break them.
node -e '
  const fs = require("fs");
  (function (root) {
    const pkg = JSON.parse(fs.readFileSync(root + "/package.json", "utf8"));
    if (pkg.type !== "module") { console.log("SKIP cjs configs: package is CJS"); return; }
    const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => {
      if (e.name === "node_modules" || e.name === "dist" || e.name === ".git") return [];
      const p = d + "/" + e.name;
      return e.isDirectory() ? walk(p)
        : /(tailwind|postcss)\.config\.(ts|js)$/.test(e.name) ? [p] : [];
    });
    const ident = (name) => {
      const s = name
        .replace(/^@/, "")
        .replace(/[^a-zA-Z0-9]+([a-zA-Z0-9])/g, (_, c) => c.toUpperCase())
        .replace(/[^a-zA-Z0-9]/g, "");
      return /^[0-9]/.test(s) ? "_" + s : s;
    };
    const files = walk(root);
    if (!files.length) { console.log("SKIP cjs configs: none found"); return; }
    for (const f of files) {
      let c = fs.readFileSync(f, "utf8");
      if (!/module\.exports\s*=/.test(c)) { console.log("SKIP " + f + ": already ESM"); continue; }
      const imports = new Map();
      c = c.replace(/require\(\s*(["\x27])([^"\x27]+)\1\s*\)/g, (_, _q, dep) => {
        const name = ident(dep);
        imports.set(dep, name);
        return name;
      });
      c = c.replace(/module\.exports\s*=/, "export default");
      const header = [...imports]
        .map(([dep, name]) => "import " + name + " from \"" + dep + "\";")
        .join("\n");
      fs.writeFileSync(f, header ? header + "\n\n" + c : c);
      console.log("PATCHED " + f + ": module.exports -> export default" +
        (imports.size ? ", " + imports.size + " require() -> import" : ""));
    }
  })(process.argv[1]);
' "$DEST"

# 2e. Anima emits Google Fonts imports whose weight list contains CSS var()
#     tokens — meaningless inside a URL, so Google Fonts never serves the
#     font. Repair any such @import (every .css file): keep the concrete
#     weights, drop the var() tokens, and emit the css2 API form (ascending
#     unique weights, as css2 requires). Falls back to a stock weight range
#     only when no concrete weight survives.
node -e '
  const fs = require("fs");
  (function (root) {
    const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => {
      if (e.name === "node_modules" || e.name === "dist" || e.name === ".git") return [];
      const p = d + "/" + e.name;
      return e.isDirectory() ? walk(p) : p.endsWith(".css") ? [p] : [];
    });
    const fixLine = (l) => {
      if (!/^\s*@import\b/.test(l) || !l.includes("fonts.googleapis.com") || !l.includes("var(")) {
        return l;
      }
      const m = l.match(/family=([^"\x27]+)/);
      if (!m) return l;
      const fams = m[1].split("&")[0].split("|").map((seg) => {
        const [name, weightList] = seg.split(":");
        const weights = [...new Set((weightList || "")
          .split(",")
          .map((t) => parseInt(t, 10))
          .filter((n) => n >= 100 && n <= 900))]
          .sort((a, b) => a - b);
        return name + ":wght@" + (weights.length ? weights : [300, 400, 500, 600, 700]).join(";");
      });
      return "@import url(\"https://fonts.googleapis.com/css2?" +
        fams.map((f) => "family=" + f).join("&") + "&display=swap\");";
    };
    let patched = 0;
    for (const f of walk(root)) {
      const before = fs.readFileSync(f, "utf8");
      const after = before.split("\n").map(fixLine).join("\n");
      if (after !== before) {
        fs.writeFileSync(f, after);
        patched++;
        console.log("PATCHED " + f + ": var() font weights -> css2 concrete weights");
      }
    }
    if (!patched) console.log("SKIP google fonts: no var() imports found");
  })(process.argv[1]);
' "$DEST"

# 3. Install at the workspace root so the artifact's deps are linked.
echo "---- pnpm install (workspace root) ----"
pnpm install

# createArtifact kicks off a background install for the template's deps; if it
# raced this one, the artifact's bin links can come out incomplete. Verify the
# vite binary landed and reinstall from a clean node_modules if not.
if [ ! -f "$DEST/node_modules/.bin/vite" ]; then
  echo "vite binary missing after install (likely raced the createArtifact background install) — reinstalling"
  rm -rf "$DEST/node_modules"
  pnpm install
fi

echo "==== FIGMA SETUP DONE: $DEST ===="
echo "Start the 'figma-design' workflow, then verify the design renders."
