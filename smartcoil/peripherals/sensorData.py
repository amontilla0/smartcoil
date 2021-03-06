import bme680
import time
from ..utils import utils

class SensorData:
    '''Serves as the class that periodically fetches information from the BME680
    sensor.'''

    def __init__(self, outqueue = None, burn_time = 300):
        '''The module is intented to be a secondary thread of the base class
        SmartCoil.
        To allow communication between the main thread and this thread, a Queue
        can be passed as an argument.
        Additionally, the BME680 needs a period of burning time to prime the gas
        sensor and read accurate air quality values. A specific amount of time
        to prime the gas sensor can be passed as an argument too.

        Args:
            outqueue (:obj:`Queue`, optional): Outbound queue to send messages
                to the main thread.
            burn_time (int): Time in seconds to allow the sensor to burn before
                sending accurate readings. Defaults to 5 minutes.
        '''
        try:
            self.outbound_queue = outqueue
            self.sensor = bme680.BME680(bme680.I2C_ADDR_PRIMARY)
             #3.32
        except IOError:
            self.sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)

        # sensor initial calibration
        for name in dir(self.sensor.calibration_data):
            if not name.startswith('_'):
                value = getattr(self.sensor.calibration_data, name)

        # These oversampling settings can be tweaked to
        # change the balance between accuracy and noise in
        # the data.
        self.sensor.set_humidity_oversample(bme680.OS_2X)
        self.sensor.set_pressure_oversample(bme680.OS_4X)
        self.sensor.set_temperature_oversample(bme680.OS_8X)
        self.sensor.set_filter(bme680.FILTER_SIZE_3)
        self.sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)

        # Up to 10 heater profiles can be configured, each
        # with their own temperature and duration.
        # sensor.set_gas_heater_profile(200, 150, nb_profile=1)
        # sensor.select_gas_heater_profile(1)
        self.sensor.set_gas_heater_temperature(320)
        self.sensor.set_gas_heater_duration(150)
        self.sensor.select_gas_heater_profile(0)

        # for building up gas resistance baseline
        self.start_time = time.time()
        self.curr_time = time.time()
        self.burn_in_time = burn_time
        self.burn_in_data = []
        self.gas_baseline = None
        self.burn_complete = False

        # Set the humidity baseline to 40%, an optimal indoor humidity.
        self.hum_baseline = 40.0
        # This sets the balance between humidity and gas reading in the
        # calculation of air_quality_score (25:75, humidity:gas)
        self.hum_weighting = 0.25

    def build_gas_baseline(self):
        ''' Primes the gas sensor based on the specified burning time in
        seconds.
        Once the time has passed, the gas baseline is built and the gas readings
        are ready to be used.
        '''
        if self.sensor_ready(): return

        if self.curr_time - self.start_time < self.burn_in_time:
            self.curr_time = time.time()
            if self.sensor.data.heat_stable:
                gas = self.sensor.data.gas_resistance
                self.burn_in_data.append(gas)
        else:
            self.burn_complete = True

        if self.burn_complete and self.gas_baseline is None:
            self.gas_baseline =  sum(self.burn_in_data[-50:]) / 50.0

    # Checks if the gas baseline is already initialized, a process that takes
    # 5 minutes of initial readings to happen.
    def sensor_ready(self):
        '''Verifies if the gas baseline has been built already (after consuming
        the specified burning time).

        Returns:
            bool: Whether the gas baseline was built or not.
        '''
        return self.gas_baseline is not None

    def calc_air_quality(self):
        '''Calculates the air quality based on readings processing data from gas
        and humidity sensors.

        Returns:
            int: Either -1 if the gas baseline is still not built,
                or a float representing the indoor air quality percentage.
        '''
        air_quality_score = -1

        if  self.sensor_ready() and self.sensor.data.heat_stable:
            gas = self.sensor.data.gas_resistance
            gas_offset = self.gas_baseline - gas

            hum = self.sensor.data.humidity
            hum_offset = hum - self.hum_baseline

            # Calculate hum_score as the distance from the hum_baseline.
            if hum_offset > 0:
                hum_score = (100 - self.hum_baseline - hum_offset)
                hum_score /= (100 - self.hum_baseline)
                hum_score *= (self.hum_weighting * 100)
            else:
                hum_score = (self.hum_baseline + hum_offset)
                hum_score /= self.hum_baseline
                hum_score *= (self.hum_weighting * 100)

            # Calculate gas_score as the distance from the gas_baseline.
            if gas_offset > 0:
                gas_score = (gas / self.gas_baseline)
                gas_score *= (100 - (self.hum_weighting * 100))
            else:
                gas_score = 100 - (self.hum_weighting * 100)

            air_quality_score = int(hum_score + gas_score)

        return air_quality_score

    def get_most_recent_readings(self, temp_in_f = True):
        '''Gets the most recent values fetched from the BME680 sensor, these
        values are:
            - temperature
            - pressure
            - humidity
            - gas resistance
            - air quality

        Args:
            temp_in_f (bool, optional): Specifies if the temperature must be
                specified in Fahrenheit. Defaults to True.

        Returns:
            list: A list with values fetched from the BME680 sensor, in the
            following order:
                temperature, pressure, humidity, gas resistance, air quality.
        '''
        if not self.sensor_ready(): return None

        temp = self.sensor.data.temperature
        if temp_in_f:
            temp = utils.c_to_f(temp)
        pres = self.sensor.data.pressure
        humi = self.sensor.data.humidity
        gas_res = self.sensor.data.gas_resistance
        airq = self.calc_air_quality()
        airq = '-' if airq < 0 else airq

        return [temp, pres, humi, gas_res, airq]

    def run_sensor(self, verbose = False, exit_evt = None, temp_in_f = True):
        '''The main loop that constantly fetches information from the BME680
        sensor.

        Args:
            verbose (bool, optional): Whether using this method should print the
                readings every second to STDOUT.
            exit_evt (:obj:`Event`, optional): Event flag to manage sensor
                cleaning before exiting the full app.
            temp_in_f (bool, optional): Specifies if the temperature must be
                specified in Fahrenheit. Defaults to True.
        '''
        sleep_func = time.sleep if exit_evt == None else exit_evt.wait

        temp = self.sensor.data.temperature
        if temp_in_f:
            temp = utils.c_to_f(temp)
        # 'half-rounding' temperature to closest 0.5 increment
        temp = round(temp) - (round(temp) - int(temp))/2

        pres = int(self.sensor.data.pressure)
        humi = int(self.sensor.data.humidity)
        airq = self.calc_air_quality()
        airq = '-' if airq < 0 else int(airq)

        while True if exit_evt == None else not exit_evt.is_set():
            new_temp = self.sensor.data.temperature
            if temp_in_f:
                new_temp = utils.c_to_f(new_temp)
            real_temp = new_temp
            # 'half-rounding' temperature to closest 0.5 increment
            new_temp = round(new_temp) - (round(new_temp) - int(new_temp))/2

            new_pres = int(self.sensor.data.pressure)
            new_humi = int(self.sensor.data.humidity)
            new_airq = self.calc_air_quality()
            new_airq = '-' if new_airq < 0 else int(new_airq)

            # temperature offset in celcius after monitoring and comparing
            #aginst another thermometer.
            self.sensor.set_temp_offset(-1.9)

            if self.sensor.get_sensor_data():
                self.build_gas_baseline()

                values_changed = (new_temp != temp or
                                  new_pres != pres or
                                  new_humi != humi or
                                  new_airq != airq)

                if self.outbound_queue is not None and values_changed:
                    self.outbound_queue.put(utils.Message('SNSMSG'))

                if verbose:
                    output = ('temp: {0:.2f} F ({1:.3f}), pressure: {2:.1f} '
                    + 'hPa, humidity: {3:.0f}%, air quaility: {4}%').format(
                        temp, real_temp,
                        pres,
                        humi,
                        airq)

                    print(output)

            # update last seen values
            temp = new_temp
            pres = new_pres
            humi = new_humi
            airq = new_airq

            sleep_func(1)

        if self.outbound_queue is not None:
            self.outbound_queue.put(utils.Message('EXIT'))

if __name__=='__main__':
    sd = SensorData()
    sd.run_sensor(True)
