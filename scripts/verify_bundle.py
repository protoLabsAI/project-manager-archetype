#!/usr/bin/env python3
"""Verify a bundle's pin set against a protoAgent checkout (ADR 0049).

Installs the bundle (at its pinned refs) into a SCRATCH agent, enables every member,
loads them through the real plugin loader, and probes every declared console-view
path over HTTP — the check that catches "the pin predates the view fix" before an
operator spawns a broken archetype.

Run from inside a protoAgent checkout with deps synced (the verify workflow does
exactly this):

    uv run --no-sync python /path/to/bundle/scripts/verify_bundle.py /path/to/bundle

The bundle path must be a git repo (a CI checkout is); the installer clones from it.
Exit code 0 = every member installed, loaded with the bundle's recommended config, every
declared view answered 200, and every tool the archetype's capability contract names
actually registered.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


def main(bundle_src: str) -> int:
    # The cwd is the protoAgent checkout (`python <script>` puts the SCRIPT's dir on
    # sys.path, not the cwd — `graph` wouldn't import without this).
    sys.path.insert(0, os.getcwd())
    # Scope EVERYTHING to a throwaway dir before importing graph modules — the
    # installer reads PROTOAGENT_PLUGINS_LOCK at import time, the rest at call time.
    scratch = Path(tempfile.mkdtemp(prefix="bundle-verify-"))
    (scratch / "cfg").mkdir()
    os.environ["PROTOAGENT_CONFIG_DIR"] = str(scratch / "cfg")
    os.environ["PROTOAGENT_PLUGINS_DIR"] = str(scratch / "cfg" / "plugins")
    os.environ["PROTOAGENT_PLUGINS_LOCK"] = str(scratch / "plugins.lock")

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from graph.config import LangGraphConfig
    from graph.plugins import installer
    from graph.plugins.loader import load_plugins, load_manifest

    failures: list[str] = []

    # ── 1. INSTALL the bundle at its pinned refs (fan-out, ADR 0040) ─────────────
    print(f"installing bundle from {bundle_src} …")
    summary = installer.install(bundle_src)
    if "bundle" not in summary:
        print("FAIL: source is a single plugin, not a bundle manifest")
        return 1
    members = [s["id"] for s in summary["installed"]]
    builtins = summary["skipped_builtin"]
    for s in summary["installed"]:
        print(f"  installed {s['id']}@{s['resolved_sha'][:10]} (ref {s.get('requested_ref') or 'HEAD'})")

    # ── 2. ENABLE everything the bundle suggests, APPLY the bundle's recommended
    #      `config:` + the config_inputs DEFAULTS, then LOAD through the real loader ──
    # The config is what a fresh member boots with BEFORE the operator answers the
    # Configure step: the recommended `config:` block (e.g. `github.write: true`, which
    # is what registers the tool the capability contract requires) and every declared
    # input's default. Loading without them verified a member no one ever gets.
    import yaml

    enabled = list(dict.fromkeys((summary.get("enabled") or []) + members))
    cfg_doc: dict = {"plugins": {"enabled": enabled, "plugins_dir": str(scratch / "cfg" / "plugins")}}
    for section, values in (summary.get("config") or {}).items():
        if isinstance(values, dict):
            cfg_doc.setdefault(section, {}).update(values)
    declared_inputs = list(summary.get("config_inputs") or [])
    for dec in declared_inputs:
        if "default" in dec and dec["default"] is not None:
            node = cfg_doc
            parts = str(dec["key"]).split(".")
            for seg in parts[:-1]:
                node = node.setdefault(seg, {})
            node.setdefault(parts[-1], dec["default"])
    cfg_path = scratch / "cfg" / "langgraph-config.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg_doc, sort_keys=False))
    for dec in declared_inputs:
        flag = " required" if dec.get("required") else ""
        print(f"  config input {dec['key']} ({dec['type']}{flag})")
    res = load_plugins(LangGraphConfig.from_yaml(str(cfg_path)))
    meta_by_id = {m["id"]: m for m in res.meta}
    for pid in members + builtins:
        m = meta_by_id.get(pid)
        if m is None:
            failures.append(f"{pid}: not found by the loader")
        elif not m.get("loaded"):
            failures.append(f"{pid}: failed to load — {m.get('error')}")
        else:
            print(f"  loaded {pid}: {len(m.get('tools') or [])} tool(s)")

    # ── 3. PROBE every declared console-view path over HTTP ──────────────────────
    app = FastAPI()
    for r in res.routers:
        app.include_router(r["router"], prefix=r.get("prefix", ""))
    client = TestClient(app)
    root = installer.live_plugins_dir()
    for pid in members:
        manifest = load_manifest(root / pid)
        for view in manifest.views if manifest else []:
            path = view.get("path", "")
            if not path:
                continue
            status = client.get(path).status_code
            ok = status == 200
            print(f"  view {pid} {path!r} -> {status}{'' if ok else '  ✗'}")
            if not ok:
                failures.append(f"{pid}: view {path!r} returned {status}")

    # ── 4. CAPABILITY CONTRACT: every tool the archetype's persona commits to must
    #      actually register with the bundle's recommended config (ADR 0100) ────────
    # This is the check that would have caught the 2026-08-21 first-run banner
    # (`github.write: false` seeded → `github_create_issue` never bound).
    bound = {
        str(getattr(t, "name", t))
        for m in res.meta
        for t in (m.get("tools") or [])
    }
    manifest_doc = yaml.safe_load((Path(bundle_src) / "protoagent.bundle.yaml").read_text()) or {}
    requires = list(((manifest_doc.get("archetype") or {}).get("requires_tools")) or [])
    for name in requires:
        if name in bound:
            print(f"  contract {name}: bound")
        else:
            failures.append(f"capability contract: {name!r} is required by the archetype but no member registered it")
    # Every `required` Configure input must be askable (a widget exists for its type) —
    # an unknown type would make the Configure step skip the very answer the gate needs.
    for dec in declared_inputs:
        if dec.get("required") and dec.get("type") not in ("string", "path", "delegate", "boolean"):
            failures.append(f"config input {dec['key']!r}: required but type {dec.get('type')!r} has no widget")

    if failures:
        print(f"\nFAIL ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"\nOK — {len(members)} member(s) installed+loaded, all declared views serve 200, contract {requires} bound.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
