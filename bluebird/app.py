#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""prefs.js file parser

This module contains contains the basis for the curses interface

classes:

Application -- Implements the low level functionality to run the
                     interface and glue together the activities.
Activity -- Basic activity. Do not use directly but specialize instead
InboxActivity -- List the emails in a mbox mailbox file
MailboxListActivity -- Lists all the mailboxes available
ProfileListActivity -- Lists all the thunderbird profiles
MessageActivity -- Display the contents of a message

"""
import curses
#import traceback
import os
import os.path
import email.message

from . import adapter
from . import thunder
from . import views
from . import utils


class Application(object):
    """Base class to maintain global application state

    This class is the top level of your curses application.
    It initializes the curses window and contains the low level
    management of activities.

    """

    _stack = None  # Stack of activities
    screen = None

    def __init__(self, screen, activity):
        self._stack = []
        self.screen = screen
        curses.curs_set(0)  # Remove cursor from screen
        #self._startActivity(eval('InboxActivity(self.screen)'))
        self._startActivity(eval(activity + '(self.screen)'))
        self._eventloop()

    def _startActivity(self, activity, bundle=None):
        """Start an activity

        Pauses any previous activity and launches the activity given
        as its first parameter. The bundle object will be passed to
        its callback methods.

        """
        if not isinstance(activity, Activity):
            raise TypeError

        try:
            self._stack[-1].onPause()
        except:
            pass

        self._stack.append(activity)
        activity.screen = self.screen
        activity._stack = self._stack

        activity.onCreate(bundle)
        activity.onResume(bundle)
        activity.draw()

    def _resumeActivity(self, activity, bundle=None):
        """Resumes an activity

        Resumes the activity given as its first parameter.
        The bundle object will be passed to its resume callback method.

        """
        activity.onResume(bundle)
        activity.draw()

    def _destroyActivity(self, activity=None):
        """Destroys an activity

        Destroy the activity given as its first parameter.
        The bundle object will be passed to its resume callback method.

        """
        success = True
        try:
            if activity is None:
                activity = self._stack[-1]

            if activity != self._stack[-1]:
                raise ValueError

            a = self._stack.pop()
            a.onPause()

            b = a.onDestroy()
            self._resumeActivity(self._stack[-1], b)
        except IndexError:
            # Should enter ONLY when destroying the last activity.
            # QUITS APPLICATION!!!
            success = False
        finally:
            return success

    def _eventloop(self):
        """Event loop

        This is the application event loop. It is the main input reading
        point and handles input events before passing them to the current
        active activity.

        """

        while True:
            ch = self.screen.getch()
            try:
                if ch in [ord('q'), ord('Q')]:
                    #self._stack.pop()
                    #if self._stack:
                    #    self._stack[-1].onResume()
                    #    self._stack[-1].draw()
                    #else: break
                    if not self._destroyActivity():
                        break
                else:
                    self._stack[-1].onKey(ch)
            except IndexError:
                break

## =================================================================


class Activity(Application):
    """An activity represents an interactive screen in your terminal

    An activity is a focused, single thing that the user can do.
    Here you can describe the UI elements in the screen and their
    interaction with the user.
    """

    _views = None  # List of views composing this activity
    _screen = None  # nCurses screen
    maxy = None
    maxx = None

    def __init__(self, screen=None):
        self._views = []
        self._setScreen(screen)

    # Property functions
    def _getScreen(self):
        return self._screen

    def _setScreen(self, screen):
        self._screen = screen
        if self._screen is not None:
            self.maxy, self.maxx = self._screen.getmaxyx()
        else:
            self.maxy, self.maxx = 0, 0

    screen = property(_getScreen, _setScreen, doc="Ncurses screen object")
    ###

    def finish(self):
        """A.finish() -> Bool

        Use this method to voluntarily terminate an activity.
        """
        super(Activity, self)._destroyActivity(self)

    def draw(self):
        """A.draw() -> None

        This method is responsible for drawing and activity on the screen.
        """
        for i in range(len(self._views)):
            if self._views[i] is None:
                continue
            self._views[i].window.clear()
            self._views[i].draw()
            self._views[i].window.noutrefresh()  # Mark for update only
        curses.doupdate()  # Update(Refresh) the physical screen

    # Event functions
    def onCreate(self, bundle=None):
        """A.onCreate(bundle=None) -> None

        This method is automatically called when an activity is created.
        Overload this method in your activity to define the layout and
        initialize its data.
        """
        return

    def onDestroy(self):
        """A.onDestroy() -> None

        This method is automatically called when an activity is destroyed.
        If your activity needs to pass on some information to the caller,
        overload this method and return a bundle object with the required
        data.

        """
        return

    def onResume(self, bundle=None):
        """A.onResume(bundle=None) -> None

        This method is automatically called after onCreate when the activity
        is created, and everytime the activity is popped from the activity
        stack. Here you should read the returning data from a previously
        called activity.

        """
        return

    def onPause(self):
        """A.onPause() -> None

        This method is automatically called when an activity starts
        another activity. This method offers the opportunity to release
        any resources and to preserve the activity's state.

        """
        return

    def onKey(self, ch):
        """A.onKey(ch) -> Bool

        This method is automatically called when an event is received.
        When the user presses a key, it is first interpreted by the
        application. If it doesn't match a rule, it is then pass down
        onto the running activity to handle. This method returns True
        when the activity handles the event, False otherwise.
        """
        return False

## =================================================================


class InboxActivity(Activity):
    """InboxActivity displays the list of messages in a mailbox"""

    _mailreader = None
    _commonfoottext = 'Q:Quit M:Mailboxes P:Profiles'
    _searchfoottext = ' /:Search'
    _undofoottext = ' U:Undo search'
    _listviewpos = None

    def __init__(self, screen=None):
        super(InboxActivity, self).__init__(screen)

    @property
    def mailreader(self):
        """Get an object with read access to email"""
        if self._mailreader is None:
            self._mailreader = thunder.ThunderReader()
        return self._mailreader

    @mailreader.setter
    def mailreader(self, mailreader):
        self._mailreader = mailreader

    def onCreate(self, bundle=None):
        for i in range(len(self._views)):
            self._views.pop()

        # Show loading dialog
        self.screen.erase()
        y = (self.maxy - 1)//2
        loadtext = 'Loading mailbox...'
        self.screen.addstr(y, (self.maxx - 1 - len(loadtext))//2,
                           loadtext, curses.A_BOLD)
        self.screen.refresh()
        #

        # Fetch the thunderbird mailreader object
        self._mailreader = self.mailreader

        # Set Activity views
        self._header = views.TextView(self._screen.subwin(1, self.maxx, 0, 0))
                                                        # Size & position
        self._views.append(self._header)

        self._footer = views.EditTextView(self._screen
                                              .subwin(1, self.maxx,
                                                      self.maxy - 1, 0))
        self._views.append(self._footer)

        self._listview = views.ListView(self._screen
                                            .subwin(self.maxy - 2,
                                                    self.maxx, 1, 0),
                                        hlcolor=curses.A_REVERSE)
        self._views.append(self._listview)

        # Configure views
        if self.mailreader.mbpath is None:
            self._header.text = ('%s %s |' %
                                ('Bluebird --', self.mailreader.profile.name))
        else:
            self._header.text = ('%s %s | %s [Msgs:%d %.2fM]' %
                                ('Bluebird --', self.mailreader.profile.name,
                                 ('/'.join(self.mailreader
                                               .mbpath.split('/')[-2:])),
                                 len(self.mailreader),
                                 (os.path.getsize(self.mailreader
                                                      .mbpath)/(1024*1024.0))))

        self._footer.text = self._commonfoottext + self._searchfoottext
        self._listview.adapter = adapter.MailboxAdapter(self._mailreader
                                                            .mailbox)

    def onResume(self, bundle=None):
        if bundle is None:
            return

        if 'mailbox_path' in bundle:
            # Change mailbox
            path = bundle['mailbox_path']
            if self.mailreader.mbpath != path:
                self.mailreader.mbpath = path
                self.onCreate()
        elif 'profilename' in bundle:
            # Change profile
            pname = bundle['profilename']
            if self.mailreader.profile.name != pname:
                self.mailreader.profile = thunder.get_profile(pname)
                self.onCreate()

    def onKey(self, ch):
        for view in self._views:
            if view is not None and view.onKey(ch):
                self.draw()
                return True

        if ch in (10, ord('e'), ord('E')):  # Enter
            #msgnum = int(self._listview.adapter[self._listview.pos]
            #                           .split()[0]) - 1
            #self._startActivity(MessageActivity(),
            #                    {'message':self.mailreader[msgnum]})
            self._startActivity(MessageActivity(),
                                {'message':
                                 self.mailreader[self._listview.pos]})
            return True
        if ch in [ord('m'), ord('M')]:
            self._startActivity(MailboxListActivity(),
                                {'mailreader': self.mailreader})
            return True
        elif ch in [ord('p'), ord('P')]:
            self._startActivity(ProfileListActivity(),
                                {'mailreader': self.mailreader})
            return True
        elif ch in [ord('/')]:  # Search
            if self._listview.adapter.isfiltered():
                curses.flash()
                return True

            tmp = self._footer.edit()
            if tmp is None:
                self.draw()
                return True

            self._footer.text = 'Searching... This could take a few minutes.'
            self._footer.draw()
            self._footer.window.refresh()

            self._listviewpos = self._listview.pos
            self._listview.adapter.filterby(tmp)

            if self._listview.adapter.isfiltered():
                self._footer.text = self._commonfoottext + self._undofoottext
                self._listview._move(0)

            self.draw()
            return True
        elif ch in [ord('u'), ord('U')]:
            self._listview.adapter.unfilter()
            if self._listviewpos is not None:
                self._listview._move(self._listviewpos)
                self._listviewpos = None
            self._footer.text = self._commonfoottext + self._searchfoottext
            self.draw()
        else:
            return super(InboxActivity, self).onKey(ch)

## =================================================================


class MailboxListActivity(Activity):
    """MailboxListActivity displays the list of available mailbox files"""

    _mailreader = None
    _privbundle = None

    def __init__(self, screen=None):
        super(MailboxListActivity, self).__init__(screen)

    def onCreate(self, bundle=None):
        if bundle is not None:
            if isinstance(bundle['mailreader'], thunder.ThunderReader):
                self.mailreader = bundle['mailreader']
            else:
                raise TypeError
        else:
            self._mailreader = self.mailreader

        # Set Activity views
        self._header = views.TextView(self._screen.subwin(1, self.maxx, 0, 0))
                                                            # Size & position
        self._views.append(self._header)

        self._footer = views.TextView(self._screen.subwin(1, self.maxx,
                                                          self.maxy - 1, 0))
        self._views.append(self._footer)

        self._listview = views.ListView(self._screen.subwin(self.maxy - 2,
                                                            self.maxx, 1, 0),
                                        hlcolor=curses.A_REVERSE)
        self._views.append(self._listview)

        # Configure views
        self._header.text = ('%s %s | %s' %
                            ('Bluebird --',
                             self.mailreader.profile.name,
                             'Available mailbox trays'))
        self._footer.text = 'Q:Quit'

        self._listview.adapter = adapter.BaseAdapter(self.mailreader.mbpaths)

        # Highlight current mailbox
        for i in range(len(self._listview.adapter)):
            if self._listview.adapter[i] == self.mailreader.mbpath:
                self._listview.pos = i
                break

    def onDestroy(self):
        return self._privbundle

    def onKey(self, ch):
        for view in self._views:
            if view is not None and view.onKey(ch):
                self.draw()
                return True

        if ch in [ord('e'), 10]:  # curses.KEY_ENTER
            self._privbundle = {'mailbox_path': (
                                self._listview.adapter[self._listview.pos])}
            self.finish()
            return True

        return super(InboxActivity, self).onKey(ch)

## =================================================================


class ProfileListActivity(Activity):
    """ProfileListActivity displays the list of available profiles"""

    _mailreader = None
    _privbundle = None

    def __init__(self, screen=None):
        super(ProfileListActivity, self).__init__(screen)

    def onCreate(self, bundle=None):
        if bundle is not None:
            if isinstance(bundle['mailreader'], thunder.ThunderReader):
                self.mailreader = bundle['mailreader']
            else:
                raise TypeError
        else:
            self._mailreader = self.mailreader

        # Set Activity views
        self._header = views.TextView(self._screen.subwin(1, self.maxx, 0, 0))
                                                            # Size & position
        self._views.append(self._header)

        self._footer = views.TextView(self._screen.subwin(1, self.maxx,
                                                          self.maxy - 1, 0))
        self._views.append(self._footer)

        self._listview = views.ListView(self._screen.subwin(self.maxy - 2,
                                                            self.maxx, 1, 0),
                                        hlcolor=curses.A_REVERSE)
        self._views.append(self._listview)

        # Configure views
        self._header.text = ('%s %s | %s' %
                            ('Bluebird --',
                             self.mailreader.profile.name,
                             'Available profiles'))
        self._footer.text = 'Q:Quit'

        profilenames = [p.name for p in thunder.get_profiles()]
        self._listview.adapter = adapter.BaseAdapter(profilenames)

        # Highlight current profile
        for i in range(len(self._listview.adapter)):
            if self._listview.adapter[i] == self.mailreader.profile.name:
                self._listview.pos = i
                break

    def onDestroy(self):
        return self._privbundle

    def onKey(self, ch):
        for view in self._views:
            if view is not None and view.onKey(ch):
                self.draw()
                return True

        if ch in [ord('e'), 10]:  # ENTER
            self._privbundle = {'profilename':
                                self._listview.adapter[self._listview.pos]}
            self.finish()
            return True

        return super(InboxActivity, self).onKey(ch)

## =================================================================


class MessageActivity(Activity):
    """MessageActivity displays the the constents of a message"""

    _message = None
    _foottext = 'Q:Quit /:Search'

    def __init__(self, screen=None):
        super(MessageActivity, self).__init__(screen)

    @property
    def message(self):
        return self._message

    @message.setter
    def message(self, message):
        self._message = message

    def onCreate(self, bundle=None):
        if bundle is not None:
            if isinstance(bundle['message'], email.message.Message):
                self.message = bundle['message']
            else:
                raise TypeError

        # Define color pairs
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_RED)

        # Set Activity views
        self._header = views.TextView(self._screen.subwin(1, self.maxx, 0, 0))
                                                            # Size & position
        self._views.append(self._header)

        self._footer = views.EditTextView(self._screen.subwin(1, self.maxx,
                                                              self.maxy - 1, 0)
                                          )
        self._views.append(self._footer)

        self._listview = views.ListView(self._screen.subwin(self.maxy - 2,
                                                            self.maxx, 1, 0),
                                        hlcolor=curses.A_REVERSE)
        self._views.append(self._listview)

        # Configure views
        self._header.text = ('%s %s' %
                            ('Bluebird --',
                             utils.get_header_param(self.message, 'subject')
                                  .strip()))
        self._footer.text = self._foottext
        self._listview.adapter = adapter.MessageAdapter(self.message)

    def onKey(self, ch):
        for view in self._views:
            if view is not None and view.onKey(ch):
                self.draw()
                return True

        if ch in [ord('/')]:
            tmp = self._footer.edit()

            if tmp is None:
                self._footer.text = self._foottext
                self.draw()
                return True

            #self._footer.text = tmp + ' mec'
            count = self._listview.highlighttext(tmp)

            self._footer.text = self._foottext
            if count != 0:
                self.draw()
            else:
                self._footer.error('Pattern not found', curses.A_REVERSE)
            return True
        elif ch in (10, ord('a'), ord('A')):
            attmsg = self._listview.adapter.get_attachment(self._listview.pos)

            if attmsg is None:
                return True

            filepath = ('%s/%s' %
                        (os.getcwd(), attmsg.get_filename(failobj='unknown')))
            filepath = self._footer.edit(filepath)

            if filepath is None:
                self.draw()
                return True

            # Define private inner function
            def save_attachment(attmsg, filepath):
                with open(filepath, 'wb') as f:
                    f.write(utils.get_content_body(attmsg, attachment=True))

            # Checks and writing
            if not os.path.exists(os.path.dirname(filepath)):
                #curses.flash()
                self._footer.error('Error: ' + filepath + ' does not exist',
                                   curses.color_pair(3)
                                   )
            elif os.path.exists(filepath):
                while True:
                    answer = self._footer.edit('File already exists. '
                                               'Overwrite? (Y/N): ')
                    if answer is None:
                        #self._footer.error('Error: %s already exists' %
                        #                   (filepath),
                        #                   curses.color_pair(3))
                        break
                    elif answer.split()[-1].lower() in ('n', 'no'):
                        self._footer.text = self._foottext
                        self._footer.draw()
                        self._footer.window.refresh()
                        break
                    elif answer.split()[-1].lower() in ('y', 'yes'):
                        save_attachment(attmsg, filepath)
                        self._footer.error('Saved ' + filepath,
                                           curses.color_pair(2))
                        break
            else:
                save_attachment(attmsg, filepath)
                self._footer.error('Saved ' + filepath,
                                   curses.color_pair(2))

            return True
        else:
            return super(MessageActivity, self).onKey(ch)
