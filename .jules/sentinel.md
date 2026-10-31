## 2026-10-31 - Prevent Arbitrary Code Execution in Tooling
**Vulnerability:** The infrastructure checker tool used `eval()` to parse a list string from Terraform HCL configs.
**Learning:** Using `eval()` on configuration strings allows arbitrary code execution. Although in a local tool context, this presents a security risk if configs are maliciously crafted or drawn from external sources.
**Prevention:** Use `ast.literal_eval()` for parsing basic Python data structures like lists, dicts, or tuples from strings safely.
