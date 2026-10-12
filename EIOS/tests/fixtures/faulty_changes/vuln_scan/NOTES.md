# vuln_scan overlay

Replaces `pyproject.toml` and `uv.lock` so the lockfile pins `requests==2.19.1`, which resolves `urllib3==1.23` and `idna==2.7`; the dependency audit reports published advisories against all three. Only the `vuln_scan` gate may fail: no code changes.

## [SPIKE] advisory record

- Package and version: `requests==2.19.1`.
- Advisory id: `PYSEC-2018-28` (fixed in 2.20.0).
- Also reported at the check: `PYSEC-2019-132` and `PYSEC-2019-133` (`urllib3==1.23`), `PYSEC-2024-60` (`idna==2.7`).
- Date checked: 2026-10-02, with `pip-audit` 2.10.1 against the PyPI advisory data it queries.

Unverified until re-run: advisory databases change, but a published advisory is not withdrawn for a release this old, so the overlay should keep failing. If it ever stops, choose another old release and refresh this note and `uv.lock` (`uv lock` inside this directory).
