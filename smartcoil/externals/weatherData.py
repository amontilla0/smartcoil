from urllib.request import urlopen
import json
from yr.libyr import Yr
from datetime import datetime
import time
from ..utils import utils

class WeatherData:
    '''Serves as the class that periodically fetches information from the norwegian weather API.'''

    def __init__(self, outqueue = None, temp_in_f = True):
        '''The module is intented to be a secondary thread of the base class SmartCoil.
        To allow communication between the main thread and this thread, a Queue can be passed
        as an argument.

        Args:
            outqueue (:obj:`Queue`, optional): Outbound queue to send messages to the main thread.
            temp_in_f (boolean, optional): Whether to transform all temperature values from celcius
                                           to fahrenheit. Defaults to True.
        '''
        self.outbound_queue = outqueue
        self.temp_in_f = temp_in_f
        self.update_values()

    def update_values(self):
        '''Method to get all weather information from the API into this class attributes.
        All the data taken from the service is:
        - Current outdoor temperature (originally in celcius).
        - Wind direction in degrees.
        - Wind direction name in cardinal points abbreviation.
        - Wind speed (originally in meters per second, translated to KMh).
        - Current humidity percentage.
        - Current pressure in hPa.
        - Precipitation forecast in mm.
        - Forecast condition name, such as 'PartCloud'
        - A related forecast condition code.
        - Forecast condition icon.
        '''
        w = self.get_weather()
        f = w.forecast()

        now = next(f)
        fcast = next(f)
        now_data = now['location']
        fcast_data = fcast['location']

        # Element denoting the temperature.
        self.temperature = float(now_data['temperature']['@value'])
        if self.temp_in_f:
            self.temperature = utils.c_to_f(self.temperature)

        # Element denoting the wind direction in degrees (0 to 360).
        self.wind_dir_degs = float(now_data['windDirection']['@deg'])
        # Element denoting the wind direction name in cardinal direction acronym, i.e. 'NW'.
        self.wind_dir_name = now_data['windDirection']['@name']
        # Element denoting the wind speed in KM/h (originally comes from the API in meters per sec).
        self.wind_speed = round(float(now_data['windSpeed']['@mps']) * 3.6, 2)
        # Element denoting the humidity percentage.
        self.humidity = float(now_data['humidity']['@value'])
        # Element denoting the pressure in hPa.
        self.pressure = float(now_data['pressure']['@value'])

        # Element denoting the precipitation in mm.
        self.precipitation = float(fcast_data['precipitation']['@value'])
        # Element denoting the condition text of current weather, i.e. 'PartCloud'
        self.condition = fcast_data['symbol']['@id']
        # Element denoting the condition id of current weather. Useful for obtaining weather icons.
        self.condition_code = fcast_data['symbol']['@number']
        is_night = 0 if datetime.now().hour < 18 else 1
        self.weather_icon = 'https://api.met.no/weatherapi/weathericon/1.1?content_type=image%2Fpng&is_night={}&symbol={}'.format(is_night, self.condition_code)

    def retry_update_values(self, exit_evt = None):
        '''Helper method that retries getting data from the API and catches any server errors.

        Args:
            exit_evt (:obj:`Event`, optional): Event flag to manage thread cleaning before exiting the full app.
        Returns:
            bool: Wether the method had to try more than once to get information from the weather API.
        '''
        sleep_func = time.sleep if exit_evt == None else exit_evt.wait
        retried = False

        while True if exit_evt == None else not exit_evt.is_set():
            try:
                self.update_values()
                break
            except Exception as e:
                retried = True
                ex_name = type(e).__name__
                ex_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print('[{}] EXCEPTION: ({}: {}) raised while fetching weather data, retrying...'.format(ex_time, ex_name, e))
                sleep_func(3)

        return retried

    def get_conditions_text(self):
        ''' Method to get all fetched information in a human readable string.

        Returns:
            :obj:`str`: human readable text showing almost all the information gotten from the API.
        '''
        temp_units = 'F' if self.temp_in_f else 'C'
        return '''temperature is {0:.1f} °{1} with humidity of {2:.0f}% and pressure of {3:.1f} hPa. General conditions are {4}
Wind is {5:.1f} Km/h {6} and we have an expected precipitation of {6} millimeters.'''.format(self.temperature, temp_units, self.humidity, self.pressure, self.condition, self.wind_speed, self.wind_dir_name, self.precipitation)

    def get_conditions_data(self):
        '''Helper method to get all informational attributes from this class.
        Returns:
            :obj:`list`: array of data fetched from the API (and location service) in the following order:
            - Latitude.
            - Longitude.
            - Temperature.
            - Humidity.
            - Pressure.
            - Condition name.
            - Condition code.
            - Wind speed.
            - Wind direction name.
            - Wind direction degrees.
            - Precipitation.
        '''
        return [self.lat, self.lon, self.temperature, self.humidity, self.pressure, self.condition, self.condition_code, self.wind_speed, self.wind_dir_name, self.wind_dir_degs, self.precipitation]

    def _get_geolocation(self, api_key):
        '''Helper method to get the current geolocation of the device based on its public IP address.

        Agrs:
            api_key (:obj:`str`): The key to use with the geolocation API (api.ipstack.com/).
        Returns:
            :obj:`tuple`: The latitude and longitude for this device's public IP.
        '''
        my_ip = urlopen('http://ip.42.pl/raw').read().decode('utf-8')
        baseurl = 'http://api.ipstack.com/{}?access_key={}'.format(my_ip, api_key)

        f = urlopen(baseurl)
        json_string = f.read().decode('utf-8')
        j = json.loads(json_string)
        f.close()
        self.lat = j['latitude']
        self.lon = j['longitude']

        return (self.lat, self.lon)

    def get_weather(self):
        '''Gets the object from the weather API library based on a given latitude and longitude.

        Returns:
            :obj:`tuple`: An instance of Yr from the yr.no library (weather API).'''
        geo = self._get_geolocation('ba8e737cd1ce0e3bf0ede0cd1caeea68')
        weather = Yr(location_xyz=(geo[1], geo[0], 0))

        return weather

    def run_updates(self, exit_evt = None):
        '''The main loop that constantly fetches information from the weather API. More specifically,
        this method gets information from the weather API on periods of multiples of 5 minutes.
        Example: 7:00pm, 7:05pm, 7:10pm, and so on.

        Args:
            exit_evt (:obj:`Event`, optional): Event flag to manage thread cleaning before exiting the full app.
        '''
        sleep_func = time.sleep if exit_evt == None else exit_evt.wait
        weatherUpdated = False
        last_updated_minute = -1
        waitTimeMins = 5

        while True if exit_evt == None else not exit_evt.is_set():
            now_minute = datetime.now().minute

            if now_minute % waitTimeMins == 0 and not weatherUpdated:
                ex_time = None
                ex_name = None
                retried = False

                # do-while until data from weather API is fetched
                retried = self.retry_update_values(exit_evt=exit_evt)

                if retried:
                    succ_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    print('[{}] SUCCESS: Exception {} raised at {} has been dealt with.'.format(succ_time, ex_name, ex_time))

                if self.outbound_queue is not None:
                    self.outbound_queue.put(utils.Message('WTHMSG'))

                weatherUpdated = True
                last_updated_minute = now_minute

            elif last_updated_minute != now_minute:
                weatherUpdated = False

            sleep_func(1)

if __name__ == "__main__":
    w = WeatherData()

    print(w.get_conditions_text())
    print()
    print(w.get_conditions_data())
