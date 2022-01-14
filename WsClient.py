import json
from websocket import WebSocketApp

class WsClient(object):
    def __init__(self):
        super(WsClient, self).__init__()
        self.url = "ws://127.0.0.1:7778"
        self.ws = None
    
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

    def send_task_message(self, *args):
        if (self.mode == 0): # remote-control mode
            self.send_control_info()
        else: # mouse moving mode
            self.move_mouse()

    def start(self):
        # websocket.enableTrace(True)  # 开启运行状态追踪。debug 的时候最好打开他，便于追踪定位问题。

        self.ws = WebSocketApp(url=self.url,
                               on_open=self.on_open,
                               on_message=self.on_message,
                               on_error=self.on_error,
                               on_close=self.on_close)

        self.ws.run_forever()