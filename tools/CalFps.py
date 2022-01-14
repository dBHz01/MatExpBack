import time

class CalFps():
    def __init__(self, sleep_time):
        self.cnt = 0
        self.sleep_time = sleep_time
        self.start_time = time.time()
        self.last_time = time.time()

    def run(self):
        if (self.last_time - self.start_time >= self.sleep_time):
            print("fps: ", 1 / (time.time() - self.last_time))
            self.start_time = time.time()
        self.last_time = time.time()