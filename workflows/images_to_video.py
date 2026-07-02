import os
import subprocess
import tempfile

IMAGES_DIR  = "images"
OUTPUT_DIR  = "videos"
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "world_income_history.mp4")

FPS          =  1      # frames per second (each year shown for 0.5 s)
HOLD_LAST    = 4      # extra seconds to hold the final frame
OUTPUT_WIDTH = 1920   # scale to this width; height auto-adjusted to keep ratio


def build():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Collect year images in chronological order
    images = sorted(
        f for f in os.listdir(IMAGES_DIR)
        if f.endswith(".png") and f[:-4].isdigit()
    )

    if not images:
        print(f"No year images found in {IMAGES_DIR}/")
        return

    print(f"Found {len(images)} frames: {images[0][:-4]} – {images[-1][:-4]}")

    # Build an ffmpeg concat input file:
    # Each entry has a 'file' line and a 'duration' line (seconds per frame).
    frame_dur   = 1.0 / FPS
    last_path   = os.path.abspath(os.path.join(IMAGES_DIR, images[-1]))

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as flist:
        for img in images:
            path = os.path.abspath(os.path.join(IMAGES_DIR, img))
            flist.write(f"file '{path}'\n")
            flist.write(f"duration {frame_dur:.6f}\n")
        # Repeat last frame with hold duration (concat demuxer needs it)
        flist.write(f"file '{last_path}'\n")
        flist.write(f"duration {float(HOLD_LAST):.6f}\n")
        flist.write(f"file '{last_path}'\n")   # sentinel required by ffmpeg
        flist_path = flist.name

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", flist_path,
        "-vf", f"scale={OUTPUT_WIDTH}:-2",   # -2 = round height to even number
        "-c:v", "libx264",
        "-crf", "18",                         # visually lossless
        "-preset", "slow",
        "-pix_fmt", "yuv420p",                # broad player compatibility
        "-movflags", "+faststart",            # web-friendly: metadata at front
        OUTPUT_PATH,
    ]

    print(f"Encoding → {OUTPUT_PATH}  ({FPS} fps, {OUTPUT_WIDTH}px wide) …")
    subprocess.run(cmd, check=True)
    os.unlink(flist_path)
    print(f"Done. Saved {OUTPUT_PATH}")


if __name__ == "__main__":
    build()
