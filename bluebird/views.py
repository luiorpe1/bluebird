#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import curses
import curses.ascii
import os.path

from . import adapter
from . import thunder
from . import utils


class View(object):
    """Base class for view objects"""

    _window = None

    def __init__(self, window):
        self._window = window
        # Window dimensions: window.get_maxyx()
        # DO NOT TRUST curses.LINES & curses.COLS
        self._maxy, self._maxx = window.getmaxyx()

    @property
    def window(self):
        return self._window

    def draw(self):
        """Draw view."""
        return

    def onKey(self, ch):
        """Receives an ASCII code

        Returns True if the event is handled, False otherwise.
        """
        return False

## =================================================================


class TextView(View):
    """Presents information in a single line"""

    _text = None
    _attr = None

    def __init__(self, window, text='', attr=None):
        super(TextView, self).__init__(window)
        self.text = text
        self._attr = attr

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, text):
        if not isinstance(text, str):
            raise TypeError
        self._text = text

    def error(self, msg, attr):
        """Draw error message msg with attr attibutes"""
        try:
            self.window.erase()
            self.window.addstr(0, 0, msg, attr)
            self.window.refresh()
        except curses.error:
            pass

    def draw(self):
        self.window.erase()
        try:
            if self._attr is None:
                self.window.addstr(0, 0, self.text[:self._maxx])
            else:
                self.window.addstr(0, 0, self.text[:self._maxx], self.attr)
        except curses.error:
            pass

## =================================================================


class EditTextView(TextView):
    """Presents editable information in a single line"""

    def __init__(self, window, text=''):
        super(EditTextView, self).__init__(window)

    def edit(self, message=''):
        """Displays an editable message"""
        curses.curs_set(1)  # Show cursor
        origtext = self.text
        self.text = message
        x = len(message)
        self.draw()
        while True:
            ch = self.window.getch()
            if ch in (27, curses.ascii.ESC):
                # Key: curses.ascii.ESC works
                # Key: integer 27 is keycode generated by Escape key press
                self.text = origtext
                curses.curs_set(0)  # Hide cursor
                self.draw()
                return None
            elif ch == 10:
                # Key: curses.KEY_ENTER does NOT work
                # Key: curses.ascii.CR does NOT work
                # Key: integer 10 is keycode generated by Enter key press
                message = self.text
                self.text = origtext
                curses.curs_set(0)  # Hide cursor
                self.draw()
                return message
            elif ch == curses.ascii.DEL:
                # Key: curses.KEY_BACKSPACE does NOT work
                # Key: curses.ascii.DEL works
                # Key: integer 263 is keycode generated by Backspace key press.
                #      Does NOT work
                if x > 0:
                    self.text = self.text[:-1]
                    x -= 1
                else:
                    curses.flash()
            elif ch == curses.ascii.SP:
                self.text += ' '
                x += 1
            elif chr(ch).isalnum() or chr(ch) in '/()-_.':
                self.text += chr(ch)
                x += 1

            self.draw()
            try:
                self.window.move(0, x)
            except curses.error:
                pass

## =================================================================


