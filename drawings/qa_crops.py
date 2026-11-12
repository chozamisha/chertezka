# -*- coding: utf-8 -*-
"""Кропы PNG 200 dpi — А3 420×297."""
from pathlib import Path
from PIL import Image

OUT = Path(__file__).resolve().parent
ART = Path("/opt/cursor/artifacts")
ART.mkdir(parents=True, exist_ok=True)
S = 200 / 25.4
W, H = 420, 297


def crop_mm(im, x0, y0, x1, y1, path):
    px0, px1 = int(x0 * S), int(x1 * S)
    py0, py1 = int((H - y1) * S), int((H - y0) * S)
    im.crop((px0, py0, px1, py1)).save(path)


def main():
    specs = {
        "00": "ПП-062215009-00_Korpus.png",
        "01": "ПП-062215009-01_Korpus_Otlivka.png",
        "02": "ПП-062215009-02_Korpus_MLU.png",
    }
    for tag, name in specs.items():
        im = Image.open(OUT / name)
        crop_mm(im, 25, 150, 280, 290, ART / f"qa{tag}_section.png")
        crop_mm(im, 25, 15, 280, 145, ART / f"qa{tag}_plan.png")
        crop_mm(im, 225, 5, 415, 65, ART / f"qa{tag}_stamp.png")
        crop_mm(im, 225, 60, 415, 160, ART / f"qa{tag}_tt.png")
        crop_mm(im, 360, 255, 415, 292, ART / f"qa{tag}_rough.png")
        im.resize((im.width // 3, im.height // 3), Image.Resampling.LANCZOS).save(ART / f"ov{tag}.png")
    im2 = Image.open(OUT / specs["02"])
    crop_mm(im2, 300, 120, 415, 290, ART / "qa02_gating.png")
    print("qa A3 crops ok")


if __name__ == "__main__":
    main()
