#!/usr/bin/env python3
"""
Main entry point for cowsay Python target.
"""

import sys
from pathlib import Path

# Ensure local packages in target/ are in sys.path
target_dir = Path(__file__).resolve().parent
if str(target_dir) not in sys.path:
    sys.path.insert(0, str(target_dir))

from cowsay.cli import main

if __name__ == "__main__":
    main()
