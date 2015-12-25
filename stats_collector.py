import json
from pprint import pprint
import sqlite3
import time


def read_temperature(path):
    f = file(path, 'r')
    data = f.read()
    temp = data.split('\n')[1].split('=')[1]
    return temp[0:2] + '.' + temp[2:-1]

pt_templ = "/sys/bus/w1/devices/{}/w1_slave"
 
con = sqlite3.connect('/home/pi/project/ess2.db')
cur = con.cursor()

print cur.lastrowid
with open('config.json') as data_file:    
    data = json.load(data_file)
    for room in data['room_mapping']:
        name = room['name']
        rs = room['room_sensor']
        hs = room['heater_sensor']
        t = read_temperature(pt_templ.format(rs))
        t_h = read_temperature(pt_templ.format(hs))
        s = 'INSERT INTO stats (room, time, temp_room, temp_htr) VALUES(\'{}\',{}, {}, {})'.format(name, int(time.time()), t, t_h)
        print s
        cur.execute(s)
        con.commit()

pprint(data)
