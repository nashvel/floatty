"""Non-modal folder browser. Filesystem work never blocks Tk's event loop."""
from pathlib import Path
import queue
import threading
import tkinter as tk


class FolderPicker(tk.Toplevel):
    def __init__(self, parent, initial, selected, finished):
        super().__init__(parent)
        self.selected, self.finished = selected, finished
        self.closed = False
        self.generation = 0
        self.events = queue.Queue()
        self.callback = None
        self.current = str(initial)
        self.title('Choose Codex project folder')
        self.configure(bg='#101116')
        self.attributes('-topmost', True)
        self.minsize(460, 360)
        self.geometry(f'520x430+{max(0, parent.winfo_x()+10)}+{max(0, parent.winfo_y()+50)}')
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.bind('<Escape>', lambda _: self.close())
        self.bind('<Return>', lambda _: self.load())
        self.path = tk.StringVar(master=self, value=str(initial))
        self.info = tk.StringVar(master=self, value='Choose a folder. This does not launch any program.')
        tk.Label(self, text='Codex project folder', bg='#101116', fg='#f2f3f8',
                 font=('DejaVu Sans', 12, 'bold')).pack(anchor='w', padx=18, pady=(16, 8))
        self.entry = tk.Entry(self, textvariable=self.path, bg='#1c1e27', fg='#f2f3f8',
                              insertbackground='#b8f28b', relief='flat', font=('DejaVu Sans', 10))
        self.entry.pack(fill='x', padx=18, ipady=8)
        navigation = tk.Frame(self, bg='#101116')
        navigation.pack(fill='x', padx=18, pady=10)
        self.button(navigation, 'Home', lambda: self.go(str(Path.home()))).pack(side='left')
        self.button(navigation, 'Parent', lambda: self.go(str(Path(self.current).parent))).pack(side='left', padx=6)
        self.button(navigation, 'Open path', self.load).pack(side='right')
        self.directories = tk.Listbox(self, height=4, bg='#1c1e27', fg='#f2f3f8', selectbackground='#3a4534',
                                     relief='flat', bd=0, highlightthickness=0, font=('DejaVu Sans', 10))
        self.directories.pack(fill='both', expand=True, padx=18)
        self.directories.bind('<Double-Button-1>', self.enter_directory)
        self.directories.bind('<Return>', self.enter_directory)
        tk.Label(self, textvariable=self.info, bg='#101116', fg='#9a9dad', wraplength=480,
                 anchor='w', justify='left', font=('DejaVu Sans', 9)).pack(fill='x', padx=18, pady=10)
        actions = tk.Frame(self, bg='#101116')
        actions.pack(fill='x', padx=18, pady=(0, 16))
        self.button(actions, 'Cancel', self.close).pack(side='left')
        self.use_button = self.button(actions, 'Use this folder', lambda: self.load(select=True), True)
        self.use_button.pack(side='right')
        self.entry.focus_set()
        self.lift()
        self.load()
        self.callback = self.after(50, self.pump)

    def button(self, parent, text, command, accent=False):
        return tk.Button(parent, text=text, command=command, bg='#b8f28b' if accent else '#1c1e27',
                         fg='#101116' if accent else '#f2f3f8', relief='flat', bd=0,
                         padx=12, pady=7, highlightthickness=0, cursor='hand2')

    def go(self, path):
        self.path.set(path)
        self.load()

    def enter_directory(self, _=None):
        selection = self.directories.curselection()
        if selection:
            self.go(str(Path(self.current)/self.directories.get(selection[0])))
        return 'break'

    def load(self, select=False):
        if self.closed:
            return
        self.generation += 1
        generation, raw = self.generation, self.path.get().strip()
        events = self.events
        self.use_button.configure(state='disabled')
        self.info.set('Checking folder…' if select else 'Loading folders… You can cancel at any time.')

        def worker():
            try:
                if not raw:
                    raise ValueError('Enter a folder path.')
                path = Path(raw).expanduser().resolve(strict=True)
                if not path.is_dir():
                    raise ValueError('Select a directory, not a file.')
                children = []
                if not select:
                    for child in path.iterdir():
                        if not child.name.startswith('.') and child.is_dir():
                            children.append(child.name)
                        if len(children) >= 1000:
                            break
                    children.sort(key=str.casefold)
                events.put((generation, str(path), children, select, None))
            except (OSError, ValueError, RuntimeError) as exc:
                message = str(exc) if isinstance(exc, ValueError) else 'Cannot access this folder. Check its path and permissions.'
                events.put((generation, None, [], select, message))
        threading.Thread(target=worker, daemon=True).start()

    def pump(self):
        self.callback = None
        if self.closed:
            return
        while True:
            try:
                generation, path, children, select, error = self.events.get_nowait()
            except queue.Empty:
                break
            if generation != self.generation:
                continue
            self.use_button.configure(state='normal')
            if error:
                self.info.set(error)
            elif select:
                self.selected(path)
                self.close()
                return
            else:
                self.current = path
                self.path.set(path)
                self.directories.delete(0, 'end')
                for name in children:
                    self.directories.insert('end', name)
                self.info.set('Double-click a folder to open it, or use this folder. Nothing launches here.')
        self.callback = self.after(50, self.pump)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.generation += 1
        if self.callback is not None:
            self.after_cancel(self.callback)
            self.callback = None
        self.destroy()
        self.path = self.info = None
        self.finished()
