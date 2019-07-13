from flask import Flask, Response, request
from waitress import serve
import os
from shutil import copyfile
import json
import subprocess
from ..utils import utils

class Endpoint(object):
    def __init__(self, action):
        self.action = action

    def __call__(self, *args):
        answer = self.action()
        self.response = Response(answer, status=200, headers={})
        return self.response

class ServerManager():
    def __init__(self, outqueue = None, inqueue = None):
        self.app = Flask(__name__)
        self.load_endpoints()

        self.inbound_queue = inqueue
        self.outbound_queue = outqueue

        self.tunnel_address = None
        self.tunnel_port = None
        self.acces_token = None
        self.load_tunnel_config()

    ### TUNNEL RELATED METHODS ###
    def load_tunnel_config(self):
        dirname = os.path.dirname(__file__)
        config_path = os.path.join(dirname, '../../assets/config/server_config.json')

        # Verify the server config file exists. If not, copy the template.
        if not os.path.exists(config_path):
            print('initializing config from template. Remember to update with proper values...')
            copyfile(config_path + '_template', config_path)

        with open(config_path, 'r') as f:
            conf = json.load(f)
            self.tunnel_address = conf['tunnel']
            self.tunnel_port = conf['port']
            self.acces_token = conf['token']

    def run_tunnel(self):
        dirname = os.path.dirname(__file__)
        pagekite_path = os.path.join(dirname, 'pagekite.py')

        tunnel = subprocess.Popen(['python2', pagekite_path, str(self.tunnel_port), self.tunnel_address], stdout=subprocess.PIPE)
        print(tunnel)

    def token_is_valid(self, tok):
        return self.acces_token == tok

    ### FLASK RELATED METHODS ###
    def add_endpoint(self, handler=None, endpoint=None, endpoint_name=None):
        endpoint_name = endpoint[1:] if endpoint_name is None else endpoint_name
        self.app.add_url_rule(endpoint, endpoint_name, Endpoint(handler), methods=['POST'])

    def load_endpoints(self):
        self.add_endpoint(self.turn_smartcoil, "/turn_smartcoil")
        self.add_endpoint(self.set_smartcoil_speed, "/set_smartcoil_speed")
        self.add_endpoint(self.set_smartcoil_temperature, "/set_smartcoil_temperature")
        self.add_endpoint(self.get_smartcoil_speed, "/get_smartcoil_speed")
        self.add_endpoint(self.get_smartcoil_temperature, "/get_smartcoil_temperature")


    def access_data_is_valid(self):
        req_data = None

        try:
            req_data = request.get_json()
            token = req_data['token']
            if not self.token_is_valid(token):
                print('INVALID TOKEN!')
                return (False, None, '{"error": "invalid token"}')
        except:
            print('INVALID ACCESS INFO!')
            return (False, None, '{"error": "invalid access info"}')

        return (True, req_data, None)

    def message_smartcoil(self, action, params):
        self.outbound_queue.put(utils.Message('SRVMSG', action, params))

    # ENDPOINTS DECLARATION:
    def turn_smartcoil(self):
        # try:
            data_is_valid, data, err = self.access_data_is_valid()
            if not data_is_valid:
                return err

            switch = data['switch']

            res = 'SmartCoil is now {}'.format(switch)
            print('DEBUG:',res)
            self.message_smartcoil('turn_smartcoil', {'value': switch})

            return '{{"success": "{}"}}'.format(res)
        # except:
        #     return '{"error": "invalid information"}'

    def set_smartcoil_speed(self):
        try:
            data_is_valid, data, err = self.access_data_is_valid()
            if not data_is_valid:
                return err

            speed = data['speed']

            res = 'the speed is now {}'.format(speed)
            print('DEBUG:',res)
            return '{{"success": "{}"}}'.format(res)
        except:
            return '{"error": "invalid information"}'

    def set_smartcoil_temperature(self):
        try:
            data_is_valid, data, err = self.access_data_is_valid()
            if not data_is_valid:
                return err

            temperature = data['temperature']

            res = 'the temp is now {}'.format(temperature)
            print('DEBUG:',res)
            return '{{"success": "{}"}}'.format(res)
        except:
            return '{"error": "invalid information"}'

    def get_smartcoil_speed(self):
        try:
            data_is_valid, data, err = self.access_data_is_valid()
            if not data_is_valid:
                return err

            speed = 5 # get speed from smartcoil..

            res = 'current smartcoil speed is {}'.format(speed)
            print('DEBUG:',res)
            return '{{"success": "speed fetched", "speed": {}}}'.format(speed)
        except:
            return '{"error": "invalid information"}'

    def get_smartcoil_temperature(self):
        try:
            data_is_valid, data, err = self.access_data_is_valid()
            if not data_is_valid:
                return err

            temp = 100 # get temperature from smartcoil..

            res = 'current smartcoil temperature is {}'.format(speed)
            print('DEBUG:',res)
            return '{{"success": "temperature fetched", "speed": {}}}'.format(speed)
        except:
            return '{"error": "invalid information"}'

    def run(self):
        self.run_tunnel()
        serve(self.app, host='0.0.0.0', port=self.tunnel_port)

if __name__ == '__main__':
    srv = ServerManager()
    srv.run()
