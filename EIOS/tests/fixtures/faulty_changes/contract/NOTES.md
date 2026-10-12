# contract overlay

Replaces `evals/registry.yaml` with one valid `contract`-tier suite, `broken-data-contract`, whose script writes its report and exits 1 (data contract check failed: required field missing). The failure is a suite failure, not a registry error.
