from .peripherals.sensorData import SensorData
from .peripherals.relayController import RelayController
from .externals.weatherData import WeatherData
from .gui.KivySmartCoilGUI import SmartCoilGUIApp
from time import sleep
from threading import Thread, Event
import asyncio
import can
import signal
import sqlite3
from datetime import datetime
import os

HEATING = 1
COOLING = 2

class SmartCoil():
    def __init__(self):
        # preparation of bus that will receive async messages.
        self.msg_bus = can.Bus('bus1', bustype='virtual', receive_own_messages=True)
        self.loop = asyncio.get_event_loop()
        self.reader = can.AsyncBufferedReader()
        listeners = [ self.reader ]
        self.notifier = can.Notifier(self.msg_bus, listeners, loop=self.loop)

        self.wthr = WeatherData()
        self.snsr = SensorData(self.msg_bus, 1)
        self.rc = RelayController()
        self.gui  = SmartCoilGUIApp(self.msg_bus)
        dirname = os.path.dirname(__file__)
        self.dbase_path = os.path.join(dirname, '../assets/db/SmartCoilDB')
        self.exit = Event()

        # Since the fancoil ability to blow cool or hot air comes from a central boiler room,
        # all we could do is predict the fan will blow cold air between march and september,
        # and cold air in the remaining months.
        self.mode = COOLING if datetime.now().month in range(4,10) else HEATING

        # Flag to check if target temperature was reached.
        self.target_reached = False

        # Flag to state if the fancoil is working right now.
        self.fancoil_running = False

        # Once initialized, report the app is up and running to the DB
        self.report_app_status_to_db('ON')

    def run_sensor(self):
        self.snsr.run_sensor(exit_evt = self.exit)

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

    def report_app_status_to_db(self, status):
        sql = 'INSERT INTO APP_STATUS VALUES (?, ?)'
        tstamp = datetime.now()
        data = [tstamp, status]
        self.commit_to_db(sql, data)

    def commit_weather_data(self, tstamp = None):
        if tstamp is None:
            tstamp = datetime.now()

        self.wthr.update_values()
        data = [tstamp] + self.wthr.get_conditions_data()
        sql = "INSERT INTO YR_WEATHER_API_DATA VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        self.commit_to_db(sql, data)

    def commit_sensor_data(self, tstamp = None):
        if tstamp is None:
            tstamp = datetime.now()

        data = [tstamp] + self.snsr.get_most_recent_readings() + [int(self.fancoil_running)]
        sql = "INSERT INTO SENSOR_BME680_DATA VALUES (?, ?, ?, ?, ?, ?, ?)"
        self.commit_to_db(sql, data)

    def commit_user_data(self, tstamp = None):
        if tstamp is None:
            tstamp = datetime.now()

        u_temp = self.gui.root.get_user_temp()
        u_speed = self.gui.root.get_user_speed()
        data = [tstamp, u_temp, u_speed]
        sql = "INSERT INTO USER_DATA VALUES (?, ?, ?)"
        self.commit_to_db(sql, data)

    def sensor_ready(self):
        return self.snsr.sensor_ready()

    def get_current_temp(self):
        t, *_ = self.snsr.get_most_recent_readings()
        return t

    def get_screen_data(self):
        t, p, h, g, a = self.snsr.get_most_recent_readings()
        return (
        '{} °F'.format(int(t))
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
            if not self.rc.fancoil_is_on():
                self.target_reached = False
                self.fancoil_running = True
                self.rc.start_coil_at(self.gui.root.get_user_speed())
        else:
            if self.rc.fancoil_is_on():
                self.target_reached = True
                self.fancoil_running = False
                self.rc.all_off()

    def update_gui_values(self):
        tmp, hum, airq = self.get_screen_data()
        self.gui.root.updateCurrentTemp(tmp)
        self.gui.root.updateHumidity(hum)
        self.gui.root.updateAirQuality(airq)

    def process_new_sensor_data(self):
        self.monitor_temperature(offset=3)
        self.update_gui_values()
        self.commit_sensor_data()

    def process_new_weather_data(self):
        self.commit_weather_data()

    def process_new_gui_data(self):
        prev_state = self.fancoil_running
        self.monitor_temperature(offset=3)
        curr_state = self.fancoil_running

        self.commit_user_data()

        # If adjusting the user temperature changes the fancoil state, report it to DB.
        fancoil_state_changed = prev_state != curr_state
        if fancoil_state_changed:
            self.commit_sensor_data()

    def quit(self, signo, _frame):
        print('cleaning up before exiting app...')
        self.exit.set()
        self.rc.cleanup()

        # Once terminated, report the app is down to the DB
        self.report_app_status_to_db('OFF')

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

    async def await_messages(self):
        switcher = {
                    'SNSMSG': lambda: self.process_new_sensor_data(),
                    'GUIMSG': lambda: self.process_new_gui_data(),
                    'WTHMSG': lambda: print('got a weather message..'),
                    'EXIT': lambda: print('stopped awaiting messages..'),
        }

        option = ''
        while option != 'EXIT':
            msg = await self.reader.get_message()
            option = msg.data.decode('utf-8')
            action = switcher.get(option, lambda: print('unrecognized message.'))

            action()

    def run_msg_handler(self):
        self.loop.run_until_complete(self.await_messages())
        self.notifier.stop()
        self.msg_bus.shutdown()
        self.loop.close()

    def run_msg_handler_thread(self):
        th = Thread(target=self.run_msg_handler, name='msghandler')
        th.start()

    # This method checks for a previous configuration made by the user to restore such state.
    # It is run as a thread and waits for the GUI to be initialized before making adjustments.
    def fetch_user_data_init(self):
        while self.gui.root is None:
            sleep(0.05)

        config_found = False
        with sqlite3.connect(self.dbase_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM USER_DATA ORDER BY timestamp DESC LIMIT 1")
            data = cur.fetchone()
            if data is not None:
                self.gui.root.set_user_temp(data[1])
                self.gui.root.set_user_speed(data[2])
                config_found = True

        # If no configuration was found, add the default one as the first one in the DB
        if not config_found:
            self.commit_user_data()

    def run_fetch_user_data_init_thread(self):
        th = Thread(target=self.fetch_user_data_init, name='usrdatainit')
        th.start()

    def run(self):
        # handling CTRL-C internally to stop all related threads and cleanup before exiting
        for sig in ('TERM', 'HUP', 'INT'):
            signal.signal(getattr(signal, 'SIG'+sig), self.quit)

        # spawn thread in charge of keeping BME680 sensor periodically burning for the gas readings.
        self.run_sensor_thread()

        # spawn thread in charge of handling messages from other classes and perform according actions.
        self.run_msg_handler_thread()

        # spawn thread that checks for previous user configuration.
        self.run_fetch_user_data_init_thread()

        # run GUI as part of the main thread.
        self.run_gui()
