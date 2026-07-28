#!/usr/bin/env python3
"""
Python Demo for qrterminal - Terminal QR Code Generator
"""

import sys
import os

# Add target directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import qrterminal

def main():
    text = "https://example.com"

    print("=== PYTHON TARGET FULL-BLOCK DEMO ===")
    qrterminal.generate(text, qrterminal.L, sys.stdout)

    print("\n=== PYTHON TARGET HALF-BLOCK DEMO ===")
    qrterminal.generate_half_block(text, qrterminal.L, sys.stdout)

if __name__ == '__main__':
    main()
