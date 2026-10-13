# Maintainer tools

Run these scripts from the repository root with Python 3.10+.

- `install_launcher.py`: installs the per-user app-menu shortcut. Accepts `--folder`.
- `build_site.py`: copies and validates the Pages-ready static site in `dist/site/`.
- `capture_screenshots.py`: captures app-only previews using fictitious paths; requires a desktop and ImageMagick.
- `package_release.py`: produces an allowlisted source archive and SHA256 file in `dist/releases/`.

Tools use Python's standard library. The site and package outputs are ignored.
See [release instructions](../docs/RELEASING.md).
