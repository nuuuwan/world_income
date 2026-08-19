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
