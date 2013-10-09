#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import email.message

from .htmlparser import BlueHTMLParser
from . import utils


class BaseAdapter(object):
    """Common base class of common implementation for an Adapter"""

    _data = None

    def __init__(self, datasource):
        if not isinstance(datasource, list):
            raise TypeError

        if sys.version_info.major == 3:
            self._data = datasource
        else:
            self._data = [line.encode('utf-8') for line in datasource]

    def __len__(self):
        return len(self._data)

    def __getitem__(self, key):
        return self._data[key]

    def __iter__(self):
        return iter(self._data)


class MailboxAdapter(BaseAdapter):
    """Adapter implementation for mailbox metadata

    Extended Adapter that is the bridge between a ListView
    and the metadata of the messages contained in a mailbox file.
    """

    _mailbox = None
    _filtereddata = None

    def __init__(self, mailbox):
        self._data = []
        self._mailbox = mailbox

        #for n, m in enumerate(mailbox):
        #    self._data.append(self.__headerline(m, n))
        for i in range(30):
            try:
                msg = mailbox[i]
            except KeyError:
                break
            self._data.append(self.__headerline(msg, i))

    def __headerline(self, message, number):
        """Format message header info into a single text line"""

        fields = [None] * 5
        fields[0] = str(number + 1).rjust(2)
        #fields[0] = str(number + 1)

        if message.is_multipart():
            fields[1] = 'a'
        else:
            fields[1] = ' '

        fields[2] = self.__pretty_date(utils.get_header_param(message, 'date'))
        fields[3] = self.__pretty_from(utils.get_header_param(message, 'from'))
        fields[4] = utils.get_header_param(message, 'subject').strip()

        return ' '.join(fields)

    def __pretty_date(self, date):
        """Extract date from the date header string"""
        # Common format is, e.g: Sat, 16 Jan 2013
        # Sometetimes the day of the week is not included
        fields = date.split()
        if len(fields[0]) > 2:  # Day of week
            fields = fields[1:]

        try:
            return ('%s %s %s' % (fields[0], fields[1], fields[2])).rjust(11)
        except TypeError:
            return date[5:16].rjust(11)  # Best effort

    def __pretty_from(self, sender):
        """Extract sender from the from header string"""
        if sender.startswith('"'):
            try:
                sender = sender[1:sender.index('"', 1)]  # chars between ""
            except ValueError:
                sender = sender[1:]
        elif sender.startswith('<'):
            try:
                sender = sender[1:sender.index('>', 1)]  # chars between <>
            except ValueError:
                sender = sender[1:]

        tmp = ''
        for elem in sender.split():
            tmp = tmp + elem + ' '
            if len(tmp) > 15:
                break
            else:
                sender = tmp

        # Return 15 leading characters left justified
        return sender[:15].ljust(15)

    def isfiltered(self):
        """A.isfiltered() -> Bool

        Return True is the data in the adapter is filtered. False otherwise.
        """
        if self._filtereddata is None:
            return False
        else:
            return True

    def unfilter(self):
        """A.unfilter() -> void

        Undo a previous search.
        """
        self._filtereddata = None

    def filterby(self, pattern):
        """A.filterby(pattern) -> void

        Filter the data in the adapter with the given pattern. The pattern
        can be prefixed with a keyword to search specific fields, otherwise
        the search will be performed in the message fields subject and from
        and in the main content.

        Valid keywords are:
        from: Filter messages by their 'from' field.
        subject: Filter messages by their 'subject' field.
        date: Filter messages by their date in dd/mm/yyyy format. If a second
              date is given it will search all messages between the two.
        """
        if self._filtereddata is not None:
            return

        p = pattern.lower().split()
        if p[0] in ('from', 'f') and len(p) > 1:
            self._filtereddata = self.__filterby_header('from', ' '.join(p[1:]))
        elif p[0] in ('subject', 's') and len(p) > 1:
            self._filtereddata = self.__filterby_header('subject', ' '.join(p[1:]))
        elif p[0] in ('date', 'd') and len(p) > 1:
            if len(p) > 2:
                self._filtereddata = self.__filterby_date(p[1], p[2])
            else:
                self._filtereddata = self.__filterby_date(p[1])
        else:
            self._filtereddata = self.__filter(pattern)

    def __filterby_header(self, param, pattern):
        data = []
        for n, m in enumerate(self._mailbox):
            if pattern in utils.get_header_param(m, param):
                data.append(self.__headerline(m, n))
        return data

    def __filter(self, pattern):
        data = []
        for n, m in enumerate(self._mailbox):
            if pattern in utils.get_header_param(m, 'from') or \
               pattern in utils.get_header_param(m, 'subject') or \
               pattern in utils.get_content_body(m):
                    data.append(self.__headerline(m, n))
        return data

    def __filterby_date(self, date1, date2=None):
        import datetime
        data = []
        #error = False
        dt1 = dt2 = None

        try:
            dt1 = datetime.datetime.strptime(date1, '%d/%m/%Y')
        except ValueError:
            pass
            #error = True

        try:
            dt2 = datetime.datetime.strptime(date2, '%d/%m/%Y')
        #except ValueError:
        #    error = True
        except TypeError:
            dt2 = datetime.datetime.now()

        if dt2 > dt1:
            dt1, dt2 = dt2, dt1

        for n, m in enumerate(self._mailbox):
            date = utils.get_header_param(m, 'date')[5:16]
            try:
                dt = datetime.datetime.strptime(date, '%d %b %Y')
            except ValueError:
                continue
            if dt > dt1:
                continue
            elif dt < dt2:
                break
            else:
                data.append(self.__headerline(m, n))
        return data

    def __len__(self):
        if self._filtereddata is None:
            #return len(self._data)
            return len(self._mailbox)
        else:
            return len(self._filtereddata)

    def __getitem__(self, key):
        """x.__getitem__(y) <==> x[y]"""
        # Delegate checks to list implementation
        if self._filtereddata is not None:
            return self._filtereddata[key]
        else:
            #return self._data[key]
            try:
                return self._data[key]
            except IndexError:
                pass  # Fetch more data from mailbox

            len_ = len(self._data)
            for i in range(len_, len_ + 10):
                try:
                    msg = self._mailbox[i]
                except KeyError:
                    break
                self._data.append(self.__headerline(msg, i))
            return self._data[key]

    def __iter__(self):
        """x.__iter__() <==> iter(x)"""
        if self._filtereddata is None:
            return iter(self._data)
        else:
            return iter(self._filtereddata)


