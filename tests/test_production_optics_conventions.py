"""Repository-wide contracts for production optics calculations."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_ROOTS = ("loco_common", "method1_madng_da", "method2_delta_orbit", "scripts")


def production_python_files():
    for directory in PRODUCTION_ROOTS:
        yield from (ROOT / directory).rglob("*.py")


def test_every_production_run_twiss_explicitly_uses_method_6():
    missing = []
    for path in production_python_files():
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func
            if not isinstance(function, ast.Attribute) or function.attr != "run_twiss":
                continue
            method = next((kw.value for kw in node.keywords if kw.arg == "method"), None)
            if not isinstance(method, ast.Constant) or method.value != 6:
                missing.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert not missing, f"Production run_twiss calls without method=6: {missing}"


def test_xtrack_is_not_imported_by_production_code():
    imports = []
    for path in production_python_files():
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            if any(name == "xtrack" or name.startswith("xtrack_tools") for name in names):
                imports.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert not imports, f"Production xtrack imports: {imports}"
