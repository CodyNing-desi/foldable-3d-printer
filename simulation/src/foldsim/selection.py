def pareto_mask(points):
    mask = []
    for i, point in enumerate(points):
        dominated = False
        for j, other in enumerate(points):
            if i == j:
                continue
            no_worse = all(o <= p for o, p in zip(other, point))
            strictly_better = any(o < p for o, p in zip(other, point))
            if no_worse and strictly_better:
                dominated = True
                break
        mask.append(not dominated)
    return mask


def choose_diverse(rows, count=3, fill_same_family=True):
    ordered = sorted(rows, key=lambda row: (-row["robust_frequency"], row["baseline_score"], row["id"]))
    selected = []
    families = set()
    for row in ordered:
        if row["family_group"] in families:
            continue
        selected.append(row["id"])
        families.add(row["family_group"])
        if len(selected) == count:
            return selected
    if fill_same_family:
        for row in ordered:
            if row["id"] not in selected:
                selected.append(row["id"])
            if len(selected) == count:
                break
    return selected
