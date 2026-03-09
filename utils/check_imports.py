import ast
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(r"C:\dev\ALEX-main")  # <-- adjust if needed
IGNORE_DIRS = {"venv", ".venv", "__pycache__", ".git", "node_modules", "dist", "build"}

def iter_py_files(root: Path):
    for p in root.rglob("*.py"):
        if any(part in IGNORE_DIRS for part in p.parts):
            continue
        yield p

def top_level_module(name: str) -> str:
    return name.split(".")[0]

def collect_imports(root: Path) -> set[str]:
    imports = set()
    for file in iter_py_files(root):
        try:
            tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(top_level_module(alias.name))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(top_level_module(node.module))
    return imports

def is_stdlib(mod: str) -> bool:
    # best-effort stdlib detection
    try:
        import importlib.util
        spec = importlib.util.find_spec(mod)
        if spec is None or spec.origin is None:
            return False
        return "Python" in spec.origin and "site-packages" not in spec.origin
    except Exception:
        return False

def main():
    imports = collect_imports(PROJECT_ROOT)

    # Filter obvious internal modules (project packages)
    internal = {p.name for p in PROJECT_ROOT.iterdir() if p.is_dir()}
    candidates = sorted(m for m in imports if m not in internal and not is_stdlib(m))

    missing = []
    for m in candidates:
        try:
            __import__(m)
        except Exception as e:
            missing.append((m, str(e)))

    if not missing:
        print("✅ No missing imports detected (best-effort).")
        return

    print("❌ Missing / failing imports:")
    for m, err in missing:
        print(f" - {m}: {err}")

    # crude suggestion: install module names directly
    pkgs = " ".join(sorted({m for m, _ in missing}))
    print("\nTry:")
    print(f"pip install {pkgs}")

if __name__ == "__main__":
    main()