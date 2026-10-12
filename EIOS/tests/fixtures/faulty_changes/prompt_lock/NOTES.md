# prompt_lock overlay

Edits the locked `prompts/smoke-echo/v1.md` without adding a new version, so its content hash no longer matches `prompts/prompts.lock.json` and `python -m tools.prompt_lock check` reports a hash mismatch.
