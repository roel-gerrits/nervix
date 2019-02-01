#!/usr/bin/env python3

import unittest

from nervixd.services.telnet.encoder import *


class TestState(unittest.TestCase):

    def test_session(self):
        self.assertEncodePacket(
            SessionPacket(b'name1', SessionPacket.STATE_ENDED),
            b'SESSION name1 ENDED\r\n'
        )

        self.assertEncodePacket(
            SessionPacket(b'name1', SessionPacket.STATE_STANDBY),
            b'SESSION name1 STANDBY\r\n'
        )

        self.assertEncodePacket(
            SessionPacket(b'name1', SessionPacket.STATE_ACTIVE),
            b'SESSION name1 ACTIVE\r\n'
        )

    def test_call(self):
        self.assertEncodePacket(
            CallPacket(False, 111, b'name', b'payload payload'),
            b'CALL 111 name payload payload\r\n'
        )

        self.assertEncodePacket(
            CallPacket(False, 111, b'name', b'payload'),
            b'CALL 111 name payload\r\n'
        )

        self.assertEncodePacket(
            CallPacket(True, None, b'name', b'payload'),
            b'CALL UNI name payload\r\n'
        )

        self.assertEncodePacket(
            CallPacket(True, 111, b'name', b'payload'),
            b'CALL UNI name payload\r\n'
        )

    def test_message(self):
        self.assertEncodePacket(

            MessagePacket(999, MessagePacket.STATUS_OK, b''),
            b'MESSAGE 999 OK \r\n'
        )

        self.assertEncodePacket(
            MessagePacket(999, MessagePacket.STATUS_OK, b'payload'),
            b'MESSAGE 999 OK payload\r\n'
        )

        self.assertEncodePacket(
            MessagePacket(999, MessagePacket.STATUS_OK, b'payload payload'),
            b'MESSAGE 999 OK payload payload\r\n'
        )

        self.assertEncodePacket(
            MessagePacket(999, MessagePacket.STATUS_TIMEOUT, b'payload payload'),
            b'MESSAGE 999 TIMEOUT\r\n'
        )

        self.assertEncodePacket(
            MessagePacket(999, MessagePacket.STATUS_UNREACHABLE, b'payload payload'),
            b'MESSAGE 999 UNREACHABLE\r\n'
        )

    def test_interest(self):
        self.assertEncodePacket(
            InterestPacket(123, InterestPacket.STATUS_INTEREST, b'name', b'topic topic'),
            b'INTEREST 123 INTEREST name topic topic\r\n'
        )

        self.assertEncodePacket(
            InterestPacket(123, InterestPacket.STATUS_NO_INTEREST, b'name', b'topic topic'),
            b'INTEREST 123 NO_INTEREST name topic topic\r\n'
        )

    def test_pong(self):
        self.assertEncodePacket(
            PongPacket(b''),
            b'PONG\r\n'
        )

        self.assertEncodePacket(
            PongPacket(b'payload payload'),
            b'PONG payload payload\r\n'
        )

    def test_welcome(self):
        self.assertEncodePacket(
            WelcomePacket(88, 99),
            b'WELCOME server_version=88 protocol_version=99\r\n'
        )

    def test_byebye(self):
        self.assertEncodePacket(
            ByeByePacket(),
            b'BYEBYE\r\n'
        )

    def test_info(self):
        e = Encoder()
        e.encode(InfoPacket(b'General'))
        chunk = e.fetch_chunk()
        self.assertIsNotNone(chunk)

    def test_invalid_request(self):
        e = Encoder()
        e.encode(InvalidRequestPacket(b'reason'))
        chunk = e.fetch_chunk()
        self.assertIsNotNone(chunk)

    def assertEncodePacket(self, packet, encoded):
        e = Encoder()
        e.encode(packet)

        chunk = e.fetch_chunk()

        self.assertEqual(chunk, encoded)


if __name__ == '__main__':
    unittest.main()
