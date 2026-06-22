#!/usr/bin/env python3

import colorsys
import itertools
import time

import board
import neopixel

from pixel_display import terminal_viz

class Pixel(list):
    keyframes = {
        0: (0,0,0),
        .125: (96, 48, 0),
        .25: (255,255,255),
        .5: (96, 48, 0),
    }
    def __init__(self):
        super().__init__([0,0,0])
        self.on = False

    def turn_on(self):
        pass

    def turn_off(self):
        pass

    def update(self):
        now = time.monotonic()
        if self.on:
            phase = now - self.on_time
            self[:] = self.color_at_time(phase)

    @classmethod
    def color_at_time(cls, t):
        nextkey = [key for key in cls.keyframes if key >= t][0]
        prevkey = [key for key in cls.keyframes if key <= t][-1]
        amount = (nextkey - prevkey) / (t - prevkey)
        r1, g1, b1 = cls.keyframes[prevkey]
        r2, g2, b2 = cls.keyframes[nextkey]
        return (
            r1+(r2-r1)*amount,
            g1+(g2-g1)*amount,
            b1+(b2-b1)*amount
        )

    def set(self, r,g,b):
        self[0] = int(r)
        self[1] = int(g)
        self[2] = int(b)
        if min(self) < 0:
            self[0] = 255
            self[1] = 0
            self[2] = 0
        elif max(self) > 255:
            self[0] = 0
            self[1] = 255
            self[2] = 0

class FakeStrip(list):
    def __init__(self, num_pixels):
        super().__init__([(0,0,0)]*num_pixels)

    def show(self):
        pass

class PixelDisplay:
    PIXEL_PIN = board.D18
    NUM_PIXELS = 416
    def __init__(self):
        self.setup_box()
        self.pixels = [Pixel() for _ in range(self.NUM_PIXELS)]
        try:
            self.strip = neopixel.NeoPixel(self.PIXEL_PIN, self.NUM_PIXELS, brightness=1, auto_write=False)
        except:
            self.strip = FakeStrip(self.NUM_PIXELS)
            print('no real pixels, not running as root?')
            time.sleep(1)

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

        self.term = terminal_viz.LayoutGrid.box(rows=rows, cols=cols, start=0, clockwise=True, rotated=False)

        self.NUM_PIXELS = self.term.num_pixels
        if rows > cols:
            self.origin = (rows + cols*1.5)
            print(f'portrait origin: {self.origin}')
        else:
            self.origin = (cols + rows*.5)
            print(f'landscape origin: {self.origin}')

        print(f'{self.NUM_PIXELS} pixels ({self.NUM_PIXELS/416:.0%})')
        if (self.NUM_PIXELS != 416) or True:
            input()

    def live(self):
        return self.term.live()

    def distance(self, i):
        return 1 - abs(((i - self.origin) % self.NUM_PIXELS) - self.NUM_PIXELS / 2) / self.NUM_PIXELS * 2

    def update(self, value):
        for i in range(self.NUM_PIXELS):
            distance = self.distance(i)
            self.pixels[i].set(distance*255,0,255)
            if distance < value:
                self.pixels[i][1] = 255
            else:
                self.pixels[i][1] = 0
        self.show()

    def show(self):
        for i, pixel in enumerate(self.pixels):
            self.strip[i] = pixel
        self.strip.show()
        self.term.render(self.pixels)
        time.sleep(0.03)

if __name__ == '__main__':
    PixelDisplay()

