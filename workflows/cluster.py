import json

import numpy as np
from sklearn.cluster import KMeans

VECTORS_PATH = "data/country_vectors.json"
OUTPUT_PATH = "data/country_clusters.json"

N_CLUSTERS = 5
RANDOM_STATE = 42

FIRST_YEAR = 1987
BAND_NAMES = ["Low", "Lower-Middle", "Upper-Middle", "High"]


def _band(val):
    """Map a float centroid value to a named income band."""
    if val < 0.5:
        return "Low"
    if val < 1.5:
        return "Lower-Middle"
    if val < 2.5:
        return "Upper-Middle"
    return "High"


def _year(idx):
    return FIRST_YEAR + idx


def _describe_cluster(mean_vec):
    """Infer a human-readable description from a cluster centroid vector."""
    arr = np.array(mean_vec)
    n = len(arr)

    start = float(np.mean(arr[:4]))
    end   = float(np.mean(arr[-4:]))
    delta = end - start

    start_band = _band(start)
    end_band   = _band(end)

    min_val = float(np.min(arr))
    min_idx = int(np.argmin(arr))
    max_val = float(np.max(arr))

    # ── Classify trajectory ───────────────────────────────────────────────
    # "Stable": start and end in the same band AND overall swing is small
    same_band  = start_band == end_band
    small_swing = abs(delta) < 0.35

    # "Dip then recovery": minimum is substantially lower than both start and
    # end, and the dip is not at the very edges of the series.
    dip_depth = min(start, end) - min_val
    has_dip = (dip_depth > 0.45) and (3 < min_idx < n - 4)

    # Year of the dip
    dip_year = _year(min_idx)

    # "Monotone rise / fall": no significant dip, clear directional trend
    # Use decade-level sub-means to detect sustained direction
    q1 = float(np.mean(arr[: n // 3]))
    q3 = float(np.mean(arr[2 * n // 3 :]))
    monotone_rise = (q3 - q1) >  0.40 and not has_dip
    monotone_fall = (q1 - q3) >  0.40 and not has_dip

    # ── Build sentence ────────────────────────────────────────────────────
    if same_band and small_swing:
        # Stable throughout
        adjective = "throughout 1987–2025"
        if max_val - min_val < 0.15:
            adjective += " with virtually no variation"
        return (
            f"Persistently {start_band} income {adjective}. "
            f"The centroid stays near {np.mean(arr):.2f} for the entire period."
        )

    if has_dip:
        # Recovery pattern: dip somewhere in the middle
        dip_band = _band(min_val)
        context = (
            "(consistent with post-Soviet transition economies)"
            if 1991 <= dip_year <= 2000
            else "(often reflecting conflict or severe economic contraction)"
        )
        return (
            f"{start_band} income in the late 1980s, declining to {dip_band} "
            f"income around {dip_year} {context}, "
            f"then recovering to {end_band} income by the early 2020s."
        )

    if monotone_rise:
        if start_band == end_band:
            return (
                f"Rising within the {start_band} income band across the full "
                f"period — from roughly {start:.2f} in 1987 to {end:.2f} by 2025."
            )
        # Find the approximate year of band transition
        threshold = {"Low": 0.5, "Lower-Middle": 1.5, "Upper-Middle": 2.5}.get(start_band)
        cross_yr = None
        if threshold is not None:
            crossings = [i for i in range(n - 1) if arr[i] < threshold <= arr[i + 1]]
            if crossings:
                cross_yr = _year(crossings[0])
        transition = f"around {cross_yr}" if cross_yr else "over the period"
        return (
            f"{start_band} income through the 1990s and into the 2000s, rising "
            f"to {end_band} income {transition} and sustaining that level through 2025."
        )

    if monotone_fall:
        return (
            f"Started as {start_band} income in 1987 and declined to "
            f"{end_band} income by 2025."
        )

    # Default: describe start and end with general trend
    trend = "gradual improvement" if delta > 0.1 else ("slight decline" if delta < -0.1 else "broad stability")
    return (
        f"Broadly {start_band} income at the start of the period, with {trend} "
        f"to {end_band} income by 2025 (centroid moved from {start:.2f} to {end:.2f})."
    )



def _impute(vec):
    """Replace None entries with the country's own mean; fall back to 1.5."""
    arr = np.array([v if v is not None else np.nan for v in vec], dtype=float)
    mean = np.nanmean(arr)
    if np.isnan(mean):
        mean = 1.5  # global mid-point fallback
    arr = np.where(np.isnan(arr), mean, arr)
    return arr


def build():
    with open(VECTORS_PATH, encoding="utf-8") as f:
        country_vectors = json.load(f)

    countries = sorted(country_vectors.keys())
    matrix = np.array([_impute(country_vectors[iso]) for iso in countries])

    kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=RANDOM_STATE, n_init=20)
    labels = kmeans.fit_predict(matrix)

    # Group countries by cluster label
    groups = {}
    for iso, label in zip(countries, labels):
        groups.setdefault(int(label), []).append(iso)

    # Build output: sort clusters by their mean income (ascending)
    clusters = []
    for label, country_list in groups.items():
        mean_vec = kmeans.cluster_centers_[label].tolist()
        overall_mean = float(np.mean(kmeans.cluster_centers_[label]))
        clusters.append({
            "cluster_mean": [round(v, 3) for v in mean_vec],
            "country_list": sorted(country_list),
            "_sort_key": overall_mean,
        })

    clusters.sort(key=lambda c: c.pop("_sort_key"))

    for i, cluster in enumerate(clusters):
        cluster["description"] = _describe_cluster(cluster["cluster_mean"])

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(clusters, f, indent=2)

    print(f"Saved {OUTPUT_PATH}")
    for i, c in enumerate(clusters):
        print(f"  Cluster {i+1:2d}: {len(c['country_list'])} countries — {c['country_list'][:5]}...")


if __name__ == "__main__":
    build()
