"""Local integrations; no GUI, shell execution, or credential-file access."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import signal
import subprocess


class IntegrationError(RuntimeError):
    pass


def run(args: list[str], timeout: int = 8) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise IntegrationError(f"{args[0]} is not installed.") from exc
    except subprocess.TimeoutExpired as exc:
        raise IntegrationError(f"{args[0]} did not respond in time.") from exc
    if result.returncode:
        raise IntegrationError(f"{args[0]} failed. Check that it is available and you have access.")
    return result.stdout


def notify(status: str, folder: str):
    titles = {"completed": "Task completed", "failed": "Task failed", "interrupted": "Task interrupted"}
    try:
        run(["notify-send", "--app-name=Floatty", "--", "Floatty · " + titles.get(status, status),
             Path(folder).name or folder], timeout=3)
    except IntegrationError:
        return False
    return True


@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    uid: int
    started: str
    parent: int
    name: str


def identity(pid: int) -> ProcessIdentity:
    path = Path("/proc") / str(pid)
    # The comm field may contain spaces and parentheses.
    stat = (path / "stat").read_text()
    end = stat.rfind(")")
    fields = stat[end + 2:].split()
    return ProcessIdentity(pid, path.stat().st_uid, fields[19], int(fields[1]), stat[stat.find("(") + 1:end])


def protected_pids(codex_pid=None):
    protected = {1, os.getpid()}
    current = os.getpid()
    while current > 1:
        try:
            current = identity(current).parent
        except (OSError, ValueError, IndexError):
            break
        if current in protected:
            break
        protected.add(current)
    if codex_pid:
        protected.add(codex_pid)
        descendants = {codex_pid, os.getpid()}
        # Include descendants, even ones that created their own process group.
        parents = {}
        for path in Path("/proc").iterdir():
            if path.name.isdigit():
                try:
                    item = identity(int(path.name))
                    parents[item.pid] = item.parent
                except (OSError, ValueError, IndexError):
                    pass
        changed = True
        while changed:
            extra = {pid for pid, parent in parents.items() if parent in descendants}
            changed = bool(extra - descendants)
            descendants.update(extra)
        protected.update(descendants)
    return protected


@dataclass(frozen=True)
class Listener:
    protocol: str
    address: str
    process: ProcessIdentity | None

    @property
    def label(self):
        owner = f"{self.process.name} · PID {self.process.pid}" if self.process else "owner unavailable"
        return f"{self.protocol.upper()}  {self.address}   {owner}"


def parse_listeners(output: str, lookup=identity):
    rows = []
    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 6 or fields[0] not in {"tcp", "udp"}:
            continue
        pids = set(map(int, re.findall(r"pid=(\d+)", line)))
        if not pids:
            rows.append(Listener(fields[0], fields[4], None))
        for pid in sorted(pids):
            try:
                process = lookup(pid)
            except (OSError, ValueError, IndexError):
                process = None
            rows.append(Listener(fields[0], fields[4], process))
    return rows


def listeners():
    return parse_listeners(run(["ss", "-H", "-lntup"]))


def stop_listener(row: Listener, codex_pid=None):
    item = row.process
    if item is None or item.pid in protected_pids(codex_pid) or item.uid != os.getuid():
        raise IntegrationError("This process cannot be stopped from the island.")
    if not hasattr(os, "pidfd_open") or not hasattr(signal, "pidfd_send_signal"):
        raise IntegrationError("Safe process stopping requires Linux pidfd support.")
    try:
        fd = os.pidfd_open(item.pid)
        try:
            if identity(item.pid) != item or row not in listeners():
                raise IntegrationError("The listener changed. Refresh and select it again.")
            signal.pidfd_send_signal(fd, signal.SIGTERM)
        finally:
            os.close(fd)
    except OSError as exc:
        raise IntegrationError("Process exited or permission was denied. Refresh the list.") from exc
    return "Termination requested; a supervisor may restart this service."


@dataclass(frozen=True)
class Container:
    identifier: str
    name: str
    ports: str

    @property
    def label(self):
        return f"{self.name}   {self.ports or 'no published ports'}"


class Docker:
    def __init__(self):
        rootless = Path(f"/run/user/{os.getuid()}/docker.sock")
        self.socket = rootless if rootless.exists() else Path("/var/run/docker.sock")

    def command(self, *args, timeout=8):
        return run(["docker", "--host", f"unix://{self.socket}", *args], timeout)

    def containers(self):
        output = self.command("ps", "--no-trunc", "--format", "{{json .}}")
        result = []
        for line in output.splitlines():
            data = json.loads(line)
            identifier = data["ID"]
            if re.fullmatch(r"[0-9a-f]{64}", identifier):
                result.append(Container(identifier, data["Names"], data.get("Ports", "")))
        return result

    def stop(self, item: Container):
        if item not in self.containers():
            raise IntegrationError("Container changed or already stopped. Refresh the list.")
        self.command("stop", "--time", "10", item.identifier, timeout=20)
        return f"Stopped {item.name}."
