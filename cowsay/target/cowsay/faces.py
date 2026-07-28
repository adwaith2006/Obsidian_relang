"""
Mode presets and face generation for cowsay.
"""

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class Face:
    eyes: str = "oo"
    tongue: str = "  "


MODES: dict[str, Face] = {
    "b": Face(eyes="==", tongue="  "),
    "d": Face(eyes="xx", tongue="U "),
    "g": Face(eyes="$$", tongue="  "),
    "p": Face(eyes="@@", tongue="  "),
    "s": Face(eyes="**", tongue="U "),
    "t": Face(eyes="--", tongue="  "),
    "w": Face(eyes="OO", tongue="  "),
    "y": Face(eyes="..", tongue="  "),
}

# Predefined mode evaluation order (matching JS reference)
MODE_ORDER: tuple[str, ...] = ("b", "d", "g", "p", "s", "t", "w", "y")


def get_face(options: Mapping[str, Any]) -> Face:
    """
    Select face based on options dictionary.
    First matching mode flag takes precedence; otherwise custom eyes (-e) and tongue (-T) are used.
    """
    for mode in MODE_ORDER:
        if options.get(mode) is True:
            return MODES[mode]

    eyes = options.get("e") or options.get("eyes") or "oo"
    tongue = options.get("T") or options.get("tongue") or "  "

    return Face(eyes=eyes, tongue=tongue)
