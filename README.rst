=========
SmartCoil
=========


.. image:: https://img.shields.io/pypi/v/smartcoil.svg
        :target: https://pypi.python.org/pypi/smartcoil

.. image:: https://img.shields.io/travis/amontilla0/smartcoil.svg
        :target: https://travis-ci.org/amontilla0/smartcoil

.. image:: https://readthedocs.org/projects/smartcoil/badge/?version=latest
        :target: https://smartcoil.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status




Full interface to automate a home-based fan coil unit with a Raspberry Pi. Notice that fan coil unit wiring may involve high voltage manipulation, any handling of this kind is under your own responsibility.

This project is based in the following technologies:

- Kivy for GUI that allows temperature and fan speed manipulation through a PiTFT touch screen.
- BME680 sensor for current temperature, humidity and air quality information in the GUI.
- 4 relay cluster to control coil valve and fan states.
- Meteorologisk institutt weather API for additional information such as outdoors temperature and weather forecast in the GUI.
- Flask for server deployment + Pagekite for HTTPS tunneling to control the app through an Alexa Smart Home Skill.

* Free software: MIT license
