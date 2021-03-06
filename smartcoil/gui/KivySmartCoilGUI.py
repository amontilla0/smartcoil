import os
import traceback
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

from ..utils import utils

class CircularSlider(Slider):
    '''Subclass that handles all interaction with the circular slider that sets
    the target temperature for the Smartcoil.
    '''
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
        '''Helper method to get coordinates in a semi circle based on a linear
        value (x).

        Args:
            base_x (double): The input x coordinate, basically the x value where
                the cursor (or finger is placed).
            handle_size (double): the radius of the slider handle, taken in
                account for final coordinates adjustment.

        Returns:
            :obj:`tuple`: (x, y) coordinates where the slider should be rendered
            as a semi-circle trajectory.
        '''
        radius = ((min(self.size[0], self.size[1]) - self.thickness / 2) /2)
        #center of circle, angle in degree and radius of circle
        center = (self.center_x - 5 - handle_size / 2, self.center_y + 5
                  - handle_size / 2)
        angle = self.trajectory_mapping(base_x)
        rad = angle * pi /180
        x = center[0] + (radius * cos(rad))
        y = center[1] + (radius * sin(rad))

        return (x, y)

    def trajectory_mapping(self, base_x):
        '''Helper method to get the angle to use for the semi-circle
        coordinates.

        Args:
            base_x (double): The input x coordinate, basically the x value where
                the cursor (or finger is placed).

        Returns:
            double: the resulting angle in the slider semi-circle, based on the
                input x coordinate.
        '''
        m = 240 / (self.right - self.x)
        # the -90 is for axis adjustment
        y = m * (base_x - self.x) + (-120) - 90
        # the negation (-1 * y) is to revert slider orientation result
        return -y

    def set_color(self):
        '''Sets the color of the slider handle based on its current position.
        The color transitions from blue hues for colder temperatures to orange
        hues for hotter values.
        '''
        vn = self.value_normalized
        cc = self.cold_color
        hc = self.hot_color

        self.handle_col = (cc[0], cc[1], cc[2], 1 - vn)
        self.halo_col = (cc[0], cc[1], cc[2], (1 - vn) * 0.3)

        self.handle_col2 = (hc[0], hc[1], hc[2], vn)
        self.halo_col2 = (hc[0], hc[1], hc[2], vn * 0.3)

