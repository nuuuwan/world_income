import json
import os

import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib
import matplotlib.cm as cm
import numpy as np

SHAPEFILE = "original_data/ne_110m/ne_110m_admin_0_countries.shp"
CLUSTERS_PATH = "data/country_clusters.json"
OUTPUT_PATH = "images/clusters.png"
SOURCE_URL = "https://datahelpdesk.worldbank.org/knowledgebase/articles/906519"

NO_DATA_COLOR = "#cccccc"


def _cluster_delta(mean_vec):
    """Change in centroid value: avg of last 4 years minus avg of first 4 years."""
    arr = np.array(mean_vec)
    return float(np.mean(arr[-4:]) - np.mean(arr[:4]))


def build():
    os.makedirs("images", exist_ok=True)

    world = gpd.read_file(SHAPEFILE)
    world["ISO_A3"] = world.apply(
        lambda r: r["ADM0_A3"] if r["ISO_A3"] == "-99" else r["ISO_A3"], axis=1
    )
    world = world[["ISO_A3", "geometry"]].copy()

    with open(CLUSTERS_PATH, encoding="utf-8") as f:
        clusters = json.load(f)

    # Assign a distinct categorical colour to each cluster (tab10 palette)
    tab10 = matplotlib.colormaps["tab10"]
    cluster_colors = [tab10(i / 10) for i in range(len(clusters))]
    cluster_hex    = ["#{:02x}{:02x}{:02x}".format(
                          int(r*255), int(g*255), int(b*255))
                      for r, g, b, _ in cluster_colors]

    # Build iso -> color map
    iso_to_color = {}
    for idx, cluster in enumerate(clusters):
        for iso in cluster["country_list"]:
            iso_to_color[iso] = cluster_hex[idx]

    world["color"] = world["ISO_A3"].map(
        lambda iso: iso_to_color.get(iso, NO_DATA_COLOR)
    )

    fig, ax = plt.subplots(1, 1, figsize=(16, 9))
    fig.patch.set_facecolor("#f0f4f8")

    world.plot(ax=ax, color=world["color"], edgecolor="#ffffff", linewidth=0.3)
    ax.set_axis_off()

    # Title / subtitle / footer
    fig.text(0.5, 0.97, "Income Trajectory Clusters",
             ha="center", va="top", fontsize=36, fontweight="bold", color="#1a1a2e")
    fig.text(0.5, 0.89,
             "Countries grouped by similarity of income-class history (1987–2025)  ·  K-Means, k=10",
             ha="center", va="top", fontsize=11, color="#444444")
    fig.text(0.5, 0.01, f"Source: {SOURCE_URL}",
             ha="center", va="bottom", fontsize=8, color="#888888", style="italic")

    # Legend: one swatch per cluster
    patches = []
    for idx, cluster in enumerate(clusters):
        label = f"Cluster {idx + 1}  –  {cluster['description']}"
        patches.append(mpatches.Patch(color=cluster_hex[idx], label=label))
    patches.append(mpatches.Patch(color=NO_DATA_COLOR, label="No data"))
    ax.legend(handles=patches, loc="lower left", fontsize=10,
              framealpha=0.9, edgecolor="#aaaaaa", ncol=1)

    fig.subplots_adjust(top=0.87, bottom=0.04, left=0.01, right=0.99)
    plt.savefig(OUTPUT_PATH, dpi=150)
    plt.close(fig)
    print(f"Saved {OUTPUT_PATH}")


if __name__ == "__main__":
    build()
