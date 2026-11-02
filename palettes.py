"""Shared preset names and sRGB colors for the app and premade packages."""

import re

ORDER = ("player", "none", "incomplete", "complete", "encount")
ORIGINAL = dict(zip(ORDER, ("#FDB905", "#378CFF", "#FFE66E", "#37DC78", "#FF4146")))
PRESETS = {
    "Vibrant - Brighter colors": dict(
        zip(ORDER, ("#FF6D00", "#2979FF", "#FFD600", "#00C853", "#FF1744"))
    ),
    "Blue & Gold - Protanomaly and deuteranomaly": dict(
        zip(ORDER, ("#FF981F", "#919191", "#438CFF", "#FFE066", "#FFFFFF"))
    ),
    "Blue & Gold - Stronger separation, protanopia and deuteranopia": dict(
        zip(ORDER, ("#D58B00", "#929292", "#4169C1", "#FFE680", "#FFFFFF"))
    ),
    "Coral & Cyan - Tritanomaly": dict(
        zip(ORDER, ("#FFD166", "#919191", "#F06464", "#42D6D0", "#FFFFFF"))
    ),
    "Coral & Cyan - Stronger separation, tritanopia": dict(
        zip(ORDER, ("#F2A6B3", "#929292", "#C74747", "#71E3DC", "#FFFFFF"))
    ),
    "Grayscale - Experimental, monochromacy": dict(
        zip(ORDER, ("#D0D0D0", "#858585", "#ADADAD", "#555555", "#FFFFFF"))
    ),
}


def effective_color(key, value):
    value = (value or "").strip().upper()
    if not value:
        return ORIGINAL[key]
    return value if re.fullmatch(r"#[0-9A-F]{6}", value) else None


def matching_preset(colors):
    effective = {key: effective_color(key, colors[key]) for key in ORDER}
    return next(
        (name for name, palette in PRESETS.items() if palette == effective), "Custom"
    )
