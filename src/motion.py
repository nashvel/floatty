"""Small cancellable Tk tweens; no worker threads or blocking animation loops."""
import time


def ease_out(progress):
    return 1 - (1 - progress) ** 3


def blend(start, end, progress):
    channels = [round(int(start[i:i+2], 16) + (int(end[i:i+2], 16)-int(start[i:i+2], 16))*progress)
                for i in (1, 3, 5)]
    return '#' + ''.join(f'{channel:02x}' for channel in channels)


class Tween:
    def __init__(self, widget):
        self.widget = widget
        self.callback = None
        self.finalize = None
        self.generation = 0

    @property
    def running(self):
        return self.finalize is not None

    def cancel(self):
        self.generation += 1
        if self.callback is not None:
            self.widget.after_cancel(self.callback)
        self.callback = self.finalize = None

    def finish(self):
        final = self.finalize
        self.cancel()
        if final:
            final()

    def start(self, duration, update, complete=lambda: None):
        self.cancel()
        generation = self.generation
        started = time.monotonic()

        def final():
            update(1)
            complete()
        self.finalize = final

        def frame():
            if generation != self.generation:
                return
            self.callback = None
            progress = min(1, (time.monotonic()-started)/duration) if duration else 1
            update(ease_out(progress))
            if progress == 1:
                self.finalize = None
                complete()
            else:
                self.callback = self.widget.after(16, frame)
        frame()
