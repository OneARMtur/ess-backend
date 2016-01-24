import sys
import json
import time
import sqlite3
import logging
from pprint import pprint
from python_daemon import Daemon

def getTime(time_str):
    r = int(time_str.split(':')[0])*60
    r += int(time_str.split(':')[1])
    return r

def get_required_temperature(project_dir, room_id):
    with open(project_dir + '/schedule_{}.json'.format(room_id)) as data_file:
        data = json.load(data_file)
        entry_list = sorted(data['schedule'],key=lambda x: getTime(x))
        time_list = []
        current_time = time.localtime()
        for i in entry_list:
            minutes = current_time.tm_hour*60 + current_time.tm_min
            if minutes >= getTime(i['start']) and minutes <= getTime(i['end']) and getTime(i['start']) <= getTime(i['end']):
                return (float(i['temp_room']), float(i['temp_radiator']))
            if (minutes >= getTime(i['start']) or minutes <= getTime(i['end'])) and getTime(i['start']) > getTime(i['end']):
                return (float(i['temp_room']), float(i['temp_radiator']))


def store_statistics(project_dir, ident, name, req_temp, current_temp):
    con = sqlite3.connect(project_dir + '/ess2.db')
    cur = con.cursor()
    s = u'INSERT INTO stats (id, room, time, temp_room, temp_radiator, target_temp_room, target_temp_radiator) VALUES(\'{}\',\'{}\',{}, {}, {}, {}, {})'.format(str(ident),name, int(time.time()), current_temp[0], current_temp[1], req_temp[0], req_temp[1])
    cur.execute(s)
    con.commit()
    return True

def update_status(project_dir, ident, name, req_temp, current_temp):
    json_res = {}
    json_res['room_name']             = name
    json_res['temp_room']             = current_temp[0]
    json_res['temp_radiator']         = current_temp[1]
    json_res['target_temp_room']      = req_temp[0]
    json_res['target_temp_radiator']  = req_temp[1]
    fh = open(project_dir + '/status_{}.json'.format(ident), 'w')
    fh.write(json.dumps(json_res))
    fh.close()


def read_temperature(path):
    temp_str = '85.0'
    logger = logging.getLogger('sp_logger')
    atmp = 0
    while temp_str == '85.0':
        f = file(path, 'r')
        data = f.read()
        temp = data.split('\n')[1].split('=')[1]
        temp_str = temp[0:2] + '.' + temp[2:-1]
        atmp += 1
        if temp_str == '85.0':
            time.sleep(1)
        if atmp >= 3:
            logger.warning("After 3 attempts temp is {}; room {}".format(temp_str, path))
            break
    return temp_str


class StatsDaemon(Daemon):
    def run(self):
        pt_templ = "/sys/bus/w1/devices/{}/w1_slave"

        with open('/etc/ess.config') as data_file:
            config_data = json.load(data_file)
            project_dir = config_data['project_dir']

        formatter = logging.Formatter(fmt='%(asctime)s %(message)s')

        handler = logging.FileHandler(project_dir + '/sc_output.log')
        handler.setFormatter(formatter)

        logger = logging.getLogger('sc_logger')
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        while True:
            for room in config_data['room_mapping']:
                name  = room['name']
                rs    = room['room_sensor']
                hs    = room['heater_sensor']
                ident = room['id']
                t = read_temperature(pt_templ.format(rs))
                t_h = read_temperature(pt_templ.format(hs))
                req = get_required_temperature(project_dir, ident)
                update_status(project_dir, ident, name, req, (t, t_h))
                store_statistics(project_dir, ident, name, req, (t, t_h))
            time.sleep(60)

if __name__ == "__main__":
        daemon = StatsDaemon('/tmp/stats.pid', stdout = '/dev/stdout', stderr = '/tmp/errout')
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
