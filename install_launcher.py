#!/usr/bin/env python3
"""Install a per-user application-menu shortcut. No sudo or autostart."""
from pathlib import Path
import argparse
import sys


def desktop_quote(value):
    # Desktop Entry Exec escaping is distinct from shell quoting.
    value = str(value).replace('%', '%%')
    for character in ('\\', '"', '`', '$'):
        value = value.replace(character, '\\' + character)
    return '"' + value + '"'


def main():
    app = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, default=app, help='Initial Codex project folder')
    args = parser.parse_args()
    folder = args.folder.expanduser().resolve()
    if not folder.is_dir():
        parser.error('--folder must be an existing directory')
    target = Path.home() / '.local/share/applications/codex-island.desktop'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        '[Desktop Entry]\nType=Application\nName=Codex Island\n'
        'Comment=Floating Codex chat, task notifications, and local services\n'
        f'Exec={desktop_quote(sys.executable)} {desktop_quote(app / "island.py")} --folder {desktop_quote(folder)}\n'
        f'Icon={app / "assets/branding/codex-island.svg"}\nTerminal=false\nCategories=Development;\n',
        encoding='utf-8',
    )
    print(f'Installed application-menu shortcut: {target}', flush=True)


if __name__ == '__main__':
    main()
