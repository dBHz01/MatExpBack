import time
import pyautogui
import numpy as np
from matsense.process import Processor
from WebClient import CursorClient, IP, PORT

class TaskHandler(object):
    def __init__(self, center_col, trackpoint = True, interp = [32, 4], col_num = 16):
        self.my_remote_handle = CursorClient(IP, PORT)
        self.thumb_data = np.zeros(interp)
        self.trackpoint = trackpoint
        self.interp = interp
        self.center_col = center_col
        self.col_num = col_num
        self.mouse_processor = Processor(self.interp)
        self.mouse_processor.print_info()
        self.check_times = 0
        self.left_range = []
        self.right_range = []
        self.up_range = []
        self.down_range = []
        self.dtime = 0
        self.peak = 1.5
        self.last_press = False
        self.last_direction = "right"
        self.last_timer = 0
        self.last_send_time = 0

    def update_control_value(self, center_col):
        data_shape = self.thumb_data.shape
        self.right_range = [i % data_shape[0] for i in range(center_col - 4, center_col + 4)]
        self.down_range = [i % data_shape[0] for i in range(center_col + 4, center_col + 12)]
        self.left_range = [i % data_shape[0] for i in range(center_col + 12, center_col + 20)]
        self.up_range = [i % data_shape[0] for i in range(center_col + 20, center_col + 28)]

    def update_thumb_data(self, thumb_data):
        self.thumb_data = thumb_data
    
    def remote_control(self):
        # constants for remote-control
        RIGHT_THRESHOLD = 1.2
        LEFT_THRESHOLD = 1.8
        UP_THRESHOLD = 2
        DOWN_THRESHOLD = 2
        SEND_INTERVAL = 0.2
        from Controller import calculate_center_col
        max_id, max_row = calculate_center_col(self.thumb_data, "max")
        if max_id in self.down_range:
            if max_row > self.peak / 3 and max_row > DOWN_THRESHOLD:
                if max_row > self.peak:
                    self.peak = max_row
                self.last_direction = "down"
                self.last_press = True
                self.dtime = int((time.time() - self.last_timer) * 1000)
                # if self.dtime > 500:
                #     print((self.dtime - 500) / 1000)
                return
        elif max_id in self.right_range:
            if max_row > self.peak / 3 and max_row > RIGHT_THRESHOLD:
                if max_row > self.peak:
                    self.peak = max_row
                self.last_direction = "right"
                self.last_press = True
                self.dtime = int((time.time() - self.last_timer) * 1000)
                # if self.dtime > 500:
                # 	print((self.dtime - 500) / 1000)
                return
        elif max_id in self.up_range:
            if max_row > self.peak / 3 and max_row > UP_THRESHOLD:
                if max_row > self.peak:
                    self.peak = max_row
                self.last_direction = "up"
                self.last_press = True
                self.dtime = int((time.time() - self.last_timer) * 1000)
                # if self.dtime > 500:
                # 	print((self.dtime - 500) / 1000)
                return
        else:
            if max_row > self.peak / 3 and max_row > LEFT_THRESHOLD:
                if max_row > self.peak:
                    self.peak = max_row
                self.last_direction = "left"
                self.last_press = True
                self.dtime = int((time.time() - self.last_timer) * 1000)
                # if self.dtime > 500:
                # 	print((self.dtime - 500) / 1000)
                return
        self.last_timer = time.time()
        if self.last_press:
            self.last_press = False
            print(self.dtime)
            if self.dtime < 1000 and 100 < self.dtime:
                if time.time() - self.last_send_time > SEND_INTERVAL:
                    self.my_remote_handle.sendButton(self.last_direction)
                    # self.ws.send(json.dumps(
                    #     {"type": 3, "command": self.last_direction}))
                    print(max_row, self.last_direction)
                    self.last_send_time = time.time()
            elif self.dtime > 1000:
                if time.time() - self.last_send_time > SEND_INTERVAL:
                    # self.my_remote_handle.sendButton('click')
                    # self.ws.send(json.dumps(
                    #     {"type": 3, "command": "click"}))
                    # print(max_row, max_id, self.last_direction)
                    print("click")
                    self.last_send_time = time.time()
        self.dtime = 0
        if (max_row < 2):
            self.peak = 1.5

    def move_mouse(self):
        my_generator = mask_thumb_data([[0, 0], [self.center_col, self.col_num]], self.thumb_data)
        my_generator = self.mouse_processor.gen_points(my_generator)
        row, col, val = next(my_generator)
        x, y = point_to_movement(row, col, val)

        # print the point and pressure
        self.check_times += 1
        if (self.check_times >= 60):
            print(row, col)
            print(x, y, val)
            direction = np.array([row - 0.5, col - 0.5])
            distance_to_center = np.linalg.norm(direction)
            print("dist", distance_to_center)
            self.check_times = 0
        

        if not self.trackpoint:
            pyautogui.moveTo(x, y, _pause=False)
        else:
            pyautogui.move(x, y, _pause=False)
        time.sleep(0.001)  # about > 194 fps

    def run_task(self, mode):
        if (mode == 0):
            self.remote_control()
        elif (mode == 1):
            self.move_mouse()


