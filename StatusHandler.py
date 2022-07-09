import time
from tools.CallAfterTimes import CallAfterTimes

class StatusHandler():
    def __init__(self, interp = [12, 4], min_long_press_time = 1, press_pressure = 45, click_break_time = 0.5):
        self.data = [[0] * interp[1]] * interp[0]
        self.press = False
        self.long_press = False # set True once after release the long press and not triggered
        self.click = False
        self.double_click = False
        self.long_press_time = 0
        self.long_press_triggered = False
        self.min_long_press_time = min_long_press_time
        self.start_press_time = 0
        self.press_pressure = press_pressure
        # self.c = CallAfterTimes(self.print_status, 60)
        self.click_break_time = click_break_time
        self.last_click_time = 0
        self.last_double_click_time = 0
        self.max_click_pressure = 0
        self.min_click_pressure = 1000
        self.click_up_ratio = 0.8 # under ratio * max_click_pressure trigger a click
        self.click_down_ratio = 1.1 # over ratio * min_click_pressure, begin a new round of click
        self.click_state = 0 # 0 for up and 1 for down

    def update_data(self, data):
        self.data = data
        self.update_press()
        self.update_click()
        self.update_double_click()
        self.update_last_click_time()
        self.update_last_double_click_time()
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
            if (self.long_press_time < self.click_break_time and self.long_press_time > 0.001):
                self.click = True

        # if (self.press):
        #     cur_pressure = max([sum(j) for j in self.data])
        #     if (self.click_state == 0):
        #         self.max_click_pressure = max(self.max_click_pressure, cur_pressure)
        #         if (cur_pressure < self.click_up_ratio * self.max_click_pressure):
        #             self.click = True
        #             self.click_state = 1
        #             print("max_pressure", self.max_click_pressure)
        #             self.min_click_pressure = 1000
        #     elif (self.click_state == 1):
        #         self.min_click_pressure = min(self.min_click_pressure, cur_pressure)
        #         if (cur_pressure > self.click_down_ratio * self.min_click_pressure):
        #             self.click_state = 0
        #             self.max_click_pressure = 0
        #             print("min_pressure", self.min_click_pressure)
        # else:
        #     self.click_state = 0
        #     self.min_click_pressure = 1000
        #     self.max_click_pressure = 0


    def update_double_click(self):
        double_click_break_time = 0.5
        if (self.double_click == True):
            self.double_click = False
            return
        if (self.click):
            # print(time.time() - self.last_click_time)
            if (time.time() - self.last_click_time < double_click_break_time):
                self.double_click = True
                # print("double click")

    def update_last_click_time(self):
        if (self.click):
            self.last_click_time = time.time()

    def update_last_double_click_time(self):
        if (self.double_click):
            self.last_double_click_time = time.time()
    
    def update_long_press(self):
        if (self.long_press == True):
            self.long_press = False
        if (self.press):
            if (self.start_press_time == 0):
                self.start_press_time = time.time()
            else:
                self.long_press_time = time.time() - self.start_press_time
                if (self.long_press_time >= 1 and not self.long_press_triggered):
                    self.long_press = True
        else:
            self.start_press_time = 0
            self.long_press_time = 0
            

    def check_long_press(self):
        return self.long_press_time > self.min_long_press_time and not self.long_press_triggered

    def trigger_long_press(self):
        self.long_press_triggered = True

    def print_status(self):
        print("press ", self.press)
        # print("long press time ", self.long_press_time, " s")
        # print("long press triggered ", self.long_press_triggered)
        print("sum ", max([sum(j) for j in self.data]))
        print("click ", self.click)