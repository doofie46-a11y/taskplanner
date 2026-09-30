"""
Genera le icone placeholder per il build PyInstaller.
Richiede Pillow: pip install pillow

Uso:
    python desktop/make_icons.py

Output in desktop/icons/:
    taskplanner.png   (256×256, Linux)
    taskplanner.ico   (multi-size, Windows)
    taskplanner_1024.png  (sorgente ad alta risoluzione per iconutil macOS)
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ICONS_DIR = Path(__file__).parent / "icons"
ICONS_DIR.mkdir(exist_ok=True)

BLUE  = (0, 123, 255, 255)
WHITE = (255, 255, 255, 255)


def _make_frame(size: int) -> Image.Image:
    img  = Image.new("RGBA", (size, size), BLUE)
    draw = ImageDraw.Draw(img)
    font_size = max(size // 3, 8)
    font = None
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arialbd.ttf",
    ):
        try:
            font = ImageFont.truetype(candidate, font_size)
            break
        except Exception:
            pass
    if font is None:
        font = ImageFont.load_default()

    text = "TP"
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - w) // 2, (size - h) // 2), text, fill=WHITE, font=font)
    return img


if __name__ == "__main__":
    # PNG 256 (Linux / fallback)
    img256 = _make_frame(256)
    img256.save(ICONS_DIR / "taskplanner.png")
    print("Created desktop/icons/taskplanner.png")

    # ICO multi-size (Windows)
    sizes = [16, 32, 48, 64, 128, 256]
    frames = [_make_frame(s) for s in sizes]
    frames[0].save(
        ICONS_DIR / "taskplanner.ico",
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=frames[1:],
    )
    print("Created desktop/icons/taskplanner.ico")

    # 1024 px sorgente per iconutil (macOS)
    _make_frame(1024).save(ICONS_DIR / "taskplanner_1024.png")
    print("Created desktop/icons/taskplanner_1024.png")
    print("macOS: run 'make -f desktop/Makefile icons' or see GitHub Actions workflow")
