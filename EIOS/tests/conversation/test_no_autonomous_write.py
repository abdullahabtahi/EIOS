"""AST static analysis verifying zero direct database write statements in conversational mesh (Principle II, T022)."""

import ast
from pathlib import Path

MUTATION_KEYWORDS = [
    "INSERT INTO",
    "UPDATE ",
    "DELETE FROM",
    "DROP TABLE",
    "ALTER TABLE",
    "TRUNCATE ",
]


def test_zero_autonomous_sql_mutations_in_conversation_mesh():
    src_dir = Path(__file__).resolve().parent.parent.parent / "src" / "eios" / "conversation"
    assert src_dir.exists(), f"Directory not found: {src_dir}"

    violations = []

    for py_file in src_dir.rglob("*.py"):
        # Ignore checkpointer sqlite table creation
        if py_file.name == "checkpointer.py":
            continue

        with open(py_file, encoding="utf-8") as f:
            code = f.read()

        # Parse AST to ensure valid syntax
        ast.parse(code, filename=str(py_file))

        # Check raw code and docstrings
        for line_num, line in enumerate(code.splitlines(), start=1):
            upper_line = line.upper()
            for kw in MUTATION_KEYWORDS:
                if kw in upper_line:
                    violations.append(
                        f"{py_file.name}:{line_num} contains forbidden mutation pattern '{kw}'"
                    )

    assert len(violations) == 0, "Principle II Violations found:\n" + "\n".join(violations)
