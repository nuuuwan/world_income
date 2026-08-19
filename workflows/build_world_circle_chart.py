import argparse
import json
import math
import os
import shutil
import subprocess
import tempfile

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, LogLocator


SHAPEFILE = "original_data/ne_110m/ne_110m_admin_0_countries.shp"
DATA_PATH = "data/gdp_per_capita_ppp.json"
IMAGES_DIR = "images/world_circle_chart"
OUTPUT_PATH = "videos/world_gdp_circle_chart.mp4"
SOURCE_URL = "https://data.worldbank.org/indicator/NY.GDP.PCAP.PP.CD"

WORLD_ISO = "WLD"
REFERENCE_ISO = "LKA"
RANKING_START_YEAR = "1990"
RANKING_END_YEAR = "2025"
RANKING_COUNT = 10
FPS = 1
OUTPUT_FPS = 10
HOLD_LAST = 4
OUTPUT_WIDTH = 1920

BACKGROUND = "#f4f1e8"
TEXT_COLOR = "#202421"
GRID_COLOR = "#c9c5b9"
CONTINENT_COLORS = {
    "Africa": "#2e8b57",
    "Asia": "#f2c94c",
    "Europe": "#2f6bff",
    "North America": "#d64550",
    "Oceania": "#7a5195",
    "South America": "#f28e2b",
    "Seven seas (open ocean)": "#777777",
}


def _load_data():
    with open(DATA_PATH, encoding="utf-8") as file:
        return json.load(file)


def _load_countries():
    world = gpd.read_file(SHAPEFILE)
    world["iso"] = world.apply(
        lambda row: row["ADM0_A3"] if row["ISO_A3"] == "-99" else row["ISO_A3"],
        axis=1,
    )
    world["longitude"] = world.geometry.representative_point().x
    world = world.sort_values(["longitude", "iso"]).reset_index(drop=True)
    world["rank"] = world.index + 1
    return world[["iso", "NAME_LONG", "CONTINENT", "longitude", "rank"]]


def centered_log_limits(data, country_isos):
    ratios = []
    for year_data in data.values():
        world_mean = year_data.get(WORLD_ISO)
        if not world_mean or world_mean <= 0:
            continue
        ratios.extend(
            value / world_mean
            for iso, value in year_data.items()
            if iso in country_isos and value is not None and value > 0
        )

    if not ratios:
        raise RuntimeError("No positive country GDP values have a world mean")

    extent = max(max(ratios), 1 / min(ratios))
    padded_extent = 10 ** (math.ceil(math.log10(extent) * 10) / 10 + 0.1)
    return 1 / padded_extent, padded_extent


def growth_extremes(
    data,
    country_isos,
    start_year=RANKING_START_YEAR,
    end_year=RANKING_END_YEAR,
    count=RANKING_COUNT,
):
    start_data = data.get(start_year, {})
    end_data = data.get(end_year, {})
    changes = []
    for iso in country_isos:
        start_value = start_data.get(iso)
        end_value = end_data.get(iso)
        if start_value and end_value and start_value > 0 and end_value > 0:
            changes.append((end_value / start_value, iso))

    if len(changes) < count * 2:
        raise RuntimeError(
            f"Fewer than {count * 2} countries have GDP data in both "
            f"{start_year} and {end_year}"
        )

    changes.sort()
    losers = [iso for _change, iso in changes[:count]]
    winners = [iso for _change, iso in changes[-count:][::-1]]
    return winners, losers


def _dollar_tick_formatter(world_mean):
    def formatter(ratio, _position):
        value = ratio * world_mean
        if value >= 1_000_000:
            return f"${value / 1_000_000:.1f}m"
        if value >= 1_000:
            return f"${value / 1_000:.0f}k"
        return f"${value:,.0f}"

    return FuncFormatter(formatter)


