"""Repository-wide contracts for production optics calculations."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_ROOTS = ("loco_common", "method1_madng_da", "method2_delta_orbit", "scripts")


def production_python_files():
    for directory in PRODUCTION_ROOTS:
        yield from (ROOT / directory).rglob("*.py")


#: The integration orders a production ``run_twiss`` may pin; 8 is for the skew-multipole case and needs ``nslice=2``.
ALLOWED_METHODS = (6, 8)


def _run_twiss_calls(tree: ast.AST):
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if not isinstance(function, ast.Attribute) or function.attr != "run_twiss":
            continue
        yield node


def test_every_production_run_twiss_explicitly_pins_its_method():
    missing = []
    for path in production_python_files():
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in _run_twiss_calls(tree):
            method = next((kw.value for kw in node.keywords if kw.arg == "method"), None)
            if not isinstance(method, ast.Constant) or method.value not in ALLOWED_METHODS:
                missing.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert not missing, (
        f"Production run_twiss calls without a literal method in {ALLOWED_METHODS}: {missing}"
    )


def test_every_production_method_8_call_pins_nslice_2():
    wrong = []
    for path in production_python_files():
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in _run_twiss_calls(tree):
            method = next((kw.value for kw in node.keywords if kw.arg == "method"), None)
            if not (isinstance(method, ast.Constant) and method.value == 8):
                continue
            nslice = next((kw.value for kw in node.keywords if kw.arg == "nslice"), None)
            if not isinstance(nslice, ast.Constant) or nslice.value != 2:
                wrong.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert not wrong, f"Production method=8 run_twiss calls without nslice=2: {wrong}"


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
