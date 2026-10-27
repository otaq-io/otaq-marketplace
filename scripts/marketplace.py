#!/usr/bin/env python3
"""The marketplace's CI (docs/marketplace.md in the otaq repository).

    python3 scripts/marketplace.py validate [--base REF]   # every plugin keeps the rules; changed ones bumped
    python3 scripts/marketplace.py release --repo OWNER/REPO # bundles for versions with no tag yet, and the index

`validate` checks what the Otaq installer checks again: the id is the folder's name, an OSI-approved or FSL license
with a LICENSE file, only text files (no binaries, no scripts in protocol 1), and every command runs a CLI the plugin
lists in `requires`. The mapping of recorded CLI output is checked by Otaq's own code (the `otaq` workflow step).

`release` writes `dist/<id>-<version>.json` (the bundle Otaq downloads: every file's path and text) for each plugin
version whose tag `plugins/<id>-v<version>` doesn't exist yet, and adds those versions, with their SHA256 and release
URL, to `plugins/index.json`. The workflow then tags, uploads and commits.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGINS = os.path.join(ROOT, "plugins")
INDEX = os.path.join(PLUGINS, "index.json")

# Kept the same as Otaq's `plugins/open_source.rs`.
LICENSES = {
    l.lower()
    for l in [
        "MIT", "MIT-0", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "0BSD", "Zlib", "MPL-2.0",
        "LGPL-2.1-only", "LGPL-2.1-or-later", "LGPL-3.0-only", "LGPL-3.0-or-later", "GPL-2.0-only",
        "GPL-2.0-or-later", "GPL-3.0-only", "GPL-3.0-or-later", "AGPL-3.0-only", "AGPL-3.0-or-later", "EPL-2.0",
        "EUPL-1.2", "Unlicense", "FSL-1.1-MIT", "FSL-1.1-ALv2", "FSL-1.1-Apache-2.0",
    ]
}
TEXT_EXTENSIONS = {"yaml", "yml", "md", "txt", "json"}
PLAIN_NAMES = {"license", "licence", "copying", "notice", "authors"}
MAGIC = [b"\x7fELF", b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf", b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe",
         b"\xca\xfe\xba\xbe", b"MZ"]


def plugin_dirs():
    return sorted(
        d for d in os.listdir(PLUGINS) if os.path.isdir(os.path.join(PLUGINS, d)) and not d.startswith(".")
    )


def files_of(folder):
    out = []
    for base, dirs, names in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for name in sorted(names):
            if name.startswith("."):
                continue
            path = os.path.join(base, name)
            if os.path.islink(path):
                raise SystemExit(f"{path} is a symbolic link: plugins hold plain files")
            out.append((os.path.relpath(path, folder).replace(os.sep, "/"), path))
    return out


def problems(folder):
    found = []
    name = os.path.basename(folder)
    try:
        with open(os.path.join(folder, "plugin.yaml"), encoding="utf-8") as f:
            manifest = yaml.safe_load(f)
    except (OSError, yaml.YAMLError) as e:
        return [f"{name}: plugin.yaml can't be read: {e}"], None
    if manifest.get("id") != name:
        found.append(f"{name}: id is {manifest.get('id')!r}, not the folder's name")
    if manifest.get("protocol") != 1:
        found.append(f"{name}: protocol must be 1")
    if str(manifest.get("license", "")).lower() not in LICENSES:
        found.append(f"{name}: {manifest.get('license')!r} isn't an OSI-approved or FSL license")
    required = {r.get("id") for r in manifest.get("requires", [])}
    for command, spec in (manifest.get("commands") or {}).items():
        if "script" in spec:
            found.append(f"{name}: commands.{command}: script commands come in a later protocol")
        run = spec.get("run") or []
        if not run or run[0] not in required:
            found.append(f"{name}: commands.{command} runs {run[:1]}, which isn't in requires")
    has_license = False
    for rel, path in files_of(folder):
        base = rel.rsplit("/", 1)[-1]
        if "/" not in rel and base.split(".")[0].lower() in {"license", "licence", "copying"}:
            has_license = True
        with open(path, "rb") as f:
            data = f.read()
        if any(data.startswith(m) for m in MAGIC):
            found.append(f"{name}/{rel} is a program: plugins contain no binaries")
            continue
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            found.append(f"{name}/{rel} isn't text: plugins contain no binaries")
            continue
        ext = base.rsplit(".", 1)[-1].lower() if "." in base[1:] else ""
        if ext not in TEXT_EXTENSIONS and base.lower() not in PLAIN_NAMES:
            found.append(f"{name}/{rel}: a plugin holds only its manifest, docs, license and test fixtures")
        if len(data) > 1024 * 1024:
            found.append(f"{name}/{rel} is over 1 MB")
    if not has_license:
        found.append(f"{name}: no LICENSE file")
    return found, manifest


def tag_of(plugin, version):
    return f"plugins/{plugin}-v{version}"


def tags():
    out = subprocess.run(["git", "tag", "--list", "plugins/*"], cwd=ROOT, capture_output=True, text=True, check=True)
    return set(out.stdout.split())


def changed_since(base, folder):
    out = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD", "--", folder], cwd=ROOT, capture_output=True, text=True
    )
    return out.returncode == 0 and out.stdout.strip() != ""


def validate(base):
    all_problems = []
    existing = tags()
    for name in plugin_dirs():
        folder = os.path.join(PLUGINS, name)
        found, manifest = problems(folder)
        all_problems += found
        if manifest and base and changed_since(base, folder):
            if tag_of(name, manifest.get("version")) in existing:
                all_problems.append(f"{name}: changed, so bump its version (v{manifest.get('version')} is released)")
    for p in all_problems:
        print(f"::error::{p}")
    if all_problems:
        sys.exit(1)
    print(f"{len(plugin_dirs())} plugins keep the rules")


def bundle(name, manifest):
    folder = os.path.join(PLUGINS, name)
    files = []
    for rel, path in files_of(folder):
        with open(path, encoding="utf-8") as f:
            files.append({"path": rel, "text": f.read()})
    data = {"format": 1, "id": name, "version": str(manifest["version"]), "files": files}
    return (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def release(repo):
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
    with open(INDEX, encoding="utf-8") as f:
        index = json.load(f)
    existing = tags()
    made = []
    for name in plugin_dirs():
        found, manifest = problems(os.path.join(PLUGINS, name))
        if found:
            raise SystemExit("\n".join(found))
        version = str(manifest["version"])
        tag = tag_of(name, version)
        if tag in existing:
            continue
        data = bundle(name, manifest)
        asset = f"{name}-{version}.json"
        with open(os.path.join(ROOT, "dist", asset), "wb") as f:
            f.write(data)
        entry = next((p for p in index["plugins"] if p["id"] == name), None)
        if entry is None:
            entry = {"id": name, "versions": []}
            index["plugins"].append(entry)
        entry.update(
            {
                "name": manifest["name"],
                "description": manifest.get("description", ""),
                "license": manifest["license"],
                "maintainers": manifest.get("maintainers", []),
            }
        )
        entry["versions"] = [v for v in entry["versions"] if v["version"] != version] + [
            {
                "version": version,
                "protocol": manifest["protocol"],
                "otaq": manifest["otaq"],
                "url": f"https://github.com/{repo}/releases/download/{tag}/{asset}",
                "sha256": hashlib.sha256(data).hexdigest(),
                "tag": tag,
                "requires": [r["id"] for r in manifest.get("requires", [])],
                "capabilities": manifest.get("capabilities", []),
            }
        ]
        made.append({"tag": tag, "asset": f"dist/{asset}", "title": f"{manifest['name']} {version}"})
    index["plugins"].sort(key=lambda p: p["id"])
    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)
        f.write("\n")
    with open(os.path.join(ROOT, "dist", "releases.json"), "w", encoding="utf-8") as f:
        json.dump(made, f, indent=2)
    print(f"{len(made)} new releases")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    v = sub.add_parser("validate")
    v.add_argument("--base")
    r = sub.add_parser("release")
    r.add_argument("--repo", required=True)
    args = parser.parse_args()
    if args.command == "validate":
        validate(args.base)
    else:
        release(args.repo)


if __name__ == "__main__":
    main()
