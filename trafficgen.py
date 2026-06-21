#!/usr/bin/env python3
"""Simple Selenium-based traffic generator (entry-point shim).

⚠️ Use responsibly: This tool is intended for testing your own sites or
explicitly permitted targets (e.g., staging). Do not use it to inflate ad
impressions, manipulate analytics, or violate a website's Terms of Service.

The implementation lives in the ``trafficgen`` package; this file only forwards
to it so the historic ``python3 trafficgen.py --config urls.yaml --headless``
invocation keeps working.
"""
from trafficgen.cli import main

if __name__ == "__main__":
    main()
