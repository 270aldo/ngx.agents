#!/usr/bin/env python3
"""Script to add type hints to functions automatically."""

import ast
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import re


class TypeHintAdder(ast.NodeTransformer):
    """AST transformer to add type hints to functions."""

    def __init__(self):
        self.current_class = None
        self.imports_needed = set()

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        """Visit class definition."""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Add type hints to function definition."""
        self._add_type_hints(node)
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(
        self, node: ast.AsyncFunctionDef
    ) -> ast.AsyncFunctionDef:
        """Add type hints to async function definition."""
        self._add_type_hints(node)
        self.generic_visit(node)
        return node

    def _add_type_hints(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Add type hints based on function name and parameters."""
        # Skip if already has type hints
        if all(
            arg.annotation for arg in node.args.args if arg.arg not in ["self", "cls"]
        ):
            if node.returns or node.name == "__init__":
                return

        # Add parameter type hints
        for arg in node.args.args:
            if arg.arg in ["self", "cls"]:
                continue

            if not arg.annotation:
                # Infer type based on parameter name
                type_hint = self._infer_type_from_name(arg.arg)
                if type_hint:
                    arg.annotation = ast.Name(id=type_hint, ctx=ast.Load())

        # Add return type hint
        if not node.returns and node.name != "__init__":
            return_type = self._infer_return_type(node)
            if return_type:
                node.returns = ast.Name(id=return_type, ctx=ast.Load())

    def _infer_type_from_name(self, param_name: str) -> Optional[str]:
        """Infer type from parameter name."""
        # Common patterns
        patterns = {
            r"^(text|prompt|query|message|content|description|name|title)$": "str",
            r"^(id|user_id|session_id|conversation_id|.*_id)$": "str",
            r"^(count|num|number|size|length|timeout|limit|offset|max_.*|min_.*)$": "int",
            r"^(temperature|threshold|ratio|score|confidence|probability)$": "float",
            r"^(is_|has_|should_|enable_|disable_|.*_enabled|.*_disabled)$": "bool",
            r"^(data|config|settings|options|params|kwargs|metadata|context)$": "Dict[str, Any]",
            r"^(items|values|results|.*_list|.*s)$": "List[Any]",
            r"^(image|image_data)$": "Union[str, bytes]",
            r"^(file_path|path|filepath)$": "str",
            r"^(url|uri|endpoint)$": "str",
        }

        for pattern, type_hint in patterns.items():
            if re.match(pattern, param_name, re.IGNORECASE):
                # Add to imports if needed
                if "Dict" in type_hint:
                    self.imports_needed.add("Dict")
                if "List" in type_hint:
                    self.imports_needed.add("List")
                if "Union" in type_hint:
                    self.imports_needed.add("Union")
                if "Any" in type_hint:
                    self.imports_needed.add("Any")
                return type_hint

        return "Any"

    def _infer_return_type(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> Optional[str]:
        """Infer return type from function name and body."""
        func_name = node.name

        # Common patterns
        if func_name.startswith("get_") or func_name.startswith("fetch_"):
            if "list" in func_name or func_name.endswith("s"):
                self.imports_needed.add("List")
                self.imports_needed.add("Any")
                return "List[Any]"
            else:
                self.imports_needed.add("Any")
                return "Any"

        if (
            func_name.startswith("is_")
            or func_name.startswith("has_")
            or func_name.startswith("check_")
        ):
            return "bool"

        if func_name.startswith("count_") or func_name.startswith("get_num_"):
            return "int"

        if func_name in [
            "connect",
            "disconnect",
            "initialize",
            "close",
            "setup",
            "cleanup",
        ]:
            return "None"

        # Check for explicit return statements
        has_return_value = False
        for child in ast.walk(node):
            if isinstance(child, ast.Return) and child.value:
                has_return_value = True
                break

        if not has_return_value:
            return "None"

        # Default to Any for complex returns
        self.imports_needed.add("Any")
        return "Any"


def add_type_hints_to_file(filepath: Path) -> bool:
    """Add type hints to a single file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse the AST
        tree = ast.parse(content)

        # Transform the AST
        transformer = TypeHintAdder()
        new_tree = transformer.visit(tree)

        # Generate new code
        new_code = ast.unparse(new_tree)

        # Add necessary imports if not present
        if transformer.imports_needed:
            import_line = (
                f"from typing import {', '.join(sorted(transformer.imports_needed))}\n"
            )

            # Find where to insert the import
            lines = new_code.split("\n")
            import_added = False

            for i, line in enumerate(lines):
                if "from typing import" in line:
                    # Merge with existing typing import
                    existing_imports = re.findall(r"from typing import (.+)", line)[0]
                    all_imports = (
                        set(existing_imports.split(", ")) | transformer.imports_needed
                    )
                    lines[i] = f"from typing import {', '.join(sorted(all_imports))}"
                    import_added = True
                    break

            if not import_added:
                # Add after other imports
                for i, line in enumerate(lines):
                    if (
                        line.strip()
                        and not line.strip().startswith("#")
                        and not line.strip().startswith('"""')
                    ):
                        if "import" not in line and "from" not in line:
                            lines.insert(i, import_line)
                            break

            new_code = "\n".join(lines)

        # Write back
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_code)

        return True
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False


def main():
    """Main function to add type hints to priority files."""
    project_root = Path(__file__).parent.parent

    # Priority files to fix first
    priority_files = [
        "core/state_manager_optimized.py",
        "core/redis_pool.py",
        "core/circuit_breaker.py",
        "clients/vertex_ai/client.py",
        "clients/supabase_client.py",
        "app/routers/chat.py",
        "app/routers/agent.py",
    ]

    fixed_count = 0

    for file_path in priority_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"Adding type hints to {file_path}...")
            if add_type_hints_to_file(full_path):
                fixed_count += 1
                print(f"✓ Successfully added type hints to {file_path}")
            else:
                print(f"✗ Failed to add type hints to {file_path}")

    print(f"\nAdded type hints to {fixed_count} files")


if __name__ == "__main__":
    main()
