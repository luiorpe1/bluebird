#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import curses

import bluebird.app as app

if __name__ == '__main__':
    try:
        assert sys.platform.startswith('linux')
    except AssertionError:
        raise AssertionError('Unsupported platform ' + sys.platform)

    curses.wrapper(app.Application, 'InboxActivity')
