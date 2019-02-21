import logging
from struct import pack_into, pack

from nervixd.util.encoder import BaseEncoder

from .defines import *

logger = logging.getLogger(__name__)


class Encoder(BaseEncoder):

    def encode(self, packet):
        """
        Encode a packet object and append it to the internal 
        chunkbuffer.
        """

        chunk = packet.get_chunk()

        self.add_encoded_chunk(chunk)

        # logger.debug("Encoded %s", packet)


class BasePacket:

    def __init__(self):
        self.chunk = bytearray(5)

    def get_chunk(self):
        """
        Return a bytes object which contains the encoded data.
        """

        length = len(self.chunk) - 5

        pack_into('>i', self.chunk, 0, length)

        return bytes(self.chunk)

    def set_type(self, packettype):
        """
        Set the packet type.
        """
        self.chunk[4] = packettype

    def add_field(self, value=[]):
        """
        Add a field to the packet.
        """
        self.chunk.extend(value)

    def add_uint8_field(self, value):
        """
        Add a uint8 field to the packet.
        """
        self.add_field([value])

    def add_uint32_field(self, value):
        """
        Add a unit32 field to the packet.
        """
        self.add_field(pack('>I', value))

    def add_uint64_field(self, value):
        """
        Add a unit64 field to the packet.
        """
        self.add_field(pack('>Q', value))

    def add_string_field(self, value):
        """
        Add a string field to the packet.
        """
        self.chunk.append(len(value))
        self.chunk.extend(value)

    def add_blob_field(self, value):
        """
        Add a blob field to the packet.
        """
        self.add_uint32_field(len(value))
        self.chunk.extend(value)


class SessionPacket(BasePacket):
    STATE_ENDED = 0
    STATE_STANDBY = 1
    STATE_ACTIVE = 2

    def __init__(self, name, state):
        BasePacket.__init__(self)

        self.set_type(PACKET_SESSION)

        self.add_uint8_field(state)

        self.add_string_field(name)


class CallPacket(BasePacket):

    def __init__(self, unidirectional, postref, name, payload):
        BasePacket.__init__(self)

        self.set_type(PACKET_CALL)

        flags = 0
        flags |= (1 << 0) if unidirectional else 0

        self.add_uint8_field(flags)

        self.add_uint32_field(0 if unidirectional else postref)

        self.add_string_field(name)

        self.add_blob_field(payload)


class MessagePacket(BasePacket):
    STATUS_OK = 0
    STATUS_TIMEOUT = 1
    STATUS_UNREACHABLE = 2

    def __init__(self, messageref, status, payload):
        BasePacket.__init__(self)

        self.set_type(PACKET_MESSAGE)

        self.add_uint8_field(status)

        self.add_uint32_field(messageref)

        if status == MessagePacket.STATUS_OK:
            self.add_blob_field(payload)


class InterestPacket(BasePacket):
    STATUS_NO_INTEREST = 0
    STATUS_INTEREST = 1

    def __init__(self, postref, status, topic):
        BasePacket.__init__(self)

        self.set_type(PACKET_INTEREST)

        self.add_uint8_field(status)

        self.add_uint32_field(postref)

        self.add_blob_field(topic)


class PingPacket(BasePacket):

    def __init__(self):
        BasePacket.__init__(self)

        self.set_type(PACKET_PING)


class WelcomePacket(BasePacket):

    def __init__(self, server_version, protocol_version):
        BasePacket.__init__(self)

        self.set_type(PACKET_WELCOME)

        self.add_uint32_field(server_version)

        self.add_uint32_field(protocol_version)


class ByeByePacket(BasePacket):

    def __init__(self):
        BasePacket.__init__(self)

        self.set_type(PACKET_BYEBYE)
