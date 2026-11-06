## 2024-03-24 - Fix arbitrary code execution in budget parsing
**Vulnerability:** The infrastructure checker in `tools/infra_checks/budget.py` used `eval()` to parse string representations of lists from configuration, which could lead to arbitrary code execution if a malicious payload is supplied.
**Learning:** Parsing string representations of data structures (like arrays) from configuration files such as Terraform/HCL in Python tools should never use `eval()`, even in internal tooling, due to the risk of RCE.
**Prevention:** When parsing string representations of Python-like data structures from configs, always use `ast.literal_eval()` instead of `eval()` to safely parse literals.
