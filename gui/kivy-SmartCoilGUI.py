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
    last_seen_value = NumericProperty(0)
    last_seen_time = NumericProperty(0)

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
        center = (self.center_x - handle_size / 2, self.center_y - handle_size / 2)
        angle = self.trajectory_mapping(base_x)
        rad = angle * pi /180
        x = center[0] + (radius * cos(rad))
        y = center[1] + (radius * sin(rad))

        l = self.tmpture_txt
        if l is not None and time() - self.last_seen_time > 0.2 and int(self.value) != int(self.last_seen_value):
            Animation.cancel_all(l)
#            l.y = 240
            # print('--->', int(self.value), int(self.last_seen_value), int(self.value) != int(self.last_seen_value))
            self.last_seen_time = time()
            self.last_seen_value = int(self.value)
            anim = Animation(y=l.y+40, duration=0.0) + Animation(y = l.y, duration=0.95, t='out_elastic')
            anim.start(l)
#            anim = Animation(y = l.y -10, duration=0.3, t='out_elastic')
#            anim.start(l)
        else:
            self.last_seen_time = time()
            self.last_seen_value = int(self.value)

        return (x, y)

    def trajectory_mapping(self, base_x):
        m = (120 - (-120)) / (self.right - self.x)
        # the -90 is for axis adjustment
        y = m * (base_x - self.x) + (-120) - 90
        # the negation (-1 * y) is to revert slider orientation result
        return -y

    def circ_coords(self, base_x, handle_size):
        adjust = self.thickness / 2 + handle_size / 4
        above_horizon = self.touch_y_pos >=  self.center_y
        radius = min(self.width, self.height) / 2 - adjust
        center = (self.center_x - 30, self.center_y - handle_size / 2)


        x = base_x - adjust
        y = sqrt(pow(radius, 2) - pow(base_x + (1 if base_x <= self.center_x else -1) * adjust - self.center_x, 2)) + self.center_y
#        y = sqrt(pow(radius, 2) - pow(base_x - self.center_x, 2)) + self.center_y - adjust
        print('touch y: {}'.format(self.touch_y_pos <  self.center_y))

        y = y if above_horizon else self.top - y

        return (x, y)

    def set_color_old(self):
        curr_col = self.color_map[int(min(self.value - self.min, len(self.color_map) - 1))]
        self.handle_col = (curr_col.red, curr_col.green, curr_col.blue, 1)
        self.halo_col = (curr_col.red, curr_col.green, curr_col.blue, 0.3)

    def set_color(self):
        vn = self.value_normalized
        cc = self.cold_color
        hc = self.hot_color

        self.handle_col = (cc.red, cc.green, cc.blue, 1 - vn)
        self.halo_col = (cc.red, cc.green, cc.blue, (1 - vn) * 0.3)

        self.handle_col2 = (hc.red, hc.green, hc.blue, vn)
        self.halo_col2 = (hc.red, hc.green, hc.blue, vn * 0.3)

    def set_color_colmap(self):
        r, g, b = self.colmap(self.value_normalized)
        self.handle_col = (r/255, g/255, b/255, 1)
        self.halo_col = (r/255, g/255, b/255, 0.3)
        print(self.value_normalized, "(", r, g, b, ")")

    def colmap(self, norm_val):
        assert 0 <= norm_val <= 1
        # blue to red
        hue = .66667 - norm_val*.66667
        r, g, b = colorsys.hsv_to_rgb(hue, 1, 1)
        return map(lambda x: int(255 * x), (r, g, b))

    def on_touch_move(self, touch):
        sup = super(CircularSlider, self).on_touch_move(touch)
        self.touch_y_pos = touch.y
        self.set_color()
        l = self.tmpture_txt
        l.y = self.center_y - l.texture_size[1] / 2
        return sup

    def on_touch_down(self, touch):
        sup = super(CircularSlider, self).on_touch_down(touch)
        self.touch_y_pos = touch.y
        self.set_color()
        l = self.tmpture_txt
        l.y = self.center_y - l.texture_size[1] / 2
        return sup

class GUIWidget(BoxLayout):
    LEFT_PADDING = NumericProperty(30)
    lbl1 = ObjectProperty(None)
    c_sldr = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(GUIWidget, self).__init__(**kwargs)
        self.orientation = 'vertical'

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return
        self.lbl1.text = 'x: '+str(int(touch.x)) + ', ' + str(int(touch.y))
        #temp_slider = self.ids.temp_slider
        #handle1 = temp_slider.canvas.get_group('handle1')[0]
        #handle1.pos = (touch.x, 30)
        super(GUIWidget, self).on_touch_down(touch)

    def on_touch_move(self, touch):
        if not self.collide_point(*touch.pos):
            return
        self.lbl1.text = 'x: '+str(int(touch.x)) + ', ' + str(int(touch.y))
        #temp_slider = self.ids.temp_slider
        #handle1 = temp_slider.canvas.get_group('handle1')[0]
        #handle1.pos = (touch.x, 30)
        super(GUIWidget, self).on_touch_move(touch)

    def animate_slider(self, value, secs):
        dist = value - self.c_sldr.value
        mult = abs(dist) / dist

        while abs(value - self.c_sldr.value) > 0.5:
            Clock.schedule_once(self.move_slider, secs)
            next(tess())

    def move_slider(self, mult):
        self.c_sldr.value = self.c_sldr.value + mult * 0.5

    def yield_to_sleep(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            gen = func(*args)
            def next_step(*_):
                try:
                    t = next(gen)  # this executes 'func' before next yield and returns control to you
                except StopIteration:
                    pass
                else:
                    Clock.schedule_once(next_step, t)  # having control you can resume func execution after some time
            next_step()
        return wrapper

    @yield_to_sleep  # use this decorator to cast 'yield' to non-blocking sleep
    def test_function(self):
        for i in range(10):
            if (i % 2 == 0):
                yield 1  # use yield to "sleep"
                print('val', self.c_sldr.value)
            else:
                print('odd nums..')

    def btn1_on_press(self):
        self.test_function() #self.animate_slider(90,1)
        print('button 1 press..')
#        exit()

class SmartCoilGUIApp(App):
    def build(self):
        Window.bind(mouse_pos=lambda w, p: setattr(self.lbl1, 'text', str(p)))
        return GUIWidget()

#    def build(self):
#        layout = BoxLayout(spacing=10, background_color=Color(1,0,0,1))
#        l = Label(text="Hello!",
#                  font_size=40, size_hint=(.333, 1))
#        layout = BoxLayout(spacing=10)
#        btn1 = Button(text='Hello', size_hint=(.333, 1))
#        btn2 = Button(text='World', size_hint=(.333, 1))
#        btn1.bind(on_press=self.btn1_press)
#        layout.add_widget(btn1)
#        layout.add_widget(btn2)
#        layout.add_widget(l)
#
#        return layout
#
#    def btn1_on_press(self, instance):
#        print('exiting')
#        exit()

if __name__ == "__main__":
    SmartCoilGUIApp().run()
