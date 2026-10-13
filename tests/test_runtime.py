from dataclasses import replace
import io
import json
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import runtime


class ServiceTests(unittest.TestCase):
    def test_tcp_udp_ipv6_multiple_owners_and_unknown_owner(self):
        output = '''tcp LISTEN 0 128 [::]:3000 [::]:* users:(("node",pid=42,fd=9),("node",pid=43,fd=9))
udp UNCONN 0 0 127.0.0.1:5353 0.0.0.0:*
tcp LISTEN 0 128 0.0.0.0:8080 0.0.0.0:* users:(("gone",pid=99,fd=9))
'''
        def lookup(pid):
            if pid == 99:
                raise FileNotFoundError()
            return runtime.ProcessIdentity(pid, os.getuid(), '123', 1, 'node')
        rows = runtime.parse_listeners(output, lookup)
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0].address, '[::]:3000')
        self.assertEqual(rows[1].process.pid, 43)
        self.assertIsNone(rows[2].process)
        self.assertIsNone(rows[3].process)

    def test_protection_does_not_block_every_sibling_process(self):
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
        try:
            self.assertNotIn(child.pid, runtime.protected_pids())
            self.assertIn(child.pid, runtime.protected_pids(child.pid))
            self.assertIn(os.getpid(), runtime.protected_pids())
            self.assertIn(os.getppid(), runtime.protected_pids())
        finally:
            child.terminate()
            child.wait()

    def test_pidfd_terminates_only_revalidated_owned_child(self):
        if not hasattr(os, 'pidfd_open') or not hasattr(signal, 'pidfd_send_signal'):
            self.skipTest('Linux pidfd unavailable')
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
        try:
            row = runtime.Listener('tcp', '127.0.0.1:45678', runtime.identity(child.pid))
            with patch('runtime.listeners', return_value=[row]):
                self.assertIn('Termination requested', runtime.stop_listener(row))
            self.assertEqual(child.wait(timeout=3), -signal.SIGTERM)
        finally:
            if child.poll() is None:
                child.terminate()
                child.wait()

    def test_stale_pid_and_disappearing_port_never_signalled(self):
        item = runtime.identity(os.getpid())
        row = runtime.Listener('tcp', '127.0.0.1:3000', item)
        with patch('runtime.protected_pids', return_value=set()), patch('runtime.os.pidfd_open', return_value=7), patch('runtime.os.close'), patch('runtime.signal.pidfd_send_signal') as send:
            with patch('runtime.identity', return_value=replace(item, started='different')):
                with self.assertRaisesRegex(runtime.IntegrationError, 'changed'):
                    runtime.stop_listener(row)
            with patch('runtime.listeners', return_value=[]):
                with self.assertRaisesRegex(runtime.IntegrationError, 'changed'):
                    runtime.stop_listener(row)
            send.assert_not_called()

    def test_other_user_unknown_owner_and_protected_pids_refused(self):
        own = runtime.identity(os.getpid())
        for process in (None, own, replace(own, pid=99999, uid=os.getuid()+1)):
            with self.subTest(process=process), patch('runtime.signal.pidfd_send_signal') as send:
                with self.assertRaisesRegex(runtime.IntegrationError, 'cannot be stopped'):
                    runtime.stop_listener(runtime.Listener('tcp', '*:123', process))
                send.assert_not_called()

    def test_docker_targets_local_socket_and_exact_id(self):
        docker = runtime.Docker()
        identifier = 'a' * 64
        item = runtime.Container(identifier, 'test-app', '3000/tcp')
        output = json.dumps({'ID': identifier, 'Names': item.name, 'Ports': item.ports}) + '\n'
        with patch('runtime.run', return_value=output) as run:
            self.assertEqual(docker.containers(), [item])
            docker.stop(item)
            args = run.call_args.args[0]
            self.assertEqual(args[:2], ['docker', '--host'])
            self.assertTrue(args[2].startswith('unix:///'))
            self.assertEqual(args[-1], identifier)
            self.assertIn('stop', args)

    def test_docker_missing_or_changed_container_is_not_stopped(self):
        docker = runtime.Docker()
        with patch.object(docker, 'containers', return_value=[]), patch.object(docker, 'command') as command:
            with self.assertRaisesRegex(runtime.IntegrationError, 'changed'):
                docker.stop(runtime.Container('a'*64, 'stale', ''))
            command.assert_not_called()

    def test_notifications_preserve_failure_status_and_pass_literal_args(self):
        with patch('runtime.run') as run:
            self.assertTrue(runtime.notify('failed', '/tmp/$(touch nope)'))
            self.assertIn('Task failed', run.call_args.args[0][-2])
            self.assertEqual(run.call_args.args[0][-1], '$(touch nope)')
        with patch('runtime.run', side_effect=runtime.IntegrationError('missing')):
            self.assertFalse(runtime.notify('completed', '/tmp'))


if __name__ == '__main__':
    unittest.main()
