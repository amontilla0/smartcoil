import os
import sys
from queue import Queue
from threading import Thread
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from smartcoil.server.Manager import ServerManager
from smartcoil.utils.utils import Message

iq = Queue()
oq = Queue()
srv = ServerManager(iq, oq);

def run_server():
    srv.run()

def run_server_thread():
    th = Thread(target=run_server, name='AlexaRequestsServer')
    th.daemon = True
    th.start()

run_server_thread()

while True:
    print('waiting for next message..')
    msg = iq.get()
    type = msg.type
    action = msg.action
    info = msg.params

    if not (type == 'SRVMSG' and action == 'SCOIL_STATE'):
        print('*LISTENING MOCK*')
        continue

    state = 'COOL'
    speed = 3
    cur_temp = 100
    usr_temp = 69
    info = {'state': state, 'speed': speed, 'cur_temp': cur_temp, 'usr_temp': usr_temp}
    oq.put(Message('APPMSG', 'SCOIL_STATE-R', info))
