# Project layout

```text
codex-island/
├── src/                 Python desktop application and native helpers
├── scripts/             Shortcut installation, site build, source packaging
├── tests/               Runtime, terminal and desktop acceptance checks
├── assets/
│   ├── branding/        Supplied SVG/PNG logo set
│   └── screenshots/     App-only public screenshots
├── index.html           Static showcase entry point
├── site/                Installation guide and showcase CSS/JS
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

The website is separate from the desktop app. Its builder copies root `index.html`, the `site/` directory, and
public visual assets into `dist/site/`, validates internal links and rejects
links that escape the published directory. Source packaging uses an allowlist;
neither process publishes by itself.

The desktop shortcut uses the stable application ID
`io.github.nashvel.Floatty.desktop`. Installation retires both legacy
`codex-island.desktop` and `io.github.nashvel.CodexIsland.desktop` shortcuts
and migrates their GNOME favorite entries, when present, to avoid cached launch paths from earlier repository locations.

`header_pet.py` draws the compact interactive mascot directly in Tk, with no image
dependencies. It observes the island state and Motion preference. Petting and
idle naps never launch or interrupt Codex, change the current folder, or toggle
the island. Its timer stops on destruction and skips drawing while hidden.

The mascot reads the current desktop pointer through Tk and computes a bounded
eye offset relative to its current screen position. It continues tracking outside
the header and after the island is dragged. Reduced motion retains direct cursor
responses without automatic bobbing or blinking; sleeping and hidden pets skip
pointer reads. Cursor coordinates are never persisted.

Floatty is the application name. The existing checkout and GitHub repository
remain named `codex-island`; links and supplied logo filenames preserve that
history. The launch-screen playground embeds a scaled instance of the same `HeaderPet`
widget, with its animation driven by the parent canvas. It stops drawing when
the native terminal replaces it. Browser pets use inline SVG and `pets.mjs`;
controller tests use Node’s built-in test runner without a browser or framework.

`settings.py` persists only the opacity percentage in the per-user XDG config
directory (`~/.config/floatty/settings.json` by default). Writes replace the
file atomically with user-only permissions. Slider writes are debounced, with
a final flush before normal app close. Tests and public previews inject isolated
settings paths so they never change the user's preferences.
