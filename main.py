import queue

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from configparser import ConfigParser
from datetime import datetime
from queue import Queue
import multiprocessing
import serial
import time
import logging

serialports = []
processpool = []
measurement_queue = Queue(maxsize=20)

# Setup the logging feature
logging.basicConfig(level=logging.DEBUG,
                    format='(%(threadName)-9s) %(message)s', )


# Class to prepare the data for the InfluxDB database
# Has some basic validation and sanitization features
class Measurement:
    def __init__(self, meas_name, val):
        self.timestamp = self.createtimestamp()
        self.value = self.sanitize(val)
        self.name = meas_name

    def validate(self):
        retval = True
        # Serial connections can inject some false data
        if not self.value.isdigit():
            retval = False

        # 12bit value, so 4095 max
        intval = int(self.value)
        if intval < 0 or intval > 4095:
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
            if m.validate() and measurement_queue.not_full:
                measurement_queue.put_nowait(m)
    # The connection can be a bit flaky, Restart
    except serial.SerialException:
        serialreadforever(serinstance, measurementname)
    # Stop the process if the queue is full
    except queue.Full:
        return


def setup():
    # Open the private Config File
    config = ConfigParser()
    config.read('config.ini')

    # Retrieve the serial sections from the .ini file and create the serialport instances
    serialsectionnames = [s for s in config.sections() if s.startswith('Serial')]
    for sname in serialsectionnames:
        serialconfig = config[sname]
        serialports.append([serialconfig['Name'], serial.Serial(port=serialconfig['Port'],
                                                                baudrate=serialconfig['Baud'])])


if __name__ == "__main__":
    setup()
    print('Version 12')
    # Check if SerialPort is outputting data
    if serialports[0][1].readline():
        for name, ser in serialports:
            process = multiprocessing.Process(target=serialreadforever, args=(name, ser))
            process.start()
            processpool.append(process)

        # Keep waiting untill every process is killed
        while all([p.is_alive() for p in processpool]):
            time.sleep(0.01)
            pass

        print('Queue full')
        [p.terminate() for p in processpool]
