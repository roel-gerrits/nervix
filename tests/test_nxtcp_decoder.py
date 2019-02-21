#!/usr/bin/env python3

import unittest
from struct import pack

from nervixd.services.nxtcp.decoder import *

import tests.nxtcp_packet_definition as packets


class TestState(unittest.TestCase):

    def test_uint8(self):
        p = BasePacket(packets.uint8(99))

        self.assertEqual(
            p.get_uint8(0),
            99
        )

        self.assertEqual(p.nextbyte, 1)

    def test_uint32(self):
        p = BasePacket(packets.uint32(99))

        self.assertEqual(
            p.get_uint32(0),
            99
        )

        self.assertEqual(p.nextbyte, 4)

    def test_string(self):
        p = BasePacket(packets.string(b'test'))

        self.assertEqual(
            p.get_string(0),
            b'test'
        )

        self.assertEqual(p.nextbyte, 5)

    def test_blob(self):
        p = BasePacket(packets.blob(b'test'))

        self.assertEqual(
            p.get_blob(0),
            b'test'
        )

        self.assertEqual(p.nextbyte, 8)

    def test_login(self):
        self.assertDecodePacket(
            packets.login(b'123', False, False, False),
            LoginPacket,
            persist=False,
            standby=False,
            enforce=False,
            name=b'123'
        )

        self.assertDecodePacket(
            packets.login(b'123', True, False, False),
            LoginPacket,
            persist=True,
            standby=False,
            enforce=False,
            name=b'123'
        )

        self.assertDecodePacket(
            packets.login(b'123', False, True, False),
            LoginPacket,
            persist=False,
            standby=True,
            enforce=False,
            name=b'123'
        )

        self.assertDecodePacket(
            packets.login(b'123', False, False, True),
            LoginPacket,
            persist=False,
            standby=False,
            enforce=True,
            name=b'123'
        )

    def test_logout(self):
        self.assertDecodePacket(
            packets.logout(b'thename'),
            LogoutPacket,
            name=b'thename'
        )

    def test_request(self):
        self.assertDecodePacket(
            packets.request(b'thename', False, 12345, 1500, b'thepayload'),
            RequestPacket,
            name=b'thename',
            unidirectional=False,
            messageref=12345,
            timeout=1.5,
            payload=b'thepayload'
        )

        self.assertDecodePacket(
            packets.request(b'thename', True, 12345, 1500, b'thepayload'),
            RequestPacket,
            name=b'thename',
            unidirectional=True,
            messageref=None,
            timeout=1.5,
            payload=b'thepayload'
        )

    def test_post(self):
        self.assertDecodePacket(
            packets.post(12345, b'thepayload'),
            PostPacket,
            postref=12345,
            payload=b'thepayload'
        )

    def test_subscribe(self):
        self.assertDecodePacket(
            packets.subscribe(12345, b'thename', b'thetopic'),
            SubscribePacket,
            messageref=12345,
            name=b'thename',
            topic=b'thetopic'
        )

    def test_unsubscribe(self):
        self.assertDecodePacket(
            packets.unsubscribe(b'thename', b'thetopic'),
            UnsubscribePacket,
            name=b'thename',
            topic=b'thetopic'
        )

    def test_pong(self):
        self.assertDecodePacket(
            packets.pong(),
            PongPacket,
        )

    def test_quit(self):
        self.assertDecodePacket(
            packets.quit(),
            QuitPacket
        )

    def assertDecodePacket(self, chunk, cls, **attr):
        d = Decoder()
        d.add_chunk(chunk)

        packet = d.decode()

        self.assertIsInstance(packet, cls, msg='Decoded packet is not of type {}'.format(cls))

        for field, value in attr.items():
            self.assertEqual(
                getattr(packet, field),
                value,
                msg="attribute '{}' is not equal to {}".format(field, value)
            )


if __name__ == '__main__':
    unittest.main()
