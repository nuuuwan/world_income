import json
import math
import os
from collections import defaultdict

import geopandas as gpd
import matplotlib
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np

SHAPEFILE    = "original_data/ne_110m/ne_110m_admin_0_countries.shp"
CLASSES_PATH = "data/country_classes.json"
OUTPUT_PATH  = "images/change_1991_2025.png"
SOURCE_URL   = "https://datahelpdesk.worldbank.org/knowledgebase/articles/906519"

CLASS_INT   = {"L": 0, "LM": 1, "UM": 2, "H": 3}
CLASS_NAME  = {"L": "Low", "LM": "Lower\nMiddle", "UM": "Upper\nMiddle", "H": "High"}
CLASS_COLOR = {"L": "#b30000", "LM": "#fc8d59", "UM": "#6baed6", "H": "#08306b"}
NO_DATA_COLOR = "#e0e0e0"

YEAR_START = "1991"
YEAR_END   = "2025"

ROW_ORDER = ["H", "UM", "LM", "L"]   # 2025 class, top → bottom
COL_ORDER = ["L", "LM", "UM", "H"]   # start class, left → right

# Fallback names for countries absent from the 110m shapefile (small islands etc.)
_ISO_NAMES = {
    "ABW": "Aruba", "AFG": "Afghanistan", "AGO": "Angola", "AIA": "Anguilla",
    "ALB": "Albania", "AND": "Andorra", "ANT": "Neth. Antilles", "ARE": "UAE",
    "ARG": "Argentina", "ARM": "Armenia", "ASM": "Am. Samoa", "ATG": "Antigua & Barbuda",
    "AUS": "Australia", "AUT": "Austria", "AZE": "Azerbaijan", "BDI": "Burundi",
    "BEL": "Belgium", "BEN": "Benin", "BFA": "Burkina Faso", "BGD": "Bangladesh",
    "BGR": "Bulgaria", "BHR": "Bahrain", "BHS": "Bahamas", "BIH": "Bosnia & Herz.",
    "BLR": "Belarus", "BLZ": "Belize", "BMU": "Bermuda", "BOL": "Bolivia",
    "BRA": "Brazil", "BRB": "Barbados", "BRN": "Brunei", "BTN": "Bhutan",
    "BWA": "Botswana", "CAF": "C. African Rep.", "CAN": "Canada", "CHE": "Switzerland",
    "CHI": "Channel Islands", "CHL": "Chile", "CHN": "China", "CIV": "Côte d'Ivoire", "CMR": "Cameroon",
    "COD": "DR Congo", "COG": "Congo", "COL": "Colombia", "COM": "Comoros",
    "CPV": "Cabo Verde", "CRI": "Costa Rica", "CUB": "Cuba", "CUW": "Curaçao",
    "CYM": "Cayman Is.", "CYP": "Cyprus", "CZE": "Czech Rep.", "DEU": "Germany",
    "DJI": "Djibouti", "DMA": "Dominica", "DNK": "Denmark", "DOM": "Dominican Rep.",
    "DZA": "Algeria", "ECU": "Ecuador", "EGY": "Egypt", "ERI": "Eritrea",
    "ESP": "Spain", "EST": "Estonia", "ETH": "Ethiopia", "FIN": "Finland",
    "FJI": "Fiji", "FRA": "France", "FRO": "Faroe Is.", "FSM": "Micronesia",
    "GAB": "Gabon", "GBR": "United Kingdom", "GEO": "Georgia", "GHA": "Ghana",
    "GIB": "Gibraltar", "GIN": "Guinea", "GMB": "Gambia", "GNB": "Guinea-Bissau",
    "GNQ": "Eq. Guinea", "GRC": "Greece", "GRD": "Grenada", "GRL": "Greenland",
    "GTM": "Guatemala", "GUM": "Guam", "GUY": "Guyana", "HKG": "Hong Kong",
    "HND": "Honduras", "HRV": "Croatia", "HTI": "Haiti", "HUN": "Hungary",
    "IDN": "Indonesia", "IMN": "Isle of Man", "IND": "India", "IRL": "Ireland",
    "IRN": "Iran", "IRQ": "Iraq", "ISL": "Iceland", "ISR": "Israel",
    "ITA": "Italy", "JAM": "Jamaica", "JOR": "Jordan", "JPN": "Japan",
    "KAZ": "Kazakhstan", "KEN": "Kenya", "KGZ": "Kyrgyzstan", "KHM": "Cambodia",
    "KIR": "Kiribati", "KNA": "St. Kitts & Nevis", "KOR": "South Korea",
    "KWT": "Kuwait", "LAO": "Laos", "LBN": "Lebanon", "LBR": "Liberia",
    "LBY": "Libya", "LCA": "St. Lucia", "LIE": "Liechtenstein", "LKA": "Sri Lanka",
    "LSO": "Lesotho", "LTU": "Lithuania", "LUX": "Luxembourg", "LVA": "Latvia",
    "MAC": "Macao", "MAF": "St. Martin", "MAR": "Morocco", "MCO": "Monaco",
    "MDA": "Moldova", "MDG": "Madagascar", "MDV": "Maldives", "MEX": "Mexico",
    "MHL": "Marshall Is.", "MKD": "North Macedonia", "MLI": "Mali", "MLT": "Malta",
    "MMR": "Myanmar", "MNE": "Montenegro", "MNG": "Mongolia", "MNP": "N. Mariana Is.",
    "MOZ": "Mozambique", "MRT": "Mauritania", "MUS": "Mauritius", "MWI": "Malawi",
    "MYS": "Malaysia", "MYT": "Mayotte", "NAM": "Namibia", "NCL": "New Caledonia",
    "NER": "Niger", "NGA": "Nigeria", "NIC": "Nicaragua", "NLD": "Netherlands",
    "NOR": "Norway", "NPL": "Nepal", "NRU": "Nauru", "NZL": "New Zealand",
    "OMN": "Oman", "PAK": "Pakistan", "PAN": "Panama", "PER": "Peru",
    "PHL": "Philippines", "PLW": "Palau", "PNG": "Papua New Guinea", "POL": "Poland",
    "PRI": "Puerto Rico", "PRK": "North Korea", "PRT": "Portugal", "PRY": "Paraguay",
    "PSE": "West Bank & Gaza", "PYF": "French Polynesia", "QAT": "Qatar",
    "ROU": "Romania", "RUS": "Russia", "RWA": "Rwanda", "SAU": "Saudi Arabia",
    "SDN": "Sudan", "SEN": "Senegal", "SGP": "Singapore", "SLB": "Solomon Is.",
    "SLE": "Sierra Leone", "SLV": "El Salvador", "SMR": "San Marino",
    "SOM": "Somalia", "SRB": "Serbia", "SSD": "South Sudan", "STP": "São Tomé & Príncipe",
    "SUR": "Suriname", "SVK": "Slovakia", "SVN": "Slovenia", "SWE": "Sweden",
    "SWZ": "Eswatini", "SXM": "Sint Maarten", "SYC": "Seychelles", "SYR": "Syria",
    "TCA": "Turks & Caicos", "TCD": "Chad", "TGO": "Togo", "THA": "Thailand",
    "TJK": "Tajikistan", "TKM": "Turkmenistan", "TLS": "Timor-Leste", "TON": "Tonga",
    "TTO": "Trinidad & Tobago", "TUN": "Tunisia", "TUR": "Turkey", "TUV": "Tuvalu",
    "TZA": "Tanzania", "UGA": "Uganda", "UKR": "Ukraine", "URY": "Uruguay",
    "USA": "United States", "UZB": "Uzbekistan", "VCT": "St. Vincent & Gren.",
    "VEN": "Venezuela", "VGB": "British Virgin Is.", "VIR": "US Virgin Is.",
    "VNM": "Vietnam", "VUT": "Vanuatu", "WSM": "Samoa", "XKX": "Kosovo",
    "YEM": "Yemen", "ZAF": "South Africa", "ZMB": "Zambia", "ZWE": "Zimbabwe",
}

