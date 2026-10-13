#!/usr/bin/env python3
"""Codex Island: a small, always-on-top Linux task companion."""
from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
import queue
import shutil
import threading
import time
import tkinter as tk
from tkinter import messagebox

from runtime import Docker, IntegrationError, listeners, notify, stop_listener, protected_pids
from terminal_session import TerminalSession
from window_shape import round_window
from widgets import RoundedButton, RoundedPanel
from motion import Tween, blend
from ascii_logo import AsciiLogo
from folder_picker import FolderPicker

BG = "#101116"
PANEL = "#1c1e27"
TEXT = "#f2f3f8"
MUTED = "#9a9dad"
ACCENT = "#b8f28b"
COMPACT = (320, 58)
EXPANDED = (540, 620)


class Island:
    def __init__(self, root, folder, preview=False, motion=True):
        self.root, self.folder, self.preview = root, str(Path(folder).resolve()), preview
        self.events = queue.Queue()
        self.terminal = TerminalSession(self.events)
        self.folder_picker = None
        self.docker = Docker()
        self.busy = self.closing = False
        self.expanded = False
        self.motion = tk.BooleanVar(master=root, value=motion)
        self.resize_motion = Tween(root)
        self.corner_radius = 29
        self.started = None
        self.state = "Preview" if preview else "Ready"
        self.rows = []
        self.stopping = set()
        self.service_buttons = {}
        self.opacity = tk.DoubleVar(master=root, value=82)
        self.refreshing = False
        self.auto_refresh = False
        self.notifications = tk.BooleanVar(master=root, value=True)
        self.status = tk.StringVar(master=root, value="Choose a project folder, then click Launch Codex.")
        root.title("Codex Island")
        self.window_icon = tk.PhotoImage(master=root, file=str(Path(__file__).parent / "assets/branding/codex-island-256.png"))
        root.iconphoto(True, self.window_icon)
        root.configure(bg=BG)
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.geometry(f"{COMPACT[0]}x{COMPACT[1]}+{max(0, (root.winfo_screenwidth()-COMPACT[0])//2)}+36")
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.bind("<Escape>", lambda _: self.collapse())
        root.bind("<Control-q>", lambda _: self.close())
        self.shape_size = None
        root.bind("<Configure>", self.shape)
        root.bind("<Map>", self.mapped)
        self.build()
        self.body.pack_forget()
        self.close_button.pack_forget()
        self.toggle.configure(text="+")
        root.after(80, self.pump)
        root.after(1000, self.tick)
        root.after(80, self.pulse)

    def button(self, parent, text, command, accent=False):
        return RoundedButton(parent, text, command, BG, ACCENT if accent else PANEL,
                             BG if accent else TEXT, "#cafaab" if accent else "#303341", self.motion.get)

    def label(self, parent, text="", **kwargs):
        return tk.Label(parent, text=text, bg=BG, fg=TEXT, font=("DejaVu Sans", 10), **kwargs)

    def build(self):
        self.header = tk.Frame(self.root, bg=BG, padx=18, pady=8)
        self.header.pack(fill="x")
        self.logo_image = tk.PhotoImage(master=self.root, file=str(Path(__file__).parent / "assets/branding/codex-island-64.png")).subsample(2, 2)
        self.logo = tk.Label(self.header, image=self.logo_image, bg=BG)
        self.logo.pack(side="left", padx=(0, 8))
        self.dot = tk.Label(
            self.header, text="●", bg=BG, fg=ACCENT, font=("DejaVu Sans", 10))
        self.dot.pack(side="left", padx=(0, 6))
        heading = tk.Frame(self.header, bg=BG)
        heading.pack(side="left", fill="x", expand=True)
        self.title = self.label(heading, "CODEX ISLAND", anchor="w")
        self.title.configure(font=("DejaVu Sans", 10, "bold"))
        self.title.pack(fill="x")
        self.summary = self.label(heading, self.state, anchor="w")
        self.summary.configure(fg=MUTED, font=("DejaVu Sans", 9))
        self.summary.pack(fill="x")
        self.toggle = self.button(self.header, "−", self.collapse)
        self.toggle.pack(side="right")
        self.close_button = self.button(self.header, "×", self.close)
        self.close_button.pack(side="right", padx=4)
        for widget in (self.header, heading, self.title, self.summary, self.dot, self.logo):
            widget.bind("<Button-1>", self.drag_start)
            widget.bind("<B1-Motion>", self.drag)
            widget.bind("<ButtonRelease-1>", self.header_release)
            widget.configure(cursor="hand2")

        self.body = tk.Frame(self.root, bg=BG, padx=18)
        self.body.pack(fill="both", expand=True)
        tk.Frame(self.body, bg="#2b2e39", height=1).pack(fill="x", pady=(0, 14))
        workspace = tk.Frame(self.body, bg=BG)
        workspace.pack(fill="x")
        self.folder_button = self.button(workspace, "Folder ↗", self.choose_folder)
        self.folder_button.pack(side="right")
        self.folder_name = self.label(workspace, Path(self.folder).name, anchor="w")
        self.folder_name.configure(font=("DejaVu Sans", 13, "bold"))
        self.folder_name.pack(fill="x", pady=(2, 0))
        self.folder_path = self.label(self.body, self.folder, anchor="w", wraplength=500)
        self.folder_path.configure(fg=MUTED, font=("DejaVu Sans", 8))
        self.folder_path.pack(fill="x", pady=(3, 12))
        tabs = tk.Frame(self.body, bg=BG)
        tabs.pack(fill="x", pady=(0, 12))
        self.tab_buttons = {}
        for name in ("Chat", "Services"):
            button = self.button(tabs, name, lambda n=name: self.show_tab(n))
            button.pack(side="left", padx=(0, 6))
            self.tab_buttons[name] = button
        glass = tk.Frame(tabs, bg=BG)
        glass.pack(side="right")
        self.label(glass, "Opacity").pack(side="left", padx=(0, 6))
        tk.Scale(glass, from_=55, to=100, orient="horizontal", variable=self.opacity,
                 command=self.apply_opacity, length=110, showvalue=False, bg=BG, fg=MUTED,
                 troughcolor=PANEL, highlightthickness=0, bd=0, sliderrelief="flat",
                 width=8, sliderlength=18, activebackground=ACCENT).pack(side="left")
        self.pages = {}
        host = tk.Frame(self.body, bg=BG)
        host.pack(fill="both", expand=True)
        for name in self.tab_buttons:
            self.pages[name] = tk.Frame(host, bg=BG)

        chat = self.pages["Chat"]
        self.launch_description = self.label(chat, "", anchor="w", wraplength=490)
        self.launch_description.configure(fg=MUTED, font=("DejaVu Sans", 8))
        self.launch_description.pack(fill="x", pady=(0, 8))
        self.update_launch_description()
        terminal_panel = RoundedPanel(chat, BG, PANEL, height=320)
        terminal_panel.pack(fill="both", expand=True)
        self.terminal_container = tk.Frame(terminal_panel.content, bg=PANEL)
        self.terminal_container.pack(fill="both", expand=True)
        self.terminal_container.bind('<Configure>', self.terminal_resize)
        self.terminal_hint = AsciiLogo(self.terminal_container, self.motion.get, PANEL)
        self.terminal_hint.place(relx=0.5, rely=0.5, anchor="center")
        controls = tk.Frame(chat, bg=BG)
        controls.pack(fill="x", pady=12)
        self.launch_button = self.button(controls, "Launch Codex", self.launch_terminal, True)
        self.launch_button.pack(side="right")
        tk.Checkbutton(controls, text="Notify when done", variable=self.notifications,
                       bg=BG, fg=MUTED, selectcolor=PANEL, activebackground=BG,
                       highlightthickness=0, activeforeground=TEXT, font=("DejaVu Sans", 9)).pack(side="left")
        tk.Checkbutton(controls, text="Motion", variable=self.motion, command=self.motion_changed,
                       bg=BG, fg=MUTED, selectcolor=PANEL, activebackground=BG,
                       highlightthickness=0, activeforeground=TEXT, font=("DejaVu Sans", 9)).pack(side="left", padx=10)
        self.label(chat, "Ctrl+C interrupts · Ctrl+Shift+C / V copies / pastes", anchor="w").pack(fill="x")

        services = self.pages["Services"]
        self.label(services, "Running services", anchor="w").pack(fill="x")
        self.service_info = self.label(services, "Refresh to inspect your machine.", anchor="w", wraplength=500)
        self.service_info.configure(fg=MUTED, font=("DejaVu Sans", 9))
        self.service_info.pack(fill="x", pady=8)
        service_panel = RoundedPanel(services, BG, PANEL, height=250)
        service_panel.pack(fill="both", expand=True)
        self.service_canvas = tk.Canvas(service_panel.content, bg=PANEL, highlightthickness=0, bd=0)
        self.service_canvas.pack(side="left", fill="both", expand=True)
        self.service_cards = tk.Frame(self.service_canvas, bg=PANEL)
        self.cards_window = self.service_canvas.create_window(0, 0, window=self.service_cards, anchor="nw")
        self.service_cards.bind('<Configure>', lambda _: self.service_canvas.configure(scrollregion=self.service_canvas.bbox('all')))
        self.service_canvas.bind('<Configure>', lambda event: self.service_canvas.itemconfigure(self.cards_window, width=event.width))
        scroll = tk.Scrollbar(service_panel.content, orient="vertical", command=self.service_canvas.yview,
                              bg=PANEL, troughcolor=PANEL, activebackground=MUTED, width=10,
                              relief="flat", bd=0, highlightthickness=0)
        scroll.pack(side="right", fill="y")
        self.service_canvas.configure(yscrollcommand=scroll.set)
        buttons = tk.Frame(services, bg=BG)
        buttons.pack(fill="x", pady=12)
        self.button(buttons, "Refresh", self.refresh).pack(side="left")
        self.label(services, "Use Stop beside a service. Stopping a process closes all its ports.",
                   anchor="w", wraplength=490).pack(fill="x")
        self.footer = tk.Label(self.body, textvariable=self.status, bg=BG, fg=MUTED,
                               anchor="w", wraplength=500, font=("DejaVu Sans", 8))
        self.footer.pack(fill="x", pady=12)
        self.show_tab("Chat")

    def mapped(self, event):
        if event.widget == self.root and not self.closing:
            self.root.after_idle(self.apply_opacity)

    def apply_opacity(self, _=None):
        try:
            self.root.attributes("-alpha", self.opacity.get()/100)
        except tk.TclError:
            self.status.set("Window transparency is unavailable on this desktop.")

    def shape(self, event):
        if event.widget != self.root or self.closing:
            return
        size = (event.width, event.height, round(self.corner_radius))
        if size != self.shape_size and min(size) > 1:
            self.shape_size = size
            round_window(self.root.winfo_id(), size[0], size[1], radius=size[2])

    def drag_start(self, event):
        self.drag_origin = (event.x_root - self.root.winfo_x(), event.y_root - self.root.winfo_y())
        self.press_origin = (event.x_root, event.y_root)
        self.dragged = False

    def drag(self, event):
        if max(abs(event.x_root-self.press_origin[0]), abs(event.y_root-self.press_origin[1])) <= 5 and not self.dragged:
            return
        if not self.dragged and self.resize_motion.running:
            self.resize_motion.finish()
            self.root.update_idletasks()
            self.drag_origin = (self.press_origin[0]-self.root.winfo_x(), self.press_origin[1]-self.root.winfo_y())
        self.dragged = True
        x, y = self.drag_origin
        self.root.geometry(f"+{max(0, event.x_root-x)}+{max(0, event.y_root-y)}")

    def header_release(self, _):
        if not getattr(self, "dragged", False):
            self.collapse()

    def collapse(self):
        self.resize_motion.cancel()
        center = self.root.winfo_x() + self.root.winfo_width() // 2
        self.expanded = not self.expanded
        if self.expanded:
            self.body.pack(fill="both", expand=True)
            self.close_button.pack(side="right", padx=4)
            self.toggle.configure(text="−")
        else:
            self.close_button.pack_forget()
            self.toggle.configure(text="+")
        width, height = EXPANDED if self.expanded else COMPACT
        x = max(0, min(center-width//2, self.root.winfo_screenwidth()-width))
        initial = (self.root.winfo_width(), self.root.winfo_height(), self.root.winfo_x(), self.corner_radius)
        y = self.root.winfo_y()
        radius = 28 if self.expanded else 29
        def update(progress):
            w, h, left, corner = [start + (end-start)*progress for start, end in
                                 zip(initial, (width, height, x, radius))]
            self.corner_radius = corner
            self.root.geometry(f"{round(w)}x{round(h)}+{round(left)}+{y}")
        def complete():
            if not self.expanded:
                self.body.pack_forget()
        self.resize_motion.start(0.26 if self.motion.get() else 0, update, complete)
        self.tick_summary()

    def motion_changed(self):
        if not self.motion.get():
            self.resize_motion.finish()

    def pulse(self):
        if self.closing:
            return
        active = self.busy and self.state != "Needs you" and self.motion.get()
        if active:
            amount = (math.sin(time.monotonic()*math.tau/1.6)+1)/2
            self.dot.configure(fg=blend("#628348", ACCENT, amount))
        else:
            self.dot.configure(fg=ACCENT if self.state in {"Ready", "Completed", "Preview", "Terminal"} else "#f0bd75")
        self.root.after(80 if active else 500, self.pulse)

    def tick_summary(self):
        elapsed = f" · {int(time.monotonic()-self.started)}s" if self.started else ""
        folder = Path(self.folder).name
        if not self.expanded and len(folder) > 22:
            folder = folder[:21] + "…"
        self.summary.configure(text=f"{self.state}{elapsed} · {folder}")

    def show_tab(self, name):
        for page in self.pages.values():
            page.pack_forget()
        self.pages[name].pack(fill="both", expand=True)
        for key, button in self.tab_buttons.items():
            button.configure(fg=ACCENT if key == name else MUTED)
        self.auto_refresh = name == "Services"
        if self.auto_refresh:
            self.refresh()
        elif self.terminal.running:
            self.root.after_idle(self.terminal.focus)

    def terminal_resize(self, event):
        self.terminal.resize(event.width, event.height)

    def update_launch_description(self):
        executable = shutil.which("codex")
        self.launch_description.configure(text="Runs Codex CLI: " + (executable or "codex not found on PATH"))

    def launch_terminal(self):
        if self.folder_picker is not None:
            self.status.set("Choose or cancel the folder first. Nothing has been launched.")
            return
        if self.preview:
            self.status.set("Preview mode. Reopen without --preview to launch Codex.")
            return
        if self.terminal.running:
            self.terminal.focus()
            return
        self.root.update_idletasks()
        try:
            self.update_launch_description()
            self.terminal.start(self.terminal_container.winfo_id(), self.folder)
            self.launch_button.configure(text="Focus terminal")
            self.terminal_hint.place_forget()
            self.state = "Launching"
            self.status.set("Launching Codex CLI in " + self.folder)
        except IntegrationError as exc:
            self.status.set(str(exc))

    def work(self, fn, kind="result"):
        def worker():
            try:
                self.events.put((kind, fn()))
            except Exception as exc:
                self.events.put(("error", (kind, str(exc))))
        threading.Thread(target=worker, daemon=True).start()

    def choose_folder(self):
        if self.terminal.running:
            self.status.set("Exit Codex with Ctrl+C before changing folder.")
            return
        if self.folder_picker is not None:
            self.folder_picker.lift()
            self.folder_picker.entry.focus_set()
            return
        self.resize_motion.finish()
        self.launch_button.configure(state="disabled")
        self.status.set("Choosing a project folder. This does not launch Codex.")
        try:
            self.folder_picker = FolderPicker(self.root, self.folder, self.folder_selected, self.folder_picker_closed)
            self.root.withdraw()
        except tk.TclError as exc:
            self.folder_picker_closed()
            self.status.set("Cannot open the folder picker: " + str(exc))

    def folder_selected(self, folder):
        self.folder = folder
        self.folder_name.configure(text=Path(folder).name)
        self.folder_path.configure(text=folder)
        self.tick_summary()
        self.status.set("Folder selected. Click Launch Codex to run Codex CLI here.")

    def folder_picker_closed(self):
        self.folder_picker = None
        if not self.closing:
            self.root.deiconify()
            self.root.attributes("-topmost", True)
            self.launch_button.configure(state="normal")
            self.root.lift()

    def refresh(self):
        if self.refreshing or self.closing:
            return
        self.refreshing = True
        self.work(self.inspect_services, "services")

    def inspect_services(self):
        rows, errors = [], []
        for name, fn in (("Docker", self.docker.containers), ("Ports", listeners)):
            try:
                rows.extend((name, item) for item in fn())
            except (IntegrationError, ValueError, KeyError) as exc:
                errors.append(str(exc))
        return rows, errors

    def render_services(self):
        position = self.service_canvas.yview()[0]
        for widget in self.service_cards.winfo_children():
            widget.destroy()
        self.service_buttons.clear()
        pid = self.terminal.process.pid if self.terminal.process else None
        protected = protected_pids(pid)
        if not self.rows:
            tk.Label(self.service_cards, text="No running services found.", bg=PANEL, fg=MUTED,
                     pady=24, font=("DejaVu Sans", 10)).pack(fill="x")
        for kind, item in self.rows:
            key = (kind, item)
            card = RoundedPanel(self.service_cards, PANEL, "#252833", height=82, radius=12)
            card.pack(fill="x", pady=(0, 7))
            content = card.content
            actionable = kind == "Docker" or (item.process is not None and item.process.uid == os.getuid()
                                              and item.process.pid not in protected)
            stopping = key in self.stopping
            stop = self.button(content, "Stopping…" if stopping else "Stop" if actionable else "Read-only",
                               lambda k=kind, value=item: self.stop_service(k, value))
            # Match the button's transparent surrounding area to its card.
            stop.configure(bg="#252833", fg="#f3ab9f" if actionable else MUTED)
            stop.pack(side="right", padx=(8, 0))
            if stopping or not actionable:
                stop.configure(state="disabled")
            self.service_buttons[key] = stop
            name = item.name if kind == "Docker" else item.process.name if item.process else "Unknown process"
            detail = item.ports or "No published ports" if kind == "Docker" else f"{item.protocol.upper()} · {item.address}"
            owner = "Docker container" if kind == "Docker" else f"PID {item.process.pid}" if item.process else "Owner unavailable"
            tk.Label(content, text=name, bg="#252833", fg=TEXT, anchor="w",
                     font=("DejaVu Sans", 10, "bold")).pack(fill="x")
            tk.Label(content, text=owner, bg="#252833", fg=ACCENT, anchor="w",
                     font=("DejaVu Sans", 8)).pack(fill="x")
            tk.Label(content, text=detail, bg="#252833", fg=MUTED, anchor="w",
                     font=("DejaVu Sans", 8)).pack(fill="x")
            for widget in (card, content, *content.winfo_children()):
                widget.bind('<Button-4>', lambda _: self.service_canvas.yview_scroll(-2, 'units'))
                widget.bind('<Button-5>', lambda _: self.service_canvas.yview_scroll(2, 'units'))
        self.service_canvas.yview_moveto(position)

    def stop_service(self, kind, item):
        key = (kind, item)
        if key in self.stopping:
            return
        if kind == "Ports" and item.process is None:
            self.status.set("The owner is unavailable; this port is read-only.")
            return
        self.auto_refresh = False
        if not messagebox.askyesno("Stop local service?", f"Stop {item.label}?\n\nThis can interrupt other applications using this service.", parent=self.root):
            self.auto_refresh = self.pages["Services"].winfo_ismapped()
            return
        self.stopping.add(key)
        self.render_services()
        self.status.set("Stopping service…")
        pid = self.terminal.process.pid if self.terminal.process else None
        def stop():
            try:
                result = self.docker.stop(item) if kind == "Docker" else stop_listener(item, pid)
                self.events.put(("service_done", (key, result, False)))
            except Exception as exc:
                self.events.put(("service_done", (key, str(exc), True)))
        threading.Thread(target=stop, daemon=True).start()

    def terminal_event(self, event):
        if event.get('generation', self.terminal.generation) != self.terminal.generation:
            return
        kind = event.get('event')
        if kind == 'started':
            self.state = "Terminal"
            self.status.set("Codex is running. Type directly in the terminal; use Ctrl+C to interrupt.")
            self.terminal.resize(self.terminal_container.winfo_width(), self.terminal_container.winfo_height())
        elif kind == 'submitted':
            self.busy = True
            self.started = time.monotonic()
            self.state = "Working"
        elif kind in {'completed', 'interrupted', 'exited', 'error', 'disconnected'}:
            self.busy = False
            self.started = None
            if kind == 'completed':
                self.state = "Completed"
                self.status.set("Codex turn completed.")
                if self.notifications.get():
                    folder = self.folder
                    self.work(lambda: notify('completed', folder), 'notified')
            elif kind == 'interrupted':
                self.state = "Terminal"
                self.status.set("Ctrl+C sent to the terminal.")
            else:
                self.state = "Ready"
                self.launch_button.configure(text="Launch Codex")
                self.status.set(event.get('message', "Codex exited. Press Launch Codex to begin again."))

    def pump(self):
        if self.closing:
            return
        for _ in range(150):
            try:
                kind, data = self.events.get_nowait()
            except queue.Empty:
                break
            try:
                if kind == "terminal":
                    self.terminal_event(data)
                elif kind == "services":
                    self.refreshing = False
                    self.rows, errors = data
                    self.render_services()
                    self.service_info.configure(text=" · ".join(errors) if errors else f"{len(self.rows)} services · refreshes every 5s while visible")
                elif kind == "service_done":
                    key, message, failed = data
                    self.stopping.discard(key)
                    self.status.set(message)
                    self.service_info.configure(text=message)
                    self.render_services()
                    self.auto_refresh = self.pages["Services"].winfo_ismapped()
                    if not failed:
                        self.refresh()
                elif kind == "notified" and not data:
                    self.status.set("Task finished. Desktop notification unavailable; install libnotify tools.")
                elif kind == "error":
                    origin, detail = data
                    if origin == "services":
                        self.refreshing = False
                        self.service_info.configure(text=detail)
                    self.status.set(detail)
            except (IntegrationError, KeyError, TypeError) as exc:
                self.status.set(str(exc))
        self.root.after(80, self.pump)

    def tick(self):
        if self.closing:
            return
        self.tick_summary()
        if self.auto_refresh and self.expanded and int(time.monotonic()) % 5 == 0:
            self.refresh()
        self.root.after(1000, self.tick)

    def close(self):
        if self.closing:
            return
        if self.terminal.running:
            self.status.set("Exit Codex inside the terminal with Ctrl+C before closing.")
            if not self.expanded:
                self.collapse()
            self.show_tab("Chat")
            self.root.update_idletasks()
            self.terminal.focus()
            return
        self.closing = True
        if self.folder_picker is not None:
            self.folder_picker.close()
        self.resize_motion.cancel()
        self.root.withdraw()
        threading.Thread(target=self.cleanup, daemon=True).start()
        self.root.after(100, self.wait_closed)

    def cleanup(self):
        try:
            self.terminal.close()
        finally:
            self.events.put(("closed", None))

    def wait_closed(self):
        try:
            while True:
                kind, _ = self.events.get_nowait()
                if kind == "closed":
                    self.root.destroy()
                    return
        except queue.Empty:
            self.root.after(100, self.wait_closed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", default=str(Path.cwd()), help="Initial Codex working directory")
    parser.add_argument("--preview", action="store_true", help="Show the UI without starting Codex")
    parser.add_argument("--reduced-motion", action="store_true", help="Disable resizing, hover, and status animations")
    args = parser.parse_args()
    folder = Path(args.folder).expanduser().resolve()
    if not folder.is_dir():
        parser.error("--folder must be an existing directory")
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        parser.exit(1, f"Cannot open the desktop display: {exc}\nRun from your Linux desktop session.\n")
    Island(root, folder, args.preview, motion=not args.reduced_motion)
    root.mainloop()


if __name__ == "__main__":
    main()
