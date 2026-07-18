"""Build backend hooks: cythonize the business modules and keep their .py
source OUT of the wheel.

Every module listed in COMPILED_MODULES is compiled to a native extension
(.so on macOS / .pyd on Windows). The custom build_py then drops those .py
files from the pure-python payload, so the wheel ships machine code only.

__init__.py stays as source on purpose — keep it a trivial re-export with
zero business logic.
"""

from setuptools import Extension, setup
from setuptools.command.build_py import build_py as _build_py

try:
    from Cython.Build import cythonize
except ImportError as exc:  # pragma: no cover - build isolation installs it
    raise SystemExit("Cython is required to build this wheel (see pyproject build-system)") from exc

# module name -> source file. Add one line per protected module.
COMPILED_MODULES = {
    "demo_biz_core.engine": "src/demo_biz_core/engine.py",
}

_COMPILED_SHORT_NAMES = {name.rsplit(".", 1)[-1] for name in COMPILED_MODULES}


class build_py(_build_py):
    def find_package_modules(self, package, package_dir):
        modules = super().find_package_modules(package, package_dir)
        return [
            (pkg, mod, path)
            for pkg, mod, path in modules
            if not (f"{pkg}.{mod}" in COMPILED_MODULES or mod in _COMPILED_SHORT_NAMES)
        ]


setup(
    ext_modules=cythonize(
        [Extension(name, [src]) for name, src in COMPILED_MODULES.items()],
        language_level="3",
        # No .c/.html build artifacts next to the sources.
        build_dir="build/cython",
    ),
    cmdclass={"build_py": build_py},
)
