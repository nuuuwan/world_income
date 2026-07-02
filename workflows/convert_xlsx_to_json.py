import json
import re

import openpyxl

XLSX_PATH = "original_data/OGHIST_2026_07_01.xlsx"
JSON_PATH = "data/country_classes.json"
SHEET_NAME = "Country Analytical History"

# Row indices (0-based)
YEAR_ROW_IDX = 5   # "Data for calendar year :"
DATA_START_IDX = 6  # First country row

# Column indices
ISO_COL = 0
DATA_START_COL = 2  # First year column


def _is_valid_iso3(value):
    """Return True if value looks like a 3-letter ISO alpha-3 code."""
    return isinstance(value, str) and bool(re.fullmatch(r"[A-Za-z]{3}", value))


def _is_valid_class(value):
    """Return True if value is a meaningful income class (not missing)."""
    if value is None:
        return False
    s = str(value).strip()
    return s not in ("", ".", "..")


def convert():
    wb = openpyxl.load_workbook(XLSX_PATH, read_only=True, data_only=True)
    ws = wb[SHEET_NAME]
    rows = list(ws.iter_rows(values_only=True))

    # Build year list from the header row.
    # Columns with formula strings (e.g. 2016-2019) are inferred sequentially.
    year_row = rows[YEAR_ROW_IDX]
    years = []
    expected_year = None
    for col_idx in range(DATA_START_COL, len(year_row)):
        val = year_row[col_idx]
        if isinstance(val, int):
            years.append((col_idx, val))
            expected_year = val + 1
        elif isinstance(val, str) and val.startswith("=IF(") and expected_year is not None:
            # Formula cell: infer year from sequence
            years.append((col_idx, expected_year))
            expected_year += 1
        else:
            break

    # Build result: year -> iso3 -> class
    result = {}
    for row in rows[DATA_START_IDX:]:
        iso = row[ISO_COL]
        if not _is_valid_iso3(iso):
            continue
        iso = iso.upper()
        for col_idx, year in years:
            if col_idx >= len(row):
                continue
            class_val = row[col_idx]
            if not _is_valid_class(class_val):
                continue
            year_str = str(year)
            result.setdefault(year_str, {})[iso] = str(class_val).strip()

    # Sort by year, then by ISO code within each year
    sorted_result = {
        year: dict(sorted(countries.items()))
        for year, countries in sorted(result.items())
    }

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted_result, f, indent=2)

    print(f"Saved {JSON_PATH}")
    print(f"  Years: {min(sorted_result)}-{max(sorted_result)}")
    total_entries = sum(len(v) for v in sorted_result.values())
    print(f"  Total entries: {total_entries}")


if __name__ == "__main__":
    convert()
