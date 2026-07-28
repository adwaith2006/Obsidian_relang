"""
Text balloon formatting for cowsay.
"""

import unicodedata
from typing import Sequence


def get_string_width(s: str) -> int:
    """
    Calculate visual display width of a string.
    Wide and fullwidth characters take 2 columns; combining/non-spacing characters take 0.
    """
    width = 0
    for ch in s:
        ea = unicodedata.east_asian_width(ch)
        if ea in ("F", "W"):
            width += 2
        elif unicodedata.category(ch) in ("Mn", "Me", "Cf"):
            continue
        else:
            width += 1
    return width


def split_text(text: str, wrap: int | None) -> list[str]:
    """
    Normalize line endings and split text into lines, optionally wrapping at column `wrap`.
    """
    # Normalize newline characters, remove BOM, expand tabs to 8 spaces
    text = (
        text.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\u2028", "\n")
        .replace("\u2029", "\n")
        .lstrip("\uFEFF")
        .replace("\t", "        ")
    )

    if not wrap or wrap <= 0:
        return text.split("\n")

    lines: list[str] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        next_newline = text.find("\n", start)
        limit = text_len if next_newline == -1 else next_newline
        wrap_at = min(start + wrap, limit)

        lines.append(text[start:wrap_at])
        start = wrap_at

        # Skip explicit newline character
        if start < text_len and text[start] == "\n":
            start += 1

    return lines if lines else [""]


def pad_line(line: str, length: int) -> str:
    """Pad line with spaces to reach visual display length."""
    current_width = get_string_width(line)
    return line + (" " * (length - current_width))


def format_balloon(text: str, wrap: int | None, say_aloud: bool) -> str:
    """Format speech or thought balloon around text."""
    lines = split_text(text, wrap)
    max_length = max((get_string_width(line) for line in lines), default=0)

    top_border = " " + ("_" * (max_length + 2))
    bottom_border = " " + ("-" * (max_length + 2))

    if say_aloud:
        delimiters = {
            "first": ("/", "\\"),
            "middle": ("|", "|"),
            "last": ("\\", "/"),
            "only": ("<", ">"),
        }
    else:
        delimiters = {
            "first": ("(", ")"),
            "middle": ("(", ")"),
            "last": ("(", ")"),
            "only": ("(", ")"),
        }

    balloon_lines: list[str] = []

    if len(lines) == 1:
        left, right = delimiters["only"]
        balloon_lines.append(top_border)
        balloon_lines.append(f"{left} {lines[0]} {right}")
        balloon_lines.append(bottom_border)
    else:
        balloon_lines.append(top_border)
        num_lines = len(lines)
        for i, line in enumerate(lines):
            if i == 0:
                left, right = delimiters["first"]
            elif i == num_lines - 1:
                left, right = delimiters["last"]
            else:
                left, right = delimiters["middle"]

            padded = pad_line(line, max_length)
            balloon_lines.append(f"{left} {padded} {right}")

        balloon_lines.append(bottom_border)

    return "\n".join(balloon_lines)


def say_balloon(text: str, wrap: int | None = 40) -> str:
    return format_balloon(text, wrap, say_aloud=True)


def think_balloon(text: str, wrap: int | None = 40) -> str:
    return format_balloon(text, wrap, say_aloud=False)
