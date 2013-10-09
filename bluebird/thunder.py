#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Thunderbird Mail Reader

This module contains the ThunderReader class, a mail reader object
specialized for THunderbird.

classes:

ThunderReader -- Mail reader specialized in Thunderbird.

"""
from __future__ import print_function
import os
import os.path
import sys
import mailbox

from . import profileparser
from . import prefparser

# __ALL__: List of public objects. Overrides the import default behaviour.
#__ALL__ = ['ThunderReader']


### Module Constants ##
# Linux systems supported only.
# Add platform specifics if porting to another platform

HOMEPATH = os.getenv('HOME')
if not HOMEPATH:
    print("Error: Unable to read HOME environment variable", file=sys.stderr)
    exit(1)

THUNDERBIRDPATH = HOMEPATH + '/.thunderbird'
THUNDERBIRDPROFILES = THUNDERBIRDPATH + '/profiles.ini'


# =================================================================


### Module helper functions ##

def get_profiles():
    """Returns a list of Thunderbird profiles"""
    try:
        pparser = profileparser.ProfileParser(THUNDERBIRDPROFILES)
    except IOError:
        print("Error: Unable to read file", THUNDERBIRDPROFILES,
              file=sys.stderr)
        exit(1)

    return pparser.get_profiles()


def get_profile(name='default'):
    """Returns the Thunderbird profile specified by name

    Returns the profile wich name matches that passed as argument,
    None otherwise. If no name is passed, 'default' is assumed.

    """
    for p in get_profiles():
        if p.name == name:
            return p

    return None


def get_mail_directories(profile):
    """Returns a list of mail directories for the given profile"""
    if not isinstance(profile, profileparser.Profile):
        raise AttributeError

    THUNDERBIRDPROFILEPREFS = ("%s/%s/%s" %
                               (THUNDERBIRDPATH, profile.path, 'prefs.js'))

    try:
        pparser = prefparser.PrefParser(THUNDERBIRDPROFILEPREFS)
    except IOError:
        print("Error: Unable to read file", THUNDERBIRDPROFILEPREFS,
              file=sys.stderr)
        exit(1)

    return [d for d in pparser.get_directories()]


def is_mailbox(path):
    """ Returns True if the path points to a mailbox mbox file
        False otherwise.
    """
    #f = open('a.out', 'a')
    if os.path.isdir(path):
        #f.write(path + '\tFalse: Dir\n'); f.close()
        return False

    dirname = os.path.dirname(path)
    basename = os.path.basename(path)

    if '.' in basename:
        #f.write(path + '\tFalse: Dot\n'); f.close()
        return False

    with open(path) as g:
        if g.read(5) != 'From ':
            #f.write(path + '\tFalse: From\n'); f.close()
            return False

    #f.write(path + '\tTrue\n'); f.close()
    return True
    #if '.' not in filename: return True
    #else: return False


# =================================================================


### Module classes ##

class ThunderReader(object):
    """Thunderbird Mail reader"""

    _profile = None
    _mbpaths = None
    _crnt_mbpath = None
    _mailbox = None

    def __init__(self, profilename='default'):
        self._profile = get_profile()  # Default profile: default
        self._mbpaths = self._get_mbpaths()  # List of mailbox paths

        # Current mailbox (Default: INBOX)
        self._crnt_mbpath = self._get_inbox_path()

        # Create mailbox mbox object
        self._open_mailbox(self._crnt_mbpath)

    def __len__(self):
        return len(self._mailbox)

    def __getitem__(self, key):
        return self._mailbox[key]

    @property
    def profile(self):
        return self._profile

    @profile.setter
    def profile(self, profile):
        self._profile = profile
        self._mbpaths = self._get_mbpaths()  # get mailboxes paths
        self._crnt_mbpath = self._get_inbox_path()
        self._open_mailbox(self._crnt_mbpath)

    @property
    def mailbox(self):
        return self._mailbox

    @property
    def mbpath(self):
        return self._crnt_mbpath

    @mbpath.setter
    def mbpath(self, path):
        if path not in self._mbpaths:
            return

        self._crnt_mbpath = path
        self._open_mailbox(path)

    @property
    def mbpaths(self):
        return self._mbpaths

    def _open_mailbox(self, path):
        """Set the mailbox in path and s the current mailbox"""
        if path is None or not os.path.exists(path):
            self._mailbox = []
        else:
            self._mailbox = mailbox.mbox(path, create=False)

    def _get_mbpaths(self):
        """Searches and returns the path for all mailboxes"""
        mbpaths = []
        for d in get_mail_directories(self.profile):
            mbpaths += [d + '/' + filename
                        for filename in os.listdir(d)
                        if is_mailbox(d + '/' + filename)]

        return mbpaths

    def _get_inbox_path(self):
        """Return the path of the default mailbox

        Returns the path of the first INBOX mailbox found. If there
        is none, return the first mailbox found. If there are no
        mailboxes, return None.

        """
        mbpaths = [p for p in self._mbpaths if p.endswith('INBOX')]
        if mbpaths:
            # set self._crnt_mbpath to first INBOX mbox file
            return mbpaths[0]
        elif self._mbpaths:
            # If no INBOX, get first mailbox found
            return self._mbpaths[0]
        else:
            return None


# =================================================================
# Testing procedures.
# Execute this file directly to perform unit testing.
# =================================================================

if __name__ == '__main__':
    import unittest
    import profileparser

    class TestThunderReader(unittest.TestCase):

        def setUp(self):
            THUNDERBIRD = os.getenv('THUNDERBIRD')
            if THUNDERBIRD is not None:
                self._path = THUNDERBIRD
            else:
                self._path = os.getenv('HOME') + '/.thunderbird'

            # Set module global variables
            global THUNDERBIRDPATH
            THUNDERBIRDPATH = self._path

            global THUNDERBIRDPROFILES
            THUNDERBIRDPROFILES = self._path + '/profiles.ini'

        def test_get_profile(self):
            p = get_profile()
            self.assertEqual(p.name, 'default')
            self.assertEqual(p.path, 'asaqivy2.default')

            p = get_profile('nonexistant')
            self.assertIsNone(p)

        def test_is_mailbox(self):
            filename = (self._path +
                        '/asaqivy2.default/ImapMail/imap.googlemail.com/INBOX')
            #sys.stdout.write(self._path + '\n')
            #sys.stdout.write(filename + '\n')
            self.assertTrue(is_mailbox(filename))
            self.assertFalse(is_mailbox(filename + '.msf'))

        def test_thunder(self):
            # Get profiles
            mailreader = ThunderReader()
            self.assertEqual(len(mailreader), 2)
            self.assertEqual(mailreader[1]['subject'], 'prueba')
            self.assertEqual(mailreader[1]['to'], 'luiorpe1@upv.es')

    try:
        assert sys.platform.startswith('linux')
    except AssertionError:
        raise AssertionError('Unsupported platform ' + sys.platform)
    unittest.main()
