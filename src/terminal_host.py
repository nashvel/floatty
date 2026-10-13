"""Native GTK3/VTE terminal renderer embedded in the supplied Tk X11 window.

Uses installed shared libraries directly, so the VTE GI typelib is not required.
stdout carries lifecycle metadata only; terminal bytes remain inside VTE.
"""
import argparse
import ctypes as c
import json
import os


def emit(event, **fields):
    print(json.dumps({'event':event, **fields}), flush=True)


def bind(library, name, result, *arguments):
    function = getattr(library, name)
    function.restype, function.argtypes = result, list(arguments)
    return function


class RGBA(c.Structure):
    _fields_ = [('red', c.c_double), ('green', c.c_double), ('blue', c.c_double), ('alpha', c.c_double)]


class ClientMessage(c.Structure):
    _fields_ = [('type', c.c_int), ('serial', c.c_ulong), ('send_event', c.c_int),
                ('display', c.c_void_p), ('window', c.c_ulong), ('message_type', c.c_ulong),
                ('format', c.c_int), ('data', c.c_long*5)]


class XEvent(c.Union):
    _fields_ = [('message', ClientMessage), ('padding', c.c_long*24)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--window', type=int, required=True)
    parser.add_argument('--folder', required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('A terminal executable is required')
    try:
        gtk = c.CDLL('libgtk-3.so.0')
        vte = c.CDLL('libvte-2.91.so.0')
        gobject = c.CDLL('libgobject-2.0.so.0')
        glib = c.CDLL('libglib-2.0.so.0')
        pango = c.CDLL('libpango-1.0.so.0')
        gdk = c.CDLL('libgdk-3.so.0')
        x11 = c.CDLL('libX11.so.6')
    except OSError:
        emit('error', message='GTK3 and VTE 2.91 are required for the embedded terminal.')
        return
    if not bind(gtk, 'gtk_init_check', c.c_int, c.c_void_p, c.c_void_p)(None, None):
        emit('error', message='The terminal needs an X11/XWayland display.')
        return
    plug = bind(gtk, 'gtk_plug_new', c.c_void_p, c.c_ulong)(args.window)
    terminal = bind(vte, 'vte_terminal_new', c.c_void_p)()
    bind(gtk, 'gtk_container_add', None, c.c_void_p, c.c_void_p)(plug, terminal)
    description = bind(pango, 'pango_font_description_from_string', c.c_void_p, c.c_char_p)(b'Monospace 10')
    bind(vte, 'vte_terminal_set_font', None, c.c_void_p, c.c_void_p)(terminal, description)
    bind(pango, 'pango_font_description_free', None, c.c_void_p)(description)
    background, foreground = RGBA(0.11, 0.12, 0.15, 1), RGBA(0.95, 0.95, 0.98, 1)
    bind(vte, 'vte_terminal_set_color_background', None, c.c_void_p, c.POINTER(RGBA))(terminal, c.byref(background))
    bind(vte, 'vte_terminal_set_color_foreground', None, c.c_void_p, c.POINTER(RGBA))(terminal, c.byref(foreground))
    bind(vte, 'vte_terminal_set_scrollback_lines', None, c.c_void_p, c.c_long)(terminal, 3000)
    bind(vte, 'vte_terminal_set_audible_bell', None, c.c_void_p, c.c_int)(terminal, 0)
    bind(vte, 'vte_terminal_set_scroll_on_keystroke', None, c.c_void_p, c.c_int)(terminal, 1)
    bind(gtk, 'gtk_widget_add_events', None, c.c_void_p, c.c_int)(plug, (1 << 10) | (1 << 11))
    bind(gtk, 'gtk_widget_show_all', None, c.c_void_p)(plug)
    grab_focus = bind(gtk, 'gtk_widget_grab_focus', None, c.c_void_p)
    quit_main = bind(gtk, 'gtk_main_quit', None)
    display = bind(gdk, 'gdk_display_get_default', c.c_void_p)()
    native_display = bind(gdk, 'gdk_x11_display_get_xdisplay', c.c_void_p, c.c_void_p)(display)
    native_window = bind(gtk, 'gtk_widget_get_window', c.c_void_p, c.c_void_p)(plug)
    xid = bind(gdk, 'gdk_x11_window_get_xid', c.c_ulong, c.c_void_p)(native_window)
    set_focus = bind(x11, 'XSetInputFocus', c.c_int, c.c_void_p, c.c_ulong, c.c_int, c.c_ulong)
    flush = bind(x11, 'XFlush', c.c_int, c.c_void_p)
    map_window = bind(x11, 'XMapWindow', c.c_int, c.c_void_p, c.c_ulong)
    send = bind(x11, 'XSendEvent', c.c_int, c.c_void_p, c.c_ulong, c.c_int, c.c_long, c.POINTER(XEvent))
    atom = bind(x11, 'XInternAtom', c.c_ulong, c.c_void_p, c.c_char_p, c.c_int)(native_display, b'_XEMBED', 0)
    child_running = True
    resize = bind(gtk, 'gtk_window_resize', None, c.c_void_p, c.c_int, c.c_int)

    def focus():
        # Tk is the foreign embedder, so supply the map/focus handshake normally
        # provided by GtkSocket. XMapWindow precedes XSetInputFocus on this connection.
        map_window(native_display, xid)
        for opcode in (0, 1, 4):
            event = XEvent()
            event.message.type, event.message.display = 33, native_display
            event.message.window, event.message.message_type, event.message.format = xid, atom, 32
            event.message.data[1] = opcode
            if opcode == 0:
                event.message.data[3] = args.window
            send(native_display, xid, 0, 0, c.byref(event))
        grab_focus(terminal)
        set_focus(native_display, xid, 2, 0)
        flush(native_display)

    click_type = c.CFUNCTYPE(c.c_int, c.c_void_p, c.c_void_p, c.c_void_p)
    @click_type
    def clicked(widget, event, data):
        focus()
        return 0
    exit_type = c.CFUNCTYPE(None, c.c_void_p, c.c_int, c.c_void_p)
    @exit_type
    def exited(widget, status, data):
        nonlocal child_running
        child_running = False
        emit('exited', status=status)
    connect = bind(gobject, 'g_signal_connect_data', c.c_ulong, c.c_void_p, c.c_char_p,
                   c.c_void_p, c.c_void_p, c.c_void_p, c.c_int)
    connect(terminal, b'button-press-event', c.cast(clicked, c.c_void_p), None, None, 0)
    connect(terminal, b'child-exited', c.cast(exited, c.c_void_p), None, None, 0)
    key_value = bind(gdk, 'gdk_event_get_keyval', c.c_int, c.c_void_p, c.POINTER(c.c_uint))
    key_state = bind(gdk, 'gdk_event_get_state', c.c_int, c.c_void_p, c.POINTER(c.c_uint))
    @click_type
    def key_pressed(widget, event, data):
        value, state = c.c_uint(), c.c_uint()
        key_value(event, c.byref(value))
        key_state(event, c.byref(state))
        if state.value & 5 == 5 and value.value in (67, 99):
            bind(vte, 'vte_terminal_copy_clipboard_format', None, c.c_void_p, c.c_int)(terminal, 1)
            return 1
        if state.value & 5 == 5 and value.value in (86, 118):
            bind(vte, 'vte_terminal_paste_clipboard', None, c.c_void_p)(terminal)
            return 1
        if child_running and value.value == 65293 and state.value & 5 == 0:
            emit('submitted')
        elif child_running and value.value in (67, 99) and state.value & 4:
            emit('interrupted')
        return 0
    connect(terminal, b'key-press-event', c.cast(key_pressed, c.c_void_p), None, None, 0)
    dispatch_key = bind(gtk, 'gtk_widget_event', c.c_int, c.c_void_p, c.c_void_p)
    @click_type
    def route_key(widget, event, data):
        # A foreign Tk parent does not implement GtkSocket's key forwarding.
        # Dispatch actual native key events to VTE, which owns terminal encoding.
        return dispatch_key(terminal, event)
    connect(plug, b'key-press-event', c.cast(route_key, c.c_void_p), None, None, 0)
    connect(plug, b'key-release-event', c.cast(route_key, c.c_void_p), None, None, 0)
    callback_type = c.CFUNCTYPE(None, c.c_void_p, c.c_int, c.c_void_p, c.c_void_p)
    @callback_type
    def spawned(widget, pid, error, data):
        nonlocal child_running
        if error or pid < 0:
            child_running = False
            emit('error', message='Could not launch Codex. Check the executable and working folder.')
        else:
            emit('started', pid=pid, window=xid)
            focus()
    argv = (c.c_char_p * (len(command)+1))(*[os.fsencode(item) for item in command], None)
    spawn = bind(vte, 'vte_terminal_spawn_async', None, c.c_void_p, c.c_int, c.c_char_p,
                 c.POINTER(c.c_char_p), c.POINTER(c.c_char_p), c.c_int,
                 c.c_void_p, c.c_void_p, c.c_void_p, c.c_int, c.c_void_p, callback_type, c.c_void_p)
    spawn(terminal, 0, os.fsencode(args.folder), argv, None, 4, None, None, None, -1, None, spawned, None)

    # Parent stdin accepts lifecycle controls, never commands or terminal bytes.
    os.set_blocking(0, False)
    buffer = b''
    io_type = c.CFUNCTYPE(c.c_int, c.c_void_p, c.c_int, c.c_void_p)
    @io_type
    def control(channel, condition, data):
        nonlocal buffer
        try:
            chunk = os.read(0, 4096)
        except BlockingIOError:
            return 1
        if not chunk:
            quit_main()
            return 0
        buffer += chunk
        while b'\n' in buffer:
            line, buffer = buffer.split(b'\n', 1)
            if line == b'focus':
                focus()
            elif line.startswith(b'resize '):
                try:
                    width, height = map(int, line.split()[1:])
                    if 1 < width < 10000 and 1 < height < 10000:
                        resize(plug, width, height)
                except ValueError:
                    pass
            elif line == b'close' and not child_running:
                quit_main()
                return 0
        return 1
    channel = bind(glib, 'g_io_channel_unix_new', c.c_void_p, c.c_int)(0)
    bind(glib, 'g_io_add_watch', c.c_uint, c.c_void_p, c.c_int, io_type, c.c_void_p)(channel, 1|16, control, None)
    bind(gtk, 'gtk_main', None)()
    bind(gtk, 'gtk_widget_destroy', None, c.c_void_p)(plug)
    bind(glib, 'g_io_channel_unref', None, c.c_void_p)(channel)


if __name__ == '__main__':
    main()
