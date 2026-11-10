## 2025-03-05 - Fix arbitrary code execution vulnerability in budget infrastructure checks
**Vulnerability:** Arbitrary Code Execution (ACE) via `eval()`
**Learning:** Using `eval()` to parse string representations of lists from terraform config (e.g. `[50, 80, 100]`) is a security vulnerability as it allows arbitrary code execution.
**Prevention:** Use `ast.literal_eval()` which safely evaluates strings containing Python values from untrusted sources without allowing code execution.
