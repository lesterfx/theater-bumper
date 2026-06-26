
import os
import time

class FakeRead:
    def __init__(self, parent):
        self.parent = parent
        self._next_value = 0
        self._current_value = 0
        self._value_time = time.monotonic()

    @property
    def value(self) -> float:
        elapsed = time.monotonic() - self._value_time
        change_needed = self._next_value - self._current_value
        if not change_needed:
            return self._next_value
        percent = abs(elapsed*.7) / abs(change_needed)
        if percent > 1:
            return self._next_value
        else:
            if percent < .5:
                eased = percent * percent
            else:
                eased = 1 - ((1-percent) * (1-percent))
            percent = percent * .6 + eased * .4
            return self._current_value * (1-percent) + self._next_value * percent

    @value.setter
    def value(self, value: float):
        self._current_value = self.value
        self._next_value = float(value)
        self._value_time = time.monotonic()

    def read_forever(self):
        try:
            while not self.parent.stop_event.is_set():
                try:
                    line = open('fakelevel.txt').read()
                except FileNotFoundError:
                    time.sleep(0.01)
                    continue
                if not line:
                    continue
                try:
                    self.value = float(line)
                    os.remove('fakelevel.txt')
                except ValueError:
                    print(f"Non-numeric line: {line}")
        except KeyboardInterrupt:
            print("Stopped.")
        except:
            self.parent.stop_event.set()
            time.sleep(1)
            raise