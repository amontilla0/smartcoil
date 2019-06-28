from .weatherData import WeatherData
from .sensorData import SensorData
from .relayController import RelayController
from .gui.KivySmartCoilGUI import SmartCoilGUIApp
from time import sleep
from threading import Thread, Event
import signal
import sqlite3
from datetime import datetime
import os

HEATING = 1
COOLING = 2

class SmartCoil():
    def __init__(self):
        self.wthr = WeatherData()
        self.snsr = SensorData(1)
        self.rc = RelayController()
        self.gui  = SmartCoilGUIApp(self.rc)
        dirname = os.path.dirname(__file__)
        self.dbase_path = os.path.join(dirname, '../assets/db/SmartCoilDB')
        self.exit = Event()

        # Since the fancoil ability to blow cool or hot air comes from a central boiler room,
        # all we could do is predict the fan will blow cold air between march and september,
        # and cold air in the remaining months.
        self.mode = COOLING if datetime.now().month in range(4,10) else HEATING

        # Flag ot check if target temperature was reached.
        self.target_reached = False

    def run_sensor(self, verbose = False):
        self.snsr.run_sensor(verbose, self.exit)

    def run_sensor_thread(self):
        th = Thread(target=self.run_sensor, name='sensorRun')
        th.start()

    def run_gui(self):
        self.gui.run()

    def commit_to_db(self, sql, params):
        with sqlite3.connect(self.dbase_path) as conn:
            crsr = conn.cursor()
            crsr.execute(sql, params)
            conn.commit()

    def commit_weather_data(self, tstamp):
        self.wthr.update_values()
        data = [tstamp] + self.wthr.get_conditions_data()
        sql = "INSERT INTO YR_WEATHER_API_DATA VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        self.commit_to_db(sql, data)

    def commit_sensor_data(self, tstamp):
        data = [tstamp] + self.snsr.get_most_recent_readings()
        sql = "INSERT INTO SENSOR_BME680_DATA VALUES (?, ?, ?, ?, ?, ?)"
        self.commit_to_db(sql, data)

    def commit_user_data(self, tstamp):
        u_temp = self.gui.root.get_user_temp()
        u_speed = self.gui.root.get_user_temp()
        data = [tstamp, u_temp, u_speed]
        sql = "INSERT INTO USER_DATA VALUES (?, ?, ?)"
        self.commit_to_db(sql, data)

    def sensor_ready(self):
        return self.snsr.sensor_ready()

    def c_to_f(self, celcius):
        return celcius * 9 / 5 + 32

    def get_current_temp(self):
        t, *_ = self.snsr.get_most_recent_readings()
        return self.c_to_f(t)

    def get_screen_data(self):
        t, p, h, g, a = self.snsr.get_most_recent_readings()
        return (
        '{} °F'.format(int(self.c_to_f(t)))
        ,int(h)
        ,int(a)
        )

    def monitor_temperature(self, offset = 0):
        # there's an initial offset to reach the target temperature plus some additional degrees.
        # However, once this target is reached, the offset is set to zero in order to wait some time
        # until the room temperature is out of the initial target again (disregarding the offset).
        dynamic_offset = 0 if self.target_reached else offset

        mult  = 1 if self.mode == COOLING else -1
        trigger_fancoil = mult * self.get_current_temp() - mult * self.gui.root.get_user_temp() > -abs(dynamic_offset)

        if not self.gui.root.user_turned_off_fancoil() and trigger_fancoil:
            self.target_reached = False
            self.rc.start_coil_at(self.gui.root.get_user_speed())
        else:
            if self.rc.fancoil_is_on():
                self.target_reached = True
                self.rc.all_off()

    def quit(self, signo, _frame):
        print('cleaning up before exiting app...')
        self.exit.set()
        self.rc.cleanup()
        exit(0)

    def periodic_data_log(self):
        waitTime = 5
        sensorCommitTimeCounter = 0
        sensorCommitWaitTime = 60
        weatherUpdated = False
        iter = 0

        while not self.exit.is_set():
            # data will be stored into sqlite only if the sensor is fully primed (it takes 5 minutes of initialization to get consistent air quality data).
            if self.sensor_ready():
                self.monitor_temperature(offset = 3)

                tmp, hum, airq = self.get_screen_data()
                self.gui.root.updateCurrentTemp(tmp)
                self.gui.root.updateHumidity(hum)
                self.gui.root.updateAirQuality(airq)

                print('saving data...')
                timestamp = datetime.now()

                sensorCommitFlag = sensorCommitTimeCounter >= sensorCommitWaitTime
                if sensorCommitFlag:
                    self.commit_sensor_data(timestamp)
                    sensorCommitTimeCounter = -waitTime
                sensorCommitTimeCounter += waitTime

                if sensorCommitFlag and timestamp.hour % 4 == 0 and not weatherUpdated:
                    self.commit_weather_data(timestamp)
                    weatherUpdated = True
                elif timestamp.hour % 4 != 0:
                    weatherUpdated = False
            elif self.gui.root is not None:
                self.gui.root.updateCurrentTemp('.'*(iter%3+1))
                iter += 1

            self.exit.wait(waitTime)

    def periodic_data_log_thread(self):
        th = Thread(target=self.periodic_data_log, name='dataLog')
        th.start()

    def run(self):
        # handling CTRL-C internally to stop all related threads and cleanup before exiting
        for sig in ('TERM', 'HUP', 'INT'):
            signal.signal(getattr(signal, 'SIG'+sig), self.quit)

        # spawn thread in charge of keeping BME680 sensor periodically burning for the gas readings.
        self.run_sensor_thread()
        # spawn thread in charge of reading sensor+weather data and writing it to sqlite.
        self.periodic_data_log_thread()

        self.run_gui()
