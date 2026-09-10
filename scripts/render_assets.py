#!/usr/bin/env python3
"""Render AgentCrash launch assets to PNG with Pillow.

Rasterizes the social-preview.html design deterministically (no browser
dependency). Draws the 1280x640 GitHub social preview matching the CSS design
in assets/source/social-preview.html, and can emit a scenario-card variant.

Usage:
    python scripts/render_assets.py --out assets/generated/social-preview.png
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 640

# A small set of fonts with graceful fallbacks.
def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates = [
            "C:/Windows/Fonts/segoeuib.ttf",   # Segoe UI Bold
            "C:/Windows/Fonts/arialbd.ttf",
        ]
    else:
        candidates = [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]
    for c in candidates:
        if Path(c).exists():
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _rounded(draw: ImageDraw.ImageDraw, xy, radius, fill):
    """Draw a filled rounded rectangle (Pillow has rounded_rectangle)."""
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def render_social(out: Path) -> None:
    img = Image.new("RGB", (W, H), (11, 18, 32))   # #0b1220
    d = ImageDraw.Draw(img)

    # radial-ish accents via layered translucent circles
    accent = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ad = ImageDraw.Draw(accent)
    ad.ellipse((980, -180, 1400, 240), fill=(56, 189, 248, 26))
    ad.ellipse((-260, 460, 220, 940), fill=(56, 189, 248, 16))
    img.paste(accent, (0, 0), accent)
    d = ImageDraw.Draw(img)

    # ---- top bar ----
    # logo tile
    _rounded(d, (72, 56, 126, 110), 14, fill=(56, 189, 248, 255))
    d.text((90, 74), "AC", font=_font(26, True), fill=(8, 16, 25))
    d.text((146, 68), "Agent", font=_font(26, bold=True), fill=(233, 238, 247))
    d.text((270, 68), "Crash", font=_font(26, bold=True), fill=(56, 189, 248))
    d.text((146, 102), "open-source agent security test harness",
           font=_font(15), fill=(147, 166, 200))

    # ---- hero ----
    d.text((72, 240), "Crash-test your AI agent", font=_font(54, True), fill=(233, 238, 247))
    d.text((72, 308), "before you trust it.", font=_font(54, True), fill=(56, 189, 248))
    d.text((72, 392), "See the tool action an injected document causes, then prove your fix",
           font=_font(20), fill=(184, 197, 222))
    d.text((72, 428), "— in a synthetic workplace.", font=_font(20), fill=(184, 197, 222))

    # demo pill (mono-ish)
    _rounded(d, (72, 470, 820, 522), 12, fill=(16, 26, 45))
    d.text((92, 484), "agentcrash run invoice-confidential-note --variant attack",
           font=_font(18), fill=(125, 211, 252))
    d.text((560, 484), "\u25b6 canary \u2192 outbox", font=_font(16), fill=(245, 158, 11))

    # CTA
    _rounded(d, (72, 548, 372, 600), 12, fill=(56, 189, 248, 255))
    d.text((94, 564), "Try the offline demo", font=_font(18, True), fill=(8, 16, 25))
    d.text((256, 565), "no API key \u00b7 no model calls", font=_font(12), fill=(8, 16, 25))

    # ---- footer ----
    d.text((72, H - 52), "Apache-2.0 \u00b7 stdlib-first \u00b7 deterministic replay",
           font=_font(14), fill=(111, 130, 166))
    chips = ["prompt injection", "tool policy", "regression export"]
    x = 908
    for c in chips:
        w = d.textlength(c, font=_font(13))
        _rounded(d, (x, H - 62, x + w + 28, H - 38), 999, fill=(17, 27, 46))
        d.text((x + 13, H - 56), c, font=_font(13), fill=(159, 178, 211))
        x += w + 44

    img.save(out)
    print(f"wrote {out} ({img.size[0]}x{img.size[1]})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="assets/generated/social-preview.png")
    args = ap.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    render_social(out)


if __name__ == "__main__":
    main()