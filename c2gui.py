#!/usr/bin/env python3
"""Run c2gui from a source checkout (installed packages provide the ``c2gui`` command)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from cyclone2.gui.app import main  # noqa: E402

main()
