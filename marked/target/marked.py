#!/usr/bin/env python3
"""
marked — Markdown to HTML converter in Python.
Entrypoint CLI script.
"""

import sys
import argparse
import json

# Ensure stdout uses strict Unix line endings (\n) without Windows \r\n translation
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(newline='\n')
from lexer import MarkdownLexer
from parser import MarkdownParser


def build_arg_parser():
    parser = argparse.ArgumentParser(description="marked - Markdown to HTML processor")
    parser.add_argument("-i", "--input", help="Path to input markdown file")
    parser.add_argument("-o", "--output", help="Path to output file")
    parser.add_argument("-s", "--string", help="String of Markdown to parse")
    parser.add_argument("-t", "--tokens", action="store_true", help="Output token AST as JSON")
    return parser


def main():
    parser = build_arg_parser()
    args, unknown = parser.parse_known_args()

    content = ""

    # Priority: --string -> --input / file arg -> stdin
    if args.string:
        content = args.string
    elif args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            content = f.read()
    elif unknown and not unknown[0].startswith("-"):
        with open(unknown[0], "r", encoding="utf-8") as f:
            content = f.read()
    else:
        # Read from stdin
        content = sys.stdin.read()

    lexer = MarkdownLexer()
    tokens = lexer.lex(content)

    if args.tokens:
        # Dump AST JSON
        def token_to_dict(t):
            d = {"type": t.type, "raw": t.raw}
            if t.text is not None:
                d["text"] = t.text
            if t.tokens:
                d["tokens"] = [token_to_dict(sub) for sub in t.tokens]
            return d

        ast = [token_to_dict(t) for t in tokens]
        output_str = json.dumps(ast, indent=2) + "\n"
    else:
        parser_engine = MarkdownParser()
        output_str = parser_engine.parse(tokens)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_str + "\n")
    else:
        sys.stdout.write(output_str + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
