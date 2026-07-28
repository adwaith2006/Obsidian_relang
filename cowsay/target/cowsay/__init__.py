"""
cowsay package entry point.
"""

from typing import Any, Mapping

from .balloon import format_balloon
from .cows import get_cow, get_random_cow, list_cows, replace_variables
from .faces import get_face


def say(text: str = "", options: Mapping[str, Any] | None = None, **kwargs) -> str:
    """Generate talking cow string output."""
    opts = dict(options or {})
    opts.update(kwargs)

    if text:
        opts["text"] = text

    return _do_it(opts, say_aloud=True)


def think(text: str = "", options: Mapping[str, Any] | None = None, **kwargs) -> str:
    """Generate thinking cow string output."""
    opts = dict(options or {})
    opts.update(kwargs)

    if text:
        opts["text"] = text

    return _do_it(opts, say_aloud=False)


def _do_it(options: dict[str, Any], say_aloud: bool) -> str:
    if options.get("r"):
        cow_name = get_random_cow()
    else:
        cow_name = options.get("f") or "default"

    raw_cow = get_cow(cow_name)
    face = get_face(options)

    thoughts = "\\" if say_aloud else "o"
    variables = {
        "thoughts": thoughts,
        "eyes": face.eyes,
        "tongue": face.tongue,
    }

    # Text resolution
    text = options.get("text")
    if text is None:
        positional = options.get("_") or []
        text = " ".join(positional)

    # Wrap resolution (-n disables wrap)
    wrap: int | None
    if options.get("n"):
        wrap = None
    else:
        wrap_val = options.get("W", 40)
        try:
            wrap = int(wrap_val)
        except (ValueError, TypeError):
            wrap = 40

    balloon = format_balloon(text, wrap, say_aloud=say_aloud)
    compiled_cow = replace_variables(raw_cow, variables)

    return f"{balloon}\n{compiled_cow}"


__all__ = ["say", "think", "list_cows"]
