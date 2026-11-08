## 2024-05-15 - Arbitrary code execution in infrastructure config parsing
**Vulnerability:** The infrastructure checking tool used eval() to parse string representations of lists from HCL/Terraform files.
**Learning:** Using eval() on external configuration files, even those assumed to be static infrastructure code, introduces a critical arbitrary code execution vulnerability.
**Prevention:** Always use ast.literal_eval() instead of eval() when parsing strings into Python data structures.
