from .weatherData import WeatherData
from .sensorData import SensorData
from .gui import GUI
from time import sleep
from threading import Thread
import sqlite3
from datetime import datetime
import os

class SmartCoil():
    def __init__(self):
        self.wthr = WeatherData()
        self.snsr = SensorData()
        self.gui  = GUI()
        dirname = os.path.dirname(__file__)
        self.dbase_path = os.path.join(dirname, '../assets/SmartCoilDB')

    def run_sensor(self, verbose = False):
        self.snsr.run_sensor(verbose)

    def run_sensor_thread(self):
        th = Thread(target=self.run_sensor, name='sensorRun')
        th.start()

    def commit_to_db(self, sql, params):
        with sqlite3.connect(self.dbase_path) as conn:
            crsr = conn.cursor()
            crsr.execute(sql, params)
            conn.commit()

    def commit_weather_data(self, tstamp):
        data = [tstamp] + self.wthr.get_conditions_data()
        sql = "INSERT INTO YR_WEATHER_API_DATA VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        self.commit_to_db(sql, data)

    def commit_sensor_data(self, tstamp):
        data = [tstamp] + self.snsr.get_most_recent_readings()
        sql = "INSERT INTO SENSOR_BME680_DATA VALUES (?, ?, ?, ?, ?, ?)"
        self.commit_to_db(sql, data)

    def sensor_ready(self):
        return self.snsr.sensor_ready()

    def periodic_data_log(self):
        while True:
            # data will be stored into sqlite only if the sensor is fully primed (it takes 5 minutes of initialization to get consistent air quality data).
            if self.sensor_ready():
                print('saving data...')
                timestamp = datetime.now()
                self.commit_weather_data(timestamp)
                self.commit_sensor_data(timestamp)

            sleep(60)

    def periodic_data_log_thread(self):
        th = Thread(target=self.periodic_data_log, name='dataLog')
        th.start()

    def run(self):
        # spawn thread in charge of keeping BME680 sensor periodically burning for the gas readings.
        self.run_sensor_thread()
        # spawn thread in charge of reading sensor+weather data and writing it to sqlite.
        self.periodic_data_log_thread()


sc = SmartCoil()
