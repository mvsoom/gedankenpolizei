"""Modified from https://github.com/mingrammer/python-curses-scroll-example/issues/4#issue-1361209563"""
import curses
import curses.textpad
from textwrap import wrap


class Screen(object):
    UP, DOWN = -1, 1

    def __init__(self, text, callback):
        self.init_curses()

        self.text = text
        self.top = 0
        self.current = 0

        self.callback = callback

    def update_size(self):
        self.max_lines, self.max_width = self.window.getmaxyx()

    def wrap_text(self):
        return wrap(self.text, width=self.max_width - 1)

    def init_curses(self):
        self.window = curses.initscr()
        self.window.keypad(True)
        self.update_size()

        curses.noecho()
        curses.cbreak()

        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)

    def run(self):
        try:
            self.input_stream()
        except KeyboardInterrupt:
            pass
        finally:
            curses.endwin()
        return 0

    def input_stream(self):
        while True:
            self.display()

            match c := self.window.getch():
                case curses.KEY_UP:
                    self.scroll(self.UP)
                case curses.KEY_DOWN:
                    self.scroll(self.DOWN)

                case curses.KEY_PPAGE | curses.KEY_LEFT:
                    self.scroll(self.UP * self.max_lines)
                case curses.KEY_NPAGE | curses.KEY_RIGHT:
                    self.scroll(self.DOWN * self.max_lines)

                case curses.KEY_HOME:
                    self.scroll(self.UP * 10**10)
                case curses.KEY_END:
                    self.scroll(self.DOWN * 10**10)

                case curses.KEY_RESIZE:
                    self.update_size()
                    self.window.refresh()
                    self.scroll()

                case curses.ascii.ESC:
                    break

                case _:
                    if not (continue_loop := self.callback(self, c)):
                        break

    def scroll(self, direction=0):
        lines = self.wrap_text()
        l = len(lines)
        self.current = min(max(0, self.current + direction), l - 1)

        if l < self.max_lines:
            self.top = 0
            return

        if self.current >= self.top + self.max_lines:
            self.top = self.current - self.max_lines + 1
        elif self.current < self.top:
            self.top = self.current
        elif self.top > (p := l - self.max_lines):
            self.top = p

    def display(self):
        self.window.erase()
        lines = self.wrap_text()
        for idx, item in enumerate(lines[self.top : self.top + self.max_lines]):
            if self.top + idx == self.current:
                self.window.addstr(idx, 0, item, curses.color_pair(2))
            else:
                self.window.addstr(idx, 0, item, curses.color_pair(1))
        self.window.refresh()