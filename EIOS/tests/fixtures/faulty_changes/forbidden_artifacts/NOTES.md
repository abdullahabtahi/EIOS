# forbidden_artifacts overlay

`build.py` writes `infra/tfplan` when the test runs, so the overlay directory itself holds no plan file (a tracked `tfplan` would trip this very check on the real repository). Only the `forbidden_artifacts` gate may fail: the clean skeleton has no other forbidden file.
