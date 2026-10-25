## 2025-05-18 - Prevent Arbitrary Code Execution in Tooling Config Parsing
**Vulnerability:** Found `eval()` being used in `EIOS/tools/infra_checks/budget.py` to parse string representations of lists from Terraform/HCL configuration.
**Learning:** Tools parsing infrastructure configurations or manifests may unsafely use `eval()` for quick type conversion when processing array-like strings.
**Prevention:** Always use `ast.literal_eval()` instead of `eval()` when parsing strings that represent Python literals (like lists, dicts, tuples) to avoid arbitrary code execution vulnerabilities.
