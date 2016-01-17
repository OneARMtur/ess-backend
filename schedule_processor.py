import json
from pprint import pprint
import sqlite3
import sys
import time
import pdb
import RPi.GPIO as GPIO
from python_daemon import Daemon

BOILER_PIN = 23

GPIO.setmode(GPIO.BCM)
GPIO.setup(24, GPIO.OUT)
GPIO.setup(23, GPIO.OUT)
GPIO.setup(22, GPIO.OUT)

room_status = {}
room_temp_series = {}

def getTime(time_str):
    r = int(time_str.split(':')[0])*60
    r += int(time_str.split(':')[1])
    return r

def getKey(entry):
    return getTime(entry['start'])


def get_current_temperature(ident):
    with open('/home/pi/project/status_{}.json'.format(ident)) as data_file:
        data = json.load(data_file)
        return data['room_temp'], data['room_ht']

def get_required_temperature(ident):
    with open('/home/pi/project/status_{}.json'.format(ident)) as data_file:
        data = json.load(data_file)
        return data['room_req_temp'], data['room_req_htr']

def add_temperature_to_series(ident, temp):
    if ident in room_temp_series:
        room_temp_series[ident].append(temp)
    else:
        room_temp_series[ident] = [temp]
    if len(room_temp_series[ident]) > 10:
        room_temp_series[ident].pop(0)

def is_heating_necessary(ident, name):
    required_temp = get_required_temperature(ident)
    current_temp = get_current_temperature(ident)
    add_temperature_to_series(ident, current_temp)
    r = room_temp_series[ident]
    logger = logging.getLogger('sp_logger')
    logger.warning(u'Checking room {}'.format(name))
    logger.warning('series is {}'.format(r))
    logger.warning('Required temperature is {}'.format(required_temp))
    for temp in r:
        if float(temp[0]) > required_temp[0]:
            logger.warning('Temperature in {} is more than req'.format(temp))
            return False
        if temp[1] is not None and float(temp[1]) > required_temp[1]:
            logger.warning('Heater temperature in {} is greater than threshold'.format(temp))
            return False
    return True

def set_valves_state(room_status):
    for k, v in room_status.iteritems():
        GPIO.output(k, v)


def check_rooms(config_name, last_boiler_working_time, room_status):
    turn_boiler_on = False
    logger = logging.getLogger('sp_logger')
    logger.warning("=========== processing rooms =============")
    with open(config_name) as data_file:
        data = json.load(data_file)
        for room in data['room_mapping']:
            name  = room['name']
            ident = room['id']
            pin   = room['pin']
            if is_heating_necessary(ident, name) == True:
                turn_boiler_on = True
                last_boiler_working_time = time.time()
                if pin not in room_status or room_status[pin] == 0:
                    logger.warning(u'Turn ON heating in room {}, {}'.format(ident,name))
                    room_status[pin] = 1
            else:
                if pin not in room_status or room_status[pin] == 1:
                    logger.warning(u'Turn OFF heating in room {}, {}'.format(ident,name))
                    last_boiler_working_time = time.time()
                    room_status[pin] = 0
        #logger.warning("Last boiler working time is {}".format(last_boiler_working_time))
        if turn_boiler_on == True:
            logger.warning("Turn boiler on")
            set_valves_state(room_status)
            GPIO.output(BOILER_PIN, 1)
        else:
            GPIO.output(BOILER_PIN, 0)
            logger.warning("Turn boiler off")
            if last_boiler_working_time + 60 < time.time():
                logger.warning("Finishing rooms")
                set_valves_state(room_status)

    return last_boiler_working_time

import logging
formatter = logging.Formatter(fmt='%(asctime)s %(message)s')

handler = logging.FileHandler('/home/pi/project/sp_output.log')
handler.setFormatter(formatter)

logger = logging.getLogger('sp_logger')
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

con = sqlite3.connect('/home/pi/project/ess2.db')
cur = con.cursor()

class ScheduleDaemon(Daemon):
    def run(self):
        last_boiler_working_time = 0
        while True:
            last_boiler_working_time = check_rooms('/home/pi/project/config.json', last_boiler_working_time, room_status)
            time.sleep(30)

if __name__ == "__main__":
        daemon = ScheduleDaemon('/tmp/schedule.pid', stdout = '/dev/stdout', stderr = '/dev/stderr')
        if len(sys.argv) == 2:
                if 'start' == sys.argv[1]:
                        daemon.start()
                elif 'stop' == sys.argv[1]:
                        daemon.stop()
                elif 'restart' == sys.argv[1]:
                        daemon.restart()
                else:
                        print "Unknown command"
                        sys.exit(2)
                sys.exit(0)
        else:
                print "usage: %s start|stop|restart" % sys.argv[0]
                sys.exit(2)
