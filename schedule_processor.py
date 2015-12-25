import json
from pprint import pprint
import sqlite3
import time
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(24, GPIO.OUT)
GPIO.setup(23, GPIO.OUT)

last_boiler_working_time = 0

def getTime(time_str):
    r = int(time_str.split(':')[0])*60
    r += int(time_str.split(':')[1])
    return r

def getKey(entry):
    return getTime(entry['start'])
 
def get_required_temperature(room_id):
    with open('schedule_{}.json'.format(room_id)) as data_file:    
        data = json.load(data_file)
        entry_list = sorted(data['schedule'],key=getKey)
        time_list = []
        current_time = time.localtime()
        for i in entry_list:
            minutes = current_time.tm_hour*60 + current_time.tm_min
            if minutes >= getTime(i['start']) and minutes <= getTime(i['end']):
                return (float(i['t']), float(i['th']))
        # throw ex

def is_heating_necessary(ident):
    con = sqlite3.connect('/home/pi/project/ess2.db')
    cur = con.cursor()
    ex = cur.execute('select * from stats order by time desc limit 5')
    r = ex.fetchall()
    required_temp = get_required_temperature(ident)
    logging.warning('Required temperature is {}'.format(required_temp))
    for temp in r:
        if temp[2] > required_temp[0]:
            logging.warning('Temperature in {} is less than req'.format(temp))
            return False
        if temp[3] is not None and temp[3] > required_temp[1]:
            logging.warning('Heater temperature in {} is greater than threshold'.format(temp))
            return False
    return True


def check_rooms(config_name, last_boiler_working_time):
    turn_boiler_on = False
    with open(config_name) as data_file:    
        data = json.load(data_file)
        for room in data['room_mapping']:
            name = room['name']
            ident = room['id']
            if is_heating_necessary(ident) == True:
                GPIO.output(room['pin'], 1)
                turn_boiler_on = True
                last_boiler_working_time = time.time()
                logging.warning('Turn ON heating in room {}, {}'.format(ident,name))
            else:
                GPIO.output(room['pin'], 0)
                logging.warning('Turn OFF heating in room {}, {}'.format(ident,name))
                last_boiler_working_time = time.time()
        if turn_boiler_on == True:
            GPIO.output(23, 1)
        elif last_boiler_working_time + 60 < time.time():
            GPIO.output(23, 0)
    return last_boiler_working_time

import logging
logging.basicConfig(format='%(asctime)s %(message)s')

while True:
    last_boiler_working_time = check_rooms('config.json', last_boiler_working_time)
    time.sleep(30)