class ListView(View):
    """Present information in a scrollable list"""

    _adapter = None
    _pos = None
    _top = None
    _bottom = None
    _end = None
    _x = None

    _highlight = None
    _hltext = None
    _hly = None
    _hlcoordinates = None

    def __init__(self, window, hlcolor=None):
        super(ListView, self).__init__(window)

        if hlcolor is None:
            hlcolor = curses.color_pair(0)

        self._hlcolor = hlcolor
        self._pos = 0  # y
        self._x = 0
        # Coordinates for a vertical sliding window
        self._top = 0
        self._bottom = self._maxy
        self._end = 0

        self._highlight = False

    def onKey(self, ch):
        """Receives an ASCII code

        Returns True if the event is handled, False otherwise
        """
        if self._adapter is None:
            return False

        if ch in (curses.KEY_UP, ord('k')):  # Up arrow
            if self._pos > 0:
                self._pos -= 1
                if self._pos < self._top:
                    self._top -= 1
                    self._bottom -= 1
            return True
        elif ch in (curses.KEY_DOWN, ord('j')):  # Down arrow
            if self._pos < len(self._adapter) - 1:
                self._pos += 1
                if self._pos >= self._bottom:
                    self._top += 1
                    self._bottom += 1
            return True
        elif ch == curses.KEY_PPAGE:  # Previous page
            tmp = self._pos - self._maxy - 1
            if tmp <= 0:
                self._pos = self._top = 0
                self._bottom = self._maxy
            else:
                self._pos = tmp
                self._top = tmp
                self._bottom = self._top + self._maxy
            return True
        elif ch == curses.KEY_NPAGE:  # Next page
            tmp = self._pos + self._maxy - 1
            if tmp >= len(self._adapter) - 1:
                self._pos = len(self._adapter) - 1
                self._bottom = len(self._adapter)
                self._top = self._bottom - self._maxy
            else:
                self._pos = tmp
                self._bottom = min(tmp + self._maxy, len(self._adapter))
                self._top = self._bottom - self._maxy
            return True
        elif ch in (curses.KEY_LEFT, ord('h')):  # Left arrow
            if self._adapter is None:
                return False
            if self._x > 0:
                self._x -= 1
            return True
        elif ch in (curses.KEY_RIGHT, ord('l')):  # Right arrow
            if self._adapter is None:
                return False
            self._x += 1
            return True
        elif ch in (ord('n'), ord('N')) and self._highlight:
            for y in range(self.pos+1, self._end):
                if y in self._hlcoordinates:
                    self._move(y)
                    break
            return True
        elif ch in (ord('p'), ord('P')) and self._highlight:
            for y in range(self.pos-1, 0, -1):
                if y in self._hlcoordinates:
                    self._move(y)
                    break
            return True

        return False

    def draw(self):
        self.window.erase()
        if self._adapter is not None:
            for y in range(self.top, self.bottom):
                try:
                    text = self.adapter[y][self._x:self._maxx + self._x]
                    if y == self.pos and not self._highlight:
                        self.window.addstr(y-self.top, 0, text, self._hlcolor)
                    elif not self._highlight:
                        self._window.addstr(y-self.top, 0, text)
                    else:
                        x = 0
                        x_array = None

                        try:
                            x_array = self._hlcoordinates[y]
                        except KeyError:
                            x_array = []

                        while x < self._maxx and x < len(text):
                            if x + self._x in x_array:
                                self.window.addstr(y - self.top, x,
                                                   self._hltext, self._hlcolor)
                                x += len(self._hltext)
                            else:
                                self.window.addstr(y-self.top, x, text[x])
                                # .addch se come algunas letras con acentos.
                                # Usar .addstr
                                x += 1
                except curses.error:
                    pass  # Do nothing
                except IndexError:
                    break
                except UnicodeEncodeError:
                    pass

    def highlighttext(self, pattern):
        """ Highlights every instance of pattern from current position onwards
        """
        coord = {}

        for y, line in enumerate(self.adapter):
            x = line.find(pattern)
            while x >= 0:
                if y in coord:
                    coord[y].append(x)
                else:
                    coord[y] = [x]

                x = line.find(pattern, x+1)

        if len(coord):
            self._highlight = True
            self._hltext = pattern
            self._hlcoordinates = coord

            hly = self.pos
            for y in sorted(coord.keys()):
                if y >= self.pos:
                    hly = y
                    break

            self._move(hly)
            self.draw()

        return len(coord)

    def _move(self, y):
        """Scroll the list to position y"""
        if y == self.pos:
            return

        if y >= 0 and y < len(self.adapter):
            if y < self.top:
                self.top = y
                self.bottom = min(y + self._maxy, len(self._adapter))
            elif y > self.bottom:
                self.bottom = min(y + self._maxy, len(self._adapter))
                self.top = max(self.bottom - self._maxy, 0)
            self.pos = y

    @property
    def adapter(self):
        return self._adapter

    @adapter.setter
    def adapter(self, adapter_):
        if not isinstance(adapter_, adapter.BaseAdapter):
            raise TypeError
        self._adapter = adapter_
        self._end = len(self._adapter)

    @property
    def top(self):
        return self._top

    @top.setter
    def top(self, top):
        self._top = top

    @property
    def bottom(self):
        return self._bottom

    @bottom.setter
    def bottom(self, bottom):
        self._bottom = bottom

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, position):
        self._pos = position

## =================================================================
