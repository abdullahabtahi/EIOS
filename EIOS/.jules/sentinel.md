## 2024-05-15 - Arbitrary Code Execution via eval()
**Vulnerability:** Arbitrary code execution vulnerability via the use of eval() to parse Terraform/HCL strings in tools/infra_checks/budget.py.
**Learning:** Python's built-in eval() should never be used on string representations of data structures from untrusted or external files. It can evaluate any python expression, leading to remote code execution.
**Prevention:** Always use ast.literal_eval() for parsing string representations of python primitives instead of eval().