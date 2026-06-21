"""Traffic Generator package.

A lightweight Selenium-based traffic generator. The code is split into small
modules so that the pure logic (config parsing, scheduling math, URL matching,
registries) can be imported and unit-tested without a real browser.

Backward compatibility: the top-level ``trafficgen.py`` shim and the original
``urls.yaml`` / CLI invocation keep working unchanged.
"""

__all__ = ["__version__"]

__version__ = "0.2.0"
