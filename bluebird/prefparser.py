#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""prefs.js file parser

This parser is limited to extracting the different mail directories.

A prefs.js file consists of javascript calls to a user_pref function.
This function takes a string key as its first argument and a value of
any type as its second argument.

class:

PrefParser -- responsible for parsing a prefs.js preferences file and
              extracting the mail directories.

"""
import sys
import re
import os
import os.path


class PrefParser(object):
    """prefs.js file parser"""

    def __init__(self, filename=None):
        self._data = {}

        if filename is not None:
            with open(filename) as f:
                self.read_file(f)

    # =================================================================

    def read_file(self, f, source=None):
        """Read and parse a filename

        The `f' argument must be iterable, returning one line at a time.
        Optional second argument is the `source' specifying the name of
        the file being read. If not given, it is taken from f.name.
        If `f' has no `name' attribute, `<???>' is used.

        """
        if source is None:
            try:
                source = f.name
            except AttributeError:
                source = '<???>'
        self._read(f, source)

    # =================================================================

    def _read(self, fp, fpname):
        """Parse the file search for the mail directories"""
        for line in fp:
            if not line.startswith('user_pref'):
                continue

            # Filter by 'mail.server' preferences
            match = re.search(r'mail\.server', line)
            if not match:
                continue

            # Get directory preferences
            line = line.strip()[10:-2]  # Remove user_pref();\n
            fields = line.partition(',')

            key = fields[0].strip('"')
            if key[-9:] != 'directory':
                continue

            value = fields[2].lstrip().strip('"')
            self._data[key] = value

    # =================================================================

    def get_directories(self):
        """Return the found mail directories"""
        #return [self._data[i] for i in self._data]
        dirs = []
        for key in self._data:
            dirs.append(self._data[key])
            dirs += self._get_directories_recursive(self._data[key])
        return dirs

    def _get_directories_recursive(self, path):
        d = []
        for filename in os.listdir(path):
            p = '/'.join((path, filename))
            if os.path.isdir(p):
                d.append(p)
                d += self._get_directories_recursive(p)
        return d


# =================================================================
# Testing procedures.
# Execute this file directly to perform unit testing.
# =================================================================

if __name__ == '__main__':
    import unittest
    import profileparser

    class TestPrefParser(unittest.TestCase):

        def setUp(self):
            THUNDERBIRD = os.getenv('THUNDERBIRD')
            if THUNDERBIRD is not None:
                self._path = THUNDERBIRD
            else:
                self._path = os.getenv('HOME') + '/.thunderbird'

        def test_parser(self):
            # Get profiles
            profiles_path = self._path + '/profiles.ini'
            try:
                pparser = profileparser.ProfileParser(profiles_path)
            except IOError:
                sys.stderr.write('Error: Unable to read file %s\n' %
                                (profiles_path))
                exit(1)

            profiles = pparser.get_profiles()

            # Get mail directories
            prefs_path = self._path + '/' + profiles[0].path + '/prefs.js'
            try:
                pparser = PrefParser(prefs_path)
            except IOError:
                sys.stderr.write('Error: Unable to read file %s\n' %
                                (prefs_path))
                exit(1)

            dirs = pparser.get_directories()
            #for d in dirs: sys.stdout.write(d + '\n')
            self.assertIn('Local Folders', dirs[0])
            self.assertIn('imap.googlemail.com', dirs[1])

    try:
        assert sys.platform.startswith('linux')
    except AssertionError:
        raise AssertionError('Unsupported platform ' + sys.platform)
    unittest.main()
