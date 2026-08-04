from collections import deque

class CommandQueue:
    def __init__(self):
        self.queue = deque()

    def add(self, command):
        self.queue.append(command)

    def get_next(self):
        if self.queue:
            return self.queue.popleft()
        return None