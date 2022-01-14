class CallAfterTimes():
    def __init__(self, func, times, *args, **kwargs):
        self.func = func
        self.times = times
        self.cnt = 0
        self.args = args
        self.kwargs = kwargs

    def run(self):
        self.cnt += 1
        if (self.cnt >= self.times):
            self.func(*self.args, **self.kwargs)
            self.cnt = 0

def p(data, data1):
    print(data, data1)

if __name__ == "__main__":
    c = CallAfterTimes(p, 3, "hello world", data1 = "0")
    t = 9
    while t > 0:
        t -= 1
        c.run()