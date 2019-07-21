import RPi.GPIO as GPIO
from time import sleep

# Flag values for turning on or off a relay.
VAL_ON = False
VAL_OFF = True
# Relays identifiers
valve = 0
fanlo = 1
fanmi = 2
fanhi = 3

class RelayController():
    '''Serves as the class that controls the 4-channel relay module that deals directly with the
    Fan Coil Unit (FCU).'''

    def __init__(self):
        '''The module is intented to be a secondary thread of the base class SmartCoil.
        For this project, I use a 4 relay module to control a decades-old FCU.
        All GPIO pins below follow BCM numbering.
        - Relay 1 makes use of pin 17 and controls the valve.
        - Relay 2 makes use of pin pin 22 and controls the fan's low speed.
        - Relay 3 is controlled by pin 23 and controls the fan's mid speed.
        - Relay 4 is controlled by pin 27 and controls the fan's high speed.
        '''
        self.relays = [17,22,23,27]
        self.RELAYS_COUNT = len(self.relays)
        self.init()

    def set_relay_to(self, rel, value):
        '''Sets the value for a given relay.

        Args:
            rel (int): The desired relay to control, values go from 0 to 3.
            value (bool): Either True to turn on a signal, or False for the opposite.
        '''

        GPIO.output(self.relays[rel],value)

    # Turns the fancoil on or off.
    # speed goes from 1 to 3. 0 means turned off.
    def start_coil_at(self, speed):
        '''Sets the speed for the FCU.

        Args:
            speed (int): 1 for low speed, 2 for mid speed and 3 for high speed. 0 turns off the FCU.
        '''
        options = [0, fanlo, fanmi, fanhi]
        self.all_off()
        if speed > 0:
            self.set_relay_to(valve, VAL_ON)
            self.set_relay_to(options[speed], VAL_ON)

    def fancoil_is_on(self):
        '''Checks if the FCU is turned on.

        Returns:
            boolean: True if the valve relay is on, False otherwise.
        '''
        return GPIO.input(self.relays[valve]) == VAL_ON

    # Set all relays to a value.
    def set_all_to(self, value):
        '''Helper method to turn all the relays to the same value. Useful to turn everything off.

        Args:
            value (int): The desired value (on or off) to set all the relays to.
        '''
        for r in range(self.RELAYS_COUNT):
            self.set_relay_to(r, value)

    def all_off(self):
        '''Turns all the relays to off.'''
        self.set_all_to(VAL_OFF)

    def init(self):
        '''Initializer helper method. Used in this class constructor.'''
        # Use board GPIO numbering
        GPIO.setmode(GPIO.BCM)
        # Setting pins to OUT mode
        for r in self.relays:
            GPIO.setup(r, GPIO.OUT)
        self.all_off()

    def cleanup(self):
        '''Clean up helper method. Use it before leaving the application.'''
        self.all_off()
        GPIO.cleanup()
