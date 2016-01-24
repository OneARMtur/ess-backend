import pdb
import sys
import json
import time
import logging
import sqlite3
import RPi.GPIO as GPIO
from pprint import pprint
from python_daemon import Daemon

BOILER_PIN = 23

GPIO.setmode(GPIO.BCM)
GPIO.setup(24, GPIO.OUT)
GPIO.setup(23, GPIO.OUT)
GPIO.setup(22, GPIO.OUT)

room_status = {}
room_temp_series = {}

def get_current_temperature(project_dir, ident):
    with open(project_dir + '/status_{}.json'.format(ident)) as data_file:
        data = json.load(data_file)
        return data['temp_room'], data['temp_radiator']

def get_required_temperature(project_dir, ident):
    with open(project_dir + '/status_{}.json'.format(ident)) as data_file:
        data = json.load(data_file)
        return data['target_temp_room'], data['target_temp_radiator']

def add_temperature_to_series(ident, temp):
    if ident in room_temp_series:
        room_temp_series[ident].append(temp)
    else:
        room_temp_series[ident] = [temp]
    if len(room_temp_series[ident]) > 10:
        room_temp_series[ident].pop(0)

def is_heating_necessary(project_dir, ident, name):
    req_room_t, req_radiator_t = get_required_temperature(project_dir, ident)
    current_temp = get_current_temperature(project_dir, ident)
    add_temperature_to_series(ident, current_temp)
    r = room_temp_series[ident]
    logger = logging.getLogger('sp_logger')
    logger.warning(u'Checking room {}'.format(name))
    logger.warning('series is {}'.format(r))
    logger.warning('Required temperature is {}, {}'.format(req_room_t, req_radiator_t))
    for current_room_t, current_radiator_t in r:
        if float(current_room_t) > req_room_t:
            logger.warning('Temperature in {} is more than req'.format(current_room_t))
            return False
        if current_radiator_t is not None and float(current_radiator_t) > req_radiator_t:
            logger.warning('Heater temperature in {} is greater than threshold'.format(current_raidator_t))
            return False
    return True

def set_valves_state(room_status):
    for k, v in room_status.iteritems():
        GPIO.output(k, v)


def check_rooms(config_name, last_boiler_working_time, room_status):
    turn_boiler_on = False
    logger = logging.getLogger('sp_logger')
    logger.warning('=========== Processing rooms =============')
    with open(config_name) as data_file:
        data = json.load(data_file)
        project_dir = data['project_dir']
        for room in data['room_mapping']:
            name  = room['name']
            ident = room['id']
            if 'pin' not in room:
                logger.warning(u'Skipping room {}, no output pin'.format(name))
            pin   = room['pin']
            if is_heating_necessary(project_dir, ident, name) == True:
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


class ScheduleDaemon(Daemon):
    def run(self):
        formatter = logging.Formatter(fmt='%(asctime)s %(message)s')

        with open('/etc/ess.config') as data_file:
            config_data = json.load(data_file)
            project_dir = config_data['project_dir']

        handler = logging.FileHandler(project_dir + '/sp_output.log')
        handler.setFormatter(formatter)

        logger = logging.getLogger('sp_logger')
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        last_boiler_working_time = 0
        while True:
            last_boiler_working_time = check_rooms('/etc/ess.config', last_boiler_working_time, room_status)
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
