import json

JSON_PATH = "data/country_classes.json"
OUTPUT_PATH = "data/country_vectors.json"

# Map income class -> integer (strip trailing * before lookup)
CLASS_INT = {
    "L":  0,
    "LM": 1,
    "UM": 2,
    "H":  3,
}


def _class_to_int(raw):
    """Return integer for a class string, or None if unknown/missing."""
    if raw is None:
        return None
    return CLASS_INT.get(raw.rstrip("*"))


def build():
    with open(JSON_PATH, encoding="utf-8") as f:
        country_classes = json.load(f)

    years = sorted(country_classes.keys())

    # Collect all country codes across all years
    all_countries = sorted({iso for year_data in country_classes.values() for iso in year_data})

    vectors = {}
    for iso in all_countries:
        vec = [_class_to_int(country_classes[year].get(iso)) for year in years]
        vectors[iso] = vec

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(vectors, f, indent=2)

    print(f"Saved {OUTPUT_PATH}")
    print(f"  Countries: {len(vectors)}")
    print(f"  Years ({len(years)}): {years[0]}–{years[-1]}")
    print(f"  Sample (AFG): {vectors['AFG']}")


if __name__ == "__main__":
    build()
