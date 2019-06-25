import bme680
import time

class SensorData:
    def __init__(self, burn_time = 300):
        try:
            self.sensor = bme680.BME680(bme680.I2C_ADDR_PRIMARY)
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

    # Checks if the gas baseline is already initialized, a process that takes 5 minutes of initial readings to happen.
    def sensor_ready(self):
        return self.gas_baseline is not None

    def calc_air_quality(self):
        air_quality_score = '-'

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

    def get_most_recent_readings(self):
        if not self.sensor_ready(): return None

        temp = self.sensor.data.temperature
        pres = self.sensor.data.pressure
        humi = self.sensor.data.humidity
        gas_res = self.sensor.data.gas_resistance
        airq = self.calc_air_quality()

        return [temp, pres, humi, gas_res, airq]

    def run_sensor(self, verbose = False):
        while True:
            if self.sensor.get_sensor_data():
                self.build_gas_baseline()
                if not verbose: continue

                temp = self.sensor.data.temperature
                pres = self.sensor.data.pressure
                humi = self.sensor.data.humidity
                airq = self.calc_air_quality()
                output = 'temp: {0:.0f} C, pressure: {1:.1f} hPa, humidity: {2:.0f}%, air quaility: {3}%'.format(
                    temp,
                    pres,
                    humi,
                    airq)

                print(output)

            time.sleep(1)

if __name__=='__main__':
    sd = SensorData()
    sd.run_sensor(True)
