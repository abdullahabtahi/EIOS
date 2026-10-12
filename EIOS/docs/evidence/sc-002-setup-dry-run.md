# SC-002: setup dry run

**Date**: 2026-10-02 (re-run after the repository was reorganised into `FEIOS/`). **Target**: under 30 minutes from clean checkout to a passing local check `[TARGET]`.

## What was actually done

This is a **simulation of a fresh start, not a true first-time setup**. The `FEIOS/` repository root (excluding `web-prototype/`) was copied to a new temporary directory, excluding `.venv`, `.git`, generated reports and tool caches (`rsync`), then `uv sync --frozen` and `make check` were run there, timed.

| Step | Elapsed |
|---|---|
| `uv sync --frozen` (creates `.venv` from `uv.lock`) | under 1 s (see caveat) |
| `make check` (all 11 pr gates) | 208 s wall (46 s user CPU; the remainder was waiting and was not profiled) |
| Total | about 3.5 min |

`make check` in the clean copy: all 11 pr gates `pass`, quarantined gates 0, run `f535b3bdbf474a61bab909b3d05154d2`, state `passed`.

## Caveats

- The `uv` package cache was already warm, so the sync linked cached wheels rather than downloading them. A first run on a new machine downloads roughly the locked dependency set and will be slower; this run does not measure that.
- Python 3.14 was already installed; `uv` installing the interpreter is not included.
- `vuln_scan` used the network and succeeded. A machine without network access fails that gate by design.
- `tflint`, `trivy`, `gitleaks` and `syft` are not installed on this machine, and the dry run did not need them.
- T056 describes the dry run as a manual step. The 3.5 minute figure is a lower bound; a human first-time run on a new laptop is still worth repeating and recording here when one is available.

## Verdict against the target

Within the 30-minute `[TARGET]` with a wide margin (about 3.5 min of 30) on the steps measured. Not claimed: first-time download time, or time for a person reading `docs/setup.md` for the first time.
