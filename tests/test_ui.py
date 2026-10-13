"""Opt-in desktop acceptance checks: CODEX_ISLAND_UI_TEST=1 python3 -m unittest discover -s tests -v."""
import os
import sys
import tempfile
import gc
import threading
from pathlib import Path
import subprocess
import tkinter as tk
import unittest
from unittest.mock import patch

from island import Island
from runtime import Container, Listener, identity


@unittest.skipUnless(os.environ.get('CODEX_ISLAND_UI_TEST') == '1', 'Desktop acceptance is opt-in')
class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.app = Island(self.root, '/tmp', preview=True, motion=False)
        self.root.update()

    def tearDown(self):
        self.app.closing = True
        if self.app.folder_picker is not None:
            self.app.folder_picker.close()
        self.app.resize_motion.cancel()
        def cancel_widgets(widget):
            if hasattr(widget, 'cancel_animation'):
                widget.cancel_animation()
            if hasattr(widget, 'tween'):
                widget.tween.cancel()
            for child in widget.winfo_children():
                cancel_widgets(child)
        cancel_widgets(self.root)
        for callback in self.root.tk.call('after', 'info'):
            self.root.after_cancel(callback)
        self.root.destroy()
        self.app = self.root = None
        gc.collect()

    def wait_frames(self, milliseconds):
        self.root.after(milliseconds, self.root.quit)
        self.root.mainloop()

    def test_folder_picker_is_nonmodal_does_not_launch_and_selects_spaces(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)/'project with spaces'
            project.mkdir()
            self.app.folder = directory
            self.app.preview = False
            self.app.collapse()
            with patch.object(self.app.terminal, 'start') as start:
                self.app.choose_folder()
                picker = self.app.folder_picker
                self.root.update()
                self.assertIsNotNone(picker)
                self.assertTrue(picker.winfo_viewable())
                self.assertGreater(picker.use_button.winfo_height(), 20)
                self.assertLess(picker.use_button.winfo_rooty()+picker.use_button.winfo_height(),
                                picker.winfo_rooty()+picker.winfo_height())
                self.assertIsNone(self.root.grab_current())
                subprocess.run(['import', '-window', str(picker.winfo_id()), '/tmp/codex-island-folder.png'], check=True, timeout=5)
                self.assertEqual(self.app.launch_button.cget('state'), 'disabled')
                heartbeat = []
                self.root.after(20, lambda: heartbeat.append(True))
                self.wait_frames(100)
                self.assertTrue(heartbeat)
                self.app.launch_terminal()
                start.assert_not_called()
                picker.path.set(str(project))
                picker.load(select=True)
                self.wait_frames(200)
                self.assertEqual(self.app.folder, str(project))
                self.assertIsNone(self.app.folder_picker)
                self.assertEqual(self.app.launch_button.cget('state'), 'normal')
                self.root.update()
                self.assertTrue(self.root.winfo_viewable())
                start.assert_not_called()
                self.assertIn('Click Launch Codex', self.app.status.get())
                self.assertIn('Runs Codex CLI:', self.app.launch_description.cget('text'))

    def test_folder_picker_can_cancel_during_slow_filesystem_check(self):
        entered, release = threading.Event(), threading.Event()
        original_resolve = Path.resolve
        original = self.app.folder
        def slow_resolve(path, *args, **kwargs):
            entered.set()
            release.wait(timeout=2)
            return original_resolve(path, *args, **kwargs)
        with patch('folder_picker.Path.resolve', autospec=True, side_effect=slow_resolve):
            try:
                self.app.choose_folder()
                self.assertTrue(entered.wait(timeout=1))
                heartbeat = []
                self.root.after(20, lambda: heartbeat.append(True))
                self.wait_frames(80)
                self.assertTrue(heartbeat)
                self.app.folder_picker.close()
                self.root.update()
                self.assertIsNone(self.app.folder_picker)
                self.assertTrue(self.root.winfo_viewable())
                self.assertEqual(self.app.folder, original)
            finally:
                release.set()
            self.wait_frames(100)
        self.assertEqual(self.app.folder, original)

    def test_folder_picker_cancel_and_invalid_path_do_not_change_folder(self):
        self.app.collapse()
        original = self.app.folder
        self.app.choose_folder()
        picker = self.app.folder_picker
        picker.path.set('/this-folder-does-not-exist-codex-island')
        picker.load(select=True)
        self.wait_frames(150)
        self.assertEqual(self.app.folder, original)
        self.assertFalse(picker.closed)
        self.assertIn('Cannot access', picker.info.get())
        picker.close()
        self.assertIsNone(self.app.folder_picker)
        self.assertEqual(self.app.folder, original)
        self.root.update()
        self.assertTrue(self.root.winfo_viewable())
        self.assertEqual(self.app.launch_button.cget('state'), 'normal')

    def test_ascii_logo_motion_reduced_motion_and_launch_hiding(self):
        self.app.collapse()
        self.root.update()
        logo = self.app.terminal_hint
        self.assertTrue(logo.winfo_ismapped())
        self.app.motion.set(True)
        logo.draw(now=0.0)
        first = [(logo.itemcget(item, 'text'), logo.itemcget(item, 'fill'), logo.coords(item))
                 for item in logo.find_all()]
        logo.draw(now=1.3)
        second = [(logo.itemcget(item, 'text'), logo.itemcget(item, 'fill'), logo.coords(item))
                  for item in logo.find_all()]
        self.assertNotEqual(first, second)
        self.assertTrue(all(logo.itemcget(item, 'text').isascii() for item in logo.find_all()))
        self.app.motion.set(False)
        logo.draw(now=0.0)
        still = [(logo.itemcget(item, 'text'), logo.itemcget(item, 'fill'), logo.coords(item))
                 for item in logo.find_all()]
        logo.draw(now=1.3)
        self.assertEqual(still, [(logo.itemcget(item, 'text'), logo.itemcget(item, 'fill'), logo.coords(item))
                                for item in logo.find_all()])
        self.app.preview = False
        with patch.object(self.app.terminal, 'start'):
            self.app.launch_terminal()
        self.root.update()
        self.assertFalse(logo.winfo_ismapped())

    def test_animation_intermediate_frame_and_rapid_reversal(self):
        self.app.motion.set(True)
        self.app.title.event_generate('<Button-1>', x=10, y=5)
        self.app.title.event_generate('<ButtonRelease-1>', x=10, y=5)
        self.wait_frames(80)
        self.assertGreater(self.root.winfo_height(), 58)
        self.assertLess(self.root.winfo_height(), 620)
        intermediate = self.root.winfo_height()
        self.app.title.event_generate('<Button-1>', x=10, y=5)
        self.app.title.event_generate('<ButtonRelease-1>', x=10, y=5)
        self.root.update()
        self.assertLessEqual(self.root.winfo_height(), intermediate)
        self.wait_frames(320)
        self.assertEqual((self.root.winfo_width(), self.root.winfo_height()), (320, 58))
        self.assertFalse(self.app.body.winfo_ismapped())
        self.assertFalse(self.app.resize_motion.running)

    def test_reduced_motion_settles_inflight_resize(self):
        self.app.motion.set(True)
        self.app.collapse()
        self.wait_frames(50)
        self.app.motion.set(False)
        self.app.motion_changed()
        self.root.update()
        self.assertEqual((self.root.winfo_width(), self.root.winfo_height()), (540, 620))
        self.assertFalse(self.app.resize_motion.running)
        self.app.collapse()
        self.root.update()
        self.assertEqual(self.root.winfo_height(), 58)

    def test_button_hover_and_press_animate_without_changing_actions(self):
        self.app.collapse()
        self.root.update()
        self.app.motion.set(True)
        button = self.app.launch_button
        button.unbind('<Enter>')
        button.unbind('<Leave>')
        button.set_hover(True)
        self.wait_frames(40)
        self.assertNotEqual(button.surface_color, button.fill)
        self.assertNotEqual(button.surface_color, button.hover)
        button.set_hover(False)
        self.wait_frames(160)
        self.assertEqual(button.surface_color, button.fill)
        button.press(None)
        self.wait_frames(160)
        self.assertEqual(button.inset, 2)
        with patch.object(button, 'command') as command:
            button.release(type('Event', (), {'x':10, 'y':10})())
            command.assert_called_once()
        self.wait_frames(160)
        self.assertEqual(button.inset, 0)

    def test_status_pulse_only_while_working_and_motion_enabled(self):
        self.app.motion.set(True)
        self.app.busy = True
        self.app.state = 'Working'
        with patch('island.time.monotonic', return_value=0.4):
            self.app.pulse()
            bright = self.app.dot.cget('fg')
        with patch('island.time.monotonic', return_value=1.2):
            self.app.pulse()
            self.assertNotEqual(bright, self.app.dot.cget('fg'))
        self.app.motion.set(False)
        self.app.pulse()
        self.assertEqual(self.app.dot.cget('fg'), '#f0bd75')

    def test_layout_collapse_tabs_and_screenshot(self):
        self.assertFalse(self.app.body.winfo_ismapped())
        self.assertEqual((self.root.winfo_width(), self.root.winfo_height()), (320, 58))
        self.app.title.event_generate('<Button-1>', x=10, y=5)
        self.app.title.event_generate('<ButtonRelease-1>', x=10, y=5)
        self.root.update()
        self.assertTrue(self.app.body.winfo_ismapped())
        # Capture only the app window; no desktop contents.
        subprocess.run(['import', '-window', str(self.root.winfo_id()), '/tmp/codex-island-chat.png'], check=True, timeout=5)
        self.app.collapse()
        self.root.update()
        self.assertFalse(self.app.body.winfo_ismapped())
        self.assertEqual(self.root.winfo_height(), 58)
        subprocess.run(['import', '-window', str(self.root.winfo_id()), '/tmp/codex-island-compact.png'], check=True, timeout=5)
        self.app.collapse()
        with patch.object(self.app, 'refresh'):
            self.app.show_tab('Services')
            self.app.events.put(('services', ([], ['Docker unavailable in test'])))
            self.app.pump()
            self.root.update()
            self.assertTrue(self.app.pages['Services'].winfo_ismapped())
            self.assertIn('unavailable', self.app.service_info.cget('text'))
        self.assertNotIn('Activity', self.app.pages)
        self.assertFalse(hasattr(self.app, 'history'))
        self.assertAlmostEqual(float(self.root.attributes('-alpha')), 0.82, places=2)
        self.app.opacity.set(65)
        self.app.apply_opacity()
        self.assertAlmostEqual(float(self.root.attributes('-alpha')), 0.65, places=2)

    def test_drag_does_not_expand_and_button_state_remains_functional(self):
        self.app.title.event_generate('<Button-1>', x=10, y=5, rootx=100, rooty=100)
        self.app.title.event_generate('<B1-Motion>', x=20, y=10, rootx=150, rooty=120)
        self.app.title.event_generate('<ButtonRelease-1>', x=20, y=10, rootx=150, rooty=120)
        self.root.update()
        self.assertFalse(self.app.expanded)
        self.app.toggle.activate()
        self.root.update()
        self.assertTrue(self.app.expanded)
        self.assertEqual(self.app.toggle.cget('text'), '−')
        with patch.object(self.app.launch_button, 'command') as command:
            self.app.launch_button.configure(state='disabled')
            self.app.launch_button.activate()
            command.assert_not_called()
            self.app.launch_button.configure(state='normal')
            self.app.launch_button.activate()
            command.assert_called_once()
        self.assertIsInstance(self.app.terminal_container, tk.Frame)
        self.assertFalse(hasattr(self.app, 'input'))
        self.assertFalse(hasattr(self.app, 'transcript'))

    def test_terminal_completion_and_manual_interrupt_status(self):
        self.app.notifications.set(False)
        self.app.terminal_event({'event':'submitted'})
        self.assertTrue(self.app.busy)
        self.app.terminal_event({'event':'completed'})
        self.assertFalse(self.app.busy)
        self.assertEqual(self.app.state, 'Completed')
        self.app.terminal_event({'event':'interrupted'})
        self.assertEqual(self.app.state, 'Terminal')
        self.assertFalse(hasattr(self.app, 'interrupt'))
        self.assertFalse(hasattr(self.app, 'send'))

    def test_launch_defaults_to_codex_and_active_terminal_is_not_stopped(self):
        self.app.preview = False
        self.app.collapse()
        self.root.update()
        with patch.object(self.app.terminal, 'start') as start:
            self.app.launch_button.activate()
            start.assert_called_once_with(self.app.terminal_container.winfo_id(), '/tmp')
        self.app.terminal.running = True
        try:
            with patch.object(self.app.terminal, 'focus') as focus, patch.object(self.app.terminal, 'close') as close:
                self.app.close()
                self.assertFalse(self.app.closing)
                close.assert_not_called()
                focus.assert_called()
                self.assertIn('Ctrl+C', self.app.status.get())
        finally:
            self.app.terminal.running = False

    def test_cancelled_stop_never_executes(self):
        item = Container('a'*64, 'disposable', '3000/tcp')
        self.app.rows = [('Docker', item)]
        self.app.render_services()
        with patch('island.messagebox.askyesno', return_value=False), patch.object(self.app.docker, 'stop') as stop:
            self.app.service_buttons[('Docker', item)].activate()
            stop.assert_not_called()
            self.assertFalse(self.app.stopping)

    def test_service_cards_disable_protected_and_unknown_owners(self):
        protected = Listener('tcp', '*:123', identity(os.getpid()))
        unknown = Listener('tcp', '*:456', None)
        self.app.rows = [('Ports', protected), ('Ports', unknown)]
        self.app.render_services()
        for key in self.app.rows:
            self.assertEqual(self.app.service_buttons[key].cget('state'), 'disabled')
            self.assertEqual(self.app.service_buttons[key].cget('text'), 'Read-only')

    def test_docker_button_success_failure_and_no_chat_logs(self):
        self.app.collapse()
        item = Container('b'*64, 'disposable', '3000/tcp')
        self.app.rows = [('Docker', item)]
        with patch.object(self.app, 'refresh'):
            self.app.show_tab('Services')
        self.app.render_services()
        with patch('island.messagebox.askyesno', return_value=True), patch.object(self.app.docker, 'stop', return_value='Stopped disposable.'), patch.object(self.app, 'refresh') as refresh:
            self.app.service_buttons[('Docker', item)].activate()
            self.assertEqual(self.app.service_buttons[('Docker', item)].cget('state'), 'disabled')
            self.wait_frames(180)
            self.assertFalse(self.app.stopping)
            self.assertEqual(self.app.status.get(), 'Stopped disposable.')
            refresh.assert_called()
        with patch('island.messagebox.askyesno', return_value=True), patch.object(self.app.docker, 'stop', side_effect=RuntimeError('Permission denied')):
            self.app.service_buttons[('Docker', item)].activate()
            self.wait_frames(180)
            self.assertFalse(self.app.stopping)
            self.assertEqual(self.app.service_buttons[('Docker', item)].cget('state'), 'normal')
            self.assertEqual(self.app.status.get(), 'Permission denied')
            self.assertFalse(hasattr(self.app, 'transcript'))
        self.root.update()
        subprocess.run(['import', '-window', str(self.root.winfo_id()), '/tmp/codex-island-services.png'], check=True, timeout=5)

    def test_gui_stop_terminates_disposable_real_listener(self):
        child = subprocess.Popen([sys.executable, '-u', '-c',
            'import socket,time; s=socket.socket(); s.bind(("127.0.0.1",0)); s.listen(); print(s.getsockname()[1],flush=True); time.sleep(30)'],
            stdout=subprocess.PIPE, text=True)
        try:
            port = child.stdout.readline().strip()
            item = Listener('tcp', '127.0.0.1:'+port, identity(child.pid))
            self.app.rows = [('Ports', item)]
            self.app.render_services()
            with patch('island.messagebox.askyesno', return_value=True), patch.object(self.app, 'refresh'):
                self.app.service_buttons[('Ports', item)].activate()
                self.wait_frames(250)
                self.assertEqual(child.wait(timeout=3), -15)
                self.assertIn('Termination requested', self.app.status.get())
        finally:
            if child.poll() is None:
                child.terminate()
                child.wait()
            child.stdout.close()


if __name__ == '__main__':
    unittest.main()
