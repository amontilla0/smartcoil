import logging
import os

from flask import Flask
from flask_ask import Ask, request, session, question, statement
import RPi.GPIO as GPIO

app = Flask(__name__)
ask = Ask(app, "/")
logging.getLogger('flask_ask').setLevel(logging.DEBUG)

STATUSON = ['on','high', 'cool']
STATUSOFF = ['off','low']

@ask.launch
def launch():
    speech_text = 'Welcome to SmartCoil Alexa controller.'
    return question(speech_text).reprompt(speech_text).simple_card(speech_text)

@ask.intent('GpioIntent', mapping = {'status':'status'})
def Gpio_Intent(status,room):
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(27,GPIO.OUT)
    if status in STATUSON:
        GPIO.output(27,GPIO.LOW)
        return statement('turning {} the A.C.'.format(status))
    elif status in STATUSOFF:
        GPIO.output(27,GPIO.HIGH)
        return statement('turning {} the A.C.'.format(status))
    else:
        return statement('Smartcoil can\'t process your request.')

@ask.intent('AMAZON.HelpIntent')
def help():
    speech_text = 'You can control the SmartCoil with this app. Say things like "tell raspberry to turn on AC" or "tell raspberry to set heater on high speed."'
    return question(speech_text).reprompt(speech_text).simple_card('HelloWorld', speech_text)


@ask.session_ended
def session_ended():
    return "{}", 200


if __name__ == '__main__':
    verify = ''
    if 'ASK_VERIFY_REQUESTS' in os.environ:
        verify = str(os.environ.get('ASK_VERIFY_REQUESTS', '')).lower()
    if verify == 'false':
        app.config['ASK_VERIFY_REQUESTS'] = False

app.run(debug=True)