class GUIWidget(BoxLayout):
    '''Main widget class encapsulating temperature slider, fan speed buttons and
    status information.
    '''
    LEFT_PADDING = NumericProperty(15)

    def __init__(self, outqueue, **kwargs):
        '''The module is intented to be a secondary thread of the base class
        SmartCoil.
        To allow communication between the main thread and this thread, a Queue
        can be passed as an argument.

        Args:
            outqueue (:obj:`Queue`): Outbound queue to send messages
                to the main thread.
            **kwargs: Arbitrary keyword arguments.
        '''
        super(GUIWidget, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.ids.logo.source = os.path.join(os.path.dirname(__file__),
                                '../../assets/icons/smartcoil-logo.png')
        self.ids.h_icon.source = os.path.join(os.path.dirname(__file__),
                                '../../assets/icons/humidity_icon.png')
        self.ids.a_icon.source = os.path.join(os.path.dirname(__file__),
                                '../../assets/icons/wave_icon.png')
        self.ids.tod_icon.source = os.path.join(os.path.dirname(__file__),
                                    '../../assets/icons/placeholder.png')
        self.ids.c_sldr.set_color()
        self.outbound_queue = outqueue
        self.speed = 1
        self.speed_changed = False
        self.last_usr_spd_seen = 1
        self.last_usr_tmp_seen = int(self.ids.c_sldr.value)

    def on_touch_move(self, touch):
        '''Listener for the event of dragging a finger on the PiTFT screen.

        Args:
            touch (:obj:`tuple`): Parent-related coordinates of the touch event.
        '''
        sup = super(GUIWidget, self).on_touch_move(touch)
        self.ids.c_sldr.set_color()
        return sup

    def on_touch_down(self, touch):
        '''Listener for the event of pressing a finger on the PiTFT screen.

        Args:
            touch (:obj:`tuple`): Parent-related coordinates of the touch event.
        '''
        sup = super(GUIWidget, self).on_touch_down(touch)
        self.ids.c_sldr.set_color()
        return sup

    def on_touch_up(self, touch):
        '''Listener for the event of releasing a finger from the PiTFT screen.

        Args:
            touch (:obj:`tuple`): Parent-related coordinates of the touch event.
        '''
        sup = super(GUIWidget, self).on_touch_up(touch)
        if self.last_usr_tmp_seen != int(self.ids.c_sldr.value):
            self.outbound_queue.put(utils.Message('GUIMSG'))
            self.last_usr_tmp_seen = int(self.ids.c_sldr.value)

        return sup

    def updateCurrentTemp(self, tmp):
        '''Assigns the label for current indoor temperature to specified value.

        Args:
            tmp (double): Current indoor temperature to assign.
        '''
        self.c_sldr.ids.curr_tmpture_txt.text = 'currently {}'.format(tmp)

    def updateHumidity(self, hum):
        '''Assigns the label for current humidity to specified value.

        Args:
            hum (double): Current humidity to assign.
        '''
        self.h_lab.text = '{}%'.format(hum)

    def updateAirQuality(self, aq):
        '''Assigns the label for current ait quality to specified value.

        Args:
            aq (double): Current air quality to assign.
        '''
        self.a_lab.text = '{}%'.format(aq)

    def updateTodayTemp(self, tmp):
        '''Assigns the label for current outdoor temperature to specified value.

        Args:
            tmp (double): Current outdoor temperature to assign.
        '''
        self.tod_tmp.text = '{}'.format(tmp)

    def updateTodayIcon(self, src):
        '''Assigns the icon for today's forecast to specified value.

        Args:
            src (:obj:`str`): URI of the icon for today's forecast.
        '''
        try:
            self.tod_icon.source = src
        except Exception as e:
            print('Exception at GUIWidget.updateTodayIcon')
            print(type(e))
            print(e)
            traceback.print_tb(e.__traceback__)

    def get_user_temp(self):
        '''Gets the temperature value assigned by the user in the GUI.

        Returns:
            int: The target temperature assigned by the user.
        '''
        return int(self.c_sldr.ids.tmpture_txt.text)

    def set_user_temp(self, temp):
        '''Sets the target temperature value in the GUI.

        Args:
            temp (int): The target temperature to assign.
        '''
        self.c_sldr.value = temp
        self.ids.c_sldr.set_color()

    def user_turned_off_fancoil(self):
        '''Verifies if the user turned off the smartcoil by checking if the
        speed is zero.

        Returns:
            bool: Whether the smartcoil is explicitly turned off or not.
        '''
        return self.speed == 0

    def get_user_speed(self):
        '''Gets the speed currently set for the smartcoil.

        Returns:
            int: A value ranging from 0 (off) to 3 (high speed).
        '''
        return self.speed

    def get_last_speed_seen(self):
        '''Gets the last speed set before the smartcoil was turned off.

        Returns:
            int: A value ranging from 1 (low speed) to 3 (high speed).
        '''
        return self.last_usr_spd_seen

    def get_speed_changed_flag(self):
        '''Gets a flag that verifies if the speed was recently changed.

        Returns:
            bool: Whether the speed was recently changed.
        '''
        return self.speed_changed

    def clear_speed_changed_flag(self):
        '''Clears the "speed_changed" flag, to be used right after the flag is processed in the
            main SmartCoil app.
        '''
        self.speed_changed = False

    def set_user_speed(self, speed):
        '''Sets the speed value in the GUI.

        Args:
            speed (int): A value from 0 to 3 for off, low, medium or high speed.
        '''
        self.speed = speed
        self.speed_changed = True
        if speed > 0:
            self.last_usr_spd_seen = speed

        off = self.ids.off_button
        lo = self.ids.lo_button
        mi = self.ids.mi_button
        hi = self.ids.hi_button
        buttons = [off, lo, mi, hi]

        for b in buttons:
            b.state = 'normal'

        buttons[speed].state = 'down'

    def fancoil_on_lo(self):
        '''Helper method to report the speed was set to low on the outbound queue (read by th main
        SmartCoil app).
        '''
        self.speed = 1
        self.last_usr_spd_seen = 1
        self.speed_changed = True
        self.outbound_queue.put(utils.Message('GUIMSG'))

    def fancoil_on_mi(self):
        '''Helper method to report the speed was set to medium on the outbound queue (read by th main
        SmartCoil app).
        '''
        self.speed = 2
        self.last_usr_spd_seen = 2
        self.speed_changed = True
        self.outbound_queue.put(utils.Message('GUIMSG'))

    def fancoil_on_hi(self):
        '''Helper method to report the speed was set to high on the outbound queue (read by th main
        SmartCoil app).
        '''
        self.speed = 3
        self.last_usr_spd_seen = 3
        self.speed_changed = True
        self.outbound_queue.put(utils.Message('GUIMSG'))

    def fancoil_off(self):
        '''Helper method to report the speed was set to off on the outbound queue (read by th main
        SmartCoil app).
        '''
        self.speed = 0
        self.outbound_queue.put(utils.Message('GUIMSG'))


class SmartCoilGUIApp(App):
    '''Serves as the class that initiates the graphic user interface with Kivy.
    '''
    def __init__(self, outqueue = None):
        '''The module is intented to be a secondary thread of the base class
        SmartCoil.
        To allow communication between the main thread and this thread, a Queue
        can be passed as an argument.

        Args:
            outqueue (:obj:`Queue`, optional): Outbound queue to send messages
                to the main thread.
        '''
        super(SmartCoilGUIApp, self).__init__()
        self.outbound_queue = outqueue

    def build(self):
        '''Required Kivy method to build and show the GUI.
        '''
        return GUIWidget(self.outbound_queue)

if __name__ == "__main__":
    SmartCoilGUIApp().run()
