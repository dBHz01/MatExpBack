from websocket_server import WebsocketServer
import json

PORT = 7778
server = WebsocketServer(port=PORT, host="127.0.0.1")
rooms = {"panel": None, "task": None, "backend": None} # now there is only one room, so room_id is not used

def new_client(client, server):
    server.send_message(client, json.dumps({"code": 200}))
    print(client, " connected")

def client_left(client, server):
    # clear left client
    for key in rooms.keys():
        if (rooms[key] == client):
            rooms[key] = None
    print("Client(%d) disconnected" % client['id'])
    print("now clients ", rooms)
    
def message_received(client, server, message):
    # print(message + " received")
    try:
        message_dict = json.loads(message)
        if ("type" in message_dict.keys()):
            if (message_dict["type"] == 0):
                rooms[message_dict["identity"]] = client
            elif (message_dict["type"] == 1):
                if (rooms["panel"] != None):
                    server.send_message(rooms["panel"], message)
            elif (message_dict["type"] == 2):
                if (rooms["backend"] != None):
                    server.send_message(rooms["backend"], message)
            elif (message_dict["type"] == 3):
                if (rooms["task"] != None):
                    server.send_message(rooms["task"], message)
    except:
        print(message)
    # server.send_message_to_all(message)

if __name__ == "__main__":
    server.set_fn_new_client(new_client)
    server.set_fn_client_left(client_left)
    server.set_fn_message_received(message_received)
    server.run_forever()
