from configparser import ConfigParser
from datetime import datetime, timezone
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
    def __init__(self, meas_name, val):
        self.timestamp = self.createtimestamp()
        self.value = self.sanitize(val)
        self.name = meas_name

    def validate(self):
        retval = True
        # Serial connections can inject some false data
        for char in self.value:
            if not char.isdigit():
                retval = False
        # 12bit value, so 4095 max
        if self.value < 0 or self.value > 4095:
            retval = False
        return retval

    @staticmethod
    def sanitize(inputbytestring):
        return inputbytestring.decode("utf-8").strip()

    @staticmethod
    def createtimestamp():
        return datetime.utcnow().isoformat("T") + "Z"

    def print(self):
        return f'{self.name}, {self.timestamp}: {self.value}'


def serialreadforever(measurementname, serinstance):
    try:
        while True:
            line = serinstance.readline()
            m = Measurement(measurementname, line)
            logging.debug(m.print())
    # The connection can be a bit flaky, Restart
    except serial.SerialException:
        serialreadforever(serinstance, measurementname)


def setup():
    # Open the private Config File
    config = ConfigParser()
    config.read('config.ini')

    serialsectionnames = [s for s in config.sections() if s.startswith('Serial')]
    for sname in serialsectionnames:
        serialconfig = config[sname]
        serialports.append([serialconfig['Name'], serial.Serial(port=serialconfig['Port'],
                                                                baudrate=serialconfig['Baud'])])


if __name__ == "__main__":
    setup()
    print('Version 10')
    # Check if SerialPort is outputting data
    if serialports[0][1].readline():
        for name, ser in serialports:
            process = multiprocessing.Process(target=serialreadforever, args=(name, ser))
            process.start()
            processpool.append(process)

        time.sleep(20)
        [p.terminate() for p in processpool]
