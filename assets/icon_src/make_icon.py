"""One-off script to generate the OffShore Mentor app icon (assets/icon.ico).

Builds a branded badge (teal background matching the app theme, a wave
accent for the "offshore" context, and the existing turbine silhouette in
white) and rasterizes it at the standard Windows icon sizes.

Not part of the runtime app; kept here for reproducibility if the icon
needs to be regenerated later.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent.parent
ASSETS = ROOT / "assets"

PRIMARY = (13, 148, 136, 255)      # #0D9488 - app theme primaryColor
PRIMARY_DARK = (7, 99, 90, 255)    # darker shade for gradient/depth
WAVE = (255, 255, 255, 60)         # subtle white wave accent
WHITE = (255, 255, 255, 255)

MASTER_SIZE = 512


def make_background(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Vertical gradient circle (teal -> darker teal) for a bit of depth.
    for y in range(size):
        t = y / (size - 1)
        r = int(PRIMARY[0] + (PRIMARY_DARK[0] - PRIMARY[0]) * t)
        g = int(PRIMARY[1] + (PRIMARY_DARK[1] - PRIMARY[1]) * t)
        b = int(PRIMARY[2] + (PRIMARY_DARK[2] - PRIMARY[2]) * t)
        draw.line([(0, y), (size, y)], fill=(r, g, b, 255))

    # Mask to a circle so it reads well as a badge at any size.
    mask = Image.new("L", (size, size), 0)
    mdraw = ImageDraw.Draw(mask)
    pad = int(size * 0.03)
    mdraw.ellipse([pad, pad, size - pad, size - pad], fill=255)

    circle = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    circle.paste(img, (0, 0), mask)

    # Simple wave accent near the bottom (offshore/sea motif).
    wave_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    wdraw = ImageDraw.Draw(wave_layer)
    base_y = int(size * 0.78)
    amplitude = size * 0.035
    points = []
    steps = 40
    for i in range(steps + 1):
        x = size * i / steps
        import math

        y = base_y + amplitude * math.sin((i / steps) * math.pi * 2)
        points.append((x, y))
    points += [(size, size), (0, size)]
    wdraw.polygon(points, fill=WAVE)
    wave_masked = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    wave_masked.paste(wave_layer, (0, 0), mask)
    circle = Image.alpha_composite(circle, wave_masked)

    return circle


def load_turbine_white(target_height: int) -> Image.Image:
    # Source is a flat "L" (grayscale) PNG with NO alpha channel: dark
    # strokes on a white background. Use the inverted luminance as the
    # alpha mask so the white background becomes transparent and the
    # turbine strokes become solid white.
    src = Image.open(ASSETS / "wind-turbine.png").convert("L")
    alpha = src.point(lambda p: 255 - p)
    # Thicken the thin strokes a bit so the silhouette still reads at
    # small icon sizes (16/24 px), then punch up contrast on the edges.
    alpha = alpha.filter(ImageFilter.MaxFilter(9))
    alpha = alpha.point(lambda p: 255 if p > 40 else 0)
    white = Image.new("RGBA", src.size, WHITE)
    white.putalpha(alpha)

    # Crop to the opaque bounding box so scaling isn't skewed by padding.
    bbox = alpha.getbbox()
    if bbox:
        white = white.crop(bbox)

    ratio = target_height / white.height
    target_width = max(1, int(white.width * ratio))
    return white.resize((target_width, target_height), Image.LANCZOS)


def build_master() -> Image.Image:
    badge = make_background(MASTER_SIZE)
    turbine = load_turbine_white(int(MASTER_SIZE * 0.62))
    tx = (MASTER_SIZE - turbine.width) // 2
    ty = int(MASTER_SIZE * 0.16)
    badge.alpha_composite(turbine, (tx, ty))
    return badge


def main() -> None:
    master = build_master()
    master.save(ASSETS / "icon_master.png")

    sizes = [16, 24, 32, 48, 64, 128, 256]
    frames = [master.resize((s, s), Image.LANCZOS) for s in sizes]
    frames[-1].save(
        ASSETS / "icon.ico",
        format="ICO",
        sizes=[(s, s) for s in sizes],
    )
    print("Wrote", ASSETS / "icon.ico")


if __name__ == "__main__":
    main()
