/*
 * Sends sensordata to serial port
 *
 */
#include "S32K146.h"
#include <stdint.h>

#include "Clocks.h"
#include "IO.h"
#include "Timers.h"
#include "ADC.h"
#include "UART.h"


#include <stdlib.h>

uint16_t SensorValue;
uint32_t TimeInit;
uint8_t buffer[4];

int main(void) {
  cgmClockInit();
  cgmPccInit();
  cgmIoInit();
  cgmTimerInit();
  init_ADC();
  cgmUsbUartInit();

  for (;;){
    TimeInit = MilliSecondeCounter;
    scan_ADC();

    SensorValue = read_ADC(SENSOR_AN_INPUT5);
    while(MilliSecondeCounter - TimeInit < 100);
    itoa(SensorValue, &buffer, 10);
    cgmSendWait(buffer, 4);
    cgmSendWait((uint8_t *)"\r\n", 2);
  }
}
