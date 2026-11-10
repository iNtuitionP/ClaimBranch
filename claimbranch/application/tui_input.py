"""Mouse negotiation and bounded wheel reports, separate from keyboard arrows."""
from dataclasses import dataclass
import re
import sys


@dataclass(frozen=True)
class Wheel:
    x: int
    y: int
    dx: int = 0
    dy: int = 0


def sgr_wheel(suffix):
    match = re.fullmatch(r'\[<(\d{1,3});(\d{1,5});(\d{1,5})M', suffix)
    if not match:
        return None
    button, x, y = map(int, match.groups())
    if button not in (64, 65, 66, 67) or not x or not y:
        return None
    return Wheel(x - 1, y - 1, (0, 0, -1, 1)[button - 64], (-1, 1, 0, 0)[button - 64])


class Mouse:
    def __init__(self, curses):
        self.curses, self.owner, self.enabled = curses, None, False
        try:
            prefix = curses.tigetstr('kmous')
            if prefix == b'\x1b[M':
                # Older ncurses recognizes only X10. Leave it disabled and
                # request SGR explicitly so our bounded parser owns the bytes.
                self.owner = 'sgr'
            elif prefix == b'\x1b[<' and hasattr(curses, 'BUTTON5_PRESSED'):
                self.owner = 'curses'
        except (AttributeError, curses.error):
            pass

    def set(self, enabled):
        self.enabled = bool(enabled and self.owner)
        c = self.curses
        c.mousemask(c.ALL_MOUSE_EVENTS if self.enabled and self.owner == 'curses' else 0)
        sys.stdout.write('\x1b[?1000h\x1b[?1006h' if self.enabled else
                         '\x1b[?1006l\x1b[?1000l')
        sys.stdout.flush()

    def read(self):
        if not self.enabled or self.owner != 'curses':
            return None
        c = self.curses
        try:
            _, x, y, _, state = c.getmouse()
        except c.error:
            return None
        if state & c.BUTTON4_PRESSED:
            return Wheel(x, y, dy=-1)
        if state & c.BUTTON5_PRESSED:
            return Wheel(x, y, dy=1)
        return None
