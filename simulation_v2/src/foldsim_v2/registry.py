import json
from pathlib import Path
from typing import Any


def load_candidates(path: str | Path) -> dict[str, dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    candidates = {}
    for spec in data["candidates"]:
        c = dict(spec)
        c["common"] = dict(data["common"])
        c["units"] = dict(data["units"])
        c["seed"] = data["seed"]
        candidates[c["id"]] = c
    return candidates
