import argparse
import json
import math
import os
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request

import geopandas as gpd
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, LogLocator


SHAPEFILE = "original_data/ne_110m/ne_110m_admin_0_countries.shp"
DATA_PATH = "data/gdp_per_capita_ppp.json"
POPULATION_PATH = "data/population_2025.json"
IMAGES_DIR = "images/world_gdp_barchart"
OUTPUT_PATH = "videos/world_gdp_barchart.mp4"
SOURCE_URL = "https://data.worldbank.org/indicator/NY.GDP.PCAP.PP.CD"
POPULATION_SOURCE_URL = "https://data.worldbank.org/indicator/SP.POP.TOTL"

REFERENCE_ISO = "LKA"
POPULATION_YEAR = 2025
MIN_POPULATION = 1_000_000
FPS = 1
OUTPUT_FPS = 10
HOLD_LAST = 4
OUTPUT_WIDTH = 1920

BACKGROUND = "#f4f1e8"
TEXT_COLOR = "#202421"
GRID_COLOR = "#c9c5b9"
REGION_COLORS = {
    "Africa": "#2e8b57",
    "Asia": "#e0a800",
    "Europe": "#2f6bff",
    "North America": "#d64550",
    "Oceania": "#7a5195",
    "South America": "#f28e2b",
    "Seven seas (open ocean)": "#777777",
}


def _load_data():
    with open(DATA_PATH, encoding="utf-8") as file:
        return json.load(file)


