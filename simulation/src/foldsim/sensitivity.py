from scipy.stats import qmc


def latin_samples(spec, count, seed):
    names = list(spec["bounds"])
    if not names:
        return []
    sampler = qmc.LatinHypercube(d=len(names), seed=seed)
    unit = sampler.random(count)
    rows = []
    for sample in unit:
        row = {}
        for name, value in zip(names, sample):
            low, high = spec["bounds"][name]
            row[name] = float(low + value * (high - low))
        rows.append(row)
    return rows
