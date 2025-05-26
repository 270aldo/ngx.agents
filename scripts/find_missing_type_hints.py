#!/usr/bin/env python3
"""Script to find functions without type hints in Python files."""

import ast
import os
from pathlib import Path
from typing import List, Tuple, Dict


class TypeHintChecker(ast.NodeVisitor):
    """AST visitor to check for missing type hints."""

    def __init__(self, filename: str):
        self.filename = filename
        self.missing_hints: List[Dict[str, any]] = []
        self.current_class = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition."""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function definition for type hints."""
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check async function definition for type hints."""
        self._check_function(node)
        self.generic_visit(node)

    def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Check if function has proper type hints."""
        # Skip dunder methods except __init__
        if (
            node.name.startswith("__")
            and node.name.endswith("__")
            and node.name != "__init__"
        ):
            return

        # Skip property setters/deleters
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Attribute):
                if decorator.attr in ["setter", "deleter"]:
                    return

        missing = []

        # Check parameters
        for arg in node.args.args:
            if arg.arg != "self" and arg.arg != "cls" and arg.annotation is None:
                missing.append(f"parameter '{arg.arg}'")

        # Check return type (except for __init__)
        if node.returns is None and node.name != "__init__":
            missing.append("return type")

        if missing:
            location = (
                f"{self.current_class}.{node.name}" if self.current_class else node.name
            )
            self.missing_hints.append(
                {
                    "file": self.filename,
                    "line": node.lineno,
                    "function": location,
                    "missing": missing,
                }
            )


def check_file(filepath: Path) -> List[Dict[str, any]]:
    """Check a single file for missing type hints."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)
        checker = TypeHintChecker(str(filepath))
        checker.visit(tree)

        return checker.missing_hints
    except Exception as e:
        print(f"Error checking {filepath}: {e}")
        return []


def main():
    """Main function to check all Python files."""
    project_root = Path(__file__).parent.parent

    # Directories to check
    dirs_to_check = ["core", "clients", "app", "agents", "infrastructure"]

    all_missing = []

    for dir_name in dirs_to_check:
        dir_path = project_root / dir_name
        if not dir_path.exists():
            continue

        for filepath in dir_path.rglob("*.py"):
            # Skip __pycache__ and test files
            if "__pycache__" in str(filepath) or "test_" in filepath.name:
                continue

            missing = check_file(filepath)
            all_missing.extend(missing)

    # Sort by file and line number
    all_missing.sort(key=lambda x: (x["file"], x["line"]))

    # Print summary
    print(f"\nFound {len(all_missing)} functions with missing type hints:\n")

    # Group by file
    by_file = {}
    for item in all_missing:
        file = item["file"]
        if file not in by_file:
            by_file[file] = []
        by_file[file].append(item)

    # Print by file
    for file, items in sorted(by_file.items()):
        print(f"\n{file}:")
        for item in items:
            missing_str = ", ".join(item["missing"])
            print(f"  Line {item['line']}: {item['function']} - missing {missing_str}")

    print(f"\nTotal files with missing type hints: {len(by_file)}")
    print(f"Total functions with missing type hints: {len(all_missing)}")


if __name__ == "__main__":
    main()
