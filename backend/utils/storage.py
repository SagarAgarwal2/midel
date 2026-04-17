import json
import os
from typing import Any


def ensure_parent_dir(file_path: str) -> None:
    parent = os.path.dirname(file_path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def read_json(file_path: str, default: Any = None) -> Any:
    if default is None:
        default = []
    if not os.path.exists(file_path):
        return default
    with open(file_path, "r", encoding="utf-8") as file:
        raw = file.read().strip()

    if not raw:
        return default

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to recover if trailing shell/prompt characters were accidentally appended.
        end_positions = [idx for idx, ch in enumerate(raw) if ch in {"]", "}"}]
        for cut_index in reversed(end_positions):
            candidate = raw[: cut_index + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
        return default


def write_json(file_path: str, payload: Any) -> None:
    ensure_parent_dir(file_path)
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)
