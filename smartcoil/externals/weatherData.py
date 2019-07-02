from urllib.request import urlopen
import json
from yr.libyr import Yr
from datetime import datetime
from can import Message
import time

class WeatherData:
    def __init__(self, bus = None):
        self.bus = bus
        self.update_values()

    def update_values(self):
        print('in up')
        w = self.get_weather()
        f = w.forecast()
        print('in up2')
        now = next(f)
        fcast = next(f)
        now_data = now['location']
        fcast_data = fcast['location']
        print('in up3')
        # Element denoting the precipitation in celcius.
        self.temperature = float(now_data['temperature']['@value'])
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
        print('in up4')

    def get_conditions_text(self):
        return '''temperature is {0:.1f} °C with humidity of {1:.0f}% and pressure of {2:.1f} hPa. General conditions are {3}
Wind is {4:.1f} Km/h {5} and we have an expected precipitation of {6} millimeters.'''.format(self.temperature, self.humidity, self.pressure, self.condition, self.wind_speed, self.wind_dir_name, self.precipitation)

    def get_conditions_data(self):
        return [self.lat, self.lon, self.temperature, self.humidity, self.pressure, self.condition, self.condition_code, self.wind_speed, self.wind_dir_name, self.wind_dir_degs, self.precipitation]

    def _get_geolocation(self, api_key):
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
        geo = self._get_geolocation('ba8e737cd1ce0e3bf0ede0cd1caeea68')
        weather = Yr(location_xyz=(geo[1], geo[0], 0))

        return weather

    def run_updates(self, exit_evt = None):
        sleep_func = time.sleep if exit_evt == None else exit_evt.wait
        weatherUpdated = False
        waitTimeMins = 1

        while True if exit_evt == None else not exit_evt.is_set():
            now_minute = datetime.now().minute

            if now_minute % waitTimeMins == 0 and not weatherUpdated:
                print('in')
                # do-while until data from weather API is fetched
                while True if exit_evt == None else not exit_evt.is_set():
                    try:
                        print('in2')
                        self.update_values()
                        raise ZeroDivisionError
                        break
                    except Exception as e:
                        print('Exception while fetching weather data, retrying..')
                        print('{}: {}'.format(type(e), e))
                        sleep_func(3)

                if self.bus is not None:
                    self.bus.send(Message(data=b'WTHMSG'))

                weatherUpdated = True

            elif now_minute % waitTimeMins != 0:
                weatherUpdated = False

            sleep_func(1)

if __name__ == "__main__":
    w = WeatherData()

    print(w.get_conditions_text())
    print()
    print(w.get_conditions_data())
