"""Generate tray icons for macOS (.icns) and Windows (.ico)."""
from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parent.parent / "assets"


def _draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = size // 8
    draw.ellipse(
        (margin, margin, size - margin, size - margin),
        fill=(66, 133, 244, 255),
    )
    cx = size // 2
    draw.rectangle((cx - size // 16, size // 4, cx + size // 16, size // 2), fill="white")
    draw.ellipse(
        (cx - size // 8, size // 2, cx + size // 8, size * 5 // 8),
        fill="white",
    )
    return img


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    base = _draw_icon(512)
    png_path = ASSETS / "icon.png"
    base.save(png_path)
    ico_path = ASSETS / "icon.ico"
    base.save(
        ico_path,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    icns_path = ASSETS / "icon.icns"
    try:
        base.save(icns_path, format="ICNS")
    except Exception:
        base.resize((256, 256)).save(ASSETS / "icon.icns.png")
    print(f"Wrote {png_path}, {ico_path}")


if __name__ == "__main__":
    main()
