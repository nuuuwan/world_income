import argparse
import json
import os

import geopandas as gpd
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable


DATA_PATH = "data/gdp_per_capita_ppp.json"
SHAPEFILE = "original_data/ne_110m/ne_110m_admin_0_countries.shp"
OUTPUT_PATH = "outputs/biggest_winners_and_losers.png"
SOURCE_URL = "https://data.worldbank.org/indicator/NY.GDP.PCAP.PP.CD"
DEFAULT_START_YEAR = "1990"
DEFAULT_END_YEAR = "2025"
REFERENCE_ISO = "LKA"
NO_DATA_COLOR = "#d9d9d9"


def load_world():
    world = gpd.read_file(SHAPEFILE)
    world["iso"] = world.apply(
        lambda row: row["ADM0_A3"] if row["ISO_A3"] == "-99" else row["ISO_A3"],
        axis=1,
    )
    return world


def calculate_multipliers(data, country_isos, start_year, end_year):
    start_data = data.get(start_year, {})
    end_data = data.get(end_year, {})
    multipliers = {}

    for iso in country_isos:
        start_value = start_data.get(iso)
        end_value = end_data.get(iso)
        if start_value and end_value and start_value > 0 and end_value > 0:
            multipliers[iso] = end_value / start_value

    if not multipliers:
        raise RuntimeError(
            f"No countries have GDP data in both {start_year} and {end_year}"
        )
    return multipliers


def add_side_label(ax, label, label_position, alignment):
    ax.text(
        *label_position,
        label,
        transform=ax.transAxes,
        ha=alignment,
        va="center",
        fontsize=8,
        fontweight="bold",
        color="#202421",
        zorder=5,
    )


def build_map(world, data, start_year, end_year):
    multipliers = calculate_multipliers(
        data, set(world["iso"]), start_year, end_year
    )
    if len(multipliers) < 2:
        raise RuntimeError("At least two comparable countries are required to rank")
    ranked_countries = sorted(multipliers, key=lambda iso: (multipliers[iso], iso))
    rank_percentiles = {
        iso: rank / (len(ranked_countries) - 1) * 100
        for rank, iso in enumerate(ranked_countries)
    }

    color_map = mcolors.LinearSegmentedColormap.from_list(
        "losers_to_winners",
        ["#ff0000", "#ffff00", "#00ff00", "#00ffff", "#0000ff"],
    )
    normalization = mcolors.Normalize(vmin=0, vmax=100)
    world["rank_percentile"] = world["iso"].map(rank_percentiles)

    fig, ax = plt.subplots(figsize=(16, 9))
    fig.patch.set_facecolor("#f4f1e8")
    ax.set_facecolor("#f4f1e8")
    world.plot(
        ax=ax,
        column="rank_percentile",
        cmap=color_map,
        norm=normalization,
        missing_kwds={"color": NO_DATA_COLOR},
        edgecolor="#ffffff",
        linewidth=0.35,
    )
    ax.set_axis_off()

    name_by_iso = dict(zip(world["iso"], world["NAME_LONG"]))
    label_y_positions = [0.78, 0.64, 0.50, 0.36, 0.22]
    smallest = ranked_countries[:5]
    biggest = list(reversed(ranked_countries[-5:]))

    ax.text(
        -0.03, 0.88, "Smallest improvements", transform=ax.transAxes,
        ha="right", va="center", fontsize=10, fontweight="bold", color="#202421",
    )
    ax.text(
        1.03, 0.88, "Biggest winners", transform=ax.transAxes,
        ha="left", va="center", fontsize=10, fontweight="bold", color="#202421",
    )
    for iso, label_y in zip(smallest, label_y_positions):
        add_side_label(
            ax,
            f"{name_by_iso[iso]}\n{multipliers[iso]:.2f}x | "
            f"Pct. {rank_percentiles[iso]:.1f}",
            (-0.03, label_y),
            "right",
        )
    for iso, label_y in zip(biggest, label_y_positions):
        add_side_label(
            ax,
            f"{name_by_iso[iso]}\n{multipliers[iso]:.2f}x | "
            f"Pct. {rank_percentiles[iso]:.1f}",
            (1.03, label_y),
            "left",
        )

    if REFERENCE_ISO in multipliers:
        fig.text(
            0.5,
            0.855,
            f"Sri Lanka: {multipliers[REFERENCE_ISO]:.2f}x | "
            f"Pct. {rank_percentiles[REFERENCE_ISO]:.1f}",
            ha="center",
            va="center",
            fontsize=10,
            fontweight="bold",
            color="#202421",
        )
    ax.legend(
        handles=[mpatches.Patch(color=NO_DATA_COLOR, label="No data")],
        loc="lower left",
        frameon=False,
        fontsize=9,
    )

    color_bar = fig.colorbar(
        ScalarMappable(norm=normalization, cmap=color_map),
        ax=ax,
        orientation="horizontal",
        fraction=0.045,
        pad=0.025,
        aspect=45,
    )
    ticks = [0, 25, 50, 75, 100]
    color_bar.set_ticks(ticks)
    color_bar.set_ticklabels(
        ["Smallest", "25th percentile", "Median", "75th percentile", "Largest"]
    )
    color_bar.set_label(
        "Rank by GDP per capita PPP improvement",
        fontsize=11,
    )
    color_bar.outline.set_visible(False)

    fig.suptitle(
        f"GDP per capita, PPP change ({start_year}-{end_year})",
        fontsize=25,
        fontweight="bold",
        color="#202421",
        y=0.95,
    )
    fig.text(
        0.5,
        0.895,
        f"{len(multipliers)} countries compared; color scaled by improvement rank",
        ha="center",
        fontsize=11,
        color="#555a56",
    )
    fig.text(
        0.5,
        0.015,
        f"Source: World Bank - {SOURCE_URL}",
        ha="center",
        fontsize=8,
        color="#777b77",
    )
    fig.subplots_adjust(top=0.86, bottom=0.1, left=0.17, right=0.83)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    plt.savefig(OUTPUT_PATH, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(
        description="Map country GDP-per-capita PPP improvements."
    )
    parser.add_argument("--start-year", default=DEFAULT_START_YEAR)
    parser.add_argument("--end-year", default=DEFAULT_END_YEAR)
    args = parser.parse_args()

    with open(DATA_PATH, encoding="utf-8") as file:
        data = json.load(file)

    build_map(load_world(), data, args.start_year, args.end_year)
    print(f"Saved {OUTPUT_PATH}")


if __name__ == "__main__":
    main()