"""Architectural tests: enforce module boundaries and import conventions."""

import ast
import pathlib

from pytestarch import Rule, get_evaluable_architecture

_ROOT = str(pathlib.Path(__file__).resolve().parents[1])
_SRC = str(pathlib.Path(__file__).resolve().parents[1] / "evlampiy")

_arch = get_evaluable_architecture(_ROOT, _SRC)

# Prefix depends on the project directory name (differs locally vs CI).
# Detect it from the graph nodes: find node ending with ".evlampiy.const" and strip ".const".
_PREFIX = next(n.removesuffix(".const") for n in _arch._graph._graph.nodes() if n.endswith(".evlampiy.const"))


# --- Rule 1: telegram <-> whatsapp domain isolation ---


class TestDomainIsolation:
    def test_telegram_does_not_import_whatsapp(self):
        rule = (
            Rule()
            .modules_that()
            .are_sub_modules_of(f"{_PREFIX}.telegram")
            .should_not()
            .import_modules_that()
            .are_sub_modules_of(f"{_PREFIX}.whatsapp")
        )
        rule.assert_applies(_arch)

    def test_whatsapp_does_not_import_telegram(self):
        rule = (
            Rule()
            .modules_that()
            .are_sub_modules_of(f"{_PREFIX}.whatsapp")
            .should_not()
            .import_modules_that()
            .are_sub_modules_of(f"{_PREFIX}.telegram")
        )
        rule.assert_applies(_arch)


# --- Rule 2: transcription is independent of delivery channels ---


class TestTranscriptionIndependence:
    def test_transcription_does_not_import_telegram(self):
        rule = (
            Rule()
            .modules_that()
            .are_sub_modules_of(f"{_PREFIX}.transcription")
            .should_not()
            .import_modules_that()
            .are_sub_modules_of(f"{_PREFIX}.telegram")
        )
        rule.assert_applies(_arch)

    def test_transcription_does_not_import_whatsapp(self):
        rule = (
            Rule()
            .modules_that()
            .are_sub_modules_of(f"{_PREFIX}.transcription")
            .should_not()
            .import_modules_that()
            .are_sub_modules_of(f"{_PREFIX}.whatsapp")
        )
        rule.assert_applies(_arch)


# --- Rule 3: services layer is framework-agnostic ---


class TestServicesFrameworkIsolation:
    """`evlampiy/services/*` must not import aiogram / pywa / fastapi.

    Catches regressions where a use-case service starts depending on a delivery channel.
    """

    def test_services_do_not_import_aiogram(self):
        violations = _services_importing(("aiogram",))
        assert not violations, "services modules import aiogram (must stay framework-agnostic):\n" + "\n".join(
            f"  {v}" for v in violations
        )

    def test_services_do_not_import_pywa(self):
        violations = _services_importing(("pywa", "pywa_async"))
        assert not violations, "services modules import pywa (must stay framework-agnostic):\n" + "\n".join(
            f"  {v}" for v in violations
        )

    def test_services_do_not_import_fastapi(self):
        violations = _services_importing(("fastapi", "uvicorn"))
        assert not violations, "services modules import fastapi/uvicorn (must stay framework-agnostic):\n" + "\n".join(
            f"  {v}" for v in violations
        )

    def test_services_do_not_import_telegram_handlers(self):
        """Services must not depend on adapter modules — that's an inversion."""
        rule = (
            Rule()
            .modules_that()
            .are_sub_modules_of(f"{_PREFIX}.services")
            .should_not()
            .import_modules_that()
            .are_sub_modules_of(f"{_PREFIX}.telegram")
        )
        rule.assert_applies(_arch)


def _services_importing(packages: tuple[str, ...]) -> list[str]:
    """Services modules that import any of the top-level ``packages``.

    The pytestarch graph leaves external libraries out, so the imports are read from the AST.
    """
    services = pathlib.Path(_SRC) / "services"
    modules = sorted(services.rglob("*.py"))
    assert modules, f"{services} has no modules: the check would pass vacuously"
    violations = []
    for py_file in modules:
        imported = _imported_packages(ast.parse(py_file.read_text(), filename=str(py_file)))
        violations.extend(f"{py_file.relative_to(_SRC)} → {name}" for name in sorted(imported.intersection(packages)))
    return violations


def _imported_packages(tree: ast.AST) -> set[str]:
    """Top-level names of the absolute imports in ``tree``."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.partition(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.partition(".")[0])
    return names


# --- Rule 4: stdlib imports through module, not from-imports ---

# Modules that must be imported as `import X`, never `from X import ...`
_STDLIB_MODULE_IMPORTS = ("datetime", "typing")


class TestStdlibImportStyle:
    def test_no_from_imports_of_guarded_stdlib_modules(self):
        """Enforce `import datetime` / `import typing` style (not from-imports)."""
        violations = []
        for py_file in pathlib.Path(_SRC).rglob("*.py"):
            tree = ast.parse(py_file.read_text(), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module in _STDLIB_MODULE_IMPORTS:
                    rel = py_file.relative_to(_SRC)
                    names = ", ".join(alias.name for alias in node.names)
                    violations.append(f"{rel}:{node.lineno} — from {node.module} import {names}")
        assert not violations, "Stdlib modules must be imported as `import X`, not `from X import ...`:\n" + "\n".join(
            f"  {v}" for v in violations
        )