def _legend_handles(continents):
    return [
        Line2D(
            [0], [0], marker="o", linestyle="", markersize=9,
            markerfacecolor=CONTINENT_COLORS[continent], markeredgecolor="white",
            alpha=0.5, label=continent,
        )
        for continent in continents
    ]


def _render_frames(countries, data, start_year=None, end_year=None):
    os.makedirs(IMAGES_DIR, exist_ok=True)
    country_isos = set(countries["iso"])
    years = [
        year for year in sorted(data)
        if (start_year is None or int(year) >= start_year)
        and (end_year is None or int(year) <= end_year)
        and data[year].get(WORLD_ISO)
    ]
    if not years:
        raise RuntimeError("No years with a world GDP mean match the requested range")

    y_min, y_max = centered_log_limits(data, country_isos)
    winners, losers = growth_extremes(data, country_isos)
    winner_isos = set(winners)
    loser_isos = set(losers)
    for year in years:
        year_data = data[year]
        world_mean = year_data[WORLD_ISO]
        points = countries[countries["iso"].isin(year_data)].copy()
        points["value"] = points["iso"].map(year_data)
        points = points[points["value"] > 0]
        points["ratio"] = points["value"] / world_mean
        points["color"] = points["CONTINENT"].map(CONTINENT_COLORS).fillna("#777777")
        continents = [
            continent for continent in CONTINENT_COLORS
            if continent in set(points["CONTINENT"])
        ]

        fig, ax = plt.subplots(figsize=(16, 9))
        fig.patch.set_facecolor(BACKGROUND)
        ax.set_facecolor(BACKGROUND)
        other_points = points[points["iso"] != REFERENCE_ISO]
        ax.scatter(
            other_points["rank"], other_points["ratio"],
            s=105, c=other_points["color"], edgecolors="white",
            linewidths=0.7, alpha=0.5, zorder=3,
        )
        reference_points = points[points["iso"] == REFERENCE_ISO]
        if not reference_points.empty:
            ax.scatter(
                reference_points["rank"], reference_points["ratio"],
                s=105, c=reference_points["color"], edgecolors="white",
                linewidths=1.0, alpha=1, zorder=4,
            )

        ax.set_yscale("log")
        ax.set_ylim(y_min, y_max)
        ax.set_xlim(0, len(countries) + 1)
        ax.axhline(
            1, color=TEXT_COLOR, linewidth=1.3, linestyle=(0, (2, 3)), zorder=2
        )
        ax.annotate(
            "WORLD MEAN",
            xy=(len(countries), 1), xytext=(-4, 7), textcoords="offset points",
            ha="right", va="bottom", fontsize=8, fontweight="bold",
            color=TEXT_COLOR, zorder=4,
        )
        ax.yaxis.set_major_locator(LogLocator(base=10))
        ax.yaxis.set_major_formatter(_dollar_tick_formatter(world_mean))
        ax.grid(axis="y", which="major", color=GRID_COLOR, linewidth=0.8, zorder=1)
        ax.grid(axis="y", which="minor", color=GRID_COLOR, linewidth=0.35, alpha=0.45)

        tick_ranks = list(range(1, len(countries) + 1, 20))
        tick_labels = [
            countries.iloc[rank - 1]["iso"] for rank in tick_ranks
        ]
        ax.set_xticks(tick_ranks, tick_labels)
        ax.tick_params(axis="both", colors="#555a56", labelsize=9, length=0)
        ax.set_xlabel(
            "WEST  ←  COUNTRY RANK BY LONGITUDE  →  EAST",
            color="#555a56", fontsize=10, labelpad=16,
        )
        ax.set_ylabel(
            "GDP PER CAPITA, PPP (LOG SCALE)",
            color="#555a56", fontsize=10, labelpad=16,
        )
        for spine in ax.spines.values():
            spine.set_visible(False)

        for point in reference_points.itertuples():
            ax.annotate(
                "Sri Lanka",
                xy=(point.rank, point.ratio), xytext=(0, 9),
                textcoords="offset points", ha="center", va="bottom",
                fontsize=8, fontweight="bold", color=TEXT_COLOR, zorder=5,
            )

        winner_points = points[points["iso"].isin(winner_isos)].sort_values("rank")
        loser_points = points[points["iso"].isin(loser_isos)].sort_values("rank")
        for label_index, point in enumerate(winner_points.itertuples()):
            ax.annotate(
                point.NAME_LONG,
                xy=(point.rank, point.ratio),
                xytext=(0, 9 + 8 * (label_index % 3)),
                textcoords="offset points", ha="center", va="bottom",
                fontsize=6.5, color="#157347", zorder=5,
            )
        for label_index, point in enumerate(loser_points.itertuples()):
            ax.annotate(
                point.NAME_LONG,
                xy=(point.rank, point.ratio),
                xytext=(0, -10 - 8 * (label_index % 3)),
                textcoords="offset points", ha="center", va="top",
                fontsize=6.5, color="#b02a37", zorder=5,
            )

        fig.text(
            0.06, 0.94, year, ha="left", va="top",
            fontsize=48, fontweight="bold", color=TEXT_COLOR,
        )
        fig.text(
            0.06, 0.865, "The world, west to east",
            ha="left", va="top", fontsize=19, color=TEXT_COLOR,
        )
        fig.text(
            0.94, 0.94, f"WORLD MEAN  ${world_mean:,.0f}",
            ha="right", va="top", fontsize=13, fontweight="bold", color=TEXT_COLOR,
        )
        fig.text(
            0.94, 0.91, "Fixed vertical position at the chart midpoint",
            ha="right", va="top", fontsize=9, color="#666b67",
        )
        fig.text(
            0.5, 0.012, f"Source: World Bank  ·  {SOURCE_URL}",
            ha="center", va="bottom", fontsize=8, color="#777b77",
        )
        ax.legend(
            handles=_legend_handles(continents), loc="upper left", ncols=3,
            bbox_to_anchor=(0, 1.015), frameon=False, fontsize=9,
            columnspacing=1.4, handletextpad=0.4,
        )

        fig.subplots_adjust(top=0.79, bottom=0.11, left=0.09, right=0.97)
        output_path = os.path.join(IMAGES_DIR, f"{year}.png")
        fig.savefig(output_path, dpi=150, facecolor=BACKGROUND)
        plt.close(fig)
        print(f"Saved {output_path}")

    return years


