"""
CLI argument parser and entry point for cowsay.
"""

import argparse
import sys
from pathlib import Path
from typing import NoReturn

from . import list_cows, say, think


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cowsay",
        usage="cowsay [-e eye_string] [-f cowfile] [-h] [-l] [-n] [-T tongue_string] [-W column] [-bdgpstwy] text",
        description="cowsay is a configurable talking cow",
        add_help=False,
    )

    parser.add_argument("-e", default="oo", help="Select the appearance of the cow's eyes.")
    parser.add_argument("-T", default="  ", help="Select the appearance of the cow's tongue.")
    parser.add_argument("-W", type=int, default=40, help="Specifies column width.")
    parser.add_argument("-f", default="default", help="Specifies a cow picture file.")
    parser.add_argument("-b", action="store_true", help="Mode: Borg")
    parser.add_argument("-d", action="store_true", help="Mode: Dead")
    parser.add_argument("-g", action="store_true", help="Mode: Greedy")
    parser.add_argument("-p", action="store_true", help="Mode: Paranoia")
    parser.add_argument("-s", action="store_true", help="Mode: Stoned")
    parser.add_argument("-t", action="store_true", help="Mode: Tired")
    parser.add_argument("-w", action="store_true", help="Mode: Wired")
    parser.add_argument("-y", action="store_true", help="Mode: Youthful")
    parser.add_argument("-n", action="store_true", help="Do not word-wrap message.")
    parser.add_argument("-l", action="store_true", help="List all cowfiles.")
    parser.add_argument("-r", action="store_true", help="Select a random cow.")
    parser.add_argument("-h", "--help", action="store_true", help="Display help message.")
    parser.add_argument("--think", action="store_true", help="Think message instead of saying it.")

    parser.add_argument("text", nargs="*", help="Message for cow to say/think.")
    return parser


def strip_final_newline(text: str) -> str:
    """Strip single trailing newline character if present (matching strip-final-newline package)."""
    if text.endswith("\r\n"):
        return text[:-2]
    if text.endswith("\n"):
        return text[:-1]
    return text


def main() -> None:
    parser = build_parser()
    args, unknown = parser.parse_known_args()

    if args.help:
        parser.print_help()
        sys.exit(0)

    if args.l:
        cows_list = list_cows()
        print("  ".join(cows_list))
        return

    # Check if text provided via CLI arguments
    text_args = args.text
    if text_args:
        message = " ".join(text_args)
    else:
        # Try reading from stdin if available
        if not sys.stdin.isatty():
            stdin_data = sys.stdin.read()
            if stdin_data:
                message = strip_final_newline(stdin_data)
            else:
                parser.print_help()
                return
        else:
            parser.print_help()
            return

    # Convert args to options dict
    opts = vars(args)
    opts["_"] = text_args
    opts["text"] = message

    prog_name = Path(sys.argv[0]).name
    think_mode = prog_name.endswith("think") or args.think

    output = think(text=message, options=opts) if think_mode else say(text=message, options=opts)
    print(output)


if __name__ == "__main__":
    main()
