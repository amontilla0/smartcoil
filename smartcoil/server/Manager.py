from flask import Flask, Response, request
from waitress import serve
import os
from shutil import copyfile
import json
from datetime import datetime
import subprocess
from ..utils import utils

class AlexaResponse():
    '''Subclass that builds up the JSON responses for the Alexa Smart Home
    lambda function.'''
    def __init__(self):
        '''This class initializes a base string to serve as a placeholder for
        different messages to be sent to Alexa. The controllers used by the
        SmartCoil Alexa Skill are:
            - ThermostatController (turns the smartcoil on or off).
            - TemperatureSensor (reads indoor temperature).
            - RangeController (controls fan speed).
        '''
        # example: "timeOfSample": "2017-09-03T16:20:50.52Z"
        self.body = json.loads(
                    '''{
                         "context": {
                             "properties": [{
                                 "namespace": "<placeholder>",
                                 "name": "<placeholder>",
                                 "value": "<placeholder>",
                                 "timeOfSample": "<placeholder>",
                                 "uncertaintyInMilliseconds": "50"
                             }]
                         },
                         "event": {
                             "header": "<placeholder>",
                             "endpoint": {
                                 "scope": {
                                     "type": "BearerToken",
                                     "token": "<placeholder>"
                                 },
                                 "endpointId": "smartcoil_id"
                             },
                             "payload": {}
                         }
                       }'''
                       )

        now = datetime.now()
        self.body['context']['properties'][0]['timeOfSample'] = (
                            now.strftime('%Y-%m-%dT%H:%M:%S.') +
                            str(round(now.microsecond / 10000)).zfill(2) + 'Z')

    def set_namespace(self, nmspc):
        '''Helper method to set the namespace of the first property in the
        Response message.

        Args:
            nmspc (:obj:`str`): Namespace to set for the first property.
        '''
        self.body['context']['properties'][0]['namespace'] = nmspc

    def set_name(self, nm):
        '''Helper method to set the name of the first property in the Response
        message.

        Args:
            nm (:obj:`str`): Name to set for the first property.
        '''
        self.body['context']['properties'][0]['name'] = nm

    def set_value(self, val):
        '''Helper method to set the value of the first property in the Response
        message.

        Args:
            val (object): This could be either a simple string or a dictionary
                that will be translated to a JSON sub-object.
        '''
        self.body['context']['properties'][0]['value'] = val

    def set_header(self, hdr):
        '''Helper method to set the header of the Response message.
        Args:
            hdr (object): Usually a dictionary that will be translated into
                a JSON sub-object.
        '''
        self.body['event']['header'] = hdr

    def set_token(self, tkn):
        '''Helper method to set the token of the Response message.
        Args:
            tkn (:obj:`str`): The same token that was provided by the incoming
                Alexa request.
        '''
        self.body['event']['endpoint']['scope']['token'] = tkn

    def add_property(self, prop, with_defaults = True):
        '''Helper method to include an additional property in the response
        message.

        Args:
            prop (object): A dictionary including data related to the property.
            with_defaults (bool, default): Wether to include default values for
                the new property. The default values are:
                - timeOfSample which includes the exact time of the response.
                - uncertaintyInMilliseconds with a value of 50.
        '''
        if with_defaults:
            prop['timeOfSample'] = (
                        self.body['context']['properties'][0]['timeOfSample'])
            prop['uncertaintyInMilliseconds'] = '50'
        self.body['context']['properties'].append(prop)

    def get_json(self):
        '''Gets the resulting JSON as a string object. Used after the Alexa
        Response is completely built.

        Returns:
            :obj:`str`: The string represeting the JSON for the Alexa Response.
        '''
        return json.dumps(self.body)


class Endpoint(object):
    '''Subclass that builds endpoints to be used by Flask. The server needs to
    be started inside of a class instead of the main module scope in order to be
    treated as an object from the main SmartCoil class.
    '''
    def __init__(self, action):
        '''The endpoint consists of a specific action to evaluate when a client
        access the corresponding URI.

        Args:
            action (:obj:`function`): The method to execute when a corresponding
                URI is accessed. This action must return a JSON string.
        '''
        self.action = action

    def __call__(self, *args):
        '''This method is required to be implemented in order for Flask to treat
        it as a proper endpoint.

        Args:
            *args: Variable length argument list.

        Returns:
            :obj:`str`: A JSON response (provided by the endpoint action) with a
            status code of 200.
        '''
        answer = self.action()
        self.response = Response(answer, status=200,
                                 mimetype='application/json')
        return self.response

