"""Internal entry point: execute one reviewed built-in capability."""
import importlib
import json
from pathlib import Path
import sys

from omega_runtime import MODULES, MAX_RESULT_BYTES


def main(workspace):
    root = Path(workspace).resolve()
    try:
        request = json.loads((root / "request.json").read_text(encoding="utf-8"))
        handler = None
        for name in MODULES:
            try:
                module = importlib.import_module(name)
            except ModuleNotFoundError as exc:
                if exc.name != name:
                    raise
                continue
            handler = module.CAPABILITIES.get(request["capability"])
            if handler:
                break
        if handler is None:
            raise ValueError("Unknown capability")
        result = handler(request["payload"], root)
        outcome = {"ok": True, "result": result}
        encoded = json.dumps(outcome, allow_nan=False)
        if len(encoded.encode()) > MAX_RESULT_BYTES:
            raise ValueError("Capability result exceeds 2 MiB")
    except Exception as exc:
        encoded = json.dumps({"ok": False, "error": {"code": type(exc).__name__, "message": str(exc)[:600]}})
    (root / "result.json").write_text(encoded, encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
