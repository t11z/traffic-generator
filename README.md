# Traffic Generator

A simple Python-based traffic generator using [Selenium](https://www.selenium.dev/). This tool can periodically visit a configurable list of URLs in a headless (or headed) Chromium browser. It supports randomized dwell times, optional scrolling, and even **special handling for YouTube videos** (plays until the video ends).

⚠️ **Disclaimer:** This project is intended for testing and educational purposes. Use it responsibly and only on websites you own or have permission to test. Do **not** use it to manipulate analytics, inflate ad impressions, or violate Terms of Service.

---

## Features

- Configurable list of URLs (via YAML or JSON file)
- Per-target intervals and dwell times
- Random jitter to avoid strict periodicity
- Auto-scroll simulation on normal websites
- User-Agent rotation (optional)
- **YouTube handler:** watches videos until completion instead of using a fixed dwell time
- Headless (server-friendly) or headed (visible browser) mode
- Graceful shutdown with `Ctrl+C`

---

## Requirements

- Python 3.8+
- Chromium or Chrome + matching `chromedriver`
- Dependencies:
  ```bash
  pip install selenium webdriver-manager pyyaml
  ```
  (On Debian/Ubuntu you may also install via `apt install chromium chromium-driver python3-yaml`)

---

## Usage

1. Clone the repository and create a configuration file (`urls.yaml`). Example:
   ```yaml
   defaults:
     dwell_seconds: 15
     interval_seconds: 300
     jitter_seconds: 10
     scroll: true

   user_agents:
     - Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36
     - Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/115.0

   targets:
     - url: https://example.com
       interval_seconds: 120
       dwell_seconds: 10

     - url: https://news.ycombinator.com
       interval_seconds: 600
       dwell_seconds: 20
       scroll: false

     - url: https://www.youtube.com/watch?v=dQw4w9WgXcQ
       interval_seconds: 1800
       # dwell_seconds is ignored for YouTube
   ```

2. Run the generator:
   ```bash
   python3 trafficgen.py --config urls.yaml --headless
   ```

   For visible browser windows (requires X11/GUI or `xvfb-run`):
   ```bash
   python3 trafficgen.py --config urls.yaml --headed
   ```

---

## YouTube Handler Explained

Normal targets use a fixed `dwell_seconds` (stay on the page, possibly auto-scroll, then move on). YouTube, however, needs special logic:

- Detects if the target URL is a YouTube video (`youtube.com/watch` or `youtu.be/...`).
- Accepts consent dialogs when present.
- Locates the `<video>` element on the page.
- Starts playback automatically (muted, if needed) to bypass autoplay restrictions.
- Reads the video `duration` and repeatedly checks `currentTime`.
- Keeps the tab open until the video ends (or a safety timeout is reached).
- Logs progress every ~15 seconds.

This way, YouTube videos are always played in full, rather than cut short by an arbitrary timer.

---

## Notes

- The script creates a temporary browser profile each run to avoid profile lock conflicts.
- For headless servers, always use `--headless` or wrap with `xvfb-run` if you need `--headed`.
- Supports Linux; should also work on macOS and Windows with minimal changes.

---

## License

MIT License – feel free to modify and adapt for your own testing setups.
