#!/usr/bin/env python3
"""Build the source-protected wheel and verify it ships no business .py.

Must run ON the target platform (native extensions do not cross-compile:
mac builds .so for mac, Windows builds .pyd for Windows). The interpreter
tag must match the Allo base runtime: cp312.

Usage:
  python3 build_wheel.py            # builds into dist/, then audits the wheel
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIST = HERE / "dist"
REQUIRED_PY = "3.12"  # Allo base bundles cp312 — the wheel MUST be built with it

# Source that is ALLOWED inside the wheel (trivial re-exports only).
ALLOWED_PY = {"demo_biz_core/__init__.py"}


def _build() -> Path:
    if DIST.exists():
        shutil.rmtree(DIST)
    uv = shutil.which("uv")
    if uv:
        subprocess.run([uv, "build", "--wheel", "--python", REQUIRED_PY, "--out-dir", str(DIST)], cwd=HERE, check=True)
    else:
        if f"{sys.version_info.major}.{sys.version_info.minor}" != REQUIRED_PY:
            sys.exit(f"no uv found and this interpreter is not {REQUIRED_PY}; install uv or run with python{REQUIRED_PY}")
        subprocess.run([sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "-w", str(DIST)], cwd=HERE, check=True)
    wheels = sorted(DIST.glob("*.whl"))
    if len(wheels) != 1:
        sys.exit(f"expected exactly one wheel in {DIST}, got {[w.name for w in wheels]}")
    return wheels[0]


def _audit(wheel: Path) -> None:
    if "cp312" not in wheel.name:
        sys.exit(f"AUDIT FAIL: {wheel.name} is not a cp312 wheel — the Allo base runtime cannot load it")
    if wheel.name.endswith("any.whl"):
        sys.exit(f"AUDIT FAIL: {wheel.name} is a pure-python wheel — nothing got compiled")
    names = zipfile.ZipFile(wheel).namelist()
    leaked = [n for n in names if n.endswith((".py", ".pyx", ".pyc", ".c")) and n not in ALLOWED_PY]
    if leaked:
        sys.exit(f"AUDIT FAIL: source files leaked into the wheel: {leaked}")
    natives = [n for n in names if n.endswith((".so", ".pyd"))]
    if not natives:
        sys.exit("AUDIT FAIL: no native extension found in the wheel")
    print(f"\nAUDIT OK: {wheel.name}")
    print(f"  native modules: {natives}")
    print(f"  shipped python source (allowed re-exports only): {sorted(n for n in names if n.endswith('.py'))}")


if __name__ == "__main__":
    _audit(_build())
