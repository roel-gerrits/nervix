#!/usr/bin/env python3

import unittest
from struct import pack

from nervixd.services.nxtcp.encoder import *
import tests.nxtcp_packet_definition as packets


def dump(bs):
    """
    Dump the chunk to stdout.
    """

    for b in bs:
        print('%02x ' % b, end='')

    print()


class TestState(unittest.TestCase):

    def test_session(self):
        self.assertEncodePacket(
            SessionPacket(b'thename', SessionPacket.STATE_ENDED),
            packets.session(b'thename', packets.SESSION_STATE_ENDED)
        )

        self.assertEncodePacket(
            SessionPacket(b'thename', SessionPacket.STATE_STANDBY),
            packets.session(b'thename', packets.SESSION_STATE_STANDBY)
        )

        self.assertEncodePacket(
            SessionPacket(b'thename', SessionPacket.STATE_ACTIVE),
            packets.session(b'thename', packets.SESSION_STATE_ACTIVE)
        )

    def test_call(self):
        self.assertEncodePacket(
            CallPacket(False, 1234, b'name', b'thepayload'),
            packets.call(False, 1234, b'name', b'thepayload')
        )

        self.assertEncodePacket(
            CallPacket(True, 1234, b'name', b'thepayload'),
            packets.call(True, 0, b'name', b'thepayload')
        )

        self.assertEncodePacket(
            CallPacket(True, None, b'name', b'thepayload'),
            packets.call(True, 0, b'name', b'thepayload')
        )

    def test_message(self):
        self.assertEncodePacket(
            MessagePacket(1234, MessagePacket.STATUS_OK, b'thepayload'),
            packets.message(1234, packets.MESSAGE_STATUS_OK, b'thepayload')
        )

        self.assertEncodePacket(
            MessagePacket(1234, MessagePacket.STATUS_TIMEOUT, b'thepayload'),
            packets.message(1234, packets.MESSAGE_STATUS_TIMEOUT)
        )

        self.assertEncodePacket(
            MessagePacket(1234, MessagePacket.STATUS_UNREACHABLE, b'thepayload'),
            packets.message(1234, packets.MESSAGE_STATUS_UNREACHABLE)
        )

    def test_interest(self):
        self.assertEncodePacket(
            InterestPacket(1234, InterestPacket.STATUS_INTEREST, b'thetopic'),
            packets.interest(1234, packets.INTEREST_STATUS_INTEREST, b'thetopic')
        )

        self.assertEncodePacket(
            InterestPacket(1234, InterestPacket.STATUS_NO_INTEREST, b'thetopic'),
            packets.interest(1234, packets.INTEREST_STATUS_NOINTEREST, b'thetopic')
        )

    def test_ping(self):
        self.assertEncodePacket(
            PingPacket(b'thepayload'),
            packets.ping(b'thepayload')
        )

    def test_welcome(self):
        self.assertEncodePacket(
            WelcomePacket(1, 1),
            packets.welcome()
        )

    def test_byebye(self):
        self.assertEncodePacket(
            ByeByePacket(),
            packets.byebye()
        )

    # def test_sync_ack(self):
    #     self.assertEncodePacket(
    #         SyncAckPacket(),
    #         uint32(0) + uint8(0x85)
    #     )
    #
    # def test_align_verb(self):
    #     self.assertEncodePacket(
    #         AlignPacket(12341234),
    #         uint32(8) + uint8(0x11) + uint64(12341234000)
    #     )

    def assertEncodePacket(self, packet, encoded):
        e = Encoder()
        e.encode(packet)

        chunk = e.fetch_chunk()

        self.assertEqual(chunk, encoded)


"""
Helper functions to help construct packets
"""


def uint64(val):
    return pack('>Q', val)


def uint32(val):
    return pack('>I', val)


def uint8(val):
    return pack('>B', val)


def string(val):
    return pack('>B', len(val)) + val


def blob(val):
    return pack('>I', len(val)) + val


if __name__ == '__main__':
    unittest.main()
