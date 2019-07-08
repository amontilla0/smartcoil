from flask import Flask, request #import main Flask class and request object
from waitress import serve
import os
from shutil import copyfile
import json
import subprocess

class TunnelHandler():
    def __init__(self):
        self.tunnel_address = None
        self.tunnel_port = None
        self.acces_token = None

    def load_config(self):
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
        tunnel = subprocess.Popen(['python2', 'pagekite.py', str(self.tunnel_port), self.tunnel_address], stdout=subprocess.PIPE)
        print(tunnel)

    def token_is_valid(self, tok):
        return self.acces_token == tok

    def run(self):
        self.load_config()
        self.run_tunnel()



th = TunnelHandler()
app = Flask(__name__) #create the Flask app

def access_data_is_valid():
    req_data = None

    try:
        req_data = request.get_json()
        token = req_data['token']
        if not th.token_is_valid(token):
            print('INVALID TOKEN!')
            return (False, None, '{"error": "invalid token"}')
    except:
        print('INVALID ACCESS INFO!')
        return (False, None, '{"error": "invalid access info"}')

    return (True, req_data, None)

@app.route('/turn_smartcoil', methods=['POST'])
def turn_smartcoil():
    try:
        data_is_valid, data, err = access_data_is_valid()
        if not data_is_valid:
            return err

        switch = data['switch']

        res = 'SmartCoil is now {}'.format(switch)
        print('DEBUG:',res)
        return '{{"success": "{}"}}'.format(res)
    except:
        return '{"error": "invalid information"}'

@app.route('/set_smartcoil_speed', methods=['POST'])
def set_smartcoil_speed():
    try:
        data_is_valid, data, err = access_data_is_valid()
        if not data_is_valid:
            return err

        speed = data['speed']

        res = 'the speed is now {}'.format(speed)
        print('DEBUG:',res)
        return '{{"success": "{}"}}'.format(res)
    except:
        return '{"error": "invalid information"}'

@app.route('/set_smartcoil_temperature', methods=['POST'])
def set_smartcoil_temperature():
    try:
        data_is_valid, data, err = access_data_is_valid()
        if not data_is_valid:
            return err

        temperature = data['temperature']

        res = 'the temp is now {}'.format(temperature)
        print('DEBUG:',res)
        return '{{"success": "{}"}}'.format(res)
    except:
        return '{"error": "invalid information"}'

@app.route('/get_smartcoil_speed', methods=['POST'])
def get_smartcoil_speed():
    try:
        data_is_valid, data, err = access_data_is_valid()
        if not data_is_valid:
            return err

        speed = 5 # get speed from smartcoil..

        res = 'current smartcoil speed is {}'.format(speed)
        print('DEBUG:',res)
        return '{{"success": "speed fetched", "speed": {}}}'.format(speed)
    except:
        return '{"error": "invalid information"}'

if __name__ == '__main__':
    th.run()
    serve(app, host='0.0.0.0', port=th.tunnel_port)
