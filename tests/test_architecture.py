"""Architectural tests: enforce module boundaries and import conventions."""

import ast
import pathlib
import re

from pytestarch import Rule, get_evaluable_architecture

_ROOT = str(pathlib.Path(__file__).resolve().parents[1])
_SRC = str(pathlib.Path(__file__).resolve().parents[1] / "evlampiy")

_arch = get_evaluable_architecture(_ROOT, _SRC)

# pytestarch names a module after the root directory, which differs locally and in CI.
_PREFIX = f"{pathlib.Path(_ROOT).name}.evlampiy"


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


# --- Rule 5: tests patch asyncio only as one module sees it ---

_TESTS = pathlib.Path(__file__).resolve().parent


class TestAsyncioPatching:
    def test_tests_never_patch_the_shared_asyncio_module(self):
        """`patch("evlampiy.x.asyncio.sleep")` replaces the sleep of `asyncio` itself, for the whole process.

        pymongo's heartbeat is a loop on `asyncio.sleep`: under the mock it spins without a pause, the
        mock records every turn, and a test run grew to 9 GB before the kernel killed it and the IDE.
        Patch the name the module under test looks up instead: `tests/fixtures.py::sleep_replaced`.
        """
        violations = []
        for py_file in sorted(_TESTS.rglob("*.py")):
            for node in ast.walk(ast.parse(py_file.read_text(), filename=str(py_file))):
                if isinstance(node, ast.Call) and _patches_shared_asyncio(node):
                    violations.append(f"{py_file.relative_to(_TESTS)}:{node.lineno}")
        assert not violations, "Tests patch the shared asyncio module:\n" + "\n".join(f"  {v}" for v in violations)


def _patches_shared_asyncio(node: ast.Call) -> bool:
    """A patch whose target is an attribute of the `asyncio` module itself."""
    if not node.args:
        return False
    called = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", None)
    target = node.args[0]
    if called in ("patch", "setattr") and isinstance(target, ast.Constant) and isinstance(target.value, str):
        return re.search(r"(^|\.)asyncio\.\w+$", target.value) is not None
    return called in ("object", "setattr") and isinstance(target, ast.Name) and target.id == "asyncio"
