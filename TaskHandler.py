import time
import json
from tkinter.messagebox import NO
import pyautogui
import numpy as np
from matsense.process import Processor


class TaskHandler(object):
    def __init__(self, center_col, trackpoint = True, interp = [6, 6], col_num = 16):
        self.thumb_data = [[0] * interp[1]] * interp[0]
        self.trackpoint = trackpoint
        self.interp = interp
        self.center_col = center_col
        self.col_num = col_num
        self.mouse_processor = Processor(self.interp)
        self.mouse_processor.print_info()

    def update_thumb_data(self, thumb_data):
        self.thumb_data = thumb_data
    
    def remote_control(self):
        # constants for remote-control
        RIGHT_THRESHOLD = 1.2
        LEFT_THRESHOLD = 1.8
        UP_THRESHOLD = 2
        DOWN_THRESHOLD = 2
        last_press = False
        last_direction = "right"
        last_timer = 0
        dtime = 0
        peak = 1.5
        last_send_time = 0
        SEND_INTERVAL = 0.2
        max_row = 0
        for i in range(len(self.thumb_data)):
            sum_row = self.thumb_data[i]
            if sum_row > max_row:
                max_row = sum_row
                max_id = i
        if max_id < 5 or max_id > 22:
            if max_row > peak / 3 and max_row > DOWN_THRESHOLD:
                if max_row > peak:
                    peak = max_row
                # print(max_row)
                # print(max_id)
                last_direction = "down"
                last_press = True
                dtime = int((time.time() - last_timer) * 1000)
                if dtime > 500:
                    print((dtime - 500) / 1000)
                return
        elif max_id <= 9:
            if max_row > peak / 3 and max_row > RIGHT_THRESHOLD:
                # print(peak)
                if max_row > peak:
                    peak = max_row
                # print(max_row)
                # print(max_id)
                last_direction = "right"
                last_press = True
                dtime = int((time.time() - last_timer) * 1000)
                # if dtime > 500:
                # 	print((dtime - 500) / 1000)
                return
        elif max_id <= 16:
            if max_row > peak / 3 and max_row > UP_THRESHOLD:
                if max_row > peak:
                    peak = max_row
                # print(max_row)
                # print(max_id)
                last_direction = "up"
                last_press = True
                dtime = int((time.time() - last_timer) * 1000)
                # if dtime > 500:
                # 	print((dtime - 500) / 1000)
                return
        else:
            if max_row > peak / 3 and max_row > LEFT_THRESHOLD:
                if max_row > peak:
                    peak = max_row
                # print(max_row)
                # print(max_id)
                last_direction = "left"
                last_press = True
                dtime = int((time.time() - last_timer) * 1000)
                # if dtime > 500:
                # 	print((dtime - 500) / 1000)
                return
        last_timer = time.time()
        if last_press:
            last_press = False
            if dtime < 500 and 100 < dtime:
                if time.time() - last_send_time > SEND_INTERVAL:
                    print(last_direction)
                    # print(max_row)
                    # my_remote_handle.sendButton(last_direction)
                    self.ws.send(json.dumps(
                        {"type": 3, "command": last_direction}))
                    last_send_time = time.time()
            elif dtime > 1000:
                if time.time() - last_send_time > SEND_INTERVAL:
                    # my_remote_handle.sendButton('click')
                    self.ws.send(json.dumps(
                        {"type": 3, "command": "click"}))
                    print("click")
                    last_send_time = time.time()
        dtime = 0
        if (max_row < 2):
            peak = 1.5

    def move_mouse(self):
        my_generator = mask_thumb_data([[0, 0], [self.center_col, self.col_num]], self.thumb_data)
        my_generator = self.mouse_processor.gen_points(my_generator)
        row, col, val = next(my_generator)
        x, y = point_to_movement(row, col, val)

        # print the point and pressure
        # check_times += 1
        # if (check_times >= 60):
        #     print(x, y, val)
        #     check_times = 0
        

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

def pressure_function(val):
    if (val < 1):
        return val
    elif (val > 6):
        return 36 + 0.5 * val
    else:
        return val ** 2

def distance_function(dist):
    if (dist <= 0.2):
        return dist
    elif (dist <= 0.3):
        return dist / 0.3
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
    x = direction[0] * pressure_function(val) * distance_function(distance_to_center) * 1.5
    y = direction[1] * pressure_function(val) * distance_function(distance_to_center)
    return x, y