# Layout: 4×4 data cells + 0.5 cell padding each side = 5×5 units
# Figure = 22" square so each cell ≈ 22/5 = 4.4" square
FIG_IN    = 22
CELL_FRAC = 4 / 5          # 0.80 — data grid occupies 80 % of figure
PAD_FRAC  = 0.5 / 5        # 0.10 — padding on each side


def _transition_color(s, e):
    base  = np.array(mcolors.to_rgb(CLASS_COLOR[e]))
    white = np.array([1.0, 1.0, 1.0])
    alpha = 0.35 + 0.65 * (CLASS_INT[s] / 3.0)
    return mcolors.to_hex(alpha * base + (1 - alpha) * white)


def _text_color(hex_bg):
    r, g, b = mcolors.to_rgb(hex_bg)
    return "#ffffff" if 0.299 * r + 0.587 * g + 0.114 * b < 0.50 else "#1a1a2e"


def _font_size(n):
    """Larger font for cells with fewer countries; min 9, max 24."""
    if n == 0:
        return 16
    return max(9, min(24, round(200 / n)))


def build():
    os.makedirs("images", exist_ok=True)

    with open(CLASSES_PATH, encoding="utf-8") as f:
        classes = json.load(f)

    start_map = classes.get(YEAR_START, {})
    end_map   = classes.get(YEAR_END, {})

    world_shp = gpd.read_file(SHAPEFILE)
    world_shp["ISO_A3"] = world_shp.apply(
        lambda r: r["ADM0_A3"] if r["ISO_A3"] == "-99" else r["ISO_A3"], axis=1
    )
    iso_to_name = dict(zip(world_shp["ISO_A3"], world_shp["NAME"]))

    grid = defaultdict(list)
    for iso in set(start_map) | set(end_map):
        s = start_map.get(iso, "").rstrip("*")
        e = end_map.get(iso, "").rstrip("*")
        if s in CLASS_INT and e in CLASS_INT:
            name = iso_to_name.get(iso) or _ISO_NAMES.get(iso, iso)
            grid[(s, e)].append(name)
    for key in grid:
        grid[key].sort()

    # ── Figure ──────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(4, 4, figsize=(FIG_IN, FIG_IN))
    fig.patch.set_facecolor("#f0f4f8")

    for row_idx, end_cls in enumerate(ROW_ORDER):
        for col_idx, start_cls in enumerate(COL_ORDER):
            ax    = axes[row_idx][col_idx]
            ctrs  = grid.get((start_cls, end_cls), [])
            n     = len(ctrs)
            bg    = _transition_color(start_cls, end_cls) if ctrs else NO_DATA_COLOR
            tc    = _text_color(bg)
            fs    = _font_size(n)

            ax.set_facecolor(bg)
            ax.set_xticks([])
            ax.set_yticks([])
            # White border between cells
            for spine in ax.spines.values():
                spine.set_color("#ffffff")
                spine.set_linewidth(3)

            if ctrs:
                # n= badge (top-right corner) — fixed size across all cells
                ax.text(0.97, 0.97, f"n={n}",
                        transform=ax.transAxes, ha="right", va="top",
                        fontsize=12, fontweight="bold",
                        color=tc, alpha=0.70)

                # Multi-column country list — target ≤10 rows per column
                n_cols    = max(1, math.ceil(n / 10))
                chunk     = math.ceil(n / n_cols)
                col_lists = [ctrs[i * chunk:(i + 1) * chunk] for i in range(n_cols)]
                x_pos     = [(i + 0.5) / n_cols for i in range(n_cols)]

                for col_text, x in zip(col_lists, x_pos):
                    ax.text(x, 0.50, "\n".join(col_text),
                            transform=ax.transAxes, ha="center", va="center",
                            fontsize=fs, color=tc, linespacing=1.5,
                            clip_on=True)
            else:
                ax.text(0.5, 0.5, "—",
                        transform=ax.transAxes, ha="center", va="center",
                        fontsize=22, color="#aaaaaa")

            # Dotted diagonal stripe on the "no change" cells
            if start_cls == end_cls:
                ax.plot([0, 1], [0, 1],
                        transform=ax.transAxes,
                        linestyle=":", linewidth=3,
                        color="#ffffff", alpha=0.85,
                        solid_capstyle="round", zorder=5)

    # ── Column headers (start year) ─────────────────────────────────────────
    for col_idx, start_cls in enumerate(COL_ORDER):
        axes[0][col_idx].set_title(
            f"{YEAR_START}: {CLASS_NAME[start_cls]}",
            fontsize=15, fontweight="bold", pad=10, color="#1a1a2e"
        )

    # ── Row headers (2025 class) ────────────────────────────────────────────
    for row_idx, end_cls in enumerate(ROW_ORDER):
        axes[row_idx][0].set_ylabel(
            f"{YEAR_END}:\n{CLASS_NAME[end_cls]}",
            fontsize=15, fontweight="bold", rotation=0,
            labelpad=80, va="center", color="#1a1a2e"
        )

    # ── Title & footer ──────────────────────────────────────────────────────
    fig.suptitle(f"Income Class Change  ({YEAR_START} \u2192 {YEAR_END})",
                 fontsize=28, fontweight="bold", color="#1a1a2e", y=0.975)
    fig.text(0.5, 0.005, f"Source: {SOURCE_URL}",
             ha="center", va="bottom", fontsize=11,
             color="#888888", style="italic")

    # Padding = PAD_FRAC on each side; header labels sit in the padding band
    fig.subplots_adjust(
        left   = PAD_FRAC + 0.04,   # extra for row labels
        right  = 1 - PAD_FRAC + 0.04,
        bottom = PAD_FRAC - 0.06,
        top    = 1 - PAD_FRAC,
        hspace = 0.02,
        wspace = 0.02,
    )

    plt.savefig(OUTPUT_PATH, dpi=150)
    plt.close(fig)
    print(f"Saved {OUTPUT_PATH}")


if __name__ == "__main__":
    build()
