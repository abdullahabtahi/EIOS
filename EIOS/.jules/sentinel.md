## 2024-10-30 - Fix arbitrary code execution via eval
**Vulnerability:** Found `eval()` being used in `tools/infra_checks/budget.py` to parse list-like strings from infrastructure configuration. This could lead to arbitrary code execution if a malicious payload is injected into the configuration.
**Learning:** Python's built-in `eval()` executes arbitrary code. When parsing string representations of data structures (like lists) from config files or user input, it's unsafe.
**Prevention:** Use `ast.literal_eval()` instead, which safely parses only literal structures (strings, numbers, tuples, lists, dicts, booleans, and None) without allowing arbitrary function calls or execution.
