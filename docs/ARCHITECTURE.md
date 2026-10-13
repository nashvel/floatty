# Project layout

```text
codex-island/
├── src/                 Python desktop application and native helpers
├── scripts/             Shortcut installation, site build, source packaging
├── tests/               Runtime, terminal and desktop acceptance checks
├── assets/
│   ├── branding/        Supplied SVG/PNG logo set
│   └── screenshots/     App-only public screenshots
├── site/                Static HTML showcase, installation guide, CSS/JS
├── docs/                Architecture and release/Pages instructions
├── .github/             CI, draft release, manual Pages, issue/PR templates
├── launch.sh            Stable launch entry point
├── VERSION              Source-release version
└── README.md            User setup, controls and troubleshooting
```

The launch script resolves its own location and starts `src/island.py`, regardless
of the caller's working directory. Without `--folder`, the caller's current
working directory remains the initial Codex project. The shortcut installer uses
absolute paths and defaults to the checkout root.

Application modules remain adjacent in `src/`, so the native helper and completion
bridge can be invoked directly using the same Python interpreter. Shared visual
assets live in the repository's `assets/`, resolved relative to the source tree.
Tests add `src/` to their import path and run from the repository root.

Tk owns the main UI thread. Background filesystem/service checks queue their
results. GTK3/VTE lives in a child helper and embeds over X11. Helper stdio carries
lifecycle metadata only; terminal bytes remain in VTE. The completion bridge
forwards only a stripped marker through a private Unix socket.

The website is separate from the desktop app. Its builder copies `site/` and
public visual assets into `dist/site/`, validates internal links and rejects
links that escape the published directory. Source packaging uses an allowlist;
neither process publishes by itself.
