#!/usr/bin/env python3
"""
Format `data/links.json` (sort keys, ensure required fields) and commit
the result back to the repo when changes are made. Intended for use from
a GitHub Actions workflow using the repo's GITHUB_TOKEN.

This script is intentionally conservative: it won't remove or alter
exophase usernames, only normalises the JSON layout and ensures every
entry has an `updated_at` unix timestamp.
"""
import json
import os
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
LINKS_FILE = REPO_ROOT / "data" / "links.json"


def load_links(path: Path):
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_links(data: dict) -> dict:
    out = {}
    now = int(time.time())

    # Sort keys numerically if possible, otherwise lexicographically
    def sort_key(k: str):
        try:
            return (0, int(k))
        except Exception:
            return (1, k)

    for key in sorted(data.keys(), key=sort_key):
        entry = data[key] or {}
        # Ensure minimal expected fields exist
        username = entry.get("exophase_username")
        updated_at = entry.get("updated_at") or now

        # Keep other metadata intact; just normalise these two fields
        new_entry = dict(entry)
        if username is None:
            # preserve as-is (no username) but still write updated_at
            new_entry.setdefault("exophase_username", None)
        new_entry["updated_at"] = int(updated_at)

        out[str(key)] = new_entry

    return out


def write_links(path: Path, data: dict):
    tmp = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(tmp)


def main():
    orig = load_links(LINKS_FILE)
    norm = normalize_links(orig)

    # Compare by JSON text to avoid ordering differences
    import io
    orig_text = json.dumps(orig, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    norm_text = json.dumps(norm, indent=2, sort_keys=True, ensure_ascii=False) + "\n"

    if orig_text == norm_text:
        print("No changes needed for data/links.json")
        return 0

    write_links(LINKS_FILE, norm)
    print("Updated data/links.json; committing changes")

    # Commit and push using the environment-provided GITHUB_TOKEN
    github_actor = os.environ.get("GITHUB_ACTOR", "github-actions[bot]")
    try:
        # Configure git
        from subprocess import check_call

        check_call(["git", "config", "user.name", github_actor])
        check_call(["git", "config", "user.email", f"{github_actor}@users.noreply.github.com"]) 

        check_call(["git", "add", str(LINKS_FILE)])
        check_call(["git", "commit", "-m", "ci(links): normalise data/links.json\n\nAutomated formatting by GitHub Actions"])
        # Push back to the current branch
        # GITHUB_REF and GITHUB_REPOSITORY are available in Actions
        remote = os.environ.get("GITHUB_REPOSITORY")
        if remote:
            # push to origin
            check_call(["git", "push", "origin", "HEAD:refs/heads/" + os.environ.get("GITHUB_REF_NAME", os.environ.get("GITHUB_REF", "main"))])
        else:
            check_call(["git", "push"])
    except Exception as e:
        print("Failed to commit/push changes:", e)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
