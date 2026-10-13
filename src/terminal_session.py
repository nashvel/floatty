"""Own one native terminal helper and a private completion-notification socket."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import threading

from runtime import IntegrationError


class TerminalSession:
    def __init__(self, events):
        self.events = events
        self.process = None
        self.running = False
        self.child_pid = None
        self.directory = None
        self.socket = None
        self.closed = threading.Event()
        self.generation = 0

    def start(self, window_id, folder, command=None):
        if self.running:
            self.focus()
            return
        self.close()
        if command is None:
            executable = shutil.which('codex')
            if not executable:
                raise IntegrationError('Install Codex CLI and run codex login first.')
        self.closed = threading.Event()
        self.generation += 1
        try:
            self.directory = tempfile.TemporaryDirectory(prefix='floatty-')
            address = str(Path(self.directory.name) / 'complete.sock')
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            self.socket.bind(address)
            os.chmod(address, 0o600)
            self.socket.settimeout(0.2)
        except OSError as exc:
            self.close()
            raise IntegrationError('Could not create the private terminal notification socket.') from exc
        if command is None:
            hook = [sys.executable, str(Path(__file__).with_name('notify_bridge.py')), address]
            command = [executable, '-c', 'notify=' + json.dumps(hook)]
        environment = os.environ.copy()
        environment['GDK_BACKEND'] = 'x11'
        self.running = True
        try:
            self.process = subprocess.Popen(
                [sys.executable, str(Path(__file__).with_name('terminal_host.py')),
                 '--window', str(window_id), '--folder', str(folder), '--', *command],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, bufsize=1, start_new_session=True, env=environment,
            )
        except OSError as exc:
            self.running = False
            self.close()
            raise IntegrationError('Could not start the terminal helper.') from exc
        threading.Thread(target=self._read, args=(self.process, self.closed, self.generation), daemon=True).start()
        threading.Thread(target=self._notifications, args=(self.socket, self.closed, self.generation), daemon=True).start()

    def _read(self, process, closed, generation):
        try:
            for line in process.stdout:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if generation != self.generation:
                    continue
                if event.get('event') == 'started':
                    self.child_pid = event['pid']
                elif event.get('event') in {'exited', 'error'}:
                    self.running = False
                    self.child_pid = None
                self.events.put(('terminal', {**event, 'generation':generation}))
        finally:
            if generation == self.generation:
                self.running = False
            if not closed.is_set():
                self.events.put(('terminal', {'event':'disconnected', 'generation':generation}))

    def _notifications(self, channel, closed, generation):
        while not closed.is_set():
            try:
                data = json.loads(channel.recv(512))
                if data == {'type':'agent-turn-complete'}:
                    self.events.put(('terminal', {'event':'completed', 'generation':generation}))
            except socket.timeout:
                continue
            except (ValueError, OSError):
                if closed.is_set():
                    break

    def control(self, action):
        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.write(action + '\n')
                self.process.stdin.flush()
            except (OSError, ValueError):
                pass

    def focus(self):
        self.control('focus')

    def resize(self, width, height):
        if width > 1 and height > 1:
            self.control(f'resize {int(width)} {int(height)}')

    def close(self):
        if self.running:
            raise IntegrationError('Exit Codex in the terminal with Ctrl+C before closing the island.')
        self.closed.set()
        if self.process:
            self.control('close')
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                # No live terminal child; only the owned rendering helper remains.
                self.process.terminate()
                self.process.wait(timeout=2)
            self.process.stdin.close()
            self.process.stdout.close()
            self.process = None
        if self.socket:
            self.socket.close()
            self.socket = None
        if self.directory:
            self.directory.cleanup()
            self.directory = None
