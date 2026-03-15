from __future__ import annotations

import ast
import os
import re
from pathlib import Path


DEFAULT_TESTS_ROOT = Path("tests")
DEFAULT_REPOSITORY_ROOT = Path(".")
JAVASCRIPT_TEST_FILE_PATTERNS = (".test.js", ".test.jsx", ".spec.js", ".spec.jsx")
PYTHON_TEST_DIRECTORY_NAMES = {"tests", "test"}
EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".pytest_cache",
    ".test_tmp",
    "node_modules",
    "venv",
    "__pycache__",
}
EXCLUDED_DIRECTORY_PREFIXES = ("pytest-cache-files-", "tmpr")

CATEGORY_RULES = (
    ("security", "security tests"),
    ("privacy", "privacy tests"),
    ("pii", "privacy tests"),
    ("auth", "security tests"),
    ("ui", "UI tests"),
    ("frontend", "UI tests"),
    ("integration", "integration tests"),
    ("api", "API tests"),
    ("router", "API tests"),
)

JEST_BLOCK_RE = re.compile(r"""\b(?P<kind>describe|test|it)\s*\(\s*(?P<quote>['\"`])(?P<name>.*?)(?P=quote)""")


def normalize_test_file_path(file_path: str | None) -> str | None:
    if not file_path:
        return None
    return str(Path(file_path).as_posix())


def build_test_node_id(*, test_name: str, file_path: str | None = None, category: str | None = None) -> str:
    normalized_file_path = normalize_test_file_path(file_path)
    if normalized_file_path:
        return f"{normalized_file_path}::{test_name}"
    if category:
        return f"{category}::{test_name}"
    return test_name


def split_test_node_id(node_id: str | None) -> tuple[str | None, str]:
    if not node_id:
        return None, ""
    if ".py::" in node_id:
        file_path, test_name = node_id.split(".py::", 1)
        return f"{file_path}.py", test_name
    if "::" not in node_id:
        return None, node_id
    file_path, test_name = node_id.rsplit("::", 1)
    return file_path, test_name


def infer_test_category(file_path: str | None, test_name: str | None = None) -> str:
    haystack = " ".join(part for part in [file_path or "", test_name or ""]).lower()
    for needle, category in CATEGORY_RULES:
        if needle in haystack:
            return category
    return "integration tests"


def _iter_discovered_tests(tree: ast.AST, *, file_path: str) -> list[dict[str, str | None]]:
    discovered: list[dict[str, str | None]] = []

    def visit_class(node: ast.ClassDef, prefix: str | None = None) -> None:
        class_prefix = node.name if prefix is None else f"{prefix}::{node.name}"
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith("test_"):
                display_name = f"{class_prefix}::{child.name}"
                discovered.append(
                    {
                        "test_name": display_name,
                        "file_path": file_path,
                        "node_id": build_test_node_id(test_name=display_name, file_path=file_path),
                        "description": ast.get_docstring(child),
                        "category": infer_test_category(file_path, display_name),
                    }
                )
            elif isinstance(child, ast.ClassDef) and child.name.startswith("Test"):
                visit_class(child, class_prefix)

    for node in tree.body if isinstance(tree, ast.Module) else []:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            discovered.append(
                {
                    "test_name": node.name,
                    "file_path": file_path,
                    "node_id": build_test_node_id(test_name=node.name, file_path=file_path),
                    "description": ast.get_docstring(node),
                    "category": infer_test_category(file_path, node.name),
                }
            )
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            visit_class(node)
    return discovered


def discover_pytest_cases(tests_root: str | Path = DEFAULT_TESTS_ROOT) -> list[dict[str, str | None]]:
    root = Path(tests_root)
    if not root.exists():
        return []

    discovered: list[dict[str, str | None]] = []
    for file_path in sorted(root.rglob("test_*.py")):
        if file_path.is_absolute():
            try:
                relative_path = str(file_path.relative_to(root.parent).as_posix())
            except ValueError:
                relative_path = str(file_path.as_posix())
        else:
            relative_path = str(file_path.as_posix())
        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        discovered.extend(_iter_discovered_tests(tree, file_path=relative_path))
    return discovered


def _is_excluded_directory(name: str) -> bool:
    normalized = name.strip().lower()
    if normalized in EXCLUDED_DIRECTORY_NAMES:
        return True
    return any(normalized.startswith(prefix) for prefix in EXCLUDED_DIRECTORY_PREFIXES)


def _iter_repository_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, onerror=lambda _err: None):
        dirnames[:] = [name for name in dirnames if not _is_excluded_directory(name)]
        current_dir = Path(dirpath)
        for filename in filenames:
            files.append(current_dir / filename)
    return sorted(files)


def _is_python_test_file(file_path: Path) -> bool:
    if file_path.suffix != ".py":
        return False
    if not (file_path.name.startswith("test_") or file_path.name.endswith("_test.py")):
        return False
    return any(part.lower() in PYTHON_TEST_DIRECTORY_NAMES for part in file_path.parts[:-1])


def _iter_python_repository_tests(root: Path) -> list[dict[str, str | None]]:
    discovered: list[dict[str, str | None]] = []
    for file_path in _iter_repository_files(root):
        if not _is_python_test_file(file_path):
            continue
        try:
            relative_path = str(file_path.relative_to(root).as_posix())
            tree = ast.parse(file_path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError, ValueError):
            continue
        discovered.extend(_iter_discovered_tests(tree, file_path=relative_path))
    return discovered


def _is_javascript_test_file(file_path: Path) -> bool:
    suffix = "".join(file_path.suffixes[-2:]) if len(file_path.suffixes) >= 2 else file_path.suffix
    return suffix in JAVASCRIPT_TEST_FILE_PATTERNS


def _iter_javascript_repository_tests(root: Path) -> list[dict[str, str | None]]:
    discovered: list[dict[str, str | None]] = []
    for file_path in _iter_repository_files(root):
        if not _is_javascript_test_file(file_path):
            continue
        try:
            relative_path = str(file_path.relative_to(root).as_posix())
            source = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError, ValueError):
            continue

        describe_stack: list[tuple[str, int]] = []
        brace_depth = 0
        for raw_line in source.splitlines():
            matches = list(JEST_BLOCK_RE.finditer(raw_line))
            brace_depth += raw_line.count("{") - raw_line.count("}")

            for match in matches:
                kind = match.group("kind")
                name = match.group("name").strip()
                if not name:
                    continue
                if kind == "describe":
                    describe_stack.append((name, brace_depth))
                    continue
                display_name = "::".join([label for label, _ in describe_stack] + [name])
                discovered.append(
                    {
                        "test_name": display_name,
                        "file_path": relative_path,
                        "node_id": build_test_node_id(test_name=display_name, file_path=relative_path),
                        "description": None,
                        "category": infer_test_category(relative_path, display_name),
                    }
                )

            while describe_stack and brace_depth < describe_stack[-1][1]:
                describe_stack.pop()
    return discovered


def discover_repository_tests(root: str | Path = DEFAULT_REPOSITORY_ROOT) -> list[dict[str, str | None]]:
    repository_root = Path(root)
    if not repository_root.exists():
        return []

    discovered_by_node_id: dict[str, dict[str, str | None]] = {}
    for item in _iter_python_repository_tests(repository_root):
        discovered_by_node_id[str(item["node_id"])] = item
    for item in _iter_javascript_repository_tests(repository_root):
        discovered_by_node_id[str(item["node_id"])] = item
    return sorted(
        discovered_by_node_id.values(),
        key=lambda item: (str(item.get("file_path") or ""), str(item.get("test_name") or "")),
    )
