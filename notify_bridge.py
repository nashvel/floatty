"""Codex notify hook: forward only completion metadata, never transcript contents."""
import json
import socket
import sys


def forward(address, payload):
    try:
        event = json.loads(payload)
        if event.get('type') != 'agent-turn-complete':
            return False
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as channel:
            channel.settimeout(0.2)
            channel.sendto(b'{"type":"agent-turn-complete"}', address)
        return True
    except (ValueError, OSError, AttributeError):
        return False


if __name__ == '__main__' and len(sys.argv) == 3:
    forward(sys.argv[1], sys.argv[2])
