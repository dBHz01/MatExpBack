import websocket
from websocket import WebSocketApp
import time
import json
import argparse
import numpy as np
try:
    import thread
except ImportError:
    import _thread as thread
from matsense.uclient import CMD, Uclient
from matsense.process import Processor, CursorController, PressureSelector
from matsense.tools import make_action
from PrepareConfig import prepare_config


# 参考 https://blog.csdn.net/tz_zs/article/details/119363470

def mask_generator(mask, input_generator):
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
    for data in input_generator:
        try:
            data_shape = np.shape(data)
            center_row, row_num, center_col, col_num = mask[0][0], mask[0][1], mask[1][0], mask[1][1]
            if (row_num >= data_shape[0] or col_num >= data_shape[1] or ((row_num == 0) and (col_num == 0))):
                yield data
            row_range = [i % data_shape[0] for i in range(center_row - int(row_num / 2), center_row + row_num - int(row_num / 2))]
            col_range = [i % data_shape[1] for i in range(center_col - int(col_num / 2), center_col + col_num - int(col_num / 2))]
            if (row_num == 0):
                yield data[:, col_range]
            elif (col_num == 0):
                yield data[row_range, :]
            else:
                yield data[row_range, col_range]
        except GeneratorExit:
            return
        except:
            yield data


TEST_PACKET = {
    "type": 0,
    "sensor_thumb": True,
    "sensor_index": True,
    "mode": 0,
    "mode_change_ratio": 50,
}

# constants for remote-control
N = 16
ZLIM = 3
FPS = 194
TH = 0.15
UDP = False
RIGHT_THRESHOLD = 1.2
LEFT_THRESHOLD = 1.8
UP_THRESHOLD = 2
DOWN_THRESHOLD = 2


class Controller(object):
    def __init__(self):
        super(Controller, self).__init__()
        self.url = "ws://127.0.0.1:7778"
        self.ws = None
        self.mode = 1  # 0 for remote-control, 1 for mouse
        self.sensor_thumb = False
        self.sensor_index = False
        self.mode_change_ratio = 0

    def get_input(self):
        packet = {"type": 0}
        packet["sensor_thumb"] = self.sensor_thumb
        packet["sensor_index"] = self.sensor_index
        packet["mode"] = self.mode
        packet["mode_change_ratio"] = self.mode_change_ratio
        self.mode_change_ratio += 10
        return json.dumps(packet)

    def on_message(self, ws, message):
        print("####### on_message #######")
        try:
            message_dict = json.loads(message)
            if ("type" in message_dict.keys()):
                if (message_dict["type"] == 2):
                    self.mode = message_dict["change_mode"]
        except:
            print(message)
        print("message：%s" % message)

    def on_error(self, ws, error):
        print("####### on_error #######")
        print("error：%s" % error)

    def on_close(self, ws, close_status_code, close_msg):
        print("####### on_close #######")

    def on_open(self, ws):
        print("####### on_open #######")
        self.ws.send(json.dumps({"identity": "backend", "room_id": 0}))
        thread.start_new_thread(self.send_panel_message, ())
        thread.start_new_thread(self.send_task_message, ())

    def send_panel_message(self, *args):
        while True:
            time.sleep(5)
            input_msg = self.get_input()
            if input_msg == "close":
                self.ws.close()  # 关闭
                print("thread terminating...")
                break
            else:
                self.ws.send(input_msg)

    def send_control_info(self):
        last_press = False
        last_direction = "right"
        last_timer = 0
        dtime = 0
        peak = 1.5
        last_send_time = 0
        SEND_INTERVAL = 0.2
        while True:
            time.sleep(0.01)
            my_client.send_cmd(1)
            max_row = 0
            for i in range(int(len(my_client.recv_frame()[0]) / 6)):
                sum_row = 0
                for j in range(6):
                    sum_row += my_client.recv_frame()[0][i * 6 + j]
                if sum_row > max_row:
                    max_row = sum_row
                    max_id = i
            # print(max_row)
            # print(max_id)
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
                    continue
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
                    continue
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
                    continue
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
                    continue
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
        ratioX = 400
        ratioY = 600
        if (config['pointing']['trackpoint']):
            ratioX = 1/0.5334880856434193
            ratioY = 1/0.4088509411708816
        my_processor = Processor(
            config['process']['interp'], threshold=config['process']['threshold'])
        my_cursor = CursorController(ratioX=ratioX, ratioY=ratioY,
                                     mapcoor=config['pointing']['mapcoor'], alpha=config['pointing']['alpha'],
                                     trackpoint=config['pointing']['trackpoint'])
        my_processor.print_info()
        my_cursor.print_info()
        my_generator = mask_generator([[23, 6], [0, 0]], my_client.gen())
        my_generator = my_processor.gen_points(my_generator)
        tmp = 0
        for row, col, val in my_generator:
            tmp += 1
            if (tmp == 300):
                print(row, col, val)
                tmp = 0

    def send_task_message(self, *args):
        if (self.mode == 0):
            self.send_control_info()
        else:
            self.move_mouse()

    def start(self):
        # websocket.enableTrace(True)  # 开启运行状态追踪。debug 的时候最好打开他，便于追踪定位问题。

        self.ws = WebSocketApp(url=self.url,
                               on_open=self.on_open,
                               on_message=self.on_message,
                               on_error=self.on_error,
                               on_close=self.on_close)

        self.ws.run_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--server_address', dest='server_address',
                        action=make_action('store'), help="specify server socket address")
    parser.add_argument('--client_address', dest='client_address',
                        action=make_action('store'), help="specify client socket address")
    parser.add_argument('-u', '--udp', dest='udp',
                        action=make_action('store_true'), default=UDP, help="use UDP protocol")
    parser.add_argument('-r', '--raw', dest='raw',
                        action=make_action('store_true'), default=False, help="plot raw data")
    parser.add_argument('-n', dest='n', action=make_action('store'),
                        default=[N], type=int, nargs='+', help="specify sensor shape")
    parser.add_argument('--interp', dest='interp', action=make_action('store'),
                        default=None, type=int, nargs='+', help="interpolated shape")
    parser.add_argument('--noblob', dest='noblob', action=make_action(
        'store_true'), default=False, help="do not filter out blob")
    parser.add_argument('--th', dest='threshold', action=make_action('store'),
                        default=TH, type=float, help="blob filter threshold")
    parser.add_argument('-i', '--interactive', dest='interactive',
                        action=make_action('store_true'), default=False, help="interactive mode")
    parser.add_argument('-z', '--zlim', dest='zlim', action=make_action('store'),
                        default=ZLIM, type=float, help="z-axis limit")
    parser.add_argument('-f', dest='fps', action=make_action('store'),
                        default=FPS, type=int, help="frames per second")
    parser.add_argument('-m', '--matplot', dest='matplot', action=make_action(
        'store_true'), default=False, help="use mathplotlib to plot")
    parser.add_argument('--config', dest='config', action=make_action('store'),
                        default=None, help="specify configuration file")
    args = parser.parse_args()
    config = prepare_config(args)
    with Uclient(
        config['connection']['client_address'],
        config['connection']['server_address'],
        udp=config['connection']['udp'],
        n=config['sensor']['shape']
    ) as my_client:
        Controller().start()
