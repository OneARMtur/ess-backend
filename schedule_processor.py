import json
from pprint import pprint
import sqlite3
import time

def getTime(time_str):
    r = int(time_str.split(':')[0])*60
    r += int(time_str.split(':')[1])
    return r

def getKey(entry):
    return getTime(entry['start'])
 
def get_required_temperature(room_id):
    with open('schedule_{}.json'.format(room_id)) as data_file:    
        data = json.load(data_file)
        pprint(data)
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
    required_temp = get_required_temp(ident)
    for temp in r:
        if temp[2] < required_temp[0]:
            return False
    return True

def turn_heater_on(ident)
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(24, GPIO.OUT)
    GPIO.output(24, 1)

def check_rooms(config_name):
    with open('config.json') as data_file:    
        data = json.load(data_file)
        for room in data['room_mapping']:
            name = room['name']
            ident = room['id']
            if is_heating_necessary(ident) == True:
                GPIO.output(room['pin'], 1)
            else:
                GPIO.output(room['pin'], 0)

