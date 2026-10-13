#!/usr/bin/env python3
"""Capture app-only public preview images using a fictitious project path.

Requires a desktop display, Tk, and ImageMagick's import command.
Never launches Codex or queries services.
"""
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from island import Island


def main():
    root = tk.Tk(className='Floatty')
    with patch('island.shutil.which', return_value='/usr/bin/codex'):
        app = Island(root, '/home/developer/projects/my-project', preview=True, motion=False)
    target = ROOT / 'assets/screenshots'
    target.mkdir(parents=True, exist_ok=True)
    try:
        root.update()
        app.tick_summary()
        root.update()
        subprocess.run(['import', '-window', str(root.winfo_id()), str(target/'compact.png')], check=True, timeout=5)
        app.collapse()
        root.update()
        app.terminal_hint.draw(now=0)
        root.update()
        subprocess.run(['import', '-window', str(root.winfo_id()), str(target/'expanded.png')], check=True, timeout=5)
    finally:
        app.closing = True
        app.resize_motion.cancel()
        def cancel_widgets(widget):
            if hasattr(widget, 'cancel_animation'):
                widget.cancel_animation()
            if hasattr(widget, 'tween'):
                widget.tween.cancel()
            for child in widget.winfo_children():
                cancel_widgets(child)
        cancel_widgets(root)
        for callback in root.tk.call('after', 'info'):
            root.after_cancel(callback)
        root.destroy()
    print('Saved app-only preview screenshots with illustrative paths.')

if __name__ == '__main__':
    main()
