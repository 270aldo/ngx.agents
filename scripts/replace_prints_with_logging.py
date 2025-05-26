#!/usr/bin/env python3
"""Script to replace print() statements with proper logging in Python files."""

import os
import re
import ast
from pathlib import Path


def get_logger_import():
    """Get the appropriate logger import statement."""
    return "from core.logging_config import get_logger"


def ensure_logger_in_file(content, filepath):
    """Ensure logger is properly imported and initialized in the file."""
    lines = content.split("\n")

    # Check if logger is already imported
    has_logger_import = any("get_logger" in line and "import" in line for line in lines)
    has_logger_init = any("logger = get_logger" in line for line in lines)

    if not has_logger_import:
        # Find the right place to insert import
        import_index = 0
        for i, line in enumerate(lines):
            if (
                line.strip()
                and not line.strip().startswith("#")
                and not line.strip().startswith('"""')
            ):
                if "import" in line or "from" in line:
                    import_index = i + 1
                else:
                    break

        # Insert logger import
        lines.insert(import_index, get_logger_import())
        lines.insert(import_index + 1, "")

    if not has_logger_init:
        # Find the right place to insert logger initialization
        # After imports but before any class or function definitions
        init_index = import_index + 2 if not has_logger_import else 0

        for i, line in enumerate(lines[init_index:], start=init_index):
            if (
                line.strip()
                and not line.strip().startswith("#")
                and not line.strip().startswith('"""')
            ):
                if not ("import" in line or "from" in line):
                    if "class " in line or "def " in line or line.startswith("@"):
                        init_index = i
                        break

        # Insert logger initialization
        module_name = Path(filepath).stem
        lines.insert(init_index, f"logger = get_logger(__name__)")
        lines.insert(init_index + 1, "")

    return "\n".join(lines)


def replace_print_with_logger(content):
    """Replace print() statements with logger calls."""
    lines = content.split("\n")
    new_lines = []

    for line in lines:
        # Skip if it's a comment or docstring
        stripped = line.strip()
        if (
            stripped.startswith("#")
            or stripped.startswith('"""')
            or stripped.startswith("'''")
        ):
            new_lines.append(line)
            continue

        # Match print statements
        # Handle various print patterns
        patterns = [
            (r"^(\s*)print\s*\((.*)\)\s*$", r"\1logger.info(\2)"),
            (r"^(\s*)print\s*\((.*)\)\s*#(.*)$", r"\1logger.info(\2)  #\3"),
        ]

        replaced = False
        for pattern, replacement in patterns:
            if re.match(pattern, line):
                # Check if it's a debug/error/warning print
                if "error" in line.lower() or "exception" in line.lower():
                    new_line = re.sub(pattern, r"\1logger.error(\2)", line)
                elif "warn" in line.lower():
                    new_line = re.sub(pattern, r"\1logger.warning(\2)", line)
                elif "debug" in line.lower():
                    new_line = re.sub(pattern, r"\1logger.debug(\2)", line)
                else:
                    new_line = re.sub(pattern, replacement, line)

                new_lines.append(new_line)
                replaced = True
                break

        if not replaced:
            new_lines.append(line)

    return "\n".join(new_lines)


def process_file(filepath):
    """Process a single Python file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Skip if no print statements
        if "print(" not in content:
            return False

        # First ensure logger is in the file
        content = ensure_logger_in_file(content, filepath)

        # Then replace print statements
        new_content = replace_print_with_logger(content)

        if content != new_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Updated {filepath}")
            return True
    except Exception as e:
        print(f"Error processing {filepath}: {e}")

    return False


def main():
    """Main function to process all Python files."""
    project_root = Path(__file__).parent.parent
    updated_count = 0

    for filepath in project_root.rglob("*.py"):
        # Skip virtual environments and other common directories
        if any(
            part in filepath.parts
            for part in ["venv", ".venv", "__pycache__", ".git", "scripts"]
        ):
            continue

        if process_file(filepath):
            updated_count += 1

    print(f"\nReplaced print statements with logging in {updated_count} files")


if __name__ == "__main__":
    main()
