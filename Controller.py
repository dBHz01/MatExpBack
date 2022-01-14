from ctypes import pointer
from operator import index
from pydoc import cli
from re import T
import websocket
from websocket import WebSocketApp
import time
import json
import argparse
import numpy as np
import pyautogui
try:
    import thread
except ImportError:
    import _thread as thread
from matsense.uclient import CMD, Uclient
from matsense.process import Processor, CursorController, PressureSelector
from matsense.tools import make_action, parse_ip_port
from PrepareConfig import prepare_config
from TaskHandler import TaskHandler
from StatusHandler import StatusHandler
from tools.CalFps import CalFps


# websocket 参考 https://blog.csdn.net/tz_zs/article/details/119363470

def calibrate_center(generator, times):
    # should not be max, but the most center column
    # attention should not press all the column
    ret_col = 0
    for _ in range(times):
        __ = input("begin calibration, please press and then press enter button")
        data = next(generator)
        sequence_length = len(data)
        sum_data = []
        for i in range(sequence_length):
            # sum_data.append(sum(data[i]))
            if (sum(data[i]) > 2):
                sum_data.append(1)
            else:
                sum_data.append(0)
        # calculate the longest 1 sequence
        tmp_pointer = 0
        pointer_gap = 0
        center_col = 0
        while (tmp_pointer < sequence_length):
            if (sum_data[tmp_pointer] == 1):
                start_pointer = tmp_pointer
                while(sum_data[tmp_pointer % sequence_length] == 1 and tmp_pointer < 2 * sequence_length):
                    tmp_pointer += 1
                if (tmp_pointer - start_pointer > pointer_gap):
                    pointer_gap = tmp_pointer - start_pointer
                    center_col = round((tmp_pointer + start_pointer) / 2) % sequence_length
            else:
                tmp_pointer += 1
        ret_col += center_col
        # print(sum_data)

        # use the max col as center

        # max_col = 0
        # max_val = 0
        # for i in range(len(sum_data)):
        #     if (sum_data[i] > max_val):
        #         max_val = sum_data[i]
        #         max_col = i
        # ret_col += max_col

        print("center_col ", center_col)
    print("last_center_col ", round(ret_col / times))
    return round(ret_col / times)


TEST_PACKET = {
    "type": 0,
    "sensor_thumb": True,
    "sensor_index": True,
    "mode": 0,
    "mode_change_ratio": 50,
}

N = 16
ZLIM = 3
FPS = 194
TH = 0.15
UDP = False

class Controller(object):
    def __init__(self, thumb_client, index_client, task_handler, thumb_status, index_status):
        super(Controller, self).__init__()
        self.url = "ws://127.0.0.1:7778"
        self.ws = None
        self.mode = 1  # 0 for remote-control, 1 for mouse
        self.sensor_thumb = False
        self.sensor_index = False
        self.mode_change_ratio = 0
        self.thumb_data = [[0] * 6] * 24
        self.index_data = [[0] * 6] * 24
        self.thumb_client = thumb_client
        self.index_client = index_client
        self.task_handler = task_handler
        self.thumb_status = thumb_status
        self.index_status = index_status
        self.cal_fps = CalFps(1)
        self.click_state = 0 # state machine


    def gen_panel_message(self):
        packet = {"type": 0}
        packet["sensor_thumb"] = self.sensor_thumb
        packet["sensor_index"] = self.sensor_index
        packet["mode"] = self.mode
        packet["mode_change_ratio"] = self.mode_change_ratio
        self.mode_change_ratio += 10
        return json.dumps(packet)

    def send_panel_message(self):
        while True:
            time.sleep(5)
            input_msg = self.gen_panel_message()
            self.send_message(input_msg)

    def send_message(self, message):
        self.ws.send(message)
    
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
    
    def update_finger_data(self):
        self.thumb_data = next(self.thumb_client.gen())
        self.index_data = next(self.index_client.gen())

    def update_finger_status(self):
        self.thumb_status.update_data(self.thumb_data)
        self.index_status.update_data(self.index_data)

    def handle_task(self):
        self.task_handler.update_thumb_data(self.thumb_data)
        self.task_handler.run_task(self.mode)

    def handle_click(self):
        both_click_break_time = 0.1
        if (self.thumb_status.click and self.index_status.click):
            print("both click")
            self.click_state = 0
            return
        if (self.click_state == 0):
            if (self.thumb_status.click):
                if (not self.index_status.press):
                    print("thumb click 1", time.time())
                else:
                    self.click_state = 1
            if (self.index_status.click):
                if (not self.thumb_status.press):
                    print("index click 1", time.time())
                else:
                    self.click_state = 2
        elif (self.click_state == 1):
            # wait for index click
            if (time.time() - self.thumb_status.last_click_time >= both_click_break_time):
                print("thumb click 2", time.time())
                self.click_state = 0
            else:
                if (self.index_status.click):
                    print("both click")
                    self.click_state = 0
        elif (self.click_state == 2):
            # wait for thumb click
            if (time.time() - self.index_status.last_click_time >= both_click_break_time):
                print("index click 2", time.time())
                self.click_state = 0
            else:
                if (self.thumb_status.click):
                    print("both click")
                    self.click_state = 0
            
    def update_mode(self):
        if (self.thumb_status.check_long_press() and self.index_status.check_long_press()):
            # self.mode = 1 - self.mode # change to the other mode
            self.thumb_status.trigger_long_press()
            self.index_status.trigger_long_press()
            print("trigger long press")

    def main_loop(self):
        while True:
            self.cal_fps.run()
            self.update_finger_data()
            self.update_finger_status()
            self.handle_task()
            self.handle_click()
            self.update_mode()
            # time.sleep(0.002)

    def on_open(self, ws):
        print("####### on_open #######")
        self.ws.send(json.dumps({"identity": "backend", "room_id": 0}))
        thread.start_new_thread(self.send_panel_message, ())
        thread.start_new_thread(self.main_loop, ())

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
        parse_ip_port(config['connection']['thumb_client_address']),
        parse_ip_port(config['connection']['thumb_address']),
        udp=config['connection']['udp'],
        n=config['sensor']['shape']
    ) as thumb_client:
        with Uclient(
            parse_ip_port(config['connection']['index_client_address']),
            parse_ip_port(config['connection']['index_address']),
            udp=config['connection']['udp'],
            n=config['sensor']['shape']
        ) as index_client:
            center_col = calibrate_center(thumb_client.gen(), 5)
            task_handler = TaskHandler(center_col)
            thumb_status = StatusHandler(press_pressure=2)
            index_status = StatusHandler(press_pressure=0.5)
            Controller(thumb_client, index_client, task_handler, thumb_status, index_status).start()

