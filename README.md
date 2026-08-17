# world_income

## Sri Lanka GDP comparison animation

Build the animation from cached World Bank GDP-per-capita PPP data:

```bash
python workflows/build_sri_lanka_comparison.py
```

Pass `--refresh-data` to download the latest data, or `--frames-only` to skip
MP4 encoding. Frames are written to `images/sri_lanka_gdp_comparison/` and the
video to `videos/sri_lanka_gdp_per_capita_ppp.mp4`.