def mask_thumb_data(mask, data):
    """generate a data generator which gives the masked data

    Args:
        mask ([[int, int], [int, int]]): [[center_row, row_num], [center_col, col_num]], 
            meaning that the masked data is from range(center_row - int(row_num / 2), center_row + row_num - int(row_num / 2)) in row
                                            and  range(center_col - int(col_num / 2), center_col + col_num - int(col_num / 2)) in col
            # attention the number of row or col should not be larger than its original number
              but the label is modified
              if row_num or col_num is 0, it continues with the raw row / col
        input_data (numpy.ndarray): a frame data

    Yields:
        masked_data (numpy.ndarray): a frame of masked data
    """
    try:
        data_shape = np.shape(data)
        center_row, row_num, center_col, col_num = mask[0][0], mask[0][1], mask[1][0], mask[1][1]
        if (col_num >= data_shape[0] or row_num >= data_shape[1] or ((col_num == 0) and (row_num == 0))):
            yield data
        row_range = [i % data_shape[1] for i in range(center_row - int(row_num / 2), center_row + row_num - int(row_num / 2))]
        col_range = [i % data_shape[0] for i in range(center_col - int(col_num / 2), center_col + col_num - int(col_num / 2))]
        if (row_num == 0):
            yield data[col_range, :]
        elif (col_num == 0):
            yield data[:, row_range]
        else:
            yield data[col_range, row_range]
    except GeneratorExit:
        return
    except:
        yield data

def sigmoid(x):
    return 1/(1+np.exp(-x))

def pressure_function(val):
    ## old using quadratic funciton
    # if (val < 1):
    #     return val
    # elif (val > 5):
    #     return 22.5 + 0.5 * val
    # else:
    #     return -1.5 * ((val - 5) ** 2) + 25
    #     # return val

    ## new using sigmoid function
    if (val < 6):
        return sigmoid(val - 5) * 40
    elif (val < 10):
        return sigmoid(1) * 40 + (val - 6)
    else:
        return sigmoid(1) * 40 + 4

def distance_function(dist):
    if (dist <= 0.2):
        return 0.5 * dist
    elif (dist <= 0.4):
        return 4.5 * dist - 0.8
    else:
        return 1

def point_to_movement(row, col, val):
    """transform a pressure point in (0,1) (0,1) square to actual move point

    Args:
        row (float): 0 to 1
        col (float): 0 to 1
        val (float): pressure value


    Returns:
        x, y value of movement
    """
    direction = np.array([row - 0.5, col - 0.5])
    distance_to_center = np.linalg.norm(direction)
    direction = direction / distance_to_center
    x = direction[0] * pressure_function(val) * distance_function(distance_to_center) * -1 * 3
    y = direction[1] * pressure_function(val) * distance_function(distance_to_center)
    return x, y