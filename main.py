from gpiozero import LED
from time import sleep     # Import the sleep function from the time module

led = LED(14)

if __name__ == '__main__':
    while True:  # Run forever
        led.on()
        sleep(1)
        led.off()
        sleep(1)
