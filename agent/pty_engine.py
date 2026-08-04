import subprocess
import threading
import queue
import sys
import os
from typing import Mapping


class PTYSession:
    def __init__(self, session_id, shell_command: str | None = None, cwd: str | None = None, environment: Mapping[str, str] | None = None):
        self.session_id = session_id
        self.shell_command = shell_command
        self.cwd = cwd
        self.environment = dict(environment or {})
        self.process = None
        self.output_queue = queue.Queue()
        self.alive = False

    def start(self):
        self.alive = True

        # Windows-safe shell selection
        shell = self.shell_command or ("powershell.exe" if sys.platform == "win32" else "/bin/bash")
        env = None
        if self.environment:
            env = {**os.environ, **self.environment}

        self.process = subprocess.Popen(
            shell,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=self.cwd,
            env=env,
        )

        threading.Thread(target=self._read_output, daemon=True).start()

    def _read_output(self):
        while self.alive and self.process:
            line = self.process.stdout.readline()
            if line:
                self.output_queue.put(line)

    def send(self, command: str):
        if self.process and self.process.stdin:
            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()

    def write(self, data: str):
        if self.process and self.process.stdin:
            self.process.stdin.write(data)
            self.process.stdin.flush()

    def read_all(self):
        output = []
        while not self.output_queue.empty():
            output.append(self.output_queue.get())
        return output

    def stop(self):
        self.alive = False
        if self.process:
            self.process.terminate()