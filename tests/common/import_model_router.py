from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def load_model_router() -> ModuleType:
    root = Path(__file__).resolve().parents[2]
    module_path = root / "scripts" / "model_router.py"
    spec = importlib.util.spec_from_file_location("model_router", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module spec: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
