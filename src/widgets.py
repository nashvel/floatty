"""Rounded Tk surfaces with editable native controls inside."""
import tkinter as tk
import tkinter.font as font
from motion import Tween, blend


def rounded(canvas, width, height, radius, fill):
    radius = min(radius, width / 2, height / 2)
    return canvas.create_polygon(
        radius, 0, width-radius, 0, width, 0, width, radius,
        width, height-radius, width, height, width-radius, height,
        radius, height, 0, height, 0, height-radius, 0, radius, 0, 0,
        smooth=True, splinesteps=24, fill=fill, outline='', tags='surface',
    )


class RoundedPanel(tk.Canvas):
    def __init__(self, parent, background, fill, height, radius=18):
        super().__init__(parent, bg=background, height=height, highlightthickness=0, bd=0)
        self.fill, self.radius = fill, radius
        self.content = tk.Frame(self, bg=fill)
        self.content.place(x=10, y=10, relwidth=1, width=-20, relheight=1, height=-20)
        self.bind('<Configure>', self.draw)

    def draw(self, event):
        self.delete('surface')
        rounded(self, event.width, event.height, self.radius, self.fill)
        self.tag_lower('surface')


class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command, background, fill, foreground, hover, motion=lambda: True):
        self.typeface = font.Font(root=parent, family='DejaVu Sans', size=10)
        super().__init__(parent, bg=background, width=self.typeface.measure(text)+26,
                         height=36, highlightthickness=0, bd=0, cursor='hand2', takefocus=True)
        self.options = {'text': text, 'fg': foreground, 'state': 'normal'}
        self.fill, self.hover, self.command = fill, hover, command
        self.motion = motion
        self.surface_color = fill
        self.inset = 0
        self.tween = Tween(self)
        self.hovered = False
        self.pressed = False
        self.bind('<Configure>', lambda _: self.draw())
        self.bind('<Enter>', lambda _: self.set_hover(True))
        self.bind('<Leave>', lambda _: self.set_hover(False))
        self.bind('<Button-1>', self.press)
        self.bind('<ButtonRelease-1>', self.release)
        self.bind('<Return>', lambda _: self.activate())
        self.bind('<space>', lambda _: self.activate())
        self.bind('<FocusIn>', lambda _: self.draw())
        self.bind('<FocusOut>', lambda _: self.draw())
        self.bind('<Destroy>', lambda event: self.tween.cancel() if event.widget == self else None)

    def configure(self, cnf=None, **kwargs):
        if isinstance(cnf, dict):
            kwargs.update(cnf)
            cnf = None
        changed = False
        for key in tuple(kwargs):
            if key in self.options:
                self.options[key] = kwargs.pop(key)
                changed = True
        if kwargs or cnf is not None:
            super().configure(cnf, **kwargs)
        if changed:
            super().configure(width=self.typeface.measure(self.options['text'])+26)
            self.transition()

    config = configure

    def cget(self, key):
        return self.options[key] if key in self.options else super().cget(key)

    def draw(self):
        self.delete('all')
        disabled = self.options['state'] == 'disabled'
        width, height = self.winfo_width(), self.winfo_height()
        surface = rounded(self, width-2*self.inset, height-2*self.inset, 11,
                          self.fill if disabled else self.surface_color)
        self.move(surface, self.inset, self.inset)
        self.create_text(width/2, height/2+self.inset/2, text=self.options['text'], font=self.typeface,
                         fill='#777b88' if disabled else self.options['fg'])
        if self.focus_get() == self:
            self.create_line(13, height-5, width-13, height-5, fill=self.options['fg'])

    def set_hover(self, value):
        self.hovered = value
        if not value:
            self.pressed = False
        self.transition()

    def transition(self):
        disabled = self.options['state'] == 'disabled'
        target = self.hover if self.hovered and not disabled else self.fill
        target_inset = 2 if self.pressed and not disabled else 0
        color, inset = self.surface_color, self.inset
        def update(progress):
            self.surface_color = blend(color, target, progress)
            self.inset = inset + (target_inset-inset)*progress
            self.draw()
        self.tween.start(0.12 if self.motion() and not disabled else 0, update)

    def press(self, _):
        if self.options['state'] != 'disabled':
            self.pressed = True
            self.focus_set()
            self.transition()

    def release(self, event):
        pressed, self.pressed = self.pressed, False
        self.transition()
        if pressed and 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height():
            self.activate()

    def activate(self):
        if self.options['state'] != 'disabled':
            self.command()
