## 2024-11-03 - [Security] Prevent arbitrary code execution by avoiding eval()

**Vulnerability:** Arbitrary code execution vulnerability due to the use of `eval()` for parsing configuration values from Terraform/HCL strings in `tools/infra_checks/budget.py`.

**Learning:** When evaluating string representations of data structures, especially those that might incorporate user or file-based input from configuration, using `eval()` is highly dangerous and can lead to arbitrary code execution if the input is untrusted or tampered with.

**Prevention:** Always use safe alternatives like `ast.literal_eval()` when you need to safely parse strings containing Python literals (like lists, dictionaries, tuples, etc.). `ast.literal_eval` safely evaluates an expression node or a string containing a Python literal or container display. It does not allow function calls or operations that could execute arbitrary code.