"""Optional end-to-end smoke test. Deselected by default (needs a real browser).

Run explicitly with::

    pytest -m selenium
"""
import pytest

pytest.importorskip("selenium")


@pytest.mark.selenium
def test_once_visits_example_com():
    from trafficgen.cli import main

    # --once visits each target a single time and exits. Uses the built-in
    # default target (example.com) since no --config is given.
    main(["--once", "--no-tui", "--headless"])
