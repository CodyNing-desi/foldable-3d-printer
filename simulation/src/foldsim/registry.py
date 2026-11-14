import json
from pathlib import Path


def load_candidates(path):
    path = Path(path)
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    candidates = {}
    for spec in data["candidates"]:
        candidate = dict(spec)
        candidate["common"] = dict(data["common"])
        candidate["units"] = dict(data["units"])
        candidate["seed"] = data["seed"]
        candidates[candidate["id"]] = candidate
    return candidates
