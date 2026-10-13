import json
import os
from pathlib import Path
import queue
import socket
import subprocess
import sys
import tempfile
import time
import tkinter as tk
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from notify_bridge import forward
from runtime import IntegrationError
from terminal_session import TerminalSession


class TerminalContractTests(unittest.TestCase):
    def test_completion_hook_strips_transcripts_and_ignores_other_events(self):
        with tempfile.TemporaryDirectory() as directory, socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as receiver:
            address = directory+'/notify.sock'
            try:
                receiver.bind(address)
            except PermissionError:
                self.skipTest('Unix socket binding is unavailable in this sandbox')
            receiver.settimeout(0.1)
            self.assertTrue(forward(address, json.dumps({'type':'agent-turn-complete', 'input-messages':['private'], 'last-assistant-message':'private'})))
            self.assertEqual(json.loads(receiver.recv(1024)), {'type':'agent-turn-complete'})
            self.assertFalse(forward(address, '{"type":"other"}'))
            self.assertFalse(forward(address, 'not json'))
            with self.assertRaises(socket.timeout):
                receiver.recv(1024)

    def test_close_never_terminates_live_terminal(self):
        session = TerminalSession(queue.Queue())
        session.running = True
        with self.assertRaisesRegex(IntegrationError, 'Ctrl.C'):
            session.close()
        self.assertFalse(session.closed.is_set())

    def test_default_launch_is_codex_and_notify_override_is_process_local(self):
        session = TerminalSession(queue.Queue())
        with patch('terminal_session.shutil.which', return_value='/usr/bin/codex'), patch('terminal_session.subprocess.Popen') as popen, patch('terminal_session.threading.Thread'), patch('terminal_session.socket.socket'), patch('terminal_session.os.chmod'):
            session.start(1234, '/tmp')
            args = popen.call_args.args[0]
            self.assertEqual(args[args.index('--')+1], '/usr/bin/codex')
            self.assertIn('notify=', args[-1])
            self.assertEqual(popen.call_args.kwargs['env']['GDK_BACKEND'], 'x11')
            self.assertFalse(popen.call_args.kwargs.get('shell', False))
            session.running = False
            session.close()


@unittest.skipUnless(os.environ.get('CODEX_ISLAND_UI_TEST') == '1', 'Native terminal acceptance is opt-in')
class NativeTerminalTests(unittest.TestCase):
    def test_native_tty_keyboard_resize_and_manual_ctrl_c(self):
        root = tk.Tk()
        root.title('Codex Island Terminal Acceptance')
        root.overrideredirect(True)
        root.attributes('-topmost', True)
        root.geometry('640x400+40+40')
        frame = tk.Frame(root)
        frame.pack(fill='both', expand=True)
        root.update()
        events = queue.Queue()
        session = TerminalSession(events)
        with tempfile.TemporaryDirectory() as directory:
            proof = Path(directory)/'proof.json'
            script = '''import os,sys,signal,json,fcntl,termios,struct
from pathlib import Path
p=Path(sys.argv[1]); result={'stdin_tty':os.isatty(0),'stdout_tty':os.isatty(1),'cwd':os.getcwd()}
p.write_text(json.dumps(result))
def save():
 result['size']=list(struct.unpack('HHHH',fcntl.ioctl(0,termios.TIOCGWINSZ,b'\\0'*8))[:2]); p.write_text(json.dumps(result))
def resized(*_): save()
def interrupted(*_): result['ctrl_c']=True; save(); sys.exit(0)
signal.signal(signal.SIGINT,interrupted); signal.signal(signal.SIGWINCH,resized)
save(); print('\\033[32mNative terminal ready\\033[0m',flush=True)
for line in sys.stdin:
 result['input']=line.strip(); save(); print('Received input',flush=True)
'''
            try:
                session.start(frame.winfo_id(), directory, [sys.executable, '-u', '-c', script, str(proof)])
                deadline = time.monotonic()+8
                started = None
                while time.monotonic() < deadline and started is None:
                    root.update()
                    try:
                        _, event = events.get(timeout=0.05)
                    except queue.Empty:
                        continue
                    if event['event'] == 'error':
                        self.fail(event['message'])
                    if event['event'] == 'started':
                        started = event
                self.assertIsNotNone(started, 'Native helper did not start')
                session.resize(640, 400)
                session.focus()
                for _ in range(20):
                    root.update()
                    if proof.exists():
                        break
                    time.sleep(0.02)
                subprocess.run(['import','-window',str(frame.winfo_id()),'/tmp/codex-island-native-terminal.png'], check=True)
                initial = json.loads(proof.read_text())
                self.assertTrue(initial['stdin_tty'])
                self.assertTrue(initial['stdout_tty'])
                self.assertEqual(initial['cwd'], directory)
                session.focus()
                deadline = time.monotonic()+1
                while time.monotonic() < deadline:
                    root.update()
                    focused = subprocess.check_output(['xdotool','getwindowfocus','-f'], text=True).strip()
                    if int(focused) == started['window']:
                        break
                    time.sleep(0.02)
                root.after(200, root.quit)
                root.mainloop()
                focused = subprocess.check_output(['xdotool','getwindowfocus','-f'], text=True).strip()
                self.assertEqual(int(focused), started['window'], 'Refusing keyboard input outside the test terminal')
                subprocess.run(['xdotool', 'type', '--clearmodifiers', 'hello'], check=True)
                subprocess.run(['xdotool', 'key', 'Return'], check=True)
                deadline = time.monotonic()+3
                while time.monotonic() < deadline:
                    root.update()
                    if json.loads(proof.read_text()).get('input') == 'hello':
                        break
                    time.sleep(0.02)
                subprocess.run(['import','-window',str(frame.winfo_id()),'/tmp/codex-island-native-terminal.png'], check=True)
                self.assertEqual(json.loads(proof.read_text()).get('input'), 'hello')
                session.resize(800, 500)
                root.after(200, root.quit)
                root.mainloop()
                self.assertNotEqual(initial['size'], json.loads(proof.read_text())['size'])
                subprocess.run(['import','-window',str(frame.winfo_id()),'/tmp/codex-island-native-terminal.png'], check=True)
                focused = subprocess.check_output(['xdotool','getwindowfocus','-f'], text=True).strip()
                self.assertEqual(int(focused), started['window'])
                subprocess.run(['xdotool', 'key', '--clearmodifiers', 'ctrl+c'], check=True)
                deadline = time.monotonic()+3
                while time.monotonic() < deadline and session.running:
                    root.update()
                    time.sleep(0.02)
                self.assertFalse(session.running)
                self.assertTrue(json.loads(proof.read_text()).get('ctrl_c'))
            finally:
                # Test-only cleanup if an assertion fails before sending Ctrl+C.
                if session.running and session.child_pid:
                    os.kill(session.child_pid, 2)
                    time.sleep(0.2)
                if not session.running:
                    session.close()
                root.destroy()


if __name__ == '__main__':
    unittest.main()
