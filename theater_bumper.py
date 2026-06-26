#!/usr/bin/env python3
import threading
import time

from pixel_display.pixel_display import PixelDisplay
try:
    from dimmer_read.dimmer_read import DimmerRead
except ImportError:
    from dimmer_read.fake_read import FakeRead as DimmerRead

class TheaterBumper:
    def __init__(self):
        self.pixels = PixelDisplay()
        self.dimmer = DimmerRead(self)
        self.stop_event = threading.Event()
        self.main()

    def main(self):
        reader_thread = threading.Thread(
            target=self.dimmer.read_forever, daemon=True
        )
        reader_thread.start()
        try:
            self.update_loop()
        except KeyboardInterrupt:
            print("Shutting down...")
        finally:
            self.stop_event.set()
            reader_thread.join(timeout=2)

    def update_loop(self):
        with self.pixels.live():
            while not self.stop_event.is_set():
                self.pixels.update(self.dimmer.value)

if __name__ == "__main__":
    TheaterBumper()
