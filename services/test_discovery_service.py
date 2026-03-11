from __future__ import annotations

import ast
from pathlib import Path


DEFAULT_TESTS_ROOT = Path("tests")

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
