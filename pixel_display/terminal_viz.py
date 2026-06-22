#!/usr/bin/env python3

"""
led_terminal_viz.py — render an addressable LED strip's current colors to the
terminal using 24-bit ANSI color, laid out on a 2D grid that mirrors the
strip's physical arrangement (matrix, serpentine, or fully custom layout).

Quick start
-----------
    from led_terminal_viz import LayoutGrid

    # 400 pixels wired as a 20x20 serpentine matrix (common for LED panels)
    layout = LayoutGrid.grid(rows=20, cols=20, serpentine=True)

    # `pixels` can be any indexable sequence of (r, g, b) — including a
    # neopixel.NeoPixel object directly.
    layout.render(pixels)

For a non-rectangular physical layout (e.g. pixels mounted around a sign,
or a strip that snakes irregularly), build a custom mapping instead:

    mapping = {0: (0, 0), 1: (0, 1), 2: (1, 1), 3: (2, 0), ...}
    layout = LayoutGrid.from_dict(mapping)
"""

from contextlib import contextmanager
import os
import shutil
import sys
import time


class LayoutGrid:
    RESET = "\x1b[0m"
    HOME = "\x1b[H"
    CLEAR = "\x1b[2J"
    HIDE_CURSOR = "\x1b[?25l"
    SHOW_CURSOR = "\x1b[?25h"

    def __init__(self, coords):
        """coords: list where coords[pixel_index] = (row, col) or None to skip.

        color_mode: "truecolor" (24-bit, \\x1b[38;2;r;g;bm) works in iTerm2
        and most Linux terminals, but is NOT reliably supported by macOS's
        stock Terminal.app. Use color_mode="256" there instead — it
        approximates each color to the nearest xterm 256-color palette
        entry, which Terminal.app renders correctly.

        """
        self.coords = coords
        self.num_pixels = len(coords)
        known = [c for c in coords if c is not None]
        self.rows = int((max(r for r, c in known) + 1))
        self.cols = int((max(c for r, c in known) + 1))*2
        self.minrow = int((min(r for r, c in known)))
        self.mincol = int((min(c for r, c in known)))*2
        self.color_mode = self.detect()

    @staticmethod
    def detect():
        """Auto-detect the best color_mode and glyph for the current terminal.

        Returns (color_mode, glyph) — pass these straight to grid() or from_dict().

            layout = LayoutGrid.grid(rows=20, cols=20, **(LayoutGrid.detect()))

        Color mode detection (in priority order):
          - COLORTERM=truecolor or COLORTERM=24bit  → "truecolor"
          - TERM_PROGRAM=iTerm.app                  → "truecolor"
          - TERM contains "256color"                → "256"
          - fallback                                → "256"  (safe default)

        Glyph detection:
          - sys.stdout.encoding is UTF-8            → "●"  (3-byte, looks great)
          - anything else                           → "@"  (1-byte, always safe)

        Note: COLORTERM is not always forwarded over SSH. If auto-detection
        gives you 256-color when you expect truecolor, add
        `SendEnv COLORTERM` to ~/.ssh/config on your client machine.
        """
        colorterm  = os.environ.get("COLORTERM", "").lower()
        term       = os.environ.get("TERM", "").lower()
        term_prog  = os.environ.get("TERM_PROGRAM", "").lower()

        print('COLORTERM:', colorterm, "(need truecolor or 24bit)")
        print('TERM:', term)
        print('TERM_PROGRAM:', term_prog, "(need itsrm.app)")
        if colorterm in ("truecolor", "24bit"):
            return "truecolor"

        if term_prog == "iterm.app":
            return "truecolor"

        input("using 256 colors")
        return "256"

    @classmethod
    def from_dict(cls, mapping):
        """mapping: {pixel_index: (row, col)}. Unmapped indices render blank."""
        n = max(mapping) + 1
        coords = [mapping.get(i) for i in range(n)]
        return cls(coords)

    @staticmethod
    def maxdimension():
        size = shutil.get_terminal_size()
        width = size.columns -2
        height = (size.lines - 1) * 2
        return width, height

    @classmethod
    def maxbox(cls, aspect_ratio):
        width, height = cls.maxdimension()
        print(f'terminal is {width}x{height}')
        if False:
            # rotated
            width_plus_height = min(width, height)
            rows = int(width_plus_height / (1+aspect_ratio))
            cols = int(rows * aspect_ratio)
        elif True:
            # landscape, height-limited
            rows1 = height
            cols1 = int(height * aspect_ratio)
            # landscape, width-limited
            cols2 = width
            rows2 = int(width / aspect_ratio)
            # landscape, best valid
            rowsl = min(rows1, rows2)
            colsl = min(cols1, cols2)
            print(f'landscape options {cols1}x{rows1} and {cols2}x{rows2}')
            # portrait, height-limited
            rows1 = height
            cols1 = int(height / aspect_ratio)
            # portrait, width-limited
            cols2 = width
            rows2 = int(width * aspect_ratio)
            # portrait, best valid
            rowsp = min(rows1, rows2)
            colsp = min(cols1, cols2)
            print(f'portrait options {cols1}x{rows1} and {cols2}x{rows2}')

            print(f'best options {colsl}x{rowsl} (total={colsl+rowsl}) and {colsp}x{rowsp} (total={colsp+rowsp})')
            if rowsl+colsl > rowsp+colsp:
                print('landscape')
                rows = rowsl
                cols = colsl
            else:
                print('portrait')
                rows = rowsp
                cols = colsp

        return rows, cols

    @classmethod
    def grid(cls, rows, cols, serpentine=False):
        """Straightforward rectangular matrix layout, row-major pixel order.

        serpentine=True flips column order on odd rows — matches how most
        LED matrix panels are physically wired (boustrophedon).
        """
        coords = []
        for i in range(rows * cols):
            r, c = divmod(i, cols)
            if serpentine and r % 2 == 1:
                c = cols - 1 - c
            coords.append((r, c))
        return cls(coords)

    @classmethod
    def box(cls, rows, cols, start=0, clockwise=True, rotated=True):
        """Layout for pixels arranged around the perimeter of a rectangle.

        Generates a mapping where each strip pixel index is assigned the
        (row, col) coordinate of its physical position on the box perimeter.

        Args:
            rows, cols:  Box dimensions in pixels (corners are shared between
                         edges, so the total pixel count is 2*(rows+cols)-4).
            start:       Perimeter index of strip pixel 0.  The canonical
                         perimeter is numbered clockwise from the top-left
                         corner (0,0), so:
                           0            = top-left corner
                           cols-1       = top-right corner
                           cols+rows-2  = bottom-right corner
                           2*cols+rows-3 = bottom-left corner
                         Pass the index of whichever position your strip's
                         first pixel physically sits at.
            clockwise:   True  → strip advances clockwise  (default)
                         False → strip advances counter-clockwise

        Example — 10×20 box, strip starts at top-right corner going CCW:
            layout = LayoutGrid.box(rows=10, cols=20,
                                    start=19, clockwise=False,
                                    **LayoutGrid.detect())
        """
        if rows < 2 or cols < 2:
            raise ValueError("box() requires rows >= 2 and cols >= 2")

        # Build the canonical clockwise perimeter starting at (0, 0).
        perimeter = []
        for c in range(cols):            # top edge →
            perimeter.append([0, c])
        for r in range(1, rows):         # right edge ↓
            perimeter.append([r, cols - 1])
        for c in range(cols - 2, -1, -1):  # bottom edge ←
            perimeter.append([rows - 1, c])
        for r in range(rows - 2, 0, -1):   # left edge ↑
            perimeter.append([r, 0])

        total = len(perimeter)  # == 2*(rows+cols) - 4
        step = 1 if clockwise else -1

        mapping = {
            pixel_idx: perimeter[(start + step * pixel_idx) % total]
            for pixel_idx in range(total)
        }

        if rotated:
            for value in mapping.values():
                cls.rotate(value, rows, cols)
        else:
            for value in mapping.values():
                cls.scale(value, 0.5)

        return cls.from_dict(mapping)

    @staticmethod
    def rotate(coordinate, rows, cols):
        (row, col) = coordinate
        coordinate[0] = (row + col + cols) / 2
        coordinate[1] = (col - row + rows) / 2

    @staticmethod
    def scale(coordinate, scalar):
        coordinate[:] = [c*scalar for c in coordinate]

    @staticmethod
    def _rgb_to_256(r, g, b):
        """Approximate an RGB color to the nearest xterm 256-color index."""
        if r == g == b:
            if r < 8:
                idx = 16
            elif r > 248:
                idx = 231
            else:
                idx = 232 + round((r - 8) / 247 * 24)
            return idx
        r_idx = round(r / 255 * 5)
        g_idx = round(g / 255 * 5)
        b_idx = round(b / 255 * 5)
        return 16 + 36 * r_idx + 6 * g_idx + b_idx

    def _color(self, fg, bg):
        if not fg: fg = 0,0,0
        if not bg: bg = 0,0,0
        if self.color_mode == "256":
            return f"\x1b[38;5;{self._rgb_to_256(*fg)};48;5;{self._rgb_to_256(*bg)}m"
        return f"\x1b[38;2;{fg[0]};{fg[1]};{fg[2]};48;2;{bg[0]};{bg[1]};{bg[2]}m"

    def render(self, pixels, cell_width=1, home=True, stream=sys.stdout):
        """Draw one frame. Call repeatedly for live preview (cursor returns
        home instead of scrolling, so it updates in place)."""
        grid = [[{} for _ in range(self.cols-self.mincol)] for _ in range(self.rows-self.minrow)]
        glyph = "▄"
        for idx, coord in enumerate(self.coords):
            if coord is None or idx >= len(pixels):
                continue
            row, col = coord
            #glyph = "," if (row % 1) else "'"
            #glyph = "▄"
            fgbg = 'fg' if (row%1) else 'bg'
            col = int(col*2)-self.mincol
            row = int(row)-self.minrow
            assert row >= 0, row
            assert col >= 0, col
            try:
                grid[row][col][fgbg] = tuple(pixels[idx])[:3]
            except IndexError:
                print(f'{row}, {col} outside of range {self.rows}, {self.cols}')
                raise
                pass

        lines = []
        for row in grid:
            parts = ''
            for cell in row:
                parts += self._color(cell.get('fg'), cell.get('bg'))
                parts += glyph
                parts += self.RESET
            lines.append(parts)

        out = (self.HOME if home else "") + "\n".join(lines) + "\n"
        stream.write(out)
        stream.flush()

    @contextmanager
    def live(self):
        """Clear screen once and hide cursor before a render loop."""
        sys.stdout.write(self.CLEAR + self.HIDE_CURSOR)
        sys.stdout.flush()
        yield
        """Restore cursor when done."""
        sys.stdout.write(self.SHOW_CURSOR + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    # Demo: rainbow sweep across a 20x20 serpentine matrix (400 pixels), no
    # hardware required. Run directly to sanity-check your terminal/layout.
    import colorsys

    NUM_PIXELS = 400
    color_mode = LayoutGrid.detect()
    print(f"Detected: color_mode={color_mode!r}")
    time.sleep(1)
    layout = LayoutGrid.grid(rows=20, cols=20, serpentine=True)

    with layout.live():
        try:
            t = 0.0
            while True:
                pixels = []
                for i in range(NUM_PIXELS):
                    hue = (i / NUM_PIXELS + t) % 1.0
                    r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                    pixels.append((int(r * 255), int(g * 255), int(b * 255)))
                layout.render(pixels)
                t += 0.01
                time.sleep(0.03)
        except KeyboardInterrupt:
            pass
