"""Scanner utilities for AST parsing, PII detection, and numeric normalization (F04)."""

import ast
import re
from typing import Any

# Statutory citations exempted from numeric hallucination auditing per RL-1
STATUTORY_PATTERNS = [
    re.compile(r"31\s+CFR\s+\d+(\.\d+)?", re.IGNORECASE),
    re.compile(r"Section\s+\d+(\([a-zA-Z0-9]+\))?", re.IGNORECASE),
    re.compile(r"Form\s+\d+", re.IGNORECASE),
    re.compile(r"Directive\s+(\([A-Z]+\)\s*)?\d{4}/\d+", re.IGNORECASE),
    re.compile(r"USA\s+PATRIOT\s+Act", re.IGNORECASE),
    re.compile(r"FinCEN\s+Advisory\s+FIN-\d{4}-[A-Z0-9]+", re.IGNORECASE),
]

# Regex patterns for detecting unmasked PII per RL-5
PII_PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "credit_card": re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
}

# Allowed token patterns per Layer 1 Token Vault
PSEUDONYM_PATTERNS = [
    re.compile(r"\btok_usr_[a-zA-Z0-9_]+\b"),
    re.compile(r"\btok_id_cluster_[a-zA-Z0-9_]+\b"),
    re.compile(r"\bent_syn_[a-zA-Z0-9_]+\b"),
]

# Forbidden mutation calls in agent reasoning mesh per RL-4
FORBIDDEN_MUTATION_CALLS = frozenset(
    {
        "execute",
        "cursor.execute",
        "insert",
        "update",
        "delete",
        "write",
        "execute_action",
        "mutate",
        "post",
        "put",
        "patch",
    }
)


class NumericTokenNormalizer:
    """Normalizes text by exempting statutory references and extracting candidate metrics."""

    @classmethod
    def extract_metrics(cls, text: str) -> list[float]:
        """Strip statutory citations and extract all remaining numeric values."""
        normalized = text
        for pat in STATUTORY_PATTERNS:
            normalized = pat.sub(" ", normalized)

        # Match numbers with optional $, %, commas, decimals
        num_pattern = re.compile(r"\$?\b\d+(?:,\d{3})*(?:\.\d+)?%?\b")
        matches = num_pattern.findall(normalized)
        cleaned_numbers: list[float] = []

        for m in matches:
            cleaned = m.replace("$", "").replace("%", "").replace(",", "").strip()
            try:
                cleaned_numbers.append(float(cleaned))
            except ValueError:
                continue

        return cleaned_numbers


class ASTMutationVisitor(ast.NodeVisitor):
    """AST visitor detecting direct write and DB mutation operations in agent source."""

    def __init__(self) -> None:
        self.violations: list[dict[str, Any]] = []

    def visit_Call(self, node: ast.Call) -> None:
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name in FORBIDDEN_MUTATION_CALLS:
            self.violations.append(
                {
                    "line": getattr(node, "lineno", 0),
                    "symbol": func_name,
                    "reason": (
                        f"Direct mutation method '{func_name}' is forbidden in reasoning modules."
                    ),
                }
            )

        self.generic_visit(node)
