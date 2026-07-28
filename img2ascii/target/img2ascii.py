#!/usr/bin/env python3
"""
img2ascii — Convert JPEG/PNG images to ASCII art.

An original Python implementation that loads an image, resizes it
for terminal display, and maps each pixel's brightness to a character
from a configurable ASCII gradient ramp.
"""

import argparse
import sys
import math

from PIL import Image

# 70-character gradient from densest (darkest) to lightest (space)
DEFAULT_RAMP = '$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,"^`\'. '


def build_argument_parser():
    """Create and return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="A command-line tool for converting images to ASCII art"
    )
    parser.add_argument(
        "-i", "--input", dest="input_file", required=True,
        help="Path of the input image file (required)"
    )
    parser.add_argument(
        "-o", "--output", dest="output_file", default=None,
        help="Path of the output file"
    )
    parser.add_argument(
        "-w", "--width", type=int, default=0,
        help="Width of the output in characters"
    )
    parser.add_argument(
        "-c", "--chars", default=DEFAULT_RAMP,
        help="Characters to be used for the ASCII image"
    )
    parser.add_argument(
        "-g", "--grayscale", action="store_true",
        help="Output without ANSI color codes"
    )
    parser.add_argument(
        "-p", "--print", dest="print_to_console", action="store_true",
        help="Print the output to the console"
    )
    parser.add_argument(
        "-r", "--reverse", action="store_true",
        help="Reverse the string of characters"
    )
    parser.add_argument(
        "-d", "--debug", action="store_true",
        help="Print some useful information"
    )
    return parser


def open_and_resize(filepath, desired_width):
    """Load an image file and resize it for terminal-friendly dimensions.

    Terminal characters are approximately twice as tall as they are wide,
    so the height is halved to preserve the visual aspect ratio.

    Returns:
        A tuple of (PIL.Image in RGB mode, final_width, final_height).
    """
    img = Image.open(filepath).convert("RGB")
    orig_w, orig_h = img.size

    if desired_width > 0:
        if desired_width > orig_w:
            sys.stderr.write(
                f"Argument 'width' can not be greater than "
                f"the original image width ({orig_w}px) \n"
            )
            sys.exit(1)
        final_w = desired_width
        final_h = int(orig_h / (orig_w / float(desired_width)) / 2)
    else:
        final_w = orig_w
        final_h = orig_h // 2

    img = img.resize((final_w, final_h))
    return img, final_w, final_h


def compute_luminance(r, g, b):
    """Compute perceptual brightness from RGB using the BT.601 formula.

    Returns an integer in the range [0, 255].
    """
    return int(round(0.299 * r + 0.587 * g + 0.114 * b))


def map_to_character(luminance, ramp, ramp_length):
    """Map a luminance value (0–255) to a character in the ramp string."""
    index = int(luminance / (255.0 / (ramp_length - 1)))
    # Clamp to valid range to guard against floating-point edge cases
    if index >= ramp_length:
        index = ramp_length - 1
    return ramp[index]


def render_as_grayscale(pixels, width, height, ramp):
    """Build a plain-text ASCII art string without color codes.

    Each pixel is converted to a brightness value and then mapped
    to a character. Rows are separated by newlines.
    """
    ramp_len = len(ramp)
    parts = []

    for i in range(height * width):
        r, g, b = pixels[i]
        brightness = compute_luminance(r, g, b)
        parts.append(map_to_character(brightness, ramp, ramp_len))

        if (i + 1) % width == 0:
            parts.append("\n")

    return "".join(parts)


def render_with_color(pixels, width, height, ramp):
    """Build an ANSI-colored ASCII art string.

    Each character is prefixed with an ANSI 24-bit foreground color
    escape sequence matching the original pixel color. Consecutive
    pixels sharing the same color reuse the previous escape code
    to reduce output size.
    """
    ramp_len = len(ramp)
    parts = []
    prev_r, prev_g, prev_b = -1, -1, -1

    for i in range(height * width):
        r, g, b = pixels[i]
        brightness = compute_luminance(r, g, b)
        ch = map_to_character(brightness, ramp, ramp_len)

        # Only emit a new color code when the color actually changes
        if not (r == prev_r and g == prev_g and b == prev_b):
            parts.append(f"\033[38;2;{r};{g};{b}m")
        prev_r, prev_g, prev_b = r, g, b

        parts.append(ch)

        if (i + 1) % width == 0:
            parts.append("\n")

    # Reset terminal colors
    parts.append("\033[0m")
    return "".join(parts)


def save_to_file(text, filepath):
    """Write the ASCII art string to a text file."""
    try:
        with open(filepath, "w") as fh:
            fh.write(text)
    except OSError as err:
        sys.stderr.write(f"Could not create an output file: {err}\n")
        sys.exit(1)


def main():
    parser = build_argument_parser()
    args = parser.parse_args()

    # If no output file is specified, default to printing on the console
    if args.output_file is None:
        args.print_to_console = True

    # Prepare the character ramp
    ramp = args.chars
    if args.reverse:
        ramp = ramp[::-1]

    # Load and resize the image
    img, width, height = open_and_resize(args.input_file, args.width)
    pixels = list(img.getdata())

    # Render the ASCII art
    if args.grayscale:
        result = render_as_grayscale(pixels, width, height, ramp)
    else:
        result = render_with_color(pixels, width, height, ramp)

    # Print debug information
    if args.debug:
        target = args.output_file if args.output_file else "stdout"
        sys.stdout.write(
            f"Input: {args.input_file} \n"
            f"Output: {target} \n"
            f"Resolution: {width}x{height} \n"
            f'Characters ({len(ramp)}): "{ramp}" \n'
        )

    # Output the result
    if args.print_to_console:
        sys.stdout.write(result)
        sys.stdout.flush()

    if args.output_file:
        save_to_file(result, args.output_file)


if __name__ == "__main__":
    main()
