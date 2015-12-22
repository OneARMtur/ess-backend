def read_temperature(path):
    f = file(path, 'r')
    data = f.read()
    temp = data.split('\n')[1].split('=')[1]
    print temp[0:2] + '.' + temp[2:-1]

read_temperature('/sys/bus/w1/devices/28-00000455cbb8/w1_slave')
