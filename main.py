from configparser import ConfigParser
import multiprocessing
import serial
import time
import logging
import threading
import queue

serialports = []
processpool = []

# Setup the logging feature
logging.basicConfig(level=logging.DEBUG,
                    format='(%(threadName)-9s) %(message)s', )


class Measurement:
    def __init__(self, value):
        self.val = value

    def validate(self):
        retval = True
        # Serial connections can inject some false data
        for char in self.val:
            if not char.isdigit():
                retval = False
        # 12bit value, so 4095 max
        if self.val < 0 or self.val > 4095:
            retval = False
        return retval


def serialreadforever(serinstance):
    try:
        while True:
            line = serinstance.readline()
            line = line.decode("utf-8").strip()
            logging.debug(line)
    # The connection can be a bit flaky
    except serial.SerialException:
        serialreadforever(serinstance)


def setup():
    # Open the private Config File
    config = ConfigParser()
    config.read('config.ini')

    serialports.append(serial.Serial(port=config['Serial']['Port'],
                                     baudrate=config['Serial']['Baud']))


if __name__ == "__main__":
    setup()
    print('Version 8')
    # Check if SerialPort is outputting data
    if serialports[0].readline():
        for ser in serialports:
            process = multiprocessing.Process(target=serialreadforever, args=(ser,))
            process.start()
            processpool.append(process)

        time.sleep(20)
        [p.terminate() for p in processpool]
