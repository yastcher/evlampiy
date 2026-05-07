"""Documentation contract tests: links, structure, freshness."""

import pathlib
import re

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_DOCS = _ROOT / "docs"
_SRC = _ROOT / "src"

# All markdown files that contain internal links
_DOC_FILES = [
    _ROOT / "README.md",
    _DOCS / "README.ru.md",
    _DOCS / "README.es.md",
    _DOCS / "README.de.md",
    _DOCS / "ADMIN.md",
    _DOCS / "DEPLOY.md",
    _DOCS / "ARCHITECTURE.md",
    _DOCS / "WHATSAPP_SETUP.md",
    _DOCS / "WHATSAPP_LINKING.md",
    _DOCS / "GITHUB_TOKEN_SETUP.md",
]

# Regex for markdown links: [text](path) — skip URLs and anchors
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_SKIP_PREFIXES = ("http://", "https://", "#", "mailto:")


class TestDocLinks:
    """All internal markdown links resolve to existing files."""

    def test_all_doc_files_exist(self):
        """Every file in _DOC_FILES must exist on disk."""
        missing = [f for f in _DOC_FILES if not f.exists()]
        assert not missing, f"Documentation files missing: {missing}"

    def test_internal_links_resolve(self):
        """Every [text](path) link in docs points to an existing file."""
        broken = []
        for doc in _DOC_FILES:
            if not doc.exists():
                continue
            text = doc.read_text()
            for match in _LINK_RE.finditer(text):
                target = match.group(2)
                # Skip URLs, anchors, and anchor-only fragments on local files
                if any(target.startswith(p) for p in _SKIP_PREFIXES):
                    continue
                # Strip anchor fragment (e.g. DEPLOY.md#english)
                path_part = target.split("#")[0]
                if not path_part:
                    continue
                resolved = (doc.parent / path_part).resolve()
                if not resolved.exists():
                    broken.append(f"{doc.name}: [{match.group(1)}]({target})")
        assert not broken, "Broken links:\n" + "\n".join(f"  {b}" for b in broken)


class TestArchitectureFreshness:
    """ARCHITECTURE.md directory tree matches actual src/ structure."""

    @staticmethod
    def _parse_tree_files(text: str) -> set[str]:
        """Extract relative file paths from the directory tree block."""
        # Match lines like: │   ├── handlers.py or ├── ai_client.py
        # within the src/ tree block. Supports arbitrary nesting depth.
        in_src_block = False
        files: list[str] = []
        prefix_by_depth: dict[int, str] = {}
        for line in text.splitlines():
            if "src/" in line and "```" not in line and in_src_block is False:
                in_src_block = True
                continue
            if in_src_block and line.strip().startswith("```"):
                break
            if not in_src_block:
                continue
            m = re.search(r"[├└]── (\S+)", line)
            if not m:
                continue
            name = m.group(1)
            indent = len(re.findall(r"│   |    ", line[: line.index("├" if "├" in line else "└")]))
            parent = "".join(prefix_by_depth.get(d, "") for d in range(indent))
            if name.endswith("/"):
                prefix_by_depth[indent] = name
                # Drop deeper entries — they belong to the previous sibling
                for d in list(prefix_by_depth):
                    if d > indent:
                        del prefix_by_depth[d]
            else:
                files.append(parent + name)
        return set(files)

    def test_tree_files_exist_in_src(self):
        """Every file listed in ARCHITECTURE.md tree exists in src/."""
        arch = (_DOCS / "ARCHITECTURE.md").read_text()
        tree_files = self._parse_tree_files(arch)
        assert tree_files, "Failed to parse any files from ARCHITECTURE.md tree"
        missing = []
        for rel in tree_files:
            if not (_SRC / rel).exists():
                missing.append(f"src/{rel}")
        assert not missing, "Files in ARCHITECTURE.md tree not found on disk:\n" + "\n".join(
            f"  {m}" for m in sorted(missing)
        )

    def test_src_python_files_in_tree(self):
        """Every .py file in src/ is listed in the ARCHITECTURE.md tree."""
        arch = (_DOCS / "ARCHITECTURE.md").read_text()
        tree_files = self._parse_tree_files(arch)
        # Collect all .py files in src/ (excluding __pycache__, __init__.py)
        actual_files = set()
        for py in _SRC.rglob("*.py"):
            if "__pycache__" in str(py):
                continue
            rel = str(py.relative_to(_SRC))
            if rel == "__init__.py" or rel.endswith("/__init__.py"):
                continue
            actual_files.add(rel)
        undocumented = actual_files - tree_files
        assert not undocumented, (
            "Python files in src/ not listed in ARCHITECTURE.md tree:\n"
            + "\n".join(f"  src/{f}" for f in sorted(undocumented))
        )


_READMES = [
    _ROOT / "README.md",
    _DOCS / "README.ru.md",
    _DOCS / "README.es.md",
    _DOCS / "README.de.md",
]


class TestReadmeDocTable:
    """All READMEs have a Documentation section with a table."""

    def test_documentation_section_exists(self):
        """Each README has a Documentation/Dokumentation/Documentacion section."""
        missing = []
        for readme in _READMES:
            text = readme.read_text()
            # Match ## Documentation / ## Документация / ## Documentacion / ## Dokumentation
            if not re.search(
                r"^## (Documentation|Документация|Documentacion|Dokumentation)", text, re.M
            ):
                missing.append(readme.name)
        assert not missing, f"READMEs without Documentation section: {missing}"

    def test_documentation_table_has_architecture_link(self):
        """Each README's Documentation table links to ARCHITECTURE.md."""
        missing = []
        for readme in _READMES:
            text = readme.read_text()
            if "ARCHITECTURE.md" not in text:
                missing.append(readme.name)
        assert not missing, f"READMEs without ARCHITECTURE.md link: {missing}"


_ALLOWED_CHANGELOG_SUBSECTIONS = {"Added", "Changed", "Fixed", "Removed", "Docs"}


class TestChangelogStructure:
    """CHANGELOG.md follows the subsection naming convention."""

    def test_subsections_are_valid(self):
        """Every ### subsection in CHANGELOG.md uses an allowed name."""
        text = (_ROOT / "CHANGELOG.md").read_text()
        invalid = []
        for m in re.finditer(r"^### (\w+)", text, re.M):
            name = m.group(1)
            if name not in _ALLOWED_CHANGELOG_SUBSECTIONS:
                invalid.append(name)
        assert not invalid, (
            f"Invalid CHANGELOG subsections: {invalid}. "
            f"Allowed: {sorted(_ALLOWED_CHANGELOG_SUBSECTIONS)}"
        )
