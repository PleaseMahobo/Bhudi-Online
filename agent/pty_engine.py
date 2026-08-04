import subprocess
import threading
import queue
import sys


class PTYSession:
    def __init__(self, session_id):
        self.session_id = session_id
        self.process = None
        self.output_queue = queue.Queue()
        self.alive = False

    def start(self):
        self.alive = True

        # Windows-safe shell selection
        shell = "powershell.exe" if sys.platform == "win32" else "/bin/bash"

        self.process = subprocess.Popen(
            shell,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
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

    def read_all(self):
        output = []
        while not self.output_queue.empty():
            output.append(self.output_queue.get())
        return output

    def stop(self):
        self.alive = False
        if self.process:
            self.process.terminate()