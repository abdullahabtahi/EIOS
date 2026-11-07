## 2024-05-18 - Prevent Arbitrary Code Execution in HCL parsing
**Vulnerability:** Arbitrary Code Execution via `eval()` when parsing string representations of data structures from HCL/Terraform files.
**Learning:** The infrastructure budget tool used `eval()` to parse array strings from configuration files, creating an arbitrary code execution vector.
**Prevention:** Always use `ast.literal_eval()` instead of `eval()` when parsing string representations of data structures from configuration files in Python tools.
