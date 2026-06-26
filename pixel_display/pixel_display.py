#!/usr/bin/env python3

import time

try:
    import board
    import neopixel
except ImportError:
    neopixel = None

from pixel_display import terminal_viz

class Color(tuple):
    @classmethod
    def BLACK(cls): return cls((0, 0, 0))
    @classmethod
    def ORANGE(cls): return cls((96, 48, 0))
    @classmethod
    def WHITE(cls): return cls((255, 192, 128))

    @property
    def r(self):
        return self[0]
    @property
    def g(self):
        return self[1]
    @property
    def b(self):
        return self[2]

    def __mul__(self, value: float) -> 'Color':
        return Color([value * x for x in self])

    def __add__(self, other: 'Color') -> 'Color':
        return Color([a+b for a, b in zip(self, other)])

class Animation(dict[float, Color]):
    def at_time(self, phase: float) -> Color:
        if phase < 0: phase = 0
        nextkeys = [key for key in self if key > phase]
        prevkeys = [key for key in self if key <= phase]
        prevkey = prevkeys[-1]
        rgb1 = self[prevkey]
        if not nextkeys:
            return rgb1
        nextkey = nextkeys[0]
        rgb2 = self[nextkey]

        mix = (phase - prevkey) / (nextkey - prevkey)

        return rgb1 * (1-mix) + rgb2 * mix

class Pixel(list):
    on_keyframes_dim = Animation({
        0:   Color.BLACK(),
        1/16: Color.ORANGE(),
        1/8: Color.ORANGE(),
        1/4: Color.ORANGE(),
    })
    on_keyframes_bright = Animation({
        0:   Color.BLACK(),
        1/16: Color.ORANGE(),
        1/8: Color.WHITE(),
        1/4: Color.ORANGE(),
    })
    off_keyframes = Animation({
        0:   Color.BLACK(),
        1/4: Color.ORANGE(),
    })
    on: bool
    zero_time: float
    distance: float

    def __init__(self, distance: float):
        super().__init__(Color.BLACK())
        self.distance = distance
        self.on = False
        self.zero_time = 0

    def turn_on(self):
        if not self.on:
            now = time.monotonic()
            phase = self.zero_time - now
            if phase < 0: phase = 0
            self.zero_time = now - phase
            self.on = True

    def turn_off(self):
        if self.on:
            now = time.monotonic()
            phase = now - self.zero_time
            phase = min(phase, max(self.off_keyframes))
            self.zero_time = now + phase
            self.on = False

    def update(self, percent_animating: float):
        now = time.monotonic()
        if self.on:
            phase = now - self.zero_time
            rgb1 = self.on_keyframes_dim.at_time(phase)
            rgb2 = self.on_keyframes_bright.at_time(phase)
            self.set(rgb1 * (1-percent_animating) + rgb2 * percent_animating)
        else:
            phase = self.zero_time - now
            self.set(self.off_keyframes.at_time(phase))

    @property
    def is_animating(self) -> bool:
        return self.on and 0 < time.monotonic() - self.zero_time < max(self.on_keyframes_bright)

    def set(self, rgb: Color):
        try:
            self[0] = int(rgb.r)
            self[1] = int(rgb.g)
            self[2] = int(rgb.b)
        except ValueError:
            print(rgb)
            raise
        if min(self) < 0:
            raise ValueError(f'*rgb need to be positive, not {rgb}')
        elif max(self) > 255:
            raise ValueError(f'*rgb need to be <=255, not {rgb}')

class FakeStrip(list):
    def __init__(self, num_pixels):
        super().__init__([(0,0,0)]*num_pixels)

    def show(self):
        pass

class PixelDisplay:
    PIXEL_PIN = 'D18'
    NUM_PIXELS = 416
    def __init__(self):
        self.most_ever_animating = 0.2
        self.setup_box()
        self.pixels = [Pixel(self.distance(i)) for i in range(self.NUM_PIXELS)]
        if neopixel:
            pixel_pin = getattr(board, self.PIXEL_PIN)
            self.strip = neopixel.NeoPixel(pixel_pin, self.NUM_PIXELS, brightness=1, auto_write=False)
        else:
            self.strip = FakeStrip(self.NUM_PIXELS)
            print('no real pixels, not running as root?')

    def setup_box(self):
        # dimensions: 2.79 x 4.14 meters, 415 pixels
        # total perimeter: 13.86 meters
        # pixels per meter: 29.94 (30?)
        # pixels along 2.79 side: 83.5
        # pixels along 4.14 side: 124

        # actual size
#        self.term = terminal_viz.LayoutGrid.box(rows=84, cols=124, start=0, clockwise=True)

        aspect_ratio = 31/21
        rows, cols = terminal_viz.LayoutGrid.maxbox(aspect_ratio)
        if rows >= 85 and cols >= 125:
            rows = 85
            cols = 125
        elif rows >= 125 and cols >= 85:
            rows = 125
            cols = 85

        self.term = terminal_viz.LayoutGrid.box(
            rows=rows,
            cols=cols,
            start=0,
            clockwise=True,
            rotated=False
        )

        self.NUM_PIXELS = self.term.num_pixels
        if rows > cols:
            self.origin = ((rows-1) + (cols-1)*1.5)
            print(f'portrait origin: {self.origin}')
        else:
            self.origin = ((cols-1) + (rows-1)*.5)
            print(f'landscape origin: {self.origin}')

        if (self.NUM_PIXELS != 416):
            print(f'{self.NUM_PIXELS} pixels ({self.NUM_PIXELS/416:.0%})')
            # input('enter to confirm')

    def live(self):
        return self.term.live()

    def distance(self, i):
        return 1 - abs(((i - self.origin) % self.NUM_PIXELS) - self.NUM_PIXELS / 2) / self.NUM_PIXELS * 2

    def get_percent_of_pixels_animating(self):
        raw_percent = sum([1 for pixel in self.pixels if pixel.is_animating]) / len(self.pixels)
        self.most_ever_animating = max(self.most_ever_animating, raw_percent)
        return raw_percent / self.most_ever_animating


    def update(self, value):
        animating = self.get_percent_of_pixels_animating()
        for pixel in self.pixels:
            if pixel.distance < value:
                pixel.turn_on()
            else:
                pixel.turn_off()
            pixel.update(animating)
        self.show()

    def show(self):
        for i, pixel in enumerate(self.pixels):
            self.strip[i] = pixel
        self.strip.show()
        self.term.render(self.pixels)
        time.sleep(0.01)

if __name__ == '__main__':
    PixelDisplay()
