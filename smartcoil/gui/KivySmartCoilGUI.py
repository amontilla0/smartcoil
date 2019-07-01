import os
os.environ["KIVY_NO_CONSOLELOG"] = "1"
from functools import wraps

from kivy.app import App

from kivy.uix.scatter import Scatter
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.slider import Slider
from kivy.core.window import Window
from kivy.graphics import Ellipse, Line
from pygame.mouse import set_cursor
from kivy.uix.widget import Widget
from kivy.properties import ObjectProperty, NumericProperty, ListProperty
from kivy.animation import Animation

from time import time
from math import cos, sin, pi, sqrt

from can import Message

class CircularSlider(Slider):
    circ_slider = ObjectProperty(None)
    tmpture_txt = ObjectProperty(None)
    thickness = NumericProperty(5)
    sm_handle_size = NumericProperty(15)
    lg_handle_size = NumericProperty(40)
    touch_y_pos = NumericProperty(0)

    hr = NumericProperty(0)
    hg = NumericProperty(0.44)
    hb = NumericProperty(0.96)
    ha = NumericProperty(1)
    hha = NumericProperty(0.3)

    handle_col = ListProperty([0, 0.44, 0.96, 1])
    halo_col = ListProperty([0, 0.44, 0.96, 0.3])

    handle_col2 = ListProperty([0.99765, 0.33333, 0, 0])
    halo_col2 = ListProperty([0.99765, 0.33333, 0, 0])

    cold_color = ListProperty([0,.44, .96])
    hot_color  = ListProperty([.99765, .33333, 0])

    def linear_coords(self, base_x, handle_size):
        radius = ((min(self.size[0], self.size[1]) - self.thickness / 2) /2)
        #center of circle, angle in degree and radius of circle
        center = (self.center_x - 5 - handle_size / 2, self.center_y + 5 - handle_size / 2)
        angle = self.trajectory_mapping(base_x)
        rad = angle * pi /180
        x = center[0] + (radius * cos(rad))
        y = center[1] + (radius * sin(rad))

        return (x, y)

    def trajectory_mapping(self, base_x):
        m = 240 / (self.right - self.x)
        # the -90 is for axis adjustment
        y = m * (base_x - self.x) + (-120) - 90
        # the negation (-1 * y) is to revert slider orientation result
        return -y

    def set_color(self):
        vn = self.value_normalized
        cc = self.cold_color
        hc = self.hot_color

        self.handle_col = (cc[0], cc[1], cc[2], 1 - vn)
        self.halo_col = (cc[0], cc[1], cc[2], (1 - vn) * 0.3)

        self.handle_col2 = (hc[0], hc[1], hc[2], vn)
        self.halo_col2 = (hc[0], hc[1], hc[2], vn * 0.3)

class GUIWidget(BoxLayout):
    LEFT_PADDING = NumericProperty(15)

    def __init__(self, bus, **kwargs):
        super(GUIWidget, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.ids.logo.source = os.path.join(os.path.dirname(__file__), '../../assets/icons/smartcoil-logo.png')
        self.ids.h_icon.source = os.path.join(os.path.dirname(__file__), '../../assets/icons/humidity_icon.png')
        self.ids.a_icon.source = os.path.join(os.path.dirname(__file__), '../../assets/icons/wave_icon.png')
        self.ids.c_sldr.set_color()
        self.bus = bus
        self.speed = 1
        self.last_usr_tmp_seen = int(self.ids.c_sldr.value)

    def on_touch_up(self, touch):
        if self.last_usr_tmp_seen != int(self.ids.c_sldr.value):
            self.bus.send(Message(data=b'GUIMSG'))
            self.last_usr_tmp_seen = int(self.ids.c_sldr.value)

        return super(GUIWidget, self).on_touch_up(touch)

    def updateCurrentTemp(self, tmp):
        self.c_sldr.ids.curr_tmpture_txt.text = 'currently {}'.format(tmp)

    def updateHumidity(self, hum):
        self.h_lab.text = '{}%'.format(hum)

    def updateAirQuality(self, aq):
        self.a_lab.text = '{}%'.format(aq)

    def updateTodayTemp(self, tmp):
        self.tod_tmp.text = '{}'.format(tmp)

    def updateTodayIcon(self, src):
        self.tod_icon.source = src

    def get_user_temp(self):
        return int(self.c_sldr.ids.tmpture_txt.text)

    def set_user_temp(self, temp):
        self.c_sldr.value = temp

    def user_turned_off_fancoil(self):
        return self.speed == 0

    def get_user_speed(self):
        return self.speed

    def set_user_speed(self, speed):
        self.speed = speed

        off = self.ids.off_button
        lo = self.ids.lo_button
        mi = self.ids.mi_button
        hi = self.ids.hi_button
        buttons = [off, lo, mi, hi]

        for b in buttons:
            b.state = 'normal'

        buttons[speed].state = 'down'

    def fancoil_on_lo(self):
        self.speed = 1
        self.bus.send(Message(data=b'GUIMSG'))

    def fancoil_on_mi(self):
        self.speed = 2
        self.bus.send(Message(data=b'GUIMSG'))

    def fancoil_on_hi(self):
        self.speed = 3
        self.bus.send(Message(data=b'GUIMSG'))

    def fancoil_off(self):
        self.speed = 0
        self.bus.send(Message(data=b'GUIMSG'))


class SmartCoilGUIApp(App):
    def __init__(self, bus = None):
        super(SmartCoilGUIApp, self).__init__()
        self.bus = bus

    def build(self):
        return GUIWidget(self.bus)

if __name__ == "__main__":
    SmartCoilGUIApp().run()
