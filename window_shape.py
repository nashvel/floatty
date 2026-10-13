"""Optional X11 rounded window shape; gracefully falls back on other desktops."""
import ctypes as c
import math
import os


class Rectangle(c.Structure):
    _fields_ = [('x', c.c_short), ('y', c.c_short), ('width', c.c_ushort), ('height', c.c_ushort)]


def round_window(window, width, height, radius=24):
    if not os.environ.get('DISPLAY'):
        return False
    try:
        x11, ext = c.CDLL('libX11.so.6'), c.CDLL('libXext.so.6')
    except OSError:
        return False
    x11.XOpenDisplay.argtypes, x11.XOpenDisplay.restype = [c.c_char_p], c.c_void_p
    x11.XCloseDisplay.argtypes = [c.c_void_p]
    x11.XFlush.argtypes = [c.c_void_p]
    x11.XQueryTree.argtypes = [c.c_void_p, c.c_ulong, c.POINTER(c.c_ulong), c.POINTER(c.c_ulong),
                              c.POINTER(c.POINTER(c.c_ulong)), c.POINTER(c.c_uint)]
    x11.XFree.argtypes = [c.c_void_p]
    ext.XShapeQueryExtension.argtypes = [c.c_void_p, c.POINTER(c.c_int), c.POINTER(c.c_int)]
    ext.XShapeCombineRectangles.argtypes = [c.c_void_p, c.c_ulong, c.c_int, c.c_int, c.c_int,
                                           c.POINTER(Rectangle), c.c_int, c.c_int, c.c_int]
    display = x11.XOpenDisplay(None)
    if not display:
        return False
    try:
        event, error = c.c_int(), c.c_int()
        if not ext.XShapeQueryExtension(display, c.byref(event), c.byref(error)):
            return False
        radius = min(radius, width//2, height//2)
        rows = []
        for y in range(height):
            distance = max(radius-y-0.5, y-(height-radius)+0.5, 0)
            inset = math.ceil(radius - math.sqrt(max(0, radius*radius-distance*distance))) if distance else 0
            rows.append(Rectangle(inset, y, width-2*inset, 1))
        rectangles = (Rectangle * len(rows))(*rows)
        # Tk has an inner window and a toplevel wrapper; shape both.
        root, parent, count = c.c_ulong(), c.c_ulong(), c.c_uint()
        children = c.POINTER(c.c_ulong)()
        targets = [window]
        if x11.XQueryTree(display, window, c.byref(root), c.byref(parent), c.byref(children), c.byref(count)):
            if children:
                x11.XFree(children)
            if parent.value and parent.value != root.value:
                targets.append(parent.value)
        for target in targets:
            ext.XShapeCombineRectangles(display, target, 0, 0, 0, rectangles, len(rows), 0, 0)
        x11.XFlush(display)
        return True
    finally:
        x11.XCloseDisplay(display)
