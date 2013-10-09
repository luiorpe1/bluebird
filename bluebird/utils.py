#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import email.header


def get_header_param(message, name):
    """Get field name from a message header"""
    if sys.version_info.major == 3:
        return get_header_param3(message, name)
    else:
        return get_header_param2(message, name)


def get_header_param2(message, name):
    values = email.header.decode_header(message[name])
    pair = values.pop()
    if pair[1] is None:
        try:
            return pair[0].encode('utf-8')
        except UnicodeDecodeError:
            return pair[0]
    else:
        try:
            return pair[0].decode(pair[1]).encode('utf-8')
        except UnicodeDecodeError:
            return pair[0].decode(pair[1])


def get_header_param3(message, name):
    values = email.header.decode_header(message[name])  # message[name]
    pair = values.pop()  # returns tuple (value, encoding)
    if pair[1] is None:
        if isinstance(pair[0], bytes):
            return pair[0].decode()
        return pair[0]
    else:
        try:
            return pair[0].decode(pair[1])
        except LookupError:
            return '?' * len(pair[0])

# =================================================================


def get_content_type(message):
    """Get the content type of a message"""
    if message.is_multipart():
        return get_content_type(message.get_payload(i=0))
    else:
        return message.get_content_type()

# =================================================================


def get_content_body(message, attachment=False):
    """Get the content body of a message"""
    # attachment=True when we want the content in bytes/untouched.
    # e.g: attachments
    if sys.version_info.major == 3:
        return get_content_body3(message, attachment)
    else:
        return get_content_body2(message)


def get_content_body2(message):
    if message.is_multipart():
        # NOTA: get_payload() returns list of message objects if is_multipart()
        # [0] es el cuerpo y el resto adjuntos
        # get_filename() para recuperar el nombre del fichero adjunto
        return get_content_body2(message.get_payload(i=0))
    else:
        charset = message.get_param('charset')
        if not message.is_multipart():
            if charset is not None:
                try:
                    return (message.get_payload(decode=True)
                                   .decode(charset, errors='replace')
                                   .encode('utf-8'))
                except UnicodeDecodeError:
                    return (message.get_payload(decode=True)
                                   .decode(charset, errors='replace'))
                except LookupError:
                    return message.get_payload(decode=True)
            else:
                try:
                    return message.get_payload(decode=True).encode('utf-8')
                except UnicodeDecodeError:
                    return message.get_payload(decode=True)


def get_content_body3(message, attachment=False):
    if message.is_multipart():
        #NOTA: get_payload() returns list of message objects if is_multipart()
        # [0] es el cuerpo y el resto adjuntos
        return get_content_body3(message.get_payload(i=0))
    else:
        charset = message.get_param('charset')
        msg = None
        if charset is not None:
            try:
                msg = (message.get_payload(decode=True)
                              .decode(charset, errors='replace'))
            except LookupError:
                msg = message.get_payload(decode=True)
        else:
            msg = message.get_payload(decode=True)

        if isinstance(msg, bytes):
            if attachment:
                return msg
            else:
                return msg.decode(errors='replace')
        else:
            return msg

# =================================================================


def get_attachments(message):
    """Get the list of attachments of a message"""
    if message.is_multipart():
        return message.get_payload()[1:]
    else:
        return []


def has_attachments(message):
    """Rteturns True if a message has attachments. False otherwise"""
    if not message.is_multipart():
        return False
    else:
        return True
