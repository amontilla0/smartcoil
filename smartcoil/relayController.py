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

# For this project, I use a 4 relay module to control a decades-old Fan Coil Unit (FCU).
# All GPIO pins below follow BCM numbering.
# Relay 1 makes use of pin 17 and controls the valve.
# Relay 2 makes use of pin pin 22 and controls the fan's low speed.
# Relay 3 is controlled by pin 23 and controls the fan's mid speed.
# Relay 4 is controlled by pin 27 and controls the fan's high speed.
class RelayController():
    def __init__(self):
        self.relays = [17,22,23,27]
        self.RELAYS_COUNT = len(self.relays)
        self.init()

    # Sets the value for a given relay.
    # rel - the desired relay to control, values go from 0 to 3.
    # value - either True to turn on a signal, or False for the opposite
    def set_relay_to(self, rel, value):
        GPIO.output(self.relays[rel],value)

    def start_coil_at(self, speed):
        options = [fanlo, fanmi, fanhi]
        self.all_off()
        self.set_relay_to(valve, VAL_ON)
        self.set_relay_to(options[speed], VAL_ON)

    def fancoil_is_on(self):
        return GPIO.input(self.relays[valve]) == VAL_ON

    # Set all relays to a value.
    def set_all_to(self, value):
        for r in range(self.RELAYS_COUNT):
            self.set_relay_to(r, value)

    def all_off(self):
        self.set_all_to(VAL_OFF)

    def init(self):
        # Use board GPIO numbering
        GPIO.setmode(GPIO.BCM)
        # Setting pins to OUT mode
        for r in self.relays:
            GPIO.setup(r, GPIO.OUT)
        self.all_off()

    def cleanup(self):
        self.all_off()
        GPIO.cleanup()
