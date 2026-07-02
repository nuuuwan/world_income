import json
import os

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

SHAPEFILE = "original_data/ne_110m/ne_110m_admin_0_countries.shp"
JSON_PATH = "data/country_classes.json"
IMAGES_DIR = "images"

CLASS_COLORS = {
    "H":  "#08306b",  # dark blue
    "UM": "#6baed6",  # light blue
    "LM": "#fc8d59",  # light red
    "L":  "#b30000",  # dark red
}
NO_DATA_COLOR = "#cccccc"  # grey

LEGEND_LABELS = {
    "H":  "High income",
    "UM": "Upper-middle income",
    "LM": "Lower-middle income",
    "L":  "Low income",
}

CLASS_SHORT = {"H": "H", "UM": "UM", "LM": "LM", "L": "L"}

SOURCE_URL = "https://datahelpdesk.worldbank.org/knowledgebase/articles/906519"


def build():
    os.makedirs(IMAGES_DIR, exist_ok=True)

    world = gpd.read_file(SHAPEFILE)
    # Use ISO_A3 when valid; fall back to ADM0_A3 for entries where ISO_A3 == '-99'
    # (e.g. France and Norway are stored as '-99' in this shapefile version)
    world["ISO_A3"] = world.apply(
        lambda r: r["ADM0_A3"] if r["ISO_A3"] == "-99" else r["ISO_A3"], axis=1
    )

    # Pre-compute centroid (lon, lat) and name for each country
    world_proj = world.copy()
    world_proj["cx"] = world_proj.geometry.centroid.x
    world_proj["cy"] = world_proj.geometry.centroid.y
    centroid_map = dict(zip(world_proj["ISO_A3"], zip(world_proj["cx"], world_proj["cy"])))
    name_map     = dict(zip(world_proj["ISO_A3"], world_proj["NAME"]))

    world = world[["ISO_A3", "geometry"]].copy()

    with open(JSON_PATH, encoding="utf-8") as f:
        country_classes = json.load(f)

    years = sorted(country_classes.keys())

    for year_idx, year in enumerate(years):
        year_data = country_classes[year]
        prev_data = country_classes[years[year_idx - 1]] if year_idx > 0 else {}

        # Map each country to a fill colour
        world["color"] = world["ISO_A3"].map(
            lambda iso: CLASS_COLORS.get(year_data.get(iso), NO_DATA_COLOR)
        )

        fig, ax = plt.subplots(1, 1, figsize=(16, 9))
        fig.patch.set_facecolor("#f0f4f8")

        world.plot(
            ax=ax,
            color=world["color"],
            edgecolor="#ffffff",
            linewidth=0.3,
        )

        ax.set_axis_off()

        # Year as large title
        fig.text(
            0.5, 0.97, year,
            ha="center", va="top",
            fontsize=52, fontweight="bold", color="#1a1a2e",
        )
        # Subtitle
        fig.text(
            0.5, 0.89,
            "World Bank Country Income Classifications  (GNI per capita, Atlas method)",
            ha="center", va="top",
            fontsize=12, color="#444444",
        )
        # Source footer
        fig.text(
            0.5, 0.01, f"Source: {SOURCE_URL}",
            ha="center", va="bottom",
            fontsize=8, color="#888888", style="italic",
        )

        # ── Bar-chart legend (inset axes, bottom-left) ──────────────────────
        classes   = ["L", "LM", "UM", "H"]
        labels    = ["Low", "Lower-\nmiddle", "Upper-\nmiddle", "High", "No\ndata"]
        bar_colors = [CLASS_COLORS[c] for c in classes] + [NO_DATA_COLOR]
        no_data_count = sum(
            1 for iso in world["ISO_A3"] if year_data.get(iso) not in CLASS_COLORS
        )
        counts    = [sum(1 for v in year_data.values() if v == c) for c in classes] + [no_data_count]

        # Place inset: [left, bottom, width, height] in figure-fraction coords
        bar_ax = fig.add_axes([0.05, 0.10, 0.13, 0.22])
        bar_ax.patch.set_facecolor("#f0f4f8")
        for spine in bar_ax.spines.values():
            spine.set_visible(False)

        bars = bar_ax.bar(labels, counts, color=bar_colors, width=0.6, zorder=2)

        # Count labels above each bar
        for bar, count in zip(bars, counts):
            bar_ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.5,
                str(count),
                ha="center", va="bottom",
                fontsize=7, color="#333333",
            )

        bar_ax.tick_params(axis="x", labelsize=7, colors="#333333")
        bar_ax.tick_params(axis="y", left=False, labelleft=False)
        bar_ax.set_ylim(0, max(counts) * 1.25)

        # ── Change annotations ───────────────────────────────────────────────
        if prev_data:
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            x_span = xlim[1] - xlim[0]
            y_span = ylim[1] - ylim[0]

            for iso, cur_cls in year_data.items():
                prev_cls = prev_data.get(iso)
                if not prev_cls or prev_cls == cur_cls:
                    continue
                if prev_cls not in CLASS_COLORS or cur_cls not in CLASS_COLORS:
                    continue
                if iso not in centroid_map:
                    continue

                cx, cy = centroid_map[iso]
                name   = name_map.get(iso, iso)
                label  = f"{name}: {prev_cls} \u2192 {cur_cls}"

                # Offset text away from centroid; flip for polar countries
                offset_y = -y_span * 0.18 if cy > ylim[0] + y_span * 0.65 else y_span * 0.18
                text_x = max(xlim[0] + x_span * 0.02,
                             min(xlim[1] - x_span * 0.02, cx))
                text_y = max(ylim[0] + y_span * 0.05,
                             min(ylim[1] - y_span * 0.05, cy + offset_y))

                ax.annotate(
                    label,
                    xy=(cx, cy),
                    xytext=(text_x, text_y),
                    fontsize=6,
                    ha="center",
                    va="center",
                    color="#111111",
                    bbox=dict(
                        boxstyle="round,pad=0.25",
                        facecolor="white",
                        edgecolor="#aaaaaa",
                        alpha=0.85,
                        linewidth=0.6,
                    ),
                    arrowprops=dict(
                        arrowstyle="->",
                        color="#444444",
                        lw=0.9,
                        connectionstyle="arc3,rad=0.15",
                    ),
                    zorder=10,
                )

        # Reserve space for title/subtitle at top and footer at bottom;
        # keeps the map in the middle so the 16:9 canvas is fully used.
        fig.subplots_adjust(top=0.84, bottom=0.04, left=0.01, right=0.99)

        out_path = os.path.join(IMAGES_DIR, f"{year}.png")
        plt.savefig(out_path, dpi=150)
        plt.close(fig)
        print(f"  Saved {out_path}")

    print(f"\nDone. {len(years)} images written to {IMAGES_DIR}/")


if __name__ == "__main__":
    build()
