from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from configparser import ConfigParser
from urllib3 import exceptions
from datetime import datetime
from queue import Full, Empty
from multiprocessing import Queue, Process
import serial
import time
import logging

serialports = []
processpool = []

# Setup the logging feature
logging.basicConfig(level=logging.DEBUG,
                    format='(%(threadName)-9s) %(levelname)-8s %(message)s', )


# Class to prepare the data for the InfluxDB database
# Has some basic validation and sanitization features
class Measurement:
    def __init__(self, meas_name, val):
        self.timestamp = self.createtimestamp()
        self.value = self.sanitize(val)
        self.name = meas_name

    def validate(self):
        requirements = []
        # Serial connections can inject some false data
        requirements.append(self.value.isalnum())
        if all(requirements):
            intval = int(self.value)
            # Newlines may be lost in transmission and this may exceed the maximum 12bit value
            requirements.append(intval > 0)
            requirements.append(intval < 4095)
        return all(requirements)

    @staticmethod
    def sanitize(inputbytestring):
        return str(inputbytestring.decode("utf-8").strip())

    @staticmethod
    def createtimestamp():
        return datetime.utcnow().isoformat("T") + "Z"

    def print(self):
        return f'{self.name}, {self.timestamp}: {self.value}'


def serialreadforever(queue, measurementname, serinstance):
    try:
        while True:
            line = serinstance.readline()
            m = Measurement(measurementname, line)
            if m.validate():
                queue.put_nowait(m)
    # The connection can be a bit flaky, Restart
    except serial.SerialException:
        serialreadforever(queue, measurementname, serinstance)
    # Stop the process if the queue is full
    except Full:
        exit(7)


def databasewriteforever(queue, dbconfig, write_api):
    # Keep waiting untill a child is killed for whatever reason
    while True:
        time.sleep(0.01)
        try:
            # Consume the queue
            m = queue.get(block=False)
        except Empty:
            pass
        else:
            # Break out of the loop of the Database disappears
            if not writemeasurement(dbconfig, write_api, m):
                break


# Retrieve the serial sections from the .ini file and create the serialport instances
def setupserial(conf):
    serialsectionnames = [s for s in conf.sections() if s.startswith('Serial')]
    for sname in serialsectionnames:
        serialconfig = conf[sname]
        serialports.append([serialconfig['Name'], serial.Serial(port=serialconfig['Port'],
                                                                baudrate=serialconfig['Baud'])])


# Retrieve the database config and create the influxdb client
def setupdatabase(dbconf):
    dbclient = InfluxDBClient(url=f'{dbconf["Schema"]}://{dbconf["Host"]}:{dbconf["Port"]}',
                              token=dbconf["Token"],
                              org=dbconf["Org"])
    try:
        dbclient.ready()
        return dbclient
    except exceptions.NewConnectionError:
        return None


# Create the influxDB datapoint and sends it to the server
def writemeasurement(dbconfig, dbclient, measurement):
    logging.debug(measurement.print())
    point = Point("KoffieApparaat")\
        .tag("sensor", measurement.name)\
        .field('analog_value', int(measurement.value))\
        .time(measurement.timestamp)
    try:
        dbclient.write(dbconfig['Bucket'], dbconfig['Org'], point)
    except exceptions.NewConnectionError:
        return False
    else:
        del measurement
        return True


# Function for main as not to create globals
def main():
    # Open the private Config File
    config = ConfigParser()
    config.read('config.ini')

    # Create the neccasary serial connections
    setupserial(config)

    # Create the InfluxDB connection
    dbconfig = config['InfluxDB']
    dbclient = setupdatabase(dbconfig)

    # Create the Measurement Queue
    queue = Queue(maxsize=20)

    # Check if SerialPorts is outputting data
    if all([s[1].readline() for s in serialports]):
        # Check if the DBclient
        if dbclient:
            write_api = dbclient.write_api(write_options=SYNCHRONOUS)
            # Assign a process to each serialport and run it
            for name, ser in serialports:
                process = Process(target=serialreadforever, args=(queue, name, ser))
                processpool.append(process)

            # Create a Process for writing data to the database
            process = Process(target=databasewriteforever, args=(queue, dbconfig, write_api))
            processpool.append(process)

            # Start all the processes
            for p in processpool:
                p.start()

            # Wait for any of them to fail
            while all([p.is_alive() for p in processpool]):
                time.sleep(0.01)
            dbclient.close()

    # Check if the Queue was full when exiting
    if any([p.exitcode == 7 for p in processpool]):
        logging.error('Measurement queue full')

    # The database was unreachable
    if dbclient is None:
        logging.error('The database was unreachable')

    # Kill all orphaned child processes
    [p.terminate() for p in processpool]


# Explicit entrypoint for script
if __name__ == "__main__":
    main()
