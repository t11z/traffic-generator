"""Command-line entry point. Wires config, settings, worker, and optional TUI."""
from __future__ import annotations

import argparse
import signal
import sys
import threading
from pathlib import Path

from .config import Config, Settings
from .logging_util import log, make_file_sink, set_file_sink, set_sink
from .state import RunState


def _parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simple Selenium traffic generator")
    parser.add_argument("--config", type=str, default=None, help="Path to YAML/JSON config file")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode (default)")
    parser.add_argument("--headed", action="store_true", help="Run with a visible browser window")
    parser.add_argument("--ignore-cert-errors", action="store_true",
                        help="Ignore SSL/TLS certificate errors (self-signed, untrusted)")
    parser.add_argument("--yt-wallclock", action="store_true",
                        help="Use wall-clock timing for YouTube progress/finish (recommended in headless)")
    parser.add_argument("--tui", dest="tui", action="store_true", default=None,
                        help="Force the live TUI dashboard")
    parser.add_argument("--no-tui", dest="tui", action="store_false",
                        help="Disable the TUI; plain stdout logging (cron/CI/systemd)")
    parser.add_argument("--max-retries", type=int, default=3,
                        help="Page-load retry attempts before giving up (default 3)")
    parser.add_argument("--page-load-timeout", type=int, default=60,
                        help="Selenium page load timeout in seconds (default 60)")
    parser.add_argument("--window-size", type=str, default="1280,800",
                        help="Browser window size WxH or W,H (default 1280,800)")
    parser.add_argument("--once", action="store_true",
                        help="Visit each target once, then exit (smoke/CI)")
    parser.add_argument("--log-file", type=str, default=None,
                        help="Also append log lines to this file")
    return parser.parse_args(argv)


def _resolve_tui(arg_tui) -> bool:
    """Auto-detect: TUI only on an interactive tty with rich available."""
    from .tui import rich_available

    if arg_tui is False:
        return False
    if arg_tui is True:
        if not rich_available():
            log("--tui requested but 'rich' is not installed. Install with: pip install rich")
            return False
        return True
    # auto
    return bool(sys.stdout.isatty()) and rich_available()


def main(argv=None) -> None:
    args = _parse_args(argv)

    headless = True
    if args.headed:
        headless = False
    elif args.headless:
        headless = True

    settings = Settings(
        headless=headless,
        ignore_cert_errors=args.ignore_cert_errors,
        yt_wallclock=bool(args.yt_wallclock or headless),
        page_load_timeout=args.page_load_timeout,
        window_size=args.window_size.replace("x", ","),
        max_retries=args.max_retries,
    )

    cfg = Config.load(Path(args.config) if args.config else None)
    cfg.apply_defaults_to_settings(settings)
    if not cfg.targets:
        print("No targets configured.")
        sys.exit(1)

    if args.log_file:
        set_file_sink(make_file_sink(args.log_file))

    use_tui = _resolve_tui(args.tui)
    state = RunState([t.url for t in cfg.targets])

    if use_tui:
        set_sink(state.add_log)

    log(f"Loaded {len(cfg.targets)} targets.")

    stop_event = threading.Event()

    def _handle_signal(signum, frame):
        log("Shutting down...")
        stop_event.set()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    # Import here so plain/test paths don't require selenium until needed.
    from .scheduler import Worker

    worker = Worker(cfg, settings, state, stop_event)

    if use_tui:
        from .tui import run_dashboard

        worker_thread = threading.Thread(
            target=worker.run, kwargs={"once": args.once}, name="trafficgen-worker", daemon=True
        )
        worker_thread.start()
        try:
            run_dashboard(state, stop_event, worker_thread)
        finally:
            stop_event.set()
            worker_thread.join(timeout=10)
        set_sink(None)
    else:
        # Plain mode: run worker on the main thread (signal handlers work here).
        worker.run(once=args.once)


if __name__ == "__main__":  # pragma: no cover
    main()
