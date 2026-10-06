"""
Genera le icone per il build PyInstaller a partire dall'icona della versione
web (pwa/icon-512.png), così desktop e web condividono lo stesso logo.
Richiede Pillow: pip install pillow

Uso:
    python desktop/make_icons.py

Output in desktop/icons/:
    taskplanner.png   (256×256, Linux)
    taskplanner.ico   (multi-size, Windows)
    taskplanner_1024.png  (sorgente ad alta risoluzione per iconutil macOS)
"""
from pathlib import Path

from PIL import Image

ROOT      = Path(__file__).resolve().parent.parent
SOURCE    = ROOT / "pwa" / "icon-512.png"
ICONS_DIR = Path(__file__).parent / "icons"
ICONS_DIR.mkdir(exist_ok=True)


def _make_frame(src: Image.Image, size: int) -> Image.Image:
    return src.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    src = Image.open(SOURCE).convert("RGBA")

    # PNG 256 (Linux / fallback)
    _make_frame(src, 256).save(ICONS_DIR / "taskplanner.png")
    print("Created desktop/icons/taskplanner.png")

    # ICO multi-size (Windows): Pillow ridimensiona dall'immagine più grande
    sizes = [16, 24, 32, 48, 64, 128, 256]
    _make_frame(src, 256).save(
        ICONS_DIR / "taskplanner.ico",
        format="ICO",
        sizes=[(s, s) for s in sizes],
    )
    print("Created desktop/icons/taskplanner.ico")

    # 1024 px sorgente per iconutil (macOS) — upscale dal 512
    _make_frame(src, 1024).save(ICONS_DIR / "taskplanner_1024.png")
    print("Created desktop/icons/taskplanner_1024.png")
