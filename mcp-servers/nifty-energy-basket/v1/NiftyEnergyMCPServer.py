#!/usr/bin/env python3
"""NiftyEnergyMCPServer.py

MCP Server exposing the 5-stock energy basket valuation strategy as a tool for local AI agents and LLM clients.
"""

import sys
from pathlib import Path

# Ensure package root is in path
root_dir = Path(__file__).resolve().parent
src_dir = root_dir / "src" / "server"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from server import main

if __name__ == "__main__":
    main()

