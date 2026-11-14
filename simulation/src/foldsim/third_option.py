CRITERIA = {
    "engineering": {
        "storage": 0.10, "error": 0.20, "deflection": 0.10, "cost": 0.10,
        "reliability": 0.10, "robust": 0.40, "diversity": 0.0, "learning": 0.0,
    },
    "information": {
        "storage": 0.05, "error": 0.05, "deflection": 0.05, "cost": 0.05,
        "reliability": 0.05, "robust": 0.15, "diversity": 0.40, "learning": 0.20,
    },
}
MAXIMIZE = {"reliability", "robust", "diversity", "learning"}


def score_options(rows, criterion="information"):
    weights = CRITERIA[criterion]
    values = {}
    for name in weights:
        raw = [row[name] for row in rows]
        low, high = min(raw), max(raw)
        if high - low < 1e-12:
            values[name] = [0.0 for _ in raw]
        else:
            normalized = [(value - low) / (high - low) for value in raw]
            values[name] = [1.0 - value for value in normalized] if name in MAXIMIZE else normalized
    scores = {
        row["id"]: sum(weights[name] * values[name][index] for name in weights)
        for index, row in enumerate(rows)
    }
    return scores


def choose_third(rows, criterion="information"):
    scores = score_options(rows, criterion)
    return min(scores, key=scores.get)
