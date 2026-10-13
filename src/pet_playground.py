"""A drawn playground sharing the exact mascot used in Floatty's header."""
import math
import time
import tkinter as tk

from header_pet import HeaderPet


class PetPlayground(tk.Canvas):
    def __init__(self, parent, motion, background, state=lambda: 'Ready'):
        super().__init__(parent, width=420, height=250, bg=background,
                         highlightthickness=0, bd=0, takefocus=True, cursor='hand2')
        self.motion = motion
        self.callback = None
        self.pet = HeaderPet(self, motion, state, background, scale=3,
                             playful=True, auto_animate=False)
        self.pet_item = self.create_window(210, 105, window=self.pet, tags='pet')
        self.bind('<Configure>', lambda _: self.draw())
        self.bind('<Map>', lambda _: self.draw())
        self.bind('<Button-1>', self.play)
        self.bind('<Button-3>', lambda _: self.pet.nap())
        self.bind('<Return>', self.play)
        self.bind('<space>', self.play)
        self.bind('<n>', lambda _: self.pet.nap())
        self.bind('<Destroy>', self.destroyed)
        self.draw()
        self.callback = self.after(80, self.animate)

    def play(self, _=None):
        return self.pet.pet()

    def draw(self, now=None):
        now = time.monotonic() if now is None else now
        width = max(420, self.winfo_width())
        moving = self.motion() and not self.pet.sleeping
        for tag in ('outline', 'floor', 'ball', 'ball-detail', 'caption', 'hint'):
            self.delete(tag)
        self.create_polygon(28, 27, 65, 12, width-65, 12, width-28, 27,
                            width-15, 63, width-15, 141, width-28, 177,
                            width-65, 192, 65, 192, 28, 177, 15, 141, 15, 63,
                            smooth=True, splinesteps=24, fill='', outline='#757e70',
                            dash=(3, 6), width=1, tags='outline')
        self.create_oval(width/2-76, 157, width/2+76, 174,
                         fill='#252e24', outline='', tags='floor')
        x = width/2 + (math.sin(now*1.6)*18 if moving else 0)
        self.coords(self.pet_item, x, 105)
        self.pet.draw(now=now)
        bx = width/2+108 + (math.sin(now*2)*9 if moving else 0)
        by = 154 - (abs(math.sin(now*3+.8))*27 if moving else 0)
        self.create_oval(bx-8, by-8, bx+8, by+8, fill='#efc185', outline='', tags='ball')
        self.create_arc(bx-8, by-8, bx+8, by+8, start=75, extent=160,
                        style='arc', outline='#896b49', width=1.3, tags='ball-detail')
        self.create_text(width/2, 216, text='F L O A T T Y',
                         font=('DejaVu Sans Mono', 9), fill='#b9f785', tags='caption')
        self.create_text(width/2, 238, text='Click to pet  /  Right-click to nap',
                         font=('DejaVu Sans', 8), fill='#9a9dad', tags='hint')

    def animate(self):
        self.callback = None
        visible = self.winfo_ismapped()
        if visible:
            self.draw()
        delay = 80 if visible and self.motion() else 200 if visible and not self.pet.sleeping else 500
        self.callback = self.after(delay, self.animate)

    def cancel_animation(self):
        if self.callback is not None:
            self.after_cancel(self.callback)
            self.callback = None
        self.pet.cancel_animation()

    def destroyed(self, event):
        if event.widget == self:
            self.cancel_animation()
