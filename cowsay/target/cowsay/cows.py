"""
Cow template loader, heredoc parser, and string replacer for cowsay.
"""

import random
import re
from pathlib import Path
from typing import Mapping

# Location of reference cows directory
DEFAULT_COWS_DIR = Path(__file__).resolve().parent.parent.parent / "source" / "cows"

_TEXT_CACHE: dict[str, str] = {}


def get_cows_dir() -> Path:
    """Return path to cows folder."""
    return DEFAULT_COWS_DIR


def extract_the_cow(cow_content: str) -> str:
    """Extract raw cow string from Perl heredoc format if present."""
    cow_content = (
        cow_content.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\u2028", "\n")
        .replace("\u2029", "\n")
        .lstrip("\uFEFF")
    )

    match = re.search(
        r'\$the_cow\s*=\s*<<"*EOC"*;*\n([\s\S]+)\nEOC\n', cow_content
    )
    if not match:
        return cow_content

    raw_cow = match.group(1)
    # Perform Perl heredoc unescaping: \\ -> \, \@ -> @, \$ -> $
    raw_cow = raw_cow.replace("\\\\", "\\").replace("\\@", "@").replace("\\$", "$")
    return raw_cow


def replace_variables(cow_text: str, variables: Mapping[str, str]) -> str:
    """Perform variable substitution ($thoughts, $eyes, $tongue, $eye)."""
    thoughts = variables.get("thoughts", "\\")
    eyes = variables.get("eyes", "oo")
    tongue = variables.get("tongue", "  ")

    eye_l = eyes[0] if len(eyes) > 0 else "o"
    eye_r = eyes[1] if len(eyes) > 1 else eye_l

    cow_text = extract_the_cow(cow_text)

    # Perform order-preserved literal replacements
    cow_text = cow_text.replace("$thoughts", thoughts)
    cow_text = cow_text.replace("$eyes", eyes)
    cow_text = cow_text.replace("$tongue", tongue)
    cow_text = cow_text.replace("${eyes}", eyes)
    cow_text = cow_text.replace("$eye", eye_l, 1)
    cow_text = cow_text.replace("$eye", eye_r, 1)
    cow_text = cow_text.replace("${tongue}", tongue)

    return cow_text


def get_cow(cow_name: str = "default") -> str:
    """Read cow template file by name or path."""
    if cow_name in _TEXT_CACHE:
        return _TEXT_CACHE[cow_name]

    if "/" in cow_name or "\\" in cow_name or cow_name.endswith(".cow"):
        file_path = Path(cow_name)
    else:
        file_path = get_cows_dir() / f"{cow_name}.cow"

    text = file_path.read_text(encoding="utf-8")
    _TEXT_CACHE[cow_name] = text
    return text


def list_cows() -> list[str]:
    """Return sorted list of available cow names in the cows directory."""
    cows_dir = get_cows_dir()
    if not cows_dir.exists():
        return []

    cow_files = sorted(cows_dir.glob("*.cow"))
    return [f.stem for f in cow_files]


def get_random_cow() -> str:
    """Pick a random cow name from available cows."""
    cows = list_cows()
    if not cows:
        return "default"
    return random.choice(cows)
