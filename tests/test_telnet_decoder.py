#!/usr/bin/env python3

import unittest

from nervixd.services.telnet.decoder import *


class TestState(unittest.TestCase):

    def test_empty(self):

        self.assertEqual(
            None,
            self.parse_packet(b'\r\n')
        )

        self.assertEqual(
            None,
            self.parse_packet(b' \r\n')
        )

    def test_invalid_cmd(self):

        with self.assertRaises(DecodingError):
            self.parse_packet(b'*\r\n')

    def test_base_read_remaining(self):

        p = BasePacket(b'')
        self.assertEqual(p.read_remaining(), None)

        p = BasePacket(b'test123')
        self.assertEqual(b'test123', p.read_remaining())
        self.assertEqual(None, p.read_remaining())

    def test_base_read_string(self):

        p = BasePacket(b'string1 string2 string3')
        self.assertEqual(b'string1', p.read_string())
        self.assertEqual(b'string2', p.read_string())
        self.assertEqual(b'string3', p.read_string())
        self.assertEqual(None, p.read_string())

        p = BasePacket(b'')
        self.assertEqual(None, p.read_string())

    def test_base_read_positive_integer(self):

        p = BasePacket(b'')
        self.assertEqual(None, p.read_positive_integer())

        p = BasePacket(b'0')
        self.assertEqual(0, p.read_positive_integer())

        p = BasePacket(b'1')
        self.assertEqual(1, p.read_positive_integer())

        p = BasePacket(b'9')
        self.assertEqual(9, p.read_positive_integer())

        p = BasePacket(b'12')
        self.assertEqual(12, p.read_positive_integer())

        p = BasePacket(b'123')
        self.assertEqual(123, p.read_positive_integer())

        p = BasePacket(b'123 ')
        self.assertEqual(123, p.read_positive_integer())

        p = BasePacket(b'-123 ')
        self.assertEqual(None, p.read_positive_integer())

        p = BasePacket(b'not-a-number')
        self.assertEqual(None, p.read_positive_integer())

    def test_reread(self):

        p = BasePacket(b'111word')
        self.assertEqual(None, p.read_positive_integer())
        self.assertEqual(b'111word', p.read_remaining())

        p = BasePacket(b'word**')
        self.assertEqual(None, p.read_string())
        self.assertEqual(b'word**', p.read_remaining())

    def test_ping(self):

        self.assertDecodePacket(
            b'PING\r\n',
            PingPacket,
            payload=None
        )

        self.assertDecodePacket(
            b'PING some payload\r\n',
            PingPacket,
            payload=b'some payload'
        )

    def test_login(self):

        self.assertDecodePacket(
            b'LOGIN name1\r\n',
            LoginPacket,
            name=b'name1',
            enforce=False,
            standby=False,
            persist=False,
        )

        self.assertDecodePacket(
            b'LOGIN name1 ENFORCE\r\n',
            LoginPacket,
            name=b'name1',
            enforce=True,
            standby=False,
            persist=False,
        )

        self.assertDecodePacket(
            b'LOGIN name1 STANDBY\r\n',
            LoginPacket,
            name=b'name1',
            enforce=False,
            standby=True,
            persist=False,
        )

        self.assertDecodePacket(
            b'LOGIN name1 PERSIST\r\n',
            LoginPacket,
            name=b'name1',
            enforce=False,
            standby=False,
            persist=True,
        )

        self.assertDecodePacket(
            b'LOGIN name1 ENFORCE STANDBY PERSIST\r\n',
            LoginPacket,
            name=b'name1',
            enforce=True,
            standby=True,
            persist=True,
        )

        with self.assertRaises(DecodingError):
            self.parse_packet(b'LOGIN\r\n')

    def test_logout(self):

        self.assertDecodePacket(
            b'LOGOUT name1\r\n',
            LogoutPacket,
            name=b'name1',
        )

        with self.assertRaises(DecodingError):
            self.parse_packet(b'LOGOUT\r\n')

    def test_post(self):

        self.assertDecodePacket(
            b'POST 123 payload payload\r\n',
            PostPacket,
            postref=123,
            payload=b'payload payload',
        )

        with self.assertRaises(DecodingError):
            self.parse_packet(b'POST\r\n')

        with self.assertRaises(DecodingError):
            self.parse_packet(b'POST 123\r\n')

    def test_request(self):

        self.assertDecodePacket(
            b'REQUEST 1234 name1 5 payload payload\r\n',
            RequestPacket,
            name=b'name1',
            messageref=1234,
            unidirectional=False,
            timeout=5.0,
            payload=b'payload payload',
        )

        self.assertDecodePacket(
            b'REQUEST UNI name1 5 payload payload\r\n',
            RequestPacket,
            name=b'name1',
            messageref=None,
            unidirectional=True,
            timeout=5.0,
            payload=b'payload payload',
        )

        self.assertDecodePacket(
            b'REQUEST 1234 name1 payload payload\r\n',
            RequestPacket,
            name=b'name1',
            messageref=1234,
            unidirectional=False,
            timeout=None,
            payload=b'payload payload',
        )

        self.assertDecodePacket(
            b'REQUEST UNI name1 payload payload\r\n',
            RequestPacket,
            name=b'name1',
            messageref=None,
            unidirectional=True,
            timeout=None,
            payload=b'payload payload',
        )

        with self.assertRaises(DecodingError):
            self.parse_packet(b'REQUEST name1 payload payload\r\n')

        with self.assertRaises(DecodingError):
            self.parse_packet(b'REQUEST 123 name1\r\n')

    def test_subscribe(self):

        self.assertDecodePacket(
            b'SUBSCRIBE 999 name1 topic1\r\n',
            SubscribePacket,
            messageref=999,
            name=b'name1',
            topic=b'topic1'
        )

        self.assertDecodePacket(
            b'SUBSCRIBE 999 name1 topic topic\r\n',
            SubscribePacket,
            messageref=999,
            name=b'name1',
            topic=b'topic topic'
        )

        with self.assertRaises(DecodingError):
            self.parse_packet(b'SUBSCRIBE\r\n')

        with self.assertRaises(DecodingError):
            self.parse_packet(b'SUBSCRIBE name1\r\n')

    def test_unsubscribe(self):

        self.assertDecodePacket(
            b'UNSUBSCRIBE name1 topic1\r\n',
            UnsubscribePacket,
            name=b'name1',
            topic=b'topic1'
        )

        self.assertDecodePacket(
            b'UNSUBSCRIBE name1 topic topic\r\n',
            UnsubscribePacket,
            name=b'name1',
            topic=b'topic topic'
        )

        with self.assertRaises(DecodingError):
            self.parse_packet(b'UNSUBSCRIBE\r\n')

        with self.assertRaises(DecodingError):
            self.parse_packet(b'UNSUBSCRIBE name1\r\n')

    def test_quit(self):

        self.assertDecodePacket(
            b'QUIT\r\n',
            QuitPacket,
        )

        with self.assertRaises(DecodingError):
            self.parse_packet(b'QUIT test\r\n')

    def test_help(self):

        self.assertDecodePacket(
            b'HELP\r\n',
            HelpPacket,
            topic=None
        )

        self.assertDecodePacket(
            b'HELP topic\r\n',
            HelpPacket,
            topic=b'topic'
        )

    def assertDecodePacket(self, chunk, cls, **attr):
        d = Decoder()
        d.add_chunk(chunk)

        packet = d.decode()

        self.assertIsInstance(packet, cls, msg='Decoded packet is not of type {}'.format(cls))

        for field, value in attr.items():
            self.assertEqual(
                value,
                getattr(packet, field),
                msg="attribute '{}' is not equal to {}".format(field, value)
            )

    def parse_packet(self, chunk):
        d = Decoder()
        d.add_chunk(chunk)
        return d.decode()


if __name__ == '__main__':
    unittest.main()
