#!/usr/bin/env python3
"""Regenerate index.json — the machine-readable catalog of every plugin here.

Each plugin directory's plugin.json (id, name, kind, permissions, settings)
plus its README (the one-line blurb right under the H1) becomes one entry.
Categories mirror the sections of README.md. Run after adding or changing a
plugin:

    python3 build_index.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
GITHUB_OWNER = "DJTouchette"

# Mirrors the section grouping in README.md. A new plugin must be added here
# (the script fails loudly otherwise, so the index can't silently drift).
CATEGORIES = {
    "fleet-radar": "dashboards",
    "cost-hud": "dashboards",
    "focus-tracker": "dashboards",
    "policy-approver": "automation",
    "fleet-guardian": "automation",
    "escalation-chains": "automation",
    "typecheck-gate": "automation",
    "test-on-save": "automation",
    "ci-watcher": "automation",
    "analytics": "dashboards",
    "shiplight": "dashboards",
    "project-notes": "workbench",
    "project-board": "workbench",
    "worktree-janitor": "workbench",
    "slack-bridge": "reach",
    "phone-push": "reach",
    "standup-digest": "reach",
}


def readme_blurb(path):
    """First non-empty line after the H1 title — each README keeps a
    one-sentence summary there."""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return ""
    seen_title = False
    for line in lines:
        if line.startswith("# "):
            seen_title = True
            continue
        if seen_title and line.strip():
            return line.strip()
    return ""


def entry(dirname):
    with open(os.path.join(ROOT, dirname, "plugin.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    if dirname not in CATEGORIES:
        sys.exit(f"error: {dirname} has no category in build_index.py — add it")
    repo = f"{GITHUB_OWNER}/workspacer-plugin-{dirname}"
    panes = manifest.get("panes") or []
    return {
        "id": manifest["id"],
        "name": manifest.get("name", dirname),
        "version": manifest.get("version", ""),
        "dir": dirname,
        "category": CATEGORIES[dirname],
        "kind": "sidecar" if manifest.get("server") else "webview",
        "icon": panes[0].get("icon", "") if panes else "",
        "description": readme_blurb(os.path.join(ROOT, dirname, "README.md")),
        "repo": f"https://github.com/{repo}",
        "install": repo,
        "panes": [p.get("title", "") for p in panes],
        "capabilities": [
            c["method"] if isinstance(c, dict) else c
            for c in manifest.get("capabilities") or []
        ],
        "consumes": manifest.get("consumes") or [],
        "emits": manifest.get("emits") or [],
        "settings": [s["key"] for s in manifest.get("settings") or []],
    }


def main():
    dirs = sorted(
        d
        for d in os.listdir(ROOT)
        if os.path.isfile(os.path.join(ROOT, d, "plugin.json"))
    )
    order = {"dashboards": 0, "workbench": 1, "automation": 2, "reach": 3}
    plugins = sorted(
        (entry(d) for d in dirs), key=lambda e: (order[e["category"]], e["dir"])
    )
    index = {
        "version": 1,
        "catalog": f"https://github.com/{GITHUB_OWNER}/workspacer-plugins",
        "plugins": plugins,
    }
    out = os.path.join(ROOT, "index.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"wrote {out} ({len(plugins)} plugins)")


if __name__ == "__main__":
    main()
