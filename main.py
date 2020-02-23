# -*- coding: utf-8 -*-

import datetime
import ftplib
import io
import os
import sys
import time

import RPi.GPIO as GPIO
import smbus

'''
thing = '/home/pi/quick2wire-python-api'
sys.path.append(thing)
from quick2wire.parts.pcf8591 import *
from quick2wire.i2c import I2CMaster
'''

import platform
print(platform.python_version())

FTP = 'ftp.paullafond.com'
USERNAME = 'paullafondcom'
PASSWORD = 'Mil0380v!'
VOLTAGE_PAGE = 'voltage.html'
INTERVAL = .01  # number of seconds between microchip
POST_INTERVAL = 20 # number of measurements between posts fot ftp
SAMPLES = 500 # number of voltage samples averaged togetherper measurement
LOGPOST = 10  # number of log entires before log is posted to ftp
HTML_FILE = '/home/pi/PycharmProjects/read_voltage_python3/html_page.html'
LOGFILE = '/home/pi/Desktop/monitor_microchip.log'
log_counter = 0

address = 0x48
A0 = 0x48
bus = smbus.SMBus(1)

leds = {'blue': 25, 'green': 12, 'red': 16}
states = {'on': GPIO.HIGH, 'off': GPIO.LOW}
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

for led in leds:
    GPIO.setup(leds[led], GPIO.OUT)


def led_toggle(color, state):
    GPIO.output(leds[color], states[state])


def post_to_ftp(page, file_):
    try:
        session = ftplib.FTP(FTP, USERNAME, PASSWORD)
        session.storlines('STOR {}'.format(page), file_)
        session.quit()
        led_toggle('red', 'off')
    except Exception as e:
        print(e)
        log(get_current_time(), 'could not post to {}/{}'.format(FTP, page))
        led_toggle('red', 'on')


def log(current_time, message):
    global log_counter
    log_counter += 1
    log = LOGFILE if os.path.exists(LOGFILE) else os.path.basename(LOGFILE)
    message = '{} | {}\n'.format(current_time, message)
    with open(log, 'a') as f:
        f.write(message)
    sys.stdout.write(message)
    if log_counter == LOGPOST:
        log_counter = 0
        with open(log, 'r') as f:
            data = b'\n'.join(
                [line.strip().encode('utf-8') for line in f.readlines()])
            file_ = io.BytesIO(data)
            post_to_ftp(os.path.basename(log), file_)


def map_values_to_voltage(value):
    OldMax = 177.1
    OldMin = 137.0
    NewMax = 24.3
    NewMin = 9.0
    OldRange = (OldMax - OldMin)
    NewRange = (NewMax - NewMin)
    NewValue = (((value - OldMin) * NewRange) / OldRange) + NewMin
    return round(NewValue, 1)


def measure_voltage(html_page, count=0, total=0, post=0):
    while True:
        led_toggle('green', 'off')
        bus.write_byte(address, A0)
        value = bus.read_byte(address)
        count += 1
        total += value
        time.sleep(0.001)
        if count == SAMPLES:
            post += 1
            average = total / SAMPLES
            voltage = map_values_to_voltage(average)
            if post == POST_INTERVAL:
                post = 0
                update_html_page(html_page, voltage)
            print('value:{}  voltage:{}'.format(average, voltage))
            total = 0
            count = 0
            led_toggle('green', 'on')
            time.sleep(INTERVAL)


def get_html_page():
    with open(HTML_FILE, 'r') as f:
        return f.read()


def get_current_time():
    return datetime.datetime.now().strftime("%Y.%m.%d %H:%M:%S")


def update_html_page(html_page, voltage):
    new_html = []
    for line in html_page.split('\n'):
        if '[voltage]' in line:
            new_html.append(
                line.replace('[voltage]', str(voltage)).encode('utf-8'))
        elif '[last_updated]' in line:
            new_html.append(
                line.replace('[last_updated]', get_current_time()).encode('utf-8'))
        else:
            new_html.append(line.encode('utf-8'))

    html_file_object = io.BytesIO(b'\n'.join(new_html))
    post_to_ftp(VOLTAGE_PAGE, html_file_object)


if __name__ == '__main__':
    html_page = get_html_page()
    led_toggle('blue', 'on')
    led_toggle('red', 'on')
    try:
        measure_voltage(html_page)
    except KeyboardInterrupt:
        led_toggle('blue', 'off')
        led_toggle('green', 'off')
        led_toggle('red', 'off')