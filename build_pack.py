#!/usr/bin/env python3
"""Build a capability-pack OTA payload + manifest (protocol §6).

Stages the pack payload (pack.json + backend-ext/ + optional wheels/, assets/,
docs/) under ``<out>/<version>/`` and writes a per-platform manifest that the
desktop client's ota.ts validateManifest(kind="allo-capability-pack") accepts:
schemaVersion 2, kind, channel, version (x.y.z-beta.N), compatibility, per-file
sha256+size, and the bundleHash = sha256 of the sorted "path:sha256" lines.

pydeps/ (the client-side pip target), versions/, staging/, dist/ and pycache
are never part of a payload. wheels/ IS payload — populate it separately
(pip download per platform) before building a release with binary deps.

Usage:
  python packs/build_pack.py packs/tender_assistant \
      --version 0.1.0-beta.1 --platform darwin --arch arm64 --out packs/tender_assistant/dist
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform as _platform
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

PACK_KIND = "allo-capability-pack"
MANIFEST_SCHEMA = 2
BETA_VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)-beta\.([1-9]\d*)$")

# pip --platform tags for cross-platform wheel fetching (only-binary). The host
# platform uses a native download (no tag) which resolves multi-tag wheels
# (universal2 etc.) reliably.
_PIP_PLATFORM_TAGS = {
    ("win32", "x64"): ["win_amd64"],
    ("darwin", "arm64"): ["macosx_11_0_arm64", "macosx_11_0_universal2", "macosx_10_9_universal2"],
    ("darwin", "x64"): ["macosx_10_9_x86_64", "macosx_10_9_universal2"],
    ("linux", "x64"): ["manylinux2014_x86_64", "manylinux_2_17_x86_64"],
}


def _pip_executable() -> list[str]:
    """A python -m pip invocation that actually has pip (uv venvs don't)."""
    for candidate in (sys.executable, shutil.which("python3"), shutil.which("python")):
        if candidate and subprocess.run([candidate, "-m", "pip", "--version"], capture_output=True).returncode == 0:
            return [candidate, "-m", "pip"]
    sys.exit("no python with pip found for wheel download (install pip, or run on a machine that has it)")


def fetch_wheels(pack_dir: Path, platform: str, arch: str, python_version: str) -> None:
    """pip-download the pack's declared wheels into ``<pack_dir>/wheels/``
    (cleared first; gitignored). Always resolves for the TARGET runtime
    (cp<python_version>, target platform) regardless of the build host, since
    the desktop pack always runs the bundled 3.12 interpreter."""
    req = pack_dir / "wheels-requirements.txt"
    if not req.is_file():
        print("no wheels-requirements.txt — pack ships no binary deps")
        return
    tags = _PIP_PLATFORM_TAGS.get((platform, arch))
    if not tags:
        sys.exit(f"no pip platform tags for {platform}-{arch}")
    wheels = pack_dir / "wheels"
    if wheels.exists():
        shutil.rmtree(wheels)
    wheels.mkdir(parents=True)
    abi = f"cp{python_version.replace('.', '')}"
    cmd = [*_pip_executable(), "download", "-r", str(req), "--only-binary", ":all:", "--python-version", python_version, "--implementation", "cp", "--abi", abi, "-d", str(wheels)]
    for tag in tags:
        cmd += ["--platform", tag]
    print(f"fetching wheels for {platform}-{arch} cp{python_version.replace('.', '')}...")
    subprocess.run(cmd, check=True)
    shutil.copyfile(req, wheels / "requirements.txt")  # the client's pip install prefers this


def _host_platform() -> tuple[str, str]:
    machine = _platform.machine().lower()
    arch = "arm64" if machine in ("arm64", "aarch64") else "x64" if machine in ("x86_64", "amd64") else machine
    return sys.platform if sys.platform in ("win32", "darwin") else "linux", arch

# Only these top-level entries are payload (mirrors the pack kind's path allowlist).
PAYLOAD_ROOTS = ("pack.json", "backend-ext", "wheels", "assets", "docs")
_SKIP_DIRS = {"__pycache__", "pydeps", "versions", "staging", "dist", ".git"}
_SKIP_SUFFIXES = {".pyc", ".pyo"}
_SKIP_NAMES = {".DS_Store"}


def _payload_files(pack_dir: Path) -> list[Path]:
    files: list[Path] = []
    for root in PAYLOAD_ROOTS:
        entry = pack_dir / root
        if entry.is_file():
            files.append(entry)
        elif entry.is_dir():
            for path in entry.rglob("*"):
                if not path.is_file():
                    continue
                parts = set(path.relative_to(pack_dir).parts)
                if parts & _SKIP_DIRS or path.suffix in _SKIP_SUFFIXES or path.name in _SKIP_NAMES:
                    continue
                files.append(path)
    return sorted(files, key=lambda p: p.relative_to(pack_dir).as_posix())


def build(pack_dir: Path, version: str, channel: str, platform: str, arch: str, out: Path, min_desktop: str | None) -> dict:
    if not BETA_VERSION_RE.match(version):
        sys.exit(f"version {version!r} must be x.y.z-beta.N")
    meta = json.loads((pack_dir / "pack.json").read_text(encoding="utf-8"))
    feature_key = meta["featureKey"]

    version_dir = out / version
    if version_dir.exists():
        shutil.rmtree(version_dir)
    version_dir.mkdir(parents=True)

    files: list[dict] = []
    for src in _payload_files(pack_dir):
        rel = src.relative_to(pack_dir).as_posix()
        data = src.read_bytes()
        dst = version_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        # allo-admin's manifest.ts validates a file `url` against its own storage
        # prefix, so file entries carry ONLY path/sha256/size — the server derives
        # artifactBaseUrl itself at serve time.
        files.append({"path": rel, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)})

    if not any(f["path"] == "pack.json" for f in files):
        sys.exit("pack.json missing from payload root")
    manifest = {
        "schemaVersion": MANIFEST_SCHEMA,
        "kind": PACK_KIND,
        "channel": f"pack.{feature_key}.{channel}",
        "version": version,
        "compatibility": {"platforms": [platform], "arches": [arch], **({"minDesktopVersion": min_desktop} if min_desktop else {})},
        "files": files,
        "fileCount": len(files),
        "totalSize": sum(f["size"] for f in files),
    }
    # Upload artifact = a zip with manifest.json at the payload root + every declared
    # file at its path (the shape the allo-admin OTA console ingests).
    (version_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    zip_path = out / f"{feature_key}-{version}-{platform}-{arch}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(version_dir / "manifest.json", "manifest.json")
        for f in files:
            zf.write(version_dir / f["path"], f["path"])

    wheels = [f for f in files if f["path"].startswith("wheels/")]
    print(f"pack {feature_key} {version} channel={manifest['channel']} [{platform}-{arch}]: {len(files)} files, {manifest['totalSize']} bytes, {len(wheels)} wheel file(s)")
    if meta.get("backendExt") and not wheels:
        print("  note: no wheels/ shipped — the pack relies entirely on base deps at runtime")
    print(f"  upload zip -> {zip_path}")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a capability-pack OTA payload + manifest.")
    parser.add_argument("pack_dir", type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--channel", default="beta")
    parser.add_argument("--platform", default=_host_platform()[0])
    parser.add_argument("--arch", default=_host_platform()[1])
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--min-desktop-version", default=None, help="compatibility.minDesktopVersion (optional)")
    parser.add_argument("--fetch-wheels", action="store_true", help="pip-download the pack's wheels-requirements.txt for the target platform first")
    parser.add_argument("--python-version", default="3.12")
    args = parser.parse_args(argv)
    pack_dir = args.pack_dir.resolve()
    if not (pack_dir / "pack.json").is_file():
        parser.error(f"{pack_dir} has no pack.json")
    if args.fetch_wheels:
        fetch_wheels(pack_dir, args.platform, args.arch, args.python_version)
    out = args.out.resolve() if args.out else pack_dir / "dist"
    build(pack_dir, args.version, args.channel, args.platform, args.arch, out, args.min_desktop_version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
