import json
from pprint import pprint
import sqlite3
import time
import sys
from python_daemon import Daemon

def getTime(time_str):
    r = int(time_str.split(':')[0])*60
    r += int(time_str.split(':')[1])
    return r

def getKey(entry):
    return getTime(entry['start'])

def get_required_temperature(room_id):
    with open('/home/pi/project/schedule_{}.json'.format(room_id)) as data_file:
        data = json.load(data_file)
        entry_list = sorted(data['schedule'],key=getKey)
        time_list = []
        current_time = time.localtime()
        for i in entry_list:
            minutes = current_time.tm_hour*60 + current_time.tm_min
            if minutes >= getTime(i['start']) and minutes <= getTime(i['end']) and getTime(i['start']) <= getTime(i['end']):
                return (float(i['t']), float(i['th']))
            if minutes >= getTime(i['start']) and minutes <= getTime(i['end'])+24*60 and getTime(i['start']) > getTime(i['end']):
                return (float(i['t']), float(i['th']))


def store_statistics(ident, name, req_temp, current_temp):
    s = u'INSERT INTO stats (id, room, time, temp_room, temp_htr, target_room, target_htr) VALUES(\'{}\',\'{}\',{}, {}, {}, {}, {})'.format(str(ident),name, int(time.time()), current_temp[0], current_temp[1], req_temp[0], req_temp[1])
    cur.execute(s)
    con.commit()
    return True

def update_status(ident, name, req_temp, current_temp):
    json_res = {}
    json_res['room_name']     = name
    json_res['room_temp']     = current_temp[0]
    json_res['room_ht']       = current_temp[1]
    json_res['room_req_temp'] = req_temp[0]
    json_res['room_req_htr']  = req_temp[1]
    fh = open('/home/pi/project/status_{}.json'.format(ident), 'w')
    fh.write(json.dumps(json_res))
    fh.close()


def read_temperature(path):
    f = file(path, 'r')
    data = f.read()
    temp = data.split('\n')[1].split('=')[1]
    return temp[0:2] + '.' + temp[2:-1]

pt_templ = "/sys/bus/w1/devices/{}/w1_slave"

con = sqlite3.connect('/home/pi/project/ess2.db')
cur = con.cursor()

class StatsDaemon(Daemon):
    def run(self):
        while True:
            with open('/home/pi/project/config.json') as data_file:
                data = json.load(data_file)
                for room in data['room_mapping']:
                    name  = room['name']
                    rs    = room['room_sensor']
                    hs    = room['heater_sensor']
                    ident = room['id']
                    t = read_temperature(pt_templ.format(rs))
                    t_h = read_temperature(pt_templ.format(hs))
                    req = get_required_temperature(ident)
                    store_statistics(ident, name, req, (t, t_h))
                    update_status(ident, name, req, (t, t_h))
            time.sleep(60)

if __name__ == "__main__":
        daemon = StatsDaemon('/tmp/stats.pid', stdout = '/dev/stdout', stderr = '/dev/stderr')
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
