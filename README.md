# world_income

## Sri Lanka GDP comparison animation

Build the animation from cached World Bank GDP-per-capita PPP data:

```bash
python workflows/build_sri_lanka_comparison.py
```

Pass `--refresh-data` to download the latest data, or `--frames-only` to skip
MP4 encoding. Frames are written to `images/sri_lanka_gdp_comparison/` and the
video to `videos/sri_lanka_gdp_per_capita_ppp.mp4`.

## World GDP circle chart animation

Build the longitude-ranked GDP-per-capita animation:

```bash
python workflows/build_world_circle_chart.py
```

The vertical positions use a fixed log scale relative to each year's world
mean, keeping that mean at the chart midpoint. Use `--frames-only`,
`--start-year`, or `--end-year` to render a smaller range. Frames are written
to `images/world_circle_chart/` and the video to
`videos/world_gdp_circle_chart.mp4`.

## World GDP bar chart animation

Build the GDP-per-capita bar chart, sorted from lowest to highest each year:

```bash
python workflows/world_gpd_barchart.py
```

Bars are colored by region, with Sri Lanka identified by a vertical label. The
chart labels each region's highest and lowest country, excludes countries whose
2025 population was below one million, and uses a fixed logarithmic scale with
vertical country-name labels. Use
`--frames-only`, `--start-year`, or `--end-year` to render a smaller range.
Frames are written to `images/world_gdp_barchart/` and the video to
`videos/world_gdp_barchart.mp4`. Use `--refresh-population` to refresh the
cached World Bank 2025 population data.

## Asia GDP bar chart animation

Build the Asia-only GNI-per-capita Atlas-method bar chart:

```bash
python workflows/asia_gdp_barchart.py
```

It applies the same 2025 population threshold, colors countries by Asian
subregion, and draws the World Bank's 2025 income-category thresholds as dotted
lines. Frames are written to
`images/asia_gdp_barchart/` and the video to
`videos/asia_gdp_barchart.mp4`.
