#!/usr/bin/env python3
"""Script to find and fix bare except clauses in Python files."""

import os
import re
import sys
from pathlib import Path


def fix_bare_except_in_file(filepath):
    """Fix bare except clauses in a single file."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Pattern to match bare except:
    # Matches 'except:' with optional whitespace, ensuring it's not part of a longer word
    pattern = r"^(\s*)except\s*:\s*$"
    replacement = r"\1except Exception:"

    lines = content.split("\n")
    modified = False
    new_lines = []

    for line in lines:
        if re.match(pattern, line):
            new_line = re.sub(pattern, replacement, line)
            new_lines.append(new_line)
            modified = True
            print(f"Fixed bare except in {filepath}")
        else:
            new_lines.append(line)

    if modified:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines))

    return modified


def main():
    """Main function to process all Python files."""
    project_root = Path(__file__).parent.parent
    fixed_count = 0

    for filepath in project_root.rglob("*.py"):
        # Skip virtual environments and other common directories
        if any(
            part in filepath.parts for part in ["venv", ".venv", "__pycache__", ".git"]
        ):
            continue

        if fix_bare_except_in_file(filepath):
            fixed_count += 1

    print(f"\nFixed bare except clauses in {fixed_count} files")


if __name__ == "__main__":
    main()
