"""A tiny interactive, code-drawn mascot; it never controls the terminal."""
import math
import time
import tkinter as tk


class HeaderPet(tk.Canvas):
    def __init__(self, parent, motion, state, background, scale=1, playful=False, auto_animate=True):
        super().__init__(parent, width=round(36*scale), height=round(40*scale), bg=background,
                         highlightthickness=0, bd=0, cursor='hand2', takefocus=True)
        self.scale_factor, self.playful = scale, playful
        self.motion, self.state = motion, state
        self.callback = None
        self.hover = self.sleeping = False
        self.gaze = (0, 0)
        self.happy_until = 0
        self.bind('<Enter>', self.enter)
        self.bind('<Leave>', self.leave)
        self.bind('<Motion>', self.look)
        self.bind('<Button-1>', self.pet)
        self.bind('<Button-3>', self.nap)
        self.bind('<Return>', self.pet)
        self.bind('<space>', self.pet)
        self.bind('<n>', self.nap)
        self.bind('<FocusIn>', lambda _: self.draw())
        self.bind('<FocusOut>', lambda _: self.draw())
        self.bind('<Map>', lambda _: self.draw())
        self.bind('<Destroy>', self.destroyed)
        self.draw()
        if auto_animate:
            self.callback = self.after(80, self.animate)

    def enter(self, _):
        self.hover = True
        self.draw()

    def leave(self, _):
        self.hover = False
        self.draw()

    def look(self, _):
        self.draw()

    def update_gaze(self):
        """Read screen coordinates through Tk; no global input hooks or storage."""
        try:
            pointer = self.winfo_pointerxy()
            if pointer == (-1, -1):
                self.gaze = (0, 0)
                return
            dx = pointer[0] - (self.winfo_rootx() + 18*self.scale_factor)
            dy = pointer[1] - (self.winfo_rooty() + 19*self.scale_factor)
            distance = max(50*self.scale_factor, math.hypot(dx, dy))
            self.gaze = (2.8 * dx / distance, 1.8 * dy / distance)
        except tk.TclError:
            self.gaze = (0, 0)

    def pet(self, _=None):
        self.sleeping = False
        self.happy_until = time.monotonic() + 1.4
        self.focus_set()
        self.draw()
        return 'break'

    def nap(self, _=None):
        if self.state() not in {'Working', 'Launching', 'Needs you'}:
            self.sleeping = not self.sleeping
            self.happy_until = 0
        self.draw()
        return 'break'

    def draw(self, now=None):
        now = time.monotonic() if now is None else now
        state = self.state()
        moving = self.motion()
        if state in {'Working', 'Launching', 'Needs you'}:
            self.sleeping = False
        happy = now < self.happy_until
        self.mood = ('sleeping' if self.sleeping else 'happy' if happy else
                     'working' if state in {'Working', 'Launching'} else
                     'celebrating' if state == 'Completed' else
                     'attention' if state == 'Needs you' else 'idle')
        self.delete('all')
        active = self.mood in {'happy', 'celebrating', 'working'}
        bob = math.sin(now * (8 if active else 2.7)) * (1.6 if active else .7) if moving and not self.sleeping else 0
        y = 19 + bob
        lime = '#f0bd75' if self.mood == 'attention' else '#b9f785'
        ink = '#18251a'
        # Soft shadow, little feet, capsule body, and antenna.
        self.create_oval(9, 32, 27, 35, fill='#202723', outline='', tags='shadow')
        for x in (12, 24):
            self.create_line(x, y+9, x, y+13, fill=lime, width=3, capstyle='round', tags='feet')
        arm = (2*math.sin(now*12) if moving and self.mood == 'working' else
               3*math.sin(now*4) if moving and self.playful and not self.sleeping else 0)
        self.create_line(6, y+3, 3, y+7+arm, fill=lime, width=2, capstyle='round', tags='arms')
        self.create_line(30, y+3, 33, y+7-arm, fill=lime, width=2, capstyle='round', tags='arms')
        self.create_line(18, y-9, 18, y-13, fill=lime, width=2, tags='antenna')
        self.create_oval(16, y-16, 20, y-12, fill=lime, outline='', tags='antenna')
        self.create_polygon(7, y-7, 12, y-10, 24, y-10, 29, y-7,
                            31, y+2, 27, y+10, 9, y+10, 5, y+2,
                            smooth=True, splinesteps=16, fill=lime, outline='', tags='body')
        if self.sleeping:
            self.gaze = (0, 0)
        elif self.winfo_ismapped():
            self.update_gaze()
        gx, gy = self.gaze
        blink = moving and now % 5.2 > 5.03
        for x in (12, 24):
            if self.mood in {'happy', 'celebrating'}:
                self.create_line(x-2+gx, y+gy, x+gx, y-2+gy, x+2+gx, y+gy,
                                 fill=ink, width=2, smooth=True, tags='eyes')
            elif self.sleeping or blink:
                self.create_line(x-2, y, x+2, y, fill=ink, width=2, tags='eyes')
            else:
                self.create_oval(x-1.5+gx, y-2+gy, x+1.5+gx, y+2+gy,
                                 fill=ink, outline='', tags='eyes')
        self.create_line(15, y+5, 18, y+6.5, 21, y+5, smooth=True,
                         fill=ink, width=1.4, tags='mouth')
        if self.sleeping:
            self.create_text(30, 6, text='z', fill='#9a9dad', font=('DejaVu Sans', round(8*self.scale_factor)), tags='reaction')
        elif happy:
            self.create_text(30, 6, text='♥', fill='#e9a8bd', font=('DejaVu Sans', round(9*self.scale_factor)), tags='reaction')
        elif self.mood == 'celebrating':
            for x, top in ((4, 6), (31, 9)):
                self.create_text(x, top, text='✦', fill=lime, font=('DejaVu Sans', round(8*self.scale_factor)), tags='reaction')
        elif self.mood == 'attention':
            self.create_text(31, 6, text='!', fill=lime, font=('DejaVu Sans', round(9*self.scale_factor), 'bold'), tags='reaction')
        if self.focus_get() == self:
            self.create_line(13, 38, 23, 38, fill='#879d74', width=1, tags='focus')

        if self.scale_factor != 1:
            self.scale('all', 0, 0, self.scale_factor, self.scale_factor)
            for item in self.find_all():
                if self.type(item) == 'line':
                    self.itemconfigure(item, width=float(self.itemcget(item, 'width'))*self.scale_factor)

    def animate(self):
        self.callback = None
        if self.winfo_ismapped():
            self.draw()
        visible = self.winfo_ismapped()
        delay = 80 if visible and self.motion() else 200 if visible and not self.sleeping else 500
        self.callback = self.after(delay, self.animate)

    def cancel_animation(self):
        if self.callback is not None:
            self.after_cancel(self.callback)
            self.callback = None

    def destroyed(self, event):
        if event.widget == self:
            self.cancel_animation()
