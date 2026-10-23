## 2025-02-14 - Fix Arbitrary Code Execution in HCL Evaluation
**Vulnerability:** Use of `eval()` in `tools/infra_checks/budget.py` to parse Terraform variable string representation containing lists.
**Learning:** Tools examining infra definitions (HCL/Terraform) often need to parse literal structures. Using `eval()` directly allows arbitrary execution.
**Prevention:** Replace `eval()` with `ast.literal_eval()` which safely evaluates only string literals representing Python data structures.