def _encode_video(years):
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required to encode the animation")

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    frame_duration = 1.0 / FPS
    last_path = os.path.abspath(os.path.join(IMAGES_DIR, f"{years[-1]}.png"))
    frame_list_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as frame_list:
            frame_list_path = frame_list.name
            for year in years:
                path = os.path.abspath(os.path.join(IMAGES_DIR, f"{year}.png"))
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
                "-movflags", "+faststart", "-shortest", OUTPUT_PATH,
            ],
            check=True,
        )
    finally:
        if frame_list_path and os.path.exists(frame_list_path):
            os.unlink(frame_list_path)

    print(f"Saved {OUTPUT_PATH}")


def build(frames_only=False, start_year=None, end_year=None):
    years = _render_frames(
        _load_countries(), _load_data(), start_year=start_year, end_year=end_year
    )
    if not frames_only:
        _encode_video(years)


def main():
    parser = argparse.ArgumentParser(
        description="Build a west-to-east world GDP-per-capita circle chart animation."
    )
    parser.add_argument(
        "--frames-only", action="store_true", help="Render PNG frames without encoding an MP4."
    )
    parser.add_argument("--start-year", type=int, help="First year to render (inclusive).")
    parser.add_argument("--end-year", type=int, help="Last year to render (inclusive).")
    args = parser.parse_args()
    build(
        frames_only=args.frames_only,
        start_year=args.start_year,
        end_year=args.end_year,
    )


if __name__ == "__main__":
    main()