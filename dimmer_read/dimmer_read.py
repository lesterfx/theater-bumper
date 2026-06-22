#!/usr/bin/env python3

import serial
import time

class DimmerRead:
    def __init__(self, parent):
        self.parent = parent
        self.ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=.1)
        # time.sleep(2)  # let Arduino reset/settle
        self.value = 0

    def read_forever(self):
        try:
            while not self.parent.stop_event.is_set():
                line = self.ser.readline().decode('utf-8', errors='replace').strip()
                if not line:
                    continue
                try:
                    self.value = float(line)
                    # print(f"Phase angle: {value:.09f}")
                except ValueError:
                    print(f"Non-numeric line: {line}")
        except KeyboardInterrupt:
            print("Stopped.")
        finally:
            self.ser.close()

if __name__ == '__main__':
    DimmerRead()

