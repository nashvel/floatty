#!/usr/bin/env python3
"""Install Floatty's per-user launcher and migrate its previous desktop IDs."""
from pathlib import Path
import argparse
import ast
import sys
import shutil
import subprocess

DESKTOP_ID = 'io.github.nashvel.Floatty.desktop'
LEGACY_IDS = ('codex-island.desktop', 'io.github.nashvel.CodexIsland.desktop')


def desktop_quote(value):
    value = str(value).replace('%', '%%')
    for character in ('\\', '"', '`', '$'):
        value = value.replace(character, '\\' + character)
    return '"' + value + '"'


def main():
    app = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, default=app, help='Initial Codex project folder')
    args = parser.parse_args()
    folder = args.folder.expanduser().resolve()
    if not folder.is_dir():
        parser.error('--folder must be an existing directory')
    icon_root = Path.home() / '.local/share/icons/hicolor'
    for category, filename in (('scalable', 'codex-island-tile.svg'),
                               ('1024x1024', 'codex-island-tile.png')):
        icon_dir = icon_root / category / 'apps'
        icon_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(app / 'assets/branding' / filename,
                     icon_dir / ('floatty' + Path(filename).suffix))
    target = Path.home() / '.local/share/applications' / DESKTOP_ID
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        '[Desktop Entry]\nType=Application\nName=Floatty\n'
        'Comment=Floating Codex terminal, playful pet, and local services\n'
        f'Exec={desktop_quote(sys.executable)} {desktop_quote(app / "src/island.py")} --folder {desktop_quote(folder)}\n'
        f'Icon={icon_root / "scalable/apps/floatty.svg"}\nTerminal=false\nStartupNotify=true\nStartupWMClass=Floatty\nCategories=Development;\n',
        encoding='utf-8',
    )
    for previous_id in LEGACY_IDS:
        legacy = target.with_name(previous_id)
        if legacy.exists() and '\nName=Codex Island\n' in legacy.read_text(encoding='utf-8'):
            legacy.unlink()
    if shutil.which('gsettings'):
        try:
            result = subprocess.run(['gsettings', 'get', 'org.gnome.shell', 'favorite-apps'],
                                    capture_output=True, text=True, timeout=5, check=True)
            favorites = ast.literal_eval(result.stdout.removeprefix('@as ').strip())
            if isinstance(favorites, list) and any(item in LEGACY_IDS for item in favorites):
                replacement = []
                for item in favorites:
                    item = DESKTOP_ID if item in LEGACY_IDS else item
                    if item != DESKTOP_ID or DESKTOP_ID not in replacement:
                        replacement.append(item)
                subprocess.run(['gsettings', 'set', 'org.gnome.shell', 'favorite-apps', repr(replacement)],
                               capture_output=True, timeout=5, check=False)
        except (OSError, subprocess.SubprocessError, ValueError, SyntaxError):
            pass
    for command in (['gtk-update-icon-cache', '-f', '-t', str(icon_root)],
                    ['update-desktop-database', str(target.parent)]):
        if shutil.which(command[0]):
            try:
                subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               timeout=5, check=False)
            except (OSError, subprocess.SubprocessError):
                pass
    print(f'Installed Floatty application-menu shortcut: {target}', flush=True)

if __name__ == '__main__':
    main()
