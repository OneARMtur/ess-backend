import json
from pprint import pprint
import sqlite3
import time
import RPi.GPIO as GPIO
import python_daemon as daemon

GPIO.setmode(GPIO.BCM)
GPIO.setup(24, GPIO.OUT)
GPIO.setup(23, GPIO.OUT)

last_boiler_working_time = 0

room_status = {}

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

def update_status(ident, name, req_temp, current_temp):
    json_res = {}
    json_res['room_name']     = name
    json_res['room_temp']     = current_temp[0]
    json_res['room_ht']       = current_temp[1]
    json_res['room_req_temp'] = req_temp[0]
    json_res['room_req_htr']  = req_temp[1]
    fh = open('status_{}.json'.format(ident), 'w')
    fh.write(json.dumps(json_res))
    fh.close()

def get_current_temperature(ident):
    logger = logging.getLogger('sp_logger')
    con = sqlite3.connect('/home/pi/project/ess2.db')
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    ex = cur.execute('select * from stats order by time desc limit 5')
    r = ex.fetchall()
    return r

def is_heating_necessary(ident, name):
    required_temp = get_required_temperature(ident)
    r = get_current_temperature(ident)
    update_status(ident, name, required_temp, (r[0]['temp_room'], r[0]['temp_htr']))
    logger.warning('Required temperature is {}'.format(required_temp))
    for temp in r:
        if temp['temp_room'] > required_temp[0]:
            logger.warning('Temperature in {} is more than req'.format(temp))
            return False
        if temp['temp_htr'] is not None and temp['temp_htr'] > required_temp[1]:
            logger.warning('Heater temperature in {} is greater than threshold'.format(temp))
            return False
    return True

def set_valves_state(room_status):
    for k, v in room_status.iteritems():
        GPIO.output(k, v)


def check_rooms(config_name, last_boiler_working_time, room_status):
    turn_boiler_on = False
    logger = logging.getLogger('sp_logger')
    with open(config_name) as data_file:    
        data = json.load(data_file)
        for room in data['room_mapping']:
            name = room['name']
            ident = room['id']
            pin = room['pin']
            if is_heating_necessary(ident, name) == True:
#                GPIO.output(pin, 1)
                turn_boiler_on = True
                last_boiler_working_time = time.time()
                if pin not in room_status or room_status[pin] == 0:
                    logger.warning(u'Turn ON heating in room {}, {}'.format(ident,name))
                    room_status[pin] = 1
            else:
#                GPIO.output(pin, 0k)
                if pin not in room_status or room_status[pin] == 1:
                    logger.warning(u'Turn OFF heating in room {}, {}'.format(ident,name))
                    last_boiler_working_time = time.time()
                    room_status[pin] = 0
        logger.warning("Last boiler working time is {}".format(last_boiler_working_time))
        if turn_boiler_on == True:  
            logger.warning("Turn boiler on")
            set_valves_state(room_status)
            GPIO.output(23, 1)
        else: 
            GPIO.output(23, 0)
            logger.warning("Turn boiler off")
            if last_boiler_working_time + 60 < time.time():
                logger.warning("Finishing rooms")
                set_valves_state(room_status)

    return last_boiler_working_time

import logging
formatter = logging.Formatter(fmt='%(asctime)s %(message)s')

handler = logging.FileHandler('sp_output.log')
handler.setFormatter(formatter)

logger = logging.getLogger('sp_logger')
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

while True:
    last_boiler_working_time = check_rooms('config.json', last_boiler_working_time, room_status)
    time.sleep(30)
