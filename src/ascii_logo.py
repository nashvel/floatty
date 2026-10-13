"""Floatty's ASCII playground, drawn directly in Tk without bitmap assets."""
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
        " |                                              |",
        " |                                              |",
        " |                                              |",
        "  \\                                            /",
        "   '--.                                    .--'",
        "       '----------------------------------'",
    )

    def __init__(self, parent, motion, background):
        super().__init__(parent, width=420, height=250, bg=background,
                         highlightthickness=0, bd=0, takefocus=True, cursor='hand2')
        self.motion = motion
        self.typeface = font.Font(root=self, family='DejaVu Sans Mono', size=10)
        self.caption_font = font.Font(root=self, family='DejaVu Sans Mono', size=9)
        self.callback = None
        self.play_until = 0
        self.bind('<Configure>', lambda _: self.draw())
        self.bind('<Map>', lambda _: self.draw())
        self.bind('<Button-1>', self.play)
        self.bind('<Return>', self.play)
        self.bind('<space>', self.play)
        self.bind('<Destroy>', self.destroyed)
        self.draw()
        self.callback = self.after(120, self.animate)

    def play(self, _=None):
        self.play_until = time.monotonic() + 2.4
        self.focus_set()
        self.draw()
        return 'break'

    def draw(self, now=None):
        self.delete('all')
        now = time.monotonic() if now is None else now
        moving = self.motion()
        playing = now < self.play_until
        width = max(420, self.winfo_width())
        cell, line = self.typeface.measure('M'), self.typeface.metrics('linespace')
        left = (width - 49*cell)/2
        top = 8 + (math.sin(now*math.tau/3)*2 if moving else 0)

        def text(column, row, value, color, tag, dy=0):
            self.create_text(left+column*cell, top+row*line+dy, text=value, anchor='nw',
                             font=self.typeface, fill=color, tags=tag)

        for row, value in enumerate(self.BORDER):
            text(0, row, value, '#8f94a3', 'outline')
        text(7, 5, '>_', '#f7f8f5', 'prompt')
        glow = (math.sin(now*math.tau/2.4)+1)/2 if moving else 1
        green = blend('#8ec764', '#b9f785', glow)
        # The capsule mascot chases a bouncing ball inside the ASCII island.
        phase = now * (3.2 if playing else 1.7)
        column = 20 + (math.sin(phase)*3 if moving else 0)
        hop = -abs(math.sin(phase*1.8))*(8 if playing else 4) if moving else 0
        wink = moving and int(now*2)%8 == 0
        face = '/ ^   ^ \\' if playing else '/ -   - \\' if wink else '/ o   o \\'
        wave = moving and int(now*3)%2 == 0
        art = (
            '    o',
            ' .-----.',
            face,
            '\\| \\_/ |/' if wave or playing else '/| \\_/ |\\',
            " '-----'",
            '  /   \\' if not wave else '  \\   /',
        )
        for row, value in enumerate(art, start=2):
            text(column, row, value, green, 'pet', hop)
        ball_column = 35 + (math.sin(phase+1)*2 if moving else 0)
        ball_hop = -abs(math.sin(phase*1.8+.8))*(26 if playing else 14) if moving else 0
        text(ball_column, 7, '(o)', '#f0bd75', 'ball', ball_hop)
        text(17, 8, '. . . . . . . . .', '#4b514a', 'floor')
        if playing:
            text(22, 1, 'wheee!' if moving else 'hello!', '#f7f8f5', 'reaction')
        self.create_text(width/2, 216, text='F L O A T T Y',
                         font=self.caption_font, fill='#b9f785', tags='caption')
        self.create_text(width/2, 238, text='click to play',
                         font=('DejaVu Sans Mono', 8), fill='#9a9dad', tags='hint')

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