class MessageAdapter(BaseAdapter):
    """Adapter implementation for message data

    Extended Adapter that is the bridge between a ListView
    and the data of a mail message.
    """

    _attachment = {}

    def __init__(self, message):
        if not isinstance(message, email.message.Message):
            raise TypeError

        data = [' '.join(('Date:', utils.get_header_param(message, 'date'))),
                ' '.join(('To:', utils.get_header_param(message, 'to').strip())),
                ' '.join(('From:', utils.get_header_param(message, 'from').strip())),
                ' '.join(('Subject:', utils.get_header_param(message, 'subject').strip()))]

        if utils.has_attachments(message):
            lineno = len(data)
            #tmp = ['Attachments:']
            tmp = []
            for i, m in enumerate(utils.get_attachments(message)):
                tmp.append(' '.join(['Attachment',
                                    str(i+1) + ':',
                                    m.get_filename(failobj='<unknown>'),
                                    '<' + m.get_content_type() + '>']
                                    ))
                self._attachment[lineno + i] = m
            data = data + tmp

        if utils.get_content_type(message) == 'text/html':
            parser = BlueHTMLParser()
            parser.feed(utils.get_content_body(message))
            data += ['\n'] + ''.join(parser.get_result()).splitlines()
        else:
            data += ['\n'] + utils.get_content_body(message).splitlines()

        self._data = data

    def get_attachment(self, lineno, failobj=None):
        """A.get_attachment(lineno) -> Message

        A message text and attachments are represented as message objects.
        This method returns the message object for the attachment selected
        or failobj if not found.
        """
        message = failobj  # attachmenst are message objects
        try:
            message = self._attachment[lineno]
        except KeyError:
            pass
        finally:
            return message
