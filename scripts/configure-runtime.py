#!/usr/bin/env python3
"""Create Avalon-only OpenCode state without rewriting global CLI configuration."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime_config import configure

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--model", required=True)
    a = p.parse_args()
    configure(a.state, a.model)
    print(f"Configured isolated runtime: {a.model}; tools denied")
