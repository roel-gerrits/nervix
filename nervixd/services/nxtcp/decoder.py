from struct import unpack_from

from nervixd.util.decoder import BaseDecoder

from .defines import *


class Decoder(BaseDecoder):

    def __init__(self, *args, **kwargs):
        BaseDecoder.__init__(self, *args, **kwargs)

        self.handler_map = {
            PACKET_LOGIN: LoginPacket,
            PACKET_LOGOUT: LogoutPacket,
            PACKET_REQUEST: RequestPacket,
            PACKET_POST: PostPacket,
            PACKET_SUBSCRIBE: SubscribePacket,
            PACKET_UNSUBSCRIBE: UnsubscribePacket,
            PACKET_PONG: PongPacket,
            PACKET_QUIT: QuitPacket,
        }

    def decode(self):
        """
        Decode a single packet from the chunks that are currently 
        present in the chunkbuffer.
        
        Returns None if no packet could be constructed.
        """

        header = self.get(5)

        if not header:
            return

        length, packet_type = unpack_from('>IB', header)

        frame = self.get(length, 5)

        if frame is None:
            return

        self.commit()

        handler = self.handler_map.get(packet_type, None)

        if not handler:
            raise DecodingError('Unknown packet type 0x{:02x}'.format(packet_type))

        packet = handler(frame)

        return packet


class DecodingError(RuntimeError):
    pass


class BasePacket:

    def __init__(self, frame):
        self.frame = frame
        self.nextbyte = 0

    def get_uint8(self, offset):
        self.nextbyte = offset + 1
        return unpack_from('>B', self.frame, offset)[0]

    def get_uint32(self, offset):
        self.nextbyte = offset + 4
        return unpack_from('>I', self.frame, offset)[0]

    def get_string(self, offset):
        length = self.get_uint8(offset)

        start = offset + 1
        end = offset + 1 + length

        if end > len(self.frame):
            raise DecodingError('String size of {:d} exceeds frame size {:d}'.format(length, len(self.frame)))

        self.nextbyte = end

        return bytes(self.frame[start: end])

    def get_blob(self, offset):
        length = self.get_uint32(offset)

        start = offset + 4
        end = offset + 4 + length

        if end > len(self.frame):
            raise DecodingError('Blob size of {:d} exceeds frame size {:d}'.format(length, len(self.frame)))

        self.nextbyte = end

        return bytes(self.frame[start: end])


class LoginPacket(BasePacket):
    """
    uint8: flags
        0: persist
        1: standby
        2: enforce
    string: name
    """

    def __init__(self, frame):
        BasePacket.__init__(self, frame)

        self.flags = self.get_uint8(0)

        self.persist = (self.flags & (1 << 0)) > 0
        self.standby = (self.flags & (1 << 1)) > 0
        self.enforce = (self.flags & (1 << 2)) > 0

        self.name = self.get_string(1)


class LogoutPacket(BasePacket):
    """
    string: name
    """

    def __init__(self, frame):
        BasePacket.__init__(self, frame)

        self.name = self.get_string(0)


class RequestPacket(BasePacket):
    """
    string: name
    uint8: flags:
        0: unidirectional
    uint32: messageref
    uint32: timeout
    blob: payload
    """

    def __init__(self, frame):
        BasePacket.__init__(self, frame)

        self.name = self.get_string(0)

        offset = len(self.name) + 1

        self.flags = self.get_uint8(0 + offset)

        self.unidirectional = (self.flags & (1 << 0)) > 0

        if self.unidirectional:
            self.messageref = None
        else:
            self.messageref = self.get_uint32(1 + offset)

        timeout_ms = self.get_uint32(5 + offset)

        self.timeout = timeout_ms / 1000

        self.payload = self.get_blob(9 + offset)


class PostPacket(BasePacket):
    """
    uint32: postref
    blob: payload
    """

    def __init__(self, frame):
        BasePacket.__init__(self, frame)

        self.postref = self.get_uint32(0)
        self.payload = self.get_blob(4)


class SubscribePacket(BasePacket):
    """
    uint32: messageref
    string: name
    blob: topic
    """

    def __init__(self, frame):
        BasePacket.__init__(self, frame)

        self.messageref = self.get_uint32(0)

        self.name = self.get_string(4)

        self.topic = self.get_blob(self.nextbyte)


class UnsubscribePacket(BasePacket):
    """
    string: name
    blob: topic
    """

    def __init__(self, frame):
        BasePacket.__init__(self, frame)

        self.name = self.get_string(0)

        self.topic = self.get_blob(self.nextbyte)


class PongPacket(BasePacket):
    """
    blob: payload
    """

    def __init__(self, frame):
        BasePacket.__init__(self, frame)

        self.payload = self.get_blob(0)


class QuitPacket(BasePacket):
    """
    -
    """

    def __init__(self, frame):
        BasePacket.__init__(self, frame)