def _fetch_population():
    query = urllib.parse.urlencode(
        {"date": POPULATION_YEAR, "format": "json", "per_page": 400}
    )
    request = urllib.request.Request(
        f"https://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL?{query}",
        headers={"User-Agent": "world-income-chart/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)

    if not isinstance(payload, list) or len(payload) < 2 or not payload[1]:
        raise RuntimeError(f"World Bank returned no {POPULATION_YEAR} population data")
    return {
        record["countryiso3code"]: float(record["value"])
        for record in payload[1]
        if record.get("countryiso3code") and record.get("value") is not None
    }


def _load_population(refresh=False):
    if not refresh and os.path.exists(POPULATION_PATH):
        with open(POPULATION_PATH, encoding="utf-8") as file:
            return json.load(file)["values"]

    population = _fetch_population()
    with open(POPULATION_PATH, "w", encoding="utf-8") as file:
        json.dump(
            {"year": POPULATION_YEAR, "indicator": "SP.POP.TOTL", "values": population},
            file,
            indent=2,
            sort_keys=True,
        )
    print(f"Saved {POPULATION_PATH}")
    return population


def _load_countries():
    world = gpd.read_file(SHAPEFILE)
    world["iso"] = world.apply(
        lambda row: row["ADM0_A3"] if row["ISO_A3"] == "-99" else row["ISO_A3"],
        axis=1,
    )
    return world[
        ["iso", "NAME_LONG", "CONTINENT", "SUBREGION"]
    ].drop_duplicates("iso")


def filter_countries_by_population(
    countries, population, minimum=MIN_POPULATION
):
    population_values = countries["iso"].map(population)
    return countries[population_values.isna() | (population_values >= minimum)].copy()


def sorted_country_values(countries, year_data, ascending=True):
    bars = countries[countries["iso"].isin(year_data)].copy()
    bars["value"] = bars["iso"].map(year_data)
    bars = bars[bars["value"].notna() & (bars["value"] > 0)]
    return bars.sort_values(
        ["value", "iso"], ascending=[ascending, True]
    ).reset_index(drop=True)


def region_extremes(bars):
    extremes = []
    for _region, region_bars in bars.groupby("CONTINENT", sort=False):
        extremes.append(region_bars.iloc[0])
        if len(region_bars) > 1:
            extremes.append(region_bars.iloc[-1])
    return extremes


def ranked_country_label(country, country_names=None):
    name = (country_names or {}).get(country["iso"], country["NAME_LONG"])
    return f"{name} ({country.name + 1})"


def _annotate_bar_label(
    ax, country, label, color, fontsize=5.5, fontweight="bold"
):
    ax.annotate(
        label,
        xy=(country.name, country.value),
        xytext=(0, 4), textcoords="offset points",
        ha="left", va="center", rotation=90, rotation_mode="anchor",
        fontsize=fontsize, fontweight=fontweight, color=color, zorder=4,
    )


def log_limits(countries, data):
    country_isos = set(countries["iso"])
    values = [
        value
        for year_data in data.values()
        for iso, value in year_data.items()
        if iso in country_isos and value is not None and value > 0
    ]
    if not values:
        raise RuntimeError("No positive country GDP values were found")

    lower = 10 ** math.floor(math.log10(min(values)))
    upper = 10 ** (math.ceil(math.log10(max(values)) * 10) / 10 + 0.1)
    return lower, upper


def _dollar_formatter(value, _position):
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}m"
    if value >= 1_000:
        return f"${value / 1_000:.0f}k"
    return f"${value:,.0f}"


def _legend_handles(regions):
    return [
        mpatches.Patch(color=REGION_COLORS[region], label=region)
        for region in regions
    ]


def _render_frames(
    countries,
    data,
    start_year=None,
    end_year=None,
    images_dir=IMAGES_DIR,
    chart_title="World GDP per capita, PPP",
    tick_label_size=5,
    special_label_size=5.5,
    show_region_extremes=True,
    show_all_bar_labels=False,
    show_x_labels=True,
    color_column="CONTINENT",
    color_map=REGION_COLORS,
    y_max_multiplier=1,
    metric_axis_label="GDP PER CAPITA, PPP (LOG SCALE)",
    ranking_axis_label="COUNTRIES, LOWEST TO HIGHEST GDP PER CAPITA",
    methodology_note=None,
    source_url=SOURCE_URL,
    threshold_lines=None,
    threshold_class_labels=None,
    sort_ascending=True,
    country_names=None,
    legend_loc="upper left",
    plot_bottom=0.25,
):
    os.makedirs(images_dir, exist_ok=True)
    years = [
        year for year in sorted(data)
        if (start_year is None or int(year) >= start_year)
        and (end_year is None or int(year) <= end_year)
        and not sorted_country_values(countries, data[year]).empty
    ]
    if not years:
        raise RuntimeError("No GDP data matches the requested year range")

    y_min, y_max = log_limits(countries, data)
    for year in years:
        bars = sorted_country_values(
            countries, data[year], ascending=sort_ascending
        )
        colors = bars[color_column].map(color_map).fillna("#777777")
        regions = [
            region for region in color_map
            if region in set(bars[color_column])
        ]

        fig, ax = plt.subplots(figsize=(16, 9))
        fig.patch.set_facecolor(BACKGROUND)
        ax.set_facecolor(BACKGROUND)
        positions = range(len(bars))
        ax.bar(
            positions,
            bars["value"] - y_min,
            bottom=y_min,
            color=colors,
            width=0.88,
            linewidth=0,
            zorder=3,
        )

        ax.set_yscale("log")
        ax.set_ylim(y_min, y_max * y_max_multiplier)
        ax.set_xlim(-0.7, len(bars) - 0.3)
        ax.yaxis.set_major_locator(LogLocator(base=10))
        ax.yaxis.set_major_formatter(FuncFormatter(_dollar_formatter))
        ax.grid(axis="y", which="major", color=GRID_COLOR, linewidth=0.8, zorder=1)
        ax.grid(axis="y", which="minor", color=GRID_COLOR, linewidth=0.35, alpha=0.45)
        threshold_boundaries = []
        for threshold, _label in threshold_lines or []:
            if sort_ascending:
                boundary = sum(bars["value"] < threshold) - 0.5
            else:
                boundary = sum(bars["value"] >= threshold) - 0.5
            threshold_boundaries.append(boundary)
            ax.axvline(
                boundary, color=TEXT_COLOR, linewidth=0.8,
                linestyle=(0, (2, 3)), alpha=0.65, zorder=2,
            )
        if threshold_class_labels:
            plot_left, plot_right = ax.get_xlim()
            class_edges = [plot_left, *sorted(threshold_boundaries), plot_right]
            thresholds = sorted(threshold for threshold, _label in threshold_lines)
            class_counts = [sum(bars["value"] < thresholds[0])]
            class_counts.extend(
                sum((bars["value"] >= lower) & (bars["value"] < upper))
                for lower, upper in zip(thresholds, thresholds[1:])
            )
            class_counts.append(sum(bars["value"] >= thresholds[-1]))
            class_labels = list(threshold_class_labels)
            if not sort_ascending:
                class_labels.reverse()
                class_counts.reverse()
            for label, count, left, right in zip(
                class_labels, class_counts, class_edges, class_edges[1:]
            ):
                if count == 0:
                    continue
                ax.annotate(
                    label, xy=((left + right) / 2, 1.035),
                    xycoords=ax.get_xaxis_transform(), xytext=(0, -3),
                    textcoords="offset points", ha="center", va="top",
                    fontsize=7, color=TEXT_COLOR, zorder=4,
                )
        if show_x_labels:
            axis_labels = [
                ranked_country_label(country, country_names)
                for _, country in bars.iterrows()
            ]
            ax.set_xticks(list(positions), axis_labels, rotation=90)
            ax.tick_params(
                axis="x", colors="#555a56", labelsize=tick_label_size,
                length=0, pad=3,
            )
            plt.setp(ax.get_xticklabels(), ha="center", va="top")
        else:
            ax.set_xticks([])
        ax.tick_params(axis="y", colors="#555a56", labelsize=9, length=0)
        ax.set_xlabel(
            ranking_axis_label,
            color="#555a56", fontsize=9, labelpad=12,
        )
        ax.set_ylabel(
            metric_axis_label,
            color="#555a56", fontsize=10, labelpad=14,
        )
        for spine in ax.spines.values():
            spine.set_visible(False)

        if show_all_bar_labels:
            for _, country in bars.iterrows():
                _annotate_bar_label(
                    ax, country, ranked_country_label(country, country_names),
                    TEXT_COLOR,
                    special_label_size,
                    "bold" if country["iso"] == REFERENCE_ISO else "normal",
                )
        else:
            reference = bars[bars["iso"] == REFERENCE_ISO]
            if not reference.empty:
                _annotate_bar_label(
                    ax, reference.iloc[0],
                    ranked_country_label(reference.iloc[0], country_names),
                    TEXT_COLOR, special_label_size,
                )

        if show_region_extremes:
            for country in region_extremes(bars):
                if country["iso"] == REFERENCE_ISO:
                    continue
                color = color_map.get(country[color_column], "#777777")
                _annotate_bar_label(
                    ax, country, ranked_country_label(country, country_names), color,
                    special_label_size,
                )

        fig.text(
            0.06, 0.95, year, ha="left", va="top",
            fontsize=48, fontweight="bold", color=TEXT_COLOR,
        )
        fig.text(
            0.06, 0.875, chart_title,
            ha="left", va="top", fontsize=19, color=TEXT_COLOR,
        )
        fig.text(
            0.94, 0.94,
            methodology_note or (
                "Countries with a 2025 population below 1 million are excluded\n"
                "GDP per capita, PPP: World Bank NY.GDP.PCAP.PP.CD\n"
                "Population: World Bank SP.POP.TOTL"
            ),
            ha="right", va="top", fontsize=9, color="#666b67",
        )
        fig.text(
            0.5, 0.012, f"Source: World Bank  ·  {source_url}",
            ha="center", va="bottom", fontsize=8, color="#777b77",
        )
        ax.legend(
            handles=[
                mpatches.Patch(color=color_map[region], label=region)
                for region in regions
            ],
            loc=legend_loc,
            ncols=len(regions) if legend_loc == "upper right" else 4,
            bbox_to_anchor=(
                1 if legend_loc == "upper right" else 0,
                1.12 if legend_loc == "upper right" else 1.02,
            ),
            frameon=False, fontsize=8,
            columnspacing=1.3, handletextpad=0.45,
        )

        fig.subplots_adjust(top=0.79, bottom=plot_bottom, left=0.09, right=0.97)
        output_path = os.path.join(images_dir, f"{year}.png")
        fig.savefig(output_path, dpi=150, facecolor=BACKGROUND)
        plt.close(fig)
        print(f"Saved {output_path}")

    return years


def _encode_video(years, images_dir=IMAGES_DIR, output_path=OUTPUT_PATH):
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required to encode the animation")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    frame_duration = 1.0 / FPS
    last_path = os.path.abspath(os.path.join(images_dir, f"{years[-1]}.png"))
    frame_list_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as frame_list:
            frame_list_path = frame_list.name
            for year in years:
                path = os.path.abspath(os.path.join(images_dir, f"{year}.png"))
                frame_list.write(f"file '{path}'\n")
                frame_list.write(f"duration {frame_duration:.6f}\n")
            frame_list.write(f"file '{last_path}'\n")
            frame_list.write(f"duration {float(HOLD_LAST):.6f}\n")
            frame_list.write(f"file '{last_path}'\n")

        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", frame_list_path,
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                "-vf", f"scale={OUTPUT_WIDTH}:-2,fps={OUTPUT_FPS}",
                "-c:v", "libx264", "-crf", "18", "-preset", "slow",
                "-c:a", "aac", "-b:a", "128k", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", "-shortest", output_path,
            ],
            check=True,
        )
    finally:
        if frame_list_path and os.path.exists(frame_list_path):
            os.unlink(frame_list_path)

    print(f"Saved {output_path}")


def build(
    frames_only=False, start_year=None, end_year=None, refresh_population=False
):
    countries = filter_countries_by_population(
        _load_countries(), _load_population(refresh=refresh_population)
    )
    years = _render_frames(
        countries, _load_data(), start_year=start_year, end_year=end_year
    )
    if not frames_only:
        _encode_video(years)


def main():
    parser = argparse.ArgumentParser(
        description="Build a sorted world GDP-per-capita bar-chart animation."
    )
    parser.add_argument(
        "--frames-only", action="store_true", help="Render PNG frames without encoding an MP4."
    )
    parser.add_argument("--start-year", type=int, help="First year to render (inclusive).")
    parser.add_argument("--end-year", type=int, help="Last year to render (inclusive).")
    parser.add_argument(
        "--refresh-population", action="store_true",
        help="Download fresh 2025 population data from the World Bank.",
    )
    args = parser.parse_args()
    build(
        frames_only=args.frames_only,
        start_year=args.start_year,
        end_year=args.end_year,
        refresh_population=args.refresh_population,
    )


if __name__ == "__main__":
    main()