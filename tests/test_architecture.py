"""Architectural tests: enforce module boundaries and import conventions."""

import ast
import pathlib

from pytestarch import Rule, get_evaluable_architecture

_ROOT = str(pathlib.Path(__file__).resolve().parents[1])
_SRC = str(pathlib.Path(__file__).resolve().parents[1] / "src")

_arch = get_evaluable_architecture(_ROOT, _SRC)

# Prefix depends on the project directory name (differs locally vs CI).
# Detect it from the graph nodes: find node ending with ".src.const" and strip ".const".
_PREFIX = next(
    n.removesuffix(".const") for n in _arch._graph._graph.nodes() if n.endswith(".src.const")
)


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
    """`src/services/*` must not import aiogram / pywa / fastapi.

    Catches regressions where a use-case service starts depending on a delivery channel.
    """

    def test_services_do_not_import_aiogram(self):
        violations = _imports_targeting(_PREFIX + ".src.services", ("aiogram",))
        assert not violations, (
            "services modules import aiogram (must stay framework-agnostic):\n"
            + "\n".join(f"  {v}" for v in violations)
        )

    def test_services_do_not_import_pywa(self):
        violations = _imports_targeting(_PREFIX + ".src.services", ("pywa", "pywa_async"))
        assert not violations, (
            "services modules import pywa (must stay framework-agnostic):\n"
            + "\n".join(f"  {v}" for v in violations)
        )

    def test_services_do_not_import_fastapi(self):
        violations = _imports_targeting(_PREFIX + ".src.services", ("fastapi", "uvicorn"))
        assert not violations, (
            "services modules import fastapi/uvicorn (must stay framework-agnostic):\n"
            + "\n".join(f"  {v}" for v in violations)
        )

    def test_services_do_not_import_telegram_handlers(self):
        """Services must not depend on adapter modules — that's an inversion."""
        violations = _imports_targeting(_PREFIX + ".src.services", (_PREFIX + ".src.telegram",))
        assert not violations, (
            "services modules import src.telegram (inverted dependency):\n"
            + "\n".join(f"  {v}" for v in violations)
        )


def _imports_targeting(source_pkg: str, targets: tuple[str, ...]) -> list[str]:
    """Return nodes under ``source_pkg`` that import any module in ``targets``."""
    graph = _arch._graph._graph
    violations: list[str] = []
    for src_node in graph.nodes():
        if not src_node.startswith(source_pkg):
            continue
        for dst_node in graph.successors(src_node):
            for target in targets:
                if dst_node == target or dst_node.startswith(target + "."):
                    violations.append(f"{src_node} → {dst_node}")
                    break
    return violations


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
        assert not violations, (
            "Stdlib modules must be imported as `import X`, not `from X import ...`:\n"
            + "\n".join(f"  {v}" for v in violations)
        )
