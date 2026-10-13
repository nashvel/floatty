# Contributing to Floatty

Thanks for helping improve this Linux desktop companion. Read [AGENTS.md](AGENTS.md)
for the terminal, privacy, threading, and process-control boundaries.

## Local checks

Run from the repository root. The application needs only Python's standard
library and installed native libraries; do not add a pip installation step.

```sh
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -v
python3 scripts/build_site.py
node --check site/main.js
node --check site/pets.mjs
node --test tests/test_site.mjs
sh -n launch.sh
```

For native desktop acceptance, install Tk, GTK3/VTE, iproute2, ImageMagick and
xdotool, then run from an X11/XWayland desktop:

```sh
FLOATTY_UI_TEST=1 python3 -m unittest discover -s tests -v
```

The tests type controlled input into an owned terminal and stop only an owned
disposable listener. They do not launch paid Codex inference or stop existing
containers. CI runs this suite on a virtual X11 desktop.

## Changes and reports

- Keep pull requests focused and describe the problem and resulting behavior.
- Test altered lifecycle, input, process protection, and error behavior.
- Include an app-only screenshot for UI changes, with private content redacted.
- Keep credentials, terminal transcripts, environment files, caches and generated
  releases out of Git.
- For bugs, include Linux distribution, desktop, display mode, Python version,
  Codex CLI version, reproduction steps and actual behavior.
- Use [SECURITY.md](SECURITY.md) for sensitive vulnerability reports.

Website checks use Node's built-in test runner; the desktop app does not require
Node or npm packages.

The showcase starts at root `index.html`, with buildless HTML/CSS/JS support
files in `site/`. Do not add a framework or npm
install for static changes. The site builder checks relative links so it works
under a GitHub project Pages subdirectory.

Contributions are covered by the project's [MIT license](LICENSE).
