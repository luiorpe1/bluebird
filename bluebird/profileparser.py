#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""profiles.ini file parser

Parse Thunderbird user profiles

profiles.ini is a standard config file listing all thunderbird user profiles

classes:

Profile -- Describes a profile
ProfileParser -- Given a profile name, parses profiles.ini
                 and returns a profile object if found, None otherwise

"""
import sys
if sys.version_info.major == 3:
    import configparser
else:
    import ConfigParser as configparser


import os.path
import re

# =================================================================


class Profile(object):
    """ Thunderbird profile description """

    def __init__(self):
        self._name = None
        self._isRelative = None
        self._path = None

    @property
    def name(self):
        """Name of the profile"""
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def isRelative(self):
        """1 if the path is relative, 0 otherwise"""
        return self._isRelative

    @isRelative.setter
    def isRelative(self, isRelative):
        if isinstance(isRelative, str):
            if isRelative.isdigit():
                self._isRelative = isRelative
        elif isinstance(isRelative, bool):
            if isRelative:
                self._isRelative = '1'
            else:
                self._isRelative = '0'
        else:
            raise AttributeError

    @property
    def path(self):
        """Path of the profile's thunderbird directory"""
        return self._path

    @path.setter
    def path(self, path):
        self._path = path

    def as_string(self):
        """Returns the profile as a string"""
        data = ['Name: ' + self.name,
                'IsRelative: ' + self.isRelative,
                'Path: ' + self.path]
        return '\n'.join(data)

# =================================================================


class ProfileParser(object):
    """ Thunderbird profiles.ini file parser """

    _config = None

    def __init__(self, configname):
        """ Open and parse config file.

        If the file configname does not exist, IOError will be thrown

        """
        self._config = configparser.ConfigParser()
        self._read_config(configname)

    # =================================================================

    def _read_config(self, configname):
        """ Read config file """
        with open(configname) as f:
            if sys.version_info.major == 3:
                self._config.read_file(f)
            else:
                self._config.readfp(f)

    # =================================================================

    def get_profile(self, name=None):
        """Return a profile from the config file

        If name is not specified, the default profile will be returned
        or None if the profile is not found.

        """
        major = sys.version_info.major
        if name is not None:
            if major == 3:
                return self._get_profile3(name)
            else:
                return self._get_profile2(name)
        else:
            if major == 3:
                return self._get_profile3()
            else:
                return self._get_profile2()

    def _get_profile2(self, name='default'):
        """ Python 2 version of public method get_profile """
        profile = None

        i = -1
        prefix = 'Profile'
        while True:
            i += 1
            try:
                items = self._config.items(prefix + str(i))
            except configparser.NoSectionError:
                break

            d = dict(items)
            p = Profile()

            p.name = d['name']
            if p.name != name:
                continue

            p.isRelative = d['isrelative']
            p.path = d['path']

            profile = p
            break

        return profile

    def _get_profile3(self, name='default'):
        """ Python 3 version of public method get_profile """
        profile = None

        for i in self._config:
            match = re.search(r'Profile\d+', i)
            if not match:
                continue

            p = Profile()

            p.name = self._config[match.group()]['Name']
            if (p.name != name):
                continue

            p.isRelative = self._config[match.group()]['IsRelative']
            p.path = self._config[match.group()]['Path']

            profile = p
            break

        return profile

    # =================================================================

    def get_profiles(self):
        """ Returns a list with all the profiles in config """
        if sys.version_info.major == 3:
            return self._get_profiles3()
        else:
            return self._get_profiles2()

    def _get_profiles2(self):
        """ Python 2: Returns a list with all the profiles in config """
        profiles = []

        i = -1
        prefix = 'Profile'
        while True:
            i += 1
            try:
                items = self._config.items(prefix + str(i))
            except configparser.NoSectionError:
                break

            d = dict(items)
            p = Profile()

            p.name = d['name']
            p.isRelative = d['isrelative']
            p.path = d['path']

            profiles.append(p)

        return profiles

    def _get_profiles3(self):
        """Python3: Returns a list with all the profiles in config """
        profiles = []

        for i in self._config:
            match = re.search(r'Profile\d+', i)
            if not match:
                continue

            p = Profile()

            p.name = self._config[match.group()]['name']
            p.isRelative = self._config[match.group()]['isrelative']
            p.path = self._config[match.group()]['path']

            profiles.append(p)

        return profiles


# =================================================================
# Testing procedures.
# Execute this file directly to perform unit testing.
# =================================================================

if __name__ == '__main__':
    import unittest

    class TestProfileParser(unittest.TestCase):

        def setUp(self):
            THUNDERBIRD = os.getenv('THUNDERBIRD')
            if THUNDERBIRD is not None:
                self._path = THUNDERBIRD
            else:
                self._path = os.getenv('HOME') + '/.thunderbird'

        def test_parser(self):
            profiles_path = self._path + '/profiles.ini'
            try:
                pparser = ProfileParser(profiles_path)
            except IOError:
                sys.stderr.write('Error: Unable to read file %s\n' %
                                (profiles_path))
                exit(1)

            profiles = pparser.get_profiles()
            self.assertEqual(len(profiles), 2)
            self.assertEqual(profiles[0].name, 'default')
            self.assertEqual(profiles[0].path, 'asaqivy2.default')
            self.assertEqual(profiles[1].name, 'luis')
            self.assertEqual(profiles[1].path, 'r568ictx.luis')

    try:
        assert sys.platform.startswith('linux')
    except AssertionError:
        raise AssertionError('Unsupported platform ' + sys.platform)
    unittest.main()
