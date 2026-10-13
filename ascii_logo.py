"""Animated ASCII rendering of the project's capsule / terminal / toggle logo."""
import math
import time
import tkinter as tk
import tkinter.font as font

from motion import blend


class AsciiLogo(tk.Canvas):
    BORDER = (
        "       .----------------------------------.",
        "   .--'                                    '--.",
        "  /                                            \\",
        " |                                              |",
        " |                                              |",
        "  \\                                            /",
        "   '--.                                    .--'",
        "       '----------------------------------'",
    )

    def __init__(self, parent, motion, background):
        super().__init__(parent, width=420, height=180, bg=background,
                         highlightthickness=0, bd=0, takefocus=False)
        self.motion = motion
        self.typeface = font.Font(root=self, family='DejaVu Sans Mono', size=10)
        self.caption_font = font.Font(root=self, family='DejaVu Sans Mono', size=9)
        self.callback = None
        self.bind('<Configure>', lambda _: self.draw())
        self.bind('<Map>', lambda _: self.draw())
        self.bind('<Destroy>', self.destroyed)
        self.draw()
        self.callback = self.after(120, self.animate)

    def draw(self, now=None):
        self.delete('all')
        now = time.monotonic() if now is None else now
        moving = self.motion()
        width = max(420, self.winfo_width())
        cell, line = self.typeface.measure('M'), self.typeface.metrics('linespace')
        left = (width - 49*cell)/2
        top = 12 + (math.sin(now*math.tau/3)*3 if moving else 0)

        def text(column, row, value, color, tag):
            self.create_text(left+column*cell, top+row*line, text=value, anchor='nw',
                             font=self.typeface, fill=color, tags=tag)

        for row, value in enumerate(self.BORDER):
            text(0, row, value, '#8f94a3', 'outline')
        for row, value in ((2, '\\'), (3, ' >'), (4, '/')):
            text(10, row, value, '#f7f8f5', 'prompt')
        visible = not moving or int(now*2)%2 == 0
        text(15, 4, '____' if visible else '    ', '#f7f8f5', 'cursor')
        glow = (math.sin(now*math.tau/2.4)+1)/2 if moving else 1
        green = blend('#79ad51', '#b9f785', glow)
        shift = 1 if moving and int(now/1.2)%2 else 0
        for row, value in ((2, '.------.'), (3, '(  --  )'), (4, "'------'")):
            text(31+shift, row, value, green, 'toggle')
        self.create_text(width/2, 164, text='C O D E X   I S L A N D',
                         font=self.caption_font, fill='#9a9dad', tags='caption')

    def animate(self):
        self.callback = None
        if self.winfo_ismapped():
            self.draw()
        delay = 120 if self.winfo_ismapped() and self.motion() else 500
        self.callback = self.after(delay, self.animate)

    def cancel_animation(self):
        if self.callback is not None:
            self.after_cancel(self.callback)
            self.callback = None

    def destroyed(self, event):
        if event.widget == self:
            self.cancel_animation()
