import argparse
import json
import os
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request

import geopandas as gpd
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt


SHAPEFILE = "original_data/ne_110m/ne_110m_admin_0_countries.shp"
DATA_PATH = "data/gdp_per_capita_ppp.json"
IMAGES_DIR = "images/sri_lanka_gdp_comparison"
OUTPUT_PATH = "videos/sri_lanka_gdp_per_capita_ppp.mp4"

INDICATOR = "NY.GDP.PCAP.PP.CD"
REFERENCE_ISO = "LKA"
API_URL = f"https://api.worldbank.org/v2/country/all/indicator/{INDICATOR}"
SOURCE_URL = f"https://data.worldbank.org/indicator/{INDICATOR}"

COLORS = {
    "higher": "#2e8b57",
    "similar": "#f39c12",
    "lower": "#c0392b",
    "no_data": "#cccccc",
}

FPS = 1
OUTPUT_FPS = 10
HOLD_LAST = 4
OUTPUT_WIDTH = 1920


def comparison_group(value, reference_value):
    if value is None or reference_value is None or reference_value <= 0:
        return "no_data"
    ratio = value / reference_value
    if ratio > 1.25:
        return "higher"
    if ratio < 0.8:
        return "lower"
    return "similar"


def _fetch_data():
    query = urllib.parse.urlencode({"format": "json", "per_page": 20000})
    request = urllib.request.Request(
        f"{API_URL}?{query}",
        headers={"User-Agent": "world-income-map/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)

    if not isinstance(payload, list) or len(payload) < 2 or not payload[1]:
        raise RuntimeError("World Bank API returned no GDP data")

    data = {}
    for record in payload[1]:
        iso = record.get("countryiso3code")
        year = record.get("date")
        value = record.get("value")
        if iso and year and value is not None:
            data.setdefault(year, {})[iso] = float(value)

    return {year: dict(sorted(values.items())) for year, values in sorted(data.items())}


def _load_data(refresh=False):
    if not refresh and os.path.exists(DATA_PATH):
        with open(DATA_PATH, encoding="utf-8") as file:
            return json.load(file)

    data = _fetch_data()
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
    print(f"Saved {DATA_PATH}")
    return data


def _load_world():
    world = gpd.read_file(SHAPEFILE)
    world["ISO_A3"] = world.apply(
        lambda row: row["ADM0_A3"] if row["ISO_A3"] == "-99" else row["ISO_A3"],
        axis=1,
    )
    return world[["ISO_A3", "geometry"]].copy()


def _legend_handles():
    return [
        mpatches.Patch(color=COLORS["higher"], label="> 1.25x Sri Lanka"),
        mpatches.Patch(color=COLORS["similar"], label="0.8x to 1.25x Sri Lanka"),
        mpatches.Patch(color=COLORS["lower"], label="< 0.8x Sri Lanka"),
        mpatches.Patch(color=COLORS["no_data"], label="No data"),
    ]


def _render_frames(world, data):
    os.makedirs(IMAGES_DIR, exist_ok=True)
    years = sorted(year for year, values in data.items() if values.get(REFERENCE_ISO))
    if not years:
        raise RuntimeError("No years contain GDP data for Sri Lanka")

    for year in years:
        year_data = data[year]
        reference_value = year_data[REFERENCE_ISO]
        world["color"] = world["ISO_A3"].map(
            lambda iso: COLORS[comparison_group(year_data.get(iso), reference_value)]
        )

        fig, ax = plt.subplots(figsize=(16, 9))
        fig.patch.set_facecolor("#f0f4f8")
        world.plot(ax=ax, color=world["color"], edgecolor="#ffffff", linewidth=0.3)
        ax.set_axis_off()

        fig.text(
            0.5, 0.97, year,
            ha="center", va="top", fontsize=52, fontweight="bold", color="#1a1a2e",
        )
        fig.text(
            0.5, 0.89,
            "GDP per capita, PPP, relative to Sri Lanka",
            ha="center", va="top", fontsize=14, color="#444444",
        )
        fig.text(
            0.5, 0.845,
            f"Sri Lanka = ${reference_value:,.0f}",
            ha="center", va="top", fontsize=11, color="#666666",
        )
        fig.text(
            0.5, 0.01, f"Source: {SOURCE_URL}",
            ha="center", va="bottom", fontsize=8, color="#888888", style="italic",
        )
        ax.legend(
            handles=_legend_handles(), loc="lower left", fontsize=10,
            framealpha=0.9, edgecolor="#aaaaaa",
        )

        fig.subplots_adjust(top=0.82, bottom=0.04, left=0.01, right=0.99)
        output_path = os.path.join(IMAGES_DIR, f"{year}.png")
        plt.savefig(output_path, dpi=150)
        plt.close(fig)
        print(f"Saved {output_path}")

    return years


def _encode_video(years):
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required to encode the animation")

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    last_path = os.path.abspath(os.path.join(IMAGES_DIR, f"{years[-1]}.png"))
    frame_duration = 1.0 / FPS
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


def build(refresh_data=False, frames_only=False):
    data = _load_data(refresh=refresh_data)
    years = _render_frames(_load_world(), data)
    if not frames_only:
        _encode_video(years)


def main():
    parser = argparse.ArgumentParser(
        description="Build an animation comparing countries' PPP GDP per capita to Sri Lanka."
    )
    parser.add_argument(
        "--refresh-data", action="store_true", help="Download fresh data from the World Bank API."
    )
    parser.add_argument(
        "--frames-only", action="store_true", help="Render PNG frames without encoding an MP4."
    )
    args = parser.parse_args()
    build(refresh_data=args.refresh_data, frames_only=args.frames_only)


if __name__ == "__main__":
    main()