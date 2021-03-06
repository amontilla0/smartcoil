from .peripherals.sensorData import SensorData
from .peripherals.relayController import RelayController
from .externals.weatherData import WeatherData
from .gui.KivySmartCoilGUI import SmartCoilGUIApp
from .server.Manager import ServerManager
from time import sleep
from threading import Thread, Event
from queue import Queue
from .utils import utils
import signal
import sqlite3
from datetime import datetime
import os
from shutil import copyfile
import traceback

HEATING = 'HEAT'
COOLING = 'COOL'

class SmartCoil():
    '''Serves as the main class that orchestrates communication between
    components (peripherals, GUI and APIs).
    '''

    def __init__(self):
        '''This constructor initializes weather, sensor, relay, gui and server
        classes.
        Take in account that this classes looks for the SQLite DB "/assets/db/SmartCoilDB"
        if not found, a template is used instead, which holds all valid tables but no data included.
        '''
        try:
            # preparation of queues that will manage messages between threads.
            self.inbound_queue = Queue()
            self.outbound_queue = Queue()

            self.wthr = WeatherData(self.inbound_queue)
            self.snsr = SensorData(self.inbound_queue, 1)
            self.rc = RelayController()
            self.gui  = SmartCoilGUIApp(self.inbound_queue)
            self.srv = ServerManager(self.inbound_queue, self.outbound_queue)

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

            # Verify the database schema exists. If not, copy the template.
            if not os.path.exists(self.dbase_path):
                print('initializing DB from template...')
                copyfile(self.dbase_path + '_template', self.dbase_path)

            # Once initialized, report the app is up and running to the DB
            self.report_app_status_to_db('ON')
        except Exception as e:
            print('Exception at SmartCoil.__init__')
            print(type(e))
            print(e)
            traceback.print_tb(e.__traceback__)

    def run_sensor_fetcher(self):
        '''Method used by the thread that will handle the BME680 sensor.
        '''
        try:
            self.snsr.run_sensor(exit_evt = self.exit)
        except Exception as e:
            print('Exception at SmartCoil.run_sensor_fetcher')
            print(type(e))
            print(e)
            traceback.print_tb(e.__traceback__)

    def run_sensor_fetcher_thread(self):
        '''Method that starts the thread that will handle the BME680 sensor.
        '''
        th = Thread(target=self.run_sensor_fetcher, name='sensorFetcher')
        th.start()

    def run_weather_fetcher(self):
        '''Method used by the thread that will fetch weather data from yr.no.
        '''
        try:
            self.wthr.run_updates(exit_evt = self.exit)
        except Exception as e:
            print('Exception at SmartCoil.run_weather_fetcher')
            print(type(e))
            print(e)
            traceback.print_tb(e.__traceback__)

    def run_weather_fetcher_thread(self):
        '''Method that starts the thread that will fetch weather data from
        yr.no.
        '''
        th = Thread(target=self.run_weather_fetcher, name='weatherFetcher')
        th.start()

    def run_server(self):
        '''Method used by the thread that will run the server to get Alexa
        requests.
        '''
        try:
            self.srv.run()
        except Exception as e:
            print('Exception at SmartCoil.run_server')
            print(type(e))
            print(e)
            traceback.print_tb(e.__traceback__)

    def run_server_thread(self):
        '''Method that starts the thread that will run the server to get Alexa
        requests.
        '''
        th = Thread(target=self.run_server, name='AlexaRequestsServer')
        th.daemon = True
        th.start()

    def run_gui(self):
        '''Method that starts the GUI. Run in the main thread of the app.
        '''
        self.gui.run()

    def commit_to_db(self, sql, params):
        '''Commits a given sql query to the SQLite databse.

        Args:
            sql (:obj:`str`): The SQL string to be executed.
            params (:obj:`list`): A list of parameters to be included in the
                query.
        '''
        with sqlite3.connect(self.dbase_path) as conn:
            crsr = conn.cursor()
            crsr.execute(sql, params)
            conn.commit()

    def report_app_status_to_db(self, status):
        '''Reports the status of the SmartCoil app to the database. This method
        is used when the app starts running and when it is interrupted.

        Args:
            status (:obj:`str`): The string status which could be 'ON' or 'OFF'
        '''
        sql = 'INSERT INTO APP_STATUS VALUES (?, ?)'
        tstamp = datetime.now()
        data = [tstamp, status]
        self.commit_to_db(sql, data)

    def commit_weather_data(self, tstamp = None):
        '''Commits weather information to the database.

        Args:
            tstamp (int, optional): Timestamp of the entry. If not passed, current time is used.
        '''
        if tstamp is None:
            tstamp = datetime.now()

        data = [tstamp] + self.wthr.get_conditions_data()
        sql = "INSERT INTO YR_WEATHER_API_DATA VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        self.commit_to_db(sql, data)

    def commit_sensor_data(self, tstamp = None):
        '''Commits BME680 sensor information to the database, specifically:
        - timestamp
        - temperature
        - pressure
        - humidity
        - gas resistance
        - air quality
        - whether the smartcoil is running at moment of commit

        Args:
            tstamp (int, optional): Timestamp of the entry. If not passed, current time is used.
        '''
        if tstamp is None:
            tstamp = datetime.now()

        data = [tstamp] + self.snsr.get_most_recent_readings() + [int(self.fancoil_running)]
        sql = "INSERT INTO SENSOR_BME680_DATA VALUES (?, ?, ?, ?, ?, ?, ?)"
        self.commit_to_db(sql, data)

    def commit_user_data(self, tstamp = None):
        '''Commits user GUI information to the database, specifically:
        - current target temperature
        - current fan speed

        Args:
            tstamp (int, optional): Timestamp of the entry. If not passed, current time is used.
        '''
        if tstamp is None:
            tstamp = datetime.now()

        u_temp = self.gui.root.get_user_temp()
        u_speed = self.gui.root.get_user_speed()
        data = [tstamp, u_temp, u_speed]
        sql = "INSERT INTO USER_DATA VALUES (?, ?, ?)"
        self.commit_to_db(sql, data)

    def sensor_ready(self):
        '''Checks if the BME680 sensor completed its prime period.

        Returns:
            bool: Whether the BME680 is ready for accurate readings or not (after priming).
        '''
        return self.snsr.sensor_ready()

    def get_current_temp(self):
        '''Gets the current temperature from the BME680 sensor.

        Returns:
            float: Temperature reading, default is in Fahrenheit but it could be changed in the
                corresponding sensor class.
        '''
        t, *_ = self.snsr.get_most_recent_readings()
        return t

    def get_user_screen_data(self):
        '''Gets the current information from the BME680 sensor that applies for the GUI screen.

        Returns:
            :obj:`tuple`: Tuple with indoor temperature, humidity and air quality values.
        '''
        t, p, h, g, a = self.snsr.get_most_recent_readings()
        return (
        '{} °F'.format(round(t))
        ,round(h)
        ,round(a)
        )

    def get_weather_screen_data(self):
        '''Gets the current information from the weather API sensor that applies for the GUI screen.

        Returns:
            :obj:`tuple`: Tuple with outdoor temperatureand weather forecast icon.
        '''
        return (self.wthr.temperature, self.wthr.weather_icon)

    def monitor_temperature(self, offset = 0):
        '''This method monitors the indoor status and take actions such as cooling/heating the room
        until it reaches the target temperature.

        Args:
            offset (int, optional): A value to add some padding for the target temperature. For
               example, if set to 3, and the target cooling temperature is 70 it will cool down the
               indoors until it hits 67. Notice that the offset is sign insensitive, for example
               both 3 and -3 behave the same way. Defaults to 0.
        '''
        try:
            # There's an initial offset to reach the target temperature plus some additional degrees.
            # However, once this target is reached, the offset is set to 2 in order to wait some time
            # until the room temperature is 2 degrees before the initial target again (disregarding the offset).
            dynamic_offset = 2 if self.target_reached else -abs(offset)

            mult  = 1 if self.mode == COOLING else -1
            trigger_fancoil = mult * self.get_current_temp() - mult * self.gui.root.get_user_temp() > dynamic_offset

            if not self.gui.root.user_turned_off_fancoil() and trigger_fancoil:
                if not self.rc.fancoil_is_on() or self.gui.root.get_speed_changed_flag():
                    self.target_reached = False
                    self.fancoil_running = True
                    self.rc.start_coil_at(self.gui.root.get_user_speed())
                    self.gui.root.clear_speed_changed_flag()
            else:
                if self.rc.fancoil_is_on():
                    self.target_reached = True
                    self.fancoil_running = False
                    self.rc.all_off()
        except Exception as e:
            print('Exception at SmartCoil.monitor_temperature')
            print(type(e))
            print(e)
            traceback.print_tb(e.__traceback__)

    def update_gui_user_values(self):
        '''Updates the current indoor temperature, humidity and air quality values in the graphic
        user interface by getting the information from the sensor object and passing them into the
        GUI object.
        '''
        tmp, hum, airq = self.get_user_screen_data()
        self.gui.root.updateCurrentTemp(tmp)
        self.gui.root.updateHumidity(hum)
        self.gui.root.updateAirQuality(airq)

    def update_gui_weather_values(self):
        '''Updates the current outdoor temperature and weather forecast icon in the graphic user
        interface by getting the information from the weather API object and passing them into the
        GUI object.
        '''
        tmp, icon = self.get_weather_screen_data()
        tmp_txt = '{} °F'.format(int(tmp))
        self.gui.root.updateTodayTemp(tmp_txt)
        self.gui.root.updateTodayIcon(icon)

    def process_new_sensor_data(self):
        '''Method used to process indoor readings when the sensor object notifies the main thread
        new information is available. The specific actions inside the method are to monitor the
        temperature, update GUI user values, and commit sensor data to the DB.
        '''
        self.monitor_temperature(offset=2)
        self.update_gui_user_values()
        self.commit_sensor_data()

    def process_new_weather_data(self):
        '''Method used to process weather readings when the weather API object notifies the main
        thread new information is available. The specific actions inside the method are to update
        GUI weather values and commit weather data to the DB.
        '''
        self.commit_weather_data()
        self.update_gui_weather_values()

    def process_new_gui_data(self):
        '''Method used to process GUI input when the GUI object notifies the main thread the user
        made some interaction. The specific actions inside the method are to monitor the temperature
        given any new input values and commit new GUI data (target temperature and fan speed) to the
        DB.
        '''
        prev_state = self.fancoil_running
        self.monitor_temperature(offset=2)
        curr_state = self.fancoil_running

        self.commit_user_data()

        # If adjusting the user temperature changes the fancoil state, report it to DB.
        fancoil_state_changed = prev_state != curr_state

        if fancoil_state_changed:
            self.commit_sensor_data()

    def alexa_switch_smartcoil(self, switch):
        '''Method used to perform the "switch" Amazon Alexa command. The action comes from the Flask
        server object and is processed by this thread, updating both the GUI and the relay module
        configuration.

        Params:
            switch (:obj:`str`): Either 'on' or 'off'. If 'on', the app will look for the last fan
                speed used to turn the SmartCoil with that same setup.
        '''
        speed = 0
        if switch == 'on':
            speed = self.gui.root.get_last_speed_seen()

        self.gui.root.set_user_speed(speed)
        # take advantage of the GUI processing method, since this case is similar.
        self.process_new_gui_data()

    def alexa_chg_smartcoil_temperature(self, temperature):
        '''Method used to perform the "change temperature" Amazon Alexa command. The action comes
        from the Flask server object and is processed by this thread, updating both the GUI and the
        relay module configuration.

        Params:
            temperature (int): The new target temperature to set.
        '''
        self.gui.root.set_user_temp(temperature)
        # take advantage of the GUI processing method, since this case is similar.
        self.process_new_gui_data()

    def alexa_chg_smartcoil_speed(self, speed):
        '''Method used to perform the "change fan speed" Amazon Alexa command. The action comes
        from the Flask server object and is processed by this thread, updating both the GUI and the
        relay module configuration.

        Params:
            speed (int): The new fan speed to set.
        '''
        self.gui.root.set_user_speed(speed)
        # take advantage of the GUI processing method, since this case is similar.
        self.process_new_gui_data()

    def alexa_get_smartcoil_state(self):
        '''Method used to perform the "get state" Amazon Alexa command. The action comes
        from the Flask server object and is processed by this thread, sending back the state of
        the app regarding target temperature, current temperature, weather the SmartCoil is turned
        on or off, and the fan speed.
        '''
        state = 'OFF' if self.gui.root.user_turned_off_fancoil() else self.mode
        speed = self.gui.root.get_last_speed_seen()
        cur_temp = round(self.get_current_temp())
        usr_temp = self.gui.root.get_user_temp()
        info = {'state': state, 'speed': speed, 'cur_temp': cur_temp, 'usr_temp': usr_temp}
        self.outbound_queue.put(utils.Message('APPMSG', 'SCOIL_STATE-R', info))


    def process_new_alexa_data(self, action, params):
        '''Helper method that acts as a swtch case clause. It determines which method to run based
        on a given action.

        Params:
            action (:obj:`str`): A string specifying the action to run:
                - 'SCOIL_SWTCH' for self.alexa_switch_smartcoil
                - 'SCOIL_TEMP' for self.alexa_chg_smartcoil_temperature
                - 'SCOIL_SPEED' for self.alexa_chg_smartcoil_speed
                - 'SCOIL_STATE' for self.alexa_get_smartcoil_state
            params (:obj:`dict`): Dictionary of parameters to be used by the method of the
                corresponding action.
        '''
        switcher = {
                    'SCOIL_SWTCH': lambda switch: self.alexa_switch_smartcoil(switch),
                    'SCOIL_TEMP': lambda temp: self.alexa_chg_smartcoil_temperature(temp),
                    'SCOIL_SPEED': lambda speed: self.alexa_chg_smartcoil_speed(speed),
                    'SCOIL_STATE': lambda x: self.alexa_get_smartcoil_state(),
                    }

        method = switcher.get(action, lambda: print('unrecognized Alexa action.'))
        method(params.get('value', None))

    def quit(self, signo, _frame):
        '''Cleanup method used when interrupting the app.

        Params:
            signo (int): Type of interrupt signal.
            _frame (:obj:`obj`): Current stack frame.
        '''

        print('cleaning up before exiting app...')
        self.exit.set()
        self.rc.cleanup()
        self.srv.close_logs()
        # Once terminated, report the app is down to the DB
        self.report_app_status_to_db('OFF')
        exit(0)

    def run_msg_handler(self):
        '''Method used by the thread that will handle incoming messages from other objects such as
        the BME680 sensor, GUI, weather API, or the Flask server.
        '''
        try:
            switcher = {
                        'SNSMSG': lambda x, y: self.process_new_sensor_data(),
                        'GUIMSG': lambda x, y: self.process_new_gui_data(),
                        'WTHMSG': lambda x, y: self.process_new_weather_data(),
                        'SRVMSG': lambda action, params: self.process_new_alexa_data(action, params),
                        'EXIT': lambda x, y: print('stopped awaiting messages..'),
                        }

            type = ''
            # wait for messages until an exit message (0) is received
            while type != 'EXIT':
                msg = self.inbound_queue.get()
                type = msg.type
                action = msg.action
                params = msg.params
                method = switcher.get(type, lambda: print('unrecognized message.'))

                method(action, params)
        except Exception as e:
            print('Exception at SmartCoil.run_msg_handler')
            print(type(e))
            print(e)
            traceback.print_tb(e.__traceback__)


    def run_msg_handler_thread(self):
        '''Method that starts the thread that will handle incoming messages from other objects.
        '''
        th = Thread(target=self.run_msg_handler, name='msghandler')
        th.start()

    def fetch_gui_data_init(self):
        '''This method checks for a previous configuration made by the user to restore such state.
        It's run as a thread and waits for the GUI to be initialized before making adjustments.
        '''
        try:
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

            # fetch most recent weather data and feed it to the GUI.
            self.wthr.retry_update_values()
            self.process_new_weather_data()
        except Exception as e:
            print('Exception at SmartCoil.fetch_gui_data_init')
            print(type(e))
            print(e)
            traceback.print_tb(e.__traceback__)


    def run_fetch_gui_data_init_thread(self):
        '''Method that starts the thread that will handle GUI state initialization.
        '''
        th = Thread(target=self.fetch_gui_data_init, name='usrdatainit')
        th.start()

    def run(self):
        '''Main method for the class in charge of running all relevant threads for the app to start.
        '''
        try:
            # handling CTRL-C internally to stop all related threads and cleanup before exiting
            for sig in ('TERM', 'HUP', 'INT'):
                signal.signal(getattr(signal, 'SIG'+sig), self.quit)

            # ENVIRONMENT RELATED THREADS:
            # spawn thread in charge of fetching BME680 sensor readings.
            self.run_sensor_fetcher_thread()
            # spawn thread in charge of fetching data from the weather API.
            self.run_weather_fetcher_thread()

            # MESSAGE HANDLING THREAD:
            # spawn thread in charge of handling messages from other classes and perform according actions.
            self.run_msg_handler_thread()

            # SERVER THREAD:
            # spawn thread in charge of running server for Amazon Alexa requests.
            self.run_server_thread()

            # GUI RELATED THREADS:
            # spawn thread that checks for previous user configuration and current weather values.
            self.run_fetch_gui_data_init_thread()
            # run GUI as part of the main thread.
            self.run_gui()
        except Exception as e:
            print('Exception at SmartCoil.run')
            print(type(e))
            print(e)
            traceback.print_tb(e.__traceback__)
