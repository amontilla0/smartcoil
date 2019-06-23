#from kivy.core.window import Window
from functools import wraps

from kivy.app import App

from kivy.uix.scatter import Scatter
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.slider import Slider
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line
from pygame.mouse import set_cursor
from kivy.uix.widget import Widget
from kivy.properties import ObjectProperty, NumericProperty, ListProperty
from kivy.clock import Clock
from kivy.animation import Animation

from time import time
from math import cos, sin, pi, sqrt

from colour import Color
import colorsys

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

    cold_color = ObjectProperty(Color(rgb=(0,.44, .96)))
#    hot_color  = ObjectProperty(Color(rgb=(.91765, .53333, 0)))
    hot_color  = ObjectProperty(Color(rgb=(.99765, .33333, 0)))

    color_map = ListProperty([])

    def __init__(self, **kwargs):
        Clock.schedule_once(self.post_init, 0)

        super(CircularSlider, self).__init__(**kwargs)

    def post_init(self, dt):
        self.color_map = list(self.cold_color.range_to(self.hot_color, self.max - self.min))

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

        self.handle_col = (cc.red, cc.green, cc.blue, 1 - vn)
        self.halo_col = (cc.red, cc.green, cc.blue, (1 - vn) * 0.3)

        self.handle_col2 = (hc.red, hc.green, hc.blue, vn)
        self.halo_col2 = (hc.red, hc.green, hc.blue, vn * 0.3)

    def on_touch_move(self, touch):
        sup = super(CircularSlider, self).on_touch_move(touch)
        self.touch_y_pos = touch.y
        self.set_color()
        l = self.tmpture_txt
        l.y = self.center_y + 20 - l.texture_size[1] / 2
        return sup

    def on_touch_down(self, touch):
        sup = super(CircularSlider, self).on_touch_down(touch)
        self.touch_y_pos = touch.y
        self.set_color()
        l = self.tmpture_txt
        l.y = self.center_y + 20 - l.texture_size[1] / 2
        return sup

class GUIWidget(BoxLayout):
    LEFT_PADDING = NumericProperty(15)
    c_sldr = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(GUIWidget, self).__init__(**kwargs)
        self.orientation = 'vertical'

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return

        super(GUIWidget, self).on_touch_down(touch)

    def on_touch_move(self, touch):
        if not self.collide_point(*touch.pos):
            return

        super(GUIWidget, self).on_touch_move(touch)

    def updateHumidity(self, hum):
        c_sldr.curr_tmpture_txt.text = 'currently {}'.format(hum)

    def updateAirQuality(self, aq):
        pass

    def btn1_on_press(self):
        print('pressing button..')
        self.updateHumidity('69 °F')

class SmartCoilGUIApp(App):
    def build(self):
        return GUIWidget()

if __name__ == "__main__":
    SmartCoilGUIApp().run()
