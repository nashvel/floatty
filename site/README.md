# Showcase source

- `index.html`: product overview and interactive, explicitly simulated island.
- `guide.html`: installation, controls and troubleshooting.
- `styles.css`: responsive layouts, brand palette and reduced-motion support.
- `main.js`: preview expand/collapse, keyboard-accessible tabs, simulated confirmation and copy buttons.

Run `python3 scripts/build_site.py` from the repository root. The builder assembles
shared branding/screenshots into `dist/site/` and checks local links. Preview that
output with Python's HTTP server. Do not publish the entire repository as Pages.
