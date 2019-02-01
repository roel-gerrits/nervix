from nervixd.util.encoder import BaseEncoder


class Encoder(BaseEncoder):

    def encode(self, packet):
        """
        Encode a packet object and append it to the internal
        chunkbuffer.
        """

        chunk = packet.get_chunk()

        self.add_encoded_chunk(chunk)


class BasePacket:

    def __init__(self):
        self.type = None
        self.args = []
        self.body = None

    def get_chunk(self):
        """
        Return a bytes object which contains the encoded data.
        """

        chunk = bytearray()
        chunk.extend(self.type)

        for arg in self.args:
            chunk.extend(b' ')
            chunk.extend(arg)

        chunk.extend(b'\r\n')

        if self.body:
            chunk.extend(self.body)
            chunk.extend(b'\r\n')

        return bytes(chunk)

    def set_type(self, packettype):
        """
        Set the packet type.
        """

        self.type = packettype

    def add_string(self, string):
        """
        Add a string argument.
        """

        self.args.append(string)

    def add_integer(self, number):
        """
        Add a integer argument
        """

        string = str(number).encode()

        self.add_string(string)

    def set_body(self, body):
        self.body = body


class SessionPacket(BasePacket):
    STATE_ENDED = 0
    STATE_STANDBY = 1
    STATE_ACTIVE = 2

    def __init__(self, name, state):
        BasePacket.__init__(self)

        self.set_type(B'SESSION')

        self.add_string(name)

        state_str = [b'ENDED', b'STANDBY', b'ACTIVE'][state]
        self.add_string(state_str)


class CallPacket(BasePacket):

    def __init__(self, unidirectional, postref, name, payload):
        BasePacket.__init__(self)

        self.set_type(b'CALL')

        if unidirectional:
            self.add_string(b'UNI')

        else:
            self.add_integer(postref)

        self.add_string(name)

        self.add_string(payload)


class MessagePacket(BasePacket):
    STATUS_OK = 0
    STATUS_TIMEOUT = 1
    STATUS_UNREACHABLE = 2

    def __init__(self, messageref, status, payload):
        BasePacket.__init__(self)

        self.set_type(b'MESSAGE')

        self.add_integer(messageref)

        status_str = [b'OK', b'TIMEOUT', b'UNREACHABLE'][status]
        self.add_string(status_str)

        if status == MessagePacket.STATUS_OK:
            self.add_string(payload)


class InterestPacket(BasePacket):
    STATUS_NO_INTEREST = 0
    STATUS_INTEREST = 1

    def __init__(self, postref, status, name, topic):
        BasePacket.__init__(self)

        self.set_type(b'INTEREST')

        self.add_integer(postref)

        interest_str = [b'NO_INTEREST', b'INTEREST'][status]
        self.add_string(interest_str)

        self.add_string(name)

        self.add_string(topic)


class PongPacket(BasePacket):

    def __init__(self, payload):
        BasePacket.__init__(self)

        self.set_type(b'PONG')

        if payload:
            self.add_string(payload)


class WelcomePacket(BasePacket):

    def __init__(self, server_version, protocol_version):
        BasePacket.__init__(self)

        self.set_type(b'WELCOME')

        self.add_string(b'server_version=' + str(server_version).encode())
        self.add_string(b'protocol_version=' + str(protocol_version).encode())


class ByeByePacket(BasePacket):

    def __init__(self):
        BasePacket.__init__(self)

        self.set_type(b'BYEBYE')


class InfoPacket(BasePacket):

    def __init__(self, topic):
        BasePacket.__init__(self)

        self.set_type(b'INFO')

        if not topic:
            topic = b'General'

        self.add_string(topic)

        self.set_body(b'Some body text')


class InvalidRequestPacket(BasePacket):

    def __init__(self, reason):
        BasePacket.__init__(self)

        self.set_type(b'ERROR')

        if reason:
            self.add_string(reason)


class AlignPacket(BasePacket):

    def __init__(self, timestamp):
        BasePacket.__init__(self)

        self.set_type(b'ALIGN')

        self.add_integer(timestamp)
