import time
from tools.CallAfterTimes import CallAfterTimes

class StatusHandler():
    def __init__(self, interp = [6, 6], min_long_press_time = 1, press_pressure = 2, click_break_time = 0.5):
        self.data = [[0] * interp[1]] * interp[0]
        self.press = False
        self.click = False
        self.long_press_time = 0
        self.long_press_triggered = False
        self.min_long_press_time = min_long_press_time
        self.start_press_time = 0
        self.press_pressure = press_pressure
        # self.c = CallAfterTimes(self.print_status, 60)
        self.click_break_time = click_break_time
        self.last_click_time = 0

    def update_data(self, data):
        self.data = data
        self.update_press()
        self.update_click()
        self.update_long_press()
        # self.c.run()

    def update_press(self):
        for i in self.data:
            if sum(i) > self.press_pressure:
                self.press = True
                return
        # not press
        self.press = False
        self.long_press_triggered = False

    def update_click(self):
        if (self.click):
            # print("click")
            self.click = False
        
        if (not self.press):
            if (self.long_press_time < self.click_break_time and self.long_press_time > 0.05):
                self.last_click_time = time.time()
                self.click = True
    
    def update_long_press(self):
        if (self.press):
            if (self.start_press_time == 0):
                self.start_press_time = time.time()
            else:
                self.long_press_time = time.time() - self.start_press_time
        else:
            self.start_press_time = 0
            self.long_press_time = 0

    

    def check_long_press(self):
        return self.long_press_time > self.min_long_press_time and not self.long_press_triggered

    def trigger_long_press(self):
        self.long_press_triggered = True

    def print_status(self):
        print("press ", self.press)
        print("long press time ", self.long_press_time, " s")
        print("long press triggered ", self.long_press_triggered)
        print("sum ", max([sum(j) for j in self.data]))
        # print("click ", self.click)