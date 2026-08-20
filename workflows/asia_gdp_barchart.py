import argparse
import json
import os
import urllib.parse
import urllib.request

from workflows.world_gpd_barchart import (
    _encode_video,
    _load_countries,
    _load_population,
    _render_frames,
    filter_countries_by_population,
)


IMAGES_DIR = "images/asia_gdp_barchart"
OUTPUT_PATH = "videos/asia_gdp_barchart.mp4"
GNI_PATH = "data/gni_per_capita_atlas.json"
GNI_INDICATOR = "NY.GNP.PCAP.CD"
GNI_SOURCE_URL = f"https://data.worldbank.org/indicator/{GNI_INDICATOR}"
INCOME_THRESHOLDS_2025 = [
    (1_175, None),
    (4_635, None),
    (14_375, None),
]
INCOME_CLASSES = ["LOW", "LOWER-MIDDLE", "UPPER-MIDDLE", "HIGH"]
SUBREGION_COLORS = {
    "Central Asia": "#2f6bff",
    "Eastern Asia": "#d64550",
    "South-Eastern Asia": "#2e8b57",
    "Southern Asia": "#e0a800",
    "Western Asia": "#7a5195",
}
COUNTRY_NAMES = {
    "ARE": "UAE",
    "KOR": "R. Korea",
    "SAU": "S. Arabia",
}


def _fetch_gni_data():
    query = urllib.parse.urlencode(
        {"date": "1990:2025", "format": "json", "per_page": 20_000}
    )
    request = urllib.request.Request(
        "https://api.worldbank.org/v2/country/all/indicator/"
        f"{GNI_INDICATOR}?{query}",
        headers={"User-Agent": "world-income-chart/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    if not isinstance(payload, list) or len(payload) < 2 or not payload[1]:
        raise RuntimeError("World Bank returned no GNI per capita data")

    data = {}
    for record in payload[1]:
        iso = record.get("countryiso3code")
        year = record.get("date")
        value = record.get("value")
        if iso and year and value is not None:
            data.setdefault(year, {})[iso] = float(value)
    return {year: dict(sorted(values.items())) for year, values in sorted(data.items())}


def _load_gni_data(refresh=False):
    if not refresh and os.path.exists(GNI_PATH):
        with open(GNI_PATH, encoding="utf-8") as file:
            return json.load(file)
    data = _fetch_gni_data()
    with open(GNI_PATH, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
    print(f"Saved {GNI_PATH}")
    return data


def filter_asian_countries(countries):
    return countries[countries["CONTINENT"] == "Asia"].copy()


def build(
    frames_only=False, start_year=None, end_year=None, refresh_population=False,
    refresh_data=False,
):
    countries = filter_asian_countries(_load_countries())
    countries = filter_countries_by_population(
        countries, _load_population(refresh=refresh_population)
    )
    years = _render_frames(
        countries,
        _load_gni_data(refresh=refresh_data),
        start_year=start_year,
        end_year=end_year,
        images_dir=IMAGES_DIR,
        chart_title="Asia GNI per capita, Atlas method",
        special_label_size=10.5,
        show_region_extremes=False,
        show_all_bar_labels=True,
        show_x_labels=False,
        color_column="SUBREGION",
        color_map=SUBREGION_COLORS,
        y_max_multiplier=2,
        metric_axis_label="GNI PER CAPITA, ATLAS METHOD (LOG SCALE)",
        ranking_axis_label="COUNTRIES, HIGHEST TO LOWEST GNI PER CAPITA",
        methodology_note=(
            "Countries with a 2025 population below 1 million are excluded\n"
            "Dotted lines: World Bank 2025 income thresholds\n"
            "GNI: NY.GNP.PCAP.CD  ·  Population: SP.POP.TOTL"
        ),
        source_url=GNI_SOURCE_URL,
        threshold_lines=INCOME_THRESHOLDS_2025,
        threshold_class_labels=INCOME_CLASSES,
        sort_ascending=False,
        country_names=COUNTRY_NAMES,
        legend_loc="upper right",
        plot_bottom=0.18,
    )
    if not frames_only:
        _encode_video(years, images_dir=IMAGES_DIR, output_path=OUTPUT_PATH)


def main():
    parser = argparse.ArgumentParser(
        description="Build a sorted Asian GDP-per-capita bar-chart animation."
    )
    parser.add_argument(
        "--frames-only", action="store_true",
        help="Render PNG frames without encoding an MP4.",
    )
    parser.add_argument("--start-year", type=int, help="First year to render (inclusive).")
    parser.add_argument("--end-year", type=int, help="Last year to render (inclusive).")
    parser.add_argument(
        "--refresh-population", action="store_true",
        help="Download fresh 2025 population data from the World Bank.",
    )
    parser.add_argument(
        "--refresh-data", action="store_true",
        help="Download fresh GNI per capita data from the World Bank.",
    )
    args = parser.parse_args()
    build(
        frames_only=args.frames_only,
        start_year=args.start_year,
        end_year=args.end_year,
        refresh_population=args.refresh_population,
        refresh_data=args.refresh_data,
    )


if __name__ == "__main__":
    main()