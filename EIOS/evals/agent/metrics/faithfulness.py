"""`agents-cli eval` metric: figure faithfulness (spec 022, US6). Local, deterministic, no network.

The Google eval CLI runs this source in its own Python 3.12 process, without `__file__`, so it cannot import
`eios` or locate itself. It loads the standard-library judge in `src/eios/agent_gates/core/` as a package by
path instead, found from `EIOS_AGENT_GATES_CORE` or the working directory.
"""

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

_RELATIVE = Path("src") / "eios" / "agent_gates" / "core"


def _find_core() -> Path:
    """The judge directory. The Google CLI runs this source without `__file__`, so look from the environment
    (`EIOS_AGENT_GATES_CORE`) or upward from the working directory."""
    configured = os.environ.get("EIOS_AGENT_GATES_CORE")
    if configured:
        return Path(configured)
    for base in (Path.cwd(), *Path.cwd().parents):
        for candidate in (base / _RELATIVE, base / "EIOS" / _RELATIVE):
            if (candidate / "faithfulness.py").is_file():
                return candidate
    raise ImportError("set EIOS_AGENT_GATES_CORE or run from inside the repository")


def _load_judge() -> Any:
    core = _find_core()
    spec = importlib.util.spec_from_file_location(
        "agent_gates_core", core / "__init__.py", submodule_search_locations=[str(core)]
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load the judge from {core}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["agent_gates_core"] = module
    spec.loader.exec_module(module)
    return importlib.import_module("agent_gates_core.faithfulness")


def _record_from(instance: dict[str, Any]) -> dict[str, Any]:
    """Rebuild a Turn Record from an `agents-cli` case: the answer, and each tool call with its result."""
    response = (
        instance.get("response") or (instance.get("responses") or [{}])[0].get("response") or {}
    )
    answer = "".join(p.get("text", "") for p in response.get("parts", []))
    calls: list[dict[str, Any]] = []
    pending: dict[str, Any] | None = None
    for turn in (instance.get("agent_data") or {}).get("turns", []):
        for event in turn.get("events", []):
            for part in (event.get("content") or {}).get("parts", []):
                if part.get("function_call"):
                    pending = {
                        "name": part["function_call"]["name"],
                        "arguments": part["function_call"].get("args", {}),
                    }
                elif part.get("function_response") and pending is not None:
                    calls.append(pending | {"result": part["function_response"].get("response")})
                    pending = None
    prompt = " ".join(p.get("text", "") for p in (instance.get("prompt") or {}).get("parts", []))
    return {"answer": answer, "question": prompt, "entity_context": None, "tool_calls": calls}


def evaluate(instance: dict[str, Any]) -> dict[str, Any]:
    verdict = _load_judge().judge(_record_from(instance))
    bad = "; ".join(f"'{v.text}' {v.reason}" for v in verdict.unsupported())
    return {
        "score": 1.0 if verdict.passed else 0.0,
        "explanation": bad or "every figure is supported",
    }
