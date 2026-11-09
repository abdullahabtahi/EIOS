## 2024-11-09 - Insecure eval() in budget thresholds parser
**Vulnerability:** Arbitrary code execution vulnerability via the use of `eval()` to parse threshold lists from budget config files or HCL syntax.
**Learning:** `eval()` was used as a shortcut to parse string representations of lists from configuration strings. This is extremely dangerous in tools dealing with external or unvalidated files.
**Prevention:** Always use `ast.literal_eval()` instead of `eval()` when parsing strings representing basic Python data structures like arrays or dicts from configuration files.