class ServerManager():
    '''Serves as the class that runs both the Flask server that manages Alexa
    requests, as well as the SSH tunnel based on the pagekite library.
    '''
    def __init__(self, outqueue = None, inqueue = None):
        '''The module is intented to be a secondary thread of the base class
        SmartCoil.
        To allow communication between the main thread and this thread, a Queue
        must be passed as an argument.
        Additionally, this class receives information from the main SmartCoil
        thread, which is performed with a second Queue enabling 2-way
        communication.

        Args:
            outqueue (:obj:`Queue`): Outbound queue to send messages to the main
                thread.
            inqueue (:obj:`Queue`): Inbound queue to receive messages from the
            main thread.
        '''
        self.app = Flask(__name__)
        self.load_endpoints()

        self.inbound_queue = inqueue
        self.outbound_queue = outqueue

        self.tunnel_address = None
        self.tunnel_port = None
        self.acces_token = None
        self.b_logfile = None
        self.f_logfile = None
        self.load_tunnel_config()

    ### TUNNEL RELATED METHODS ###
    def load_tunnel_config(self):
        '''Initializes the SSH tunnel by loading the pagekite class in a new
        subprocess. Notice that this method loads config info from
        '/assets/config/server_config.json' file, if the document is not found
        a template will be used in place, but remember to change 'tunnel' (URL),
        'port' (integer) and 'token' (string) values to valid entries.
        '''
        dirname = os.path.dirname(__file__)
        config_path = os.path.join(dirname,
                                    '../../assets/config/server_config.json')

        # Verify the server config file exists. If not, copy the template.
        if not os.path.exists(config_path):
            print('initializing config from template. '
                    + 'Remember to update with proper values...')
            copyfile(config_path + '_template', config_path)

        with open(config_path, 'r') as f:
            conf = json.load(f)
            self.tunnel_address = conf['tunnel']
            self.tunnel_port = conf['port']
            self.acces_token = conf['token']

        self.b_logfile = open(os.path.join(dirname, '../../assets/logs/pagekite_back.log'), 'a+')
        self.f_logfile = open(os.path.join(dirname, '../../assets/logs/pagekite_front.log'), 'a+')

    def close_logs(self):
        self.b_logfile.close()
        self.f_logfile.close()
        print('server logs successfully closed..')

    def run_tunnel(self):
        dirname = os.path.dirname(__file__)
        pagekite_path = os.path.join(dirname, 'pagekite.py')
        tunnel = subprocess.Popen(['python2', pagekite_path, str(self.tunnel_port), self.tunnel_address], stdout=self.b_logfile, stderr=self.f_logfile)
        print(tunnel)

    def token_is_valid(self, tok):
        return self.acces_token == tok

    ### FLASK RELATED METHODS ###
    def add_endpoint(self, handler=None, endpoint=None, endpoint_name=None):
        endpoint_name = endpoint[1:] if endpoint_name is None else endpoint_name
        self.app.add_url_rule(endpoint, endpoint_name,
                                Endpoint(handler), methods=['POST'])

    def load_endpoints(self):
        self.add_endpoint(self.turn_smartcoil, "/turn_smartcoil")
        self.add_endpoint(self.set_smartcoil_temperature,
                            "/set_smartcoil_temperature")
        self.add_endpoint(self.set_smartcoil_speed, "/set_smartcoil_speed")
        self.add_endpoint(self.get_smartcoil_state, "/get_smartcoil_state")

    def access_data_is_valid(self):
        req_data = None

        try:
            req_data = request.get_json()
            # verify if incoming data contains a request element.
            # Any exception is handled below.
            req_data['request']
            token = req_data['token']
            if not self.token_is_valid(token):
                print('INVALID TOKEN!')
                return (False, None, '{"error": "invalid token"}')
        except:
            print('INVALID ACCESS INFO!')
            return (False, None, '{"error": "invalid access info"}')

        return (True, req_data, None)

    def message_smartcoil(self, action, params = {}):
        self.outbound_queue.put(utils.Message('SRVMSG', action, params))

    def debug(self, dbg_msg):
        print('[{}] DEBUG: {}'.format(datetime.now(), dbg_msg))

    # ENDPOINTS DECLARATION:
    def turn_smartcoil(self):
        try:
            data_is_valid, data, err = self.access_data_is_valid()
            if not data_is_valid:
                return err

            switch = data['switch']
            request = data['request']

            dbg = 'SmartCoil is now {}'.format(switch)
            self.debug(dbg)
            self.message_smartcoil('SCOIL_SWTCH', {'value': switch})

            res = AlexaResponse()
            res.set_namespace('Alexa.ThermostatController')
            res.set_name('thermostatMode')
            res.set_value(
                    request['directive']['payload']['thermostatMode']['value'])
            response_header = request['directive']['header']
            response_header['namespace'] = 'Alexa';
            response_header['name'] = 'Response';
            response_header['messageId'] = response_header['messageId'] + '-R';
            res.set_header(response_header)
            res.set_token(request['directive']['endpoint']['scope']['token'])

            return res.get_json()
        except:
            return '{"error": "invalid information"}'

    def set_smartcoil_temperature(self):
        try:
            data_is_valid, data, err = self.access_data_is_valid()
            if not data_is_valid:
                return err

            temperature = data['temperature']
            request = data['request']

            dbg = 'the temp is now {}'.format(temperature)
            self.debug(dbg)
            self.message_smartcoil('SCOIL_TEMP', {'value': temperature})

            res = AlexaResponse()
            res.set_namespace('Alexa.ThermostatController')
            res.set_name('targetSetpoint')
            val = temperature
            scl = request['directive']['payload']['targetSetpoint']['scale']
            res.set_value({'value': val, 'scale': scl})
            response_header = request['directive']['header']
            response_header['namespace'] = 'Alexa';
            response_header['name'] = 'Response';
            response_header['messageId'] = response_header['messageId'] + '-R';
            res.set_header(response_header)
            res.set_token(request['directive']['endpoint']['scope']['token'])
            return res.get_json()
        except:
            return '{"error": "invalid information"}'

    def set_smartcoil_speed(self):
        try:
            data_is_valid, data, err = self.access_data_is_valid()
            if not data_is_valid:
                return err

            speed = data['speed']
            request = data['request']

            dbg = 'the speed is now {}'.format(speed)
            self.debug(dbg)
            self.message_smartcoil('SCOIL_SPEED', {'value': speed})

            res = AlexaResponse()
            res.set_namespace('Alexa.RangeController')
            res.set_name('rangeValue')
            res.set_value(speed)
            response_header = request['directive']['header']
            response_header['namespace'] = 'Alexa';
            response_header['name'] = 'Response';
            response_header['messageId'] = response_header['messageId'] + '-R';
            res.set_header(response_header)
            res.set_token(request['directive']['endpoint']['scope']['token'])
            return res.get_json()
        except:
            return '{"error": "invalid information"}'

    def get_smartcoil_state(self):
        try:
            data_is_valid, data, err = self.access_data_is_valid()
            if not data_is_valid:
                return err

            request = data['request']

            self.message_smartcoil('SCOIL_STATE')

            msg = self.inbound_queue.get()
            type = msg.type
            action = msg.action
            info = msg.params

            if not (type == 'APPMSG' and action == 'SCOIL_STATE-R'):
                print('unrecognized App action.')
                return '{"error": "invalid information"}'

            dbg = ('Current state is:\nstate: {}, speed: {}, '
                    + 'thermostat temp: {}, AC temp set to: {}').format(
                info['state'], info['speed'], info['cur_temp'], info['usr_temp']
            )
            self.debug(dbg)

            res = AlexaResponse()
            res.set_namespace('Alexa.ThermostatController')
            res.set_name('targetSetpoint')
            val = info['usr_temp']
            res.set_value({'value': val, 'scale': 'FAHRENHEIT'})
            response_header = request['directive']['header']
            response_header['namespace'] = 'Alexa';
            response_header['name'] = 'StateReport';
            response_header['messageId'] = response_header['messageId'] + '-R';
            res.set_header(response_header)
            res.set_token(request['directive']['endpoint']['scope']['token'])

            prop = {
                'namespace': 'Alexa.RangeController',
                'name': 'rangeValue',
                'instance': 'Fancoil.Speed',
                'value': info['speed']
                }
            res.add_property(prop)

            prop = {
                'namespace': 'Alexa.TemperatureSensor',
                'name': 'temperature',
                'value': {'value': info['cur_temp'], 'scale': 'FAHRENHEIT'}
                }
            res.add_property(prop)

            prop = {
                'namespace': 'Alexa.ThermostatController',
                'name': 'thermostatMode',
                'value': info['state']
                }
            res.add_property(prop)

            return res.get_json()
        except:
            return '{"error": "invalid information"}'

    def run(self):
        self.run_tunnel()
        serve(self.app, host='0.0.0.0', port=self.tunnel_port)

if __name__ == '__main__':
    srv = ServerManager()
    srv.run()
