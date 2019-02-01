
from nervixd.util.decoder import BaseDecoder


class Decoder(BaseDecoder):

    def __init__(self, *args, **kwargs):
        BaseDecoder.__init__(self, *args, **kwargs)

        self.handler_map = {
            b'PING': PingPacket,
            b'LOGIN': LoginPacket,
            b'LOGOUT': LogoutPacket,
            b'POST': PostPacket,
            b'REQUEST': RequestPacket,
            b'SUBSCRIBE': SubscribePacket,
            b'UNSUBSCRIBE': UnsubscribePacket,
            b'QUIT': QuitPacket,
            b'HELP': HelpPacket,
        }

    def decode(self):
        """
        Decode a single packet from the chunks that are currently
        present in the chunkbuffer.

        Returns None if no packet could be constructed.
        """

        line = self.get_until(b'\r\n', 1024)

        if not line:
            return

        self.commit()

        # parse command from line
        pos = 0
        length = len(line)

        cmd = bytearray()
        while pos < length:

            c = line[pos]

            if c in b'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ':
                cmd.append(c)

            elif c in b'\r\n ':
                break

            else:
                raise DecodingError("Unexpected character '{}' while parsing command".format(c))

            pos += 1

        if not cmd:
            return

        cmd = cmd.upper()

        line = line[:-2]
        line_args = line[pos:]

        # command is parsed, now find and execute the correct handler
        handler = self.handler_map.get(bytes(cmd), None)

        if not handler:
            raise DecodingError("Unknown command '{}'".format(bytes(cmd).decode()))

        packet = handler(line_args)

        return packet


class DecodingError(RuntimeError):
    pass


class BasePacket:

    def __init__(self, line):
        self.line = line

        self.nextbyte = 0
        self.length = len(line)

    def skip_spaces(self):

        while self.nextbyte < self.length:

            c = self.line[self.nextbyte]

            if c != ord(b' '):
                break

            self.nextbyte += 1

    def read_remaining(self):

        self.skip_spaces()

        if self.nextbyte == self.length:
            return None

        data = self.line[self.nextbyte:]
        self.nextbyte += len(data)

        return bytes(data)

    def read_string(self):

        self.skip_spaces()

        if self.nextbyte == self.length:
            return None

        startbyte = self.nextbyte

        data = bytearray()

        while self.nextbyte < self.length:

            c = self.line[self.nextbyte]

            # test for 0-9, A-Z, a-z, -, _
            if 48 <= c <= 57 or 65 <= c <= 90 or 97 <= c <= 122 or c == ord('-') or c == ord('_'):
                data.append(c)
                self.nextbyte += 1

            elif c == ord(' '):
                self.nextbyte += 1
                break

            else:
                self.nextbyte = startbyte
                return None

        return bytes(data)

    def read_positive_integer(self):

        self.skip_spaces()

        if self.nextbyte == self.length:
            return None

        startbyte = self.nextbyte

        number = 0

        while self.nextbyte < self.length:

            c = self.line[self.nextbyte]

            # test for 0-9
            if 48 <= c <= 57:
                self.nextbyte += 1

                digit = c - 48

                number *= 10
                number += digit

            elif c == ord(' '):
                self.nextbyte += 1
                break

            else:
                self.nextbyte = startbyte
                return None

        return number


class PingPacket(BasePacket):
    """
    PING [payload]
    """

    def __init__(self, line):
        BasePacket.__init__(self, line)

        self.payload = self.read_remaining()


class LoginPacket(BasePacket):
    """
    LOGIN name [ENFORCE] [STANDBY] [PERSIST]
    """

    def __init__(self, args):
        BasePacket.__init__(self, args)

        self.name = self.read_string()

        if not self.name:
            raise DecodingError('Missing name field ')

        flags = set()
        while True:
            flag = self.read_string()
            if not flag:
                break

            flag = flag.upper()
            flags.add(flag)

        self.enforce = b'ENFORCE' in flags
        self.standby = b'STANDBY' in flags
        self.persist = b'PERSIST' in flags


class LogoutPacket(BasePacket):
    """
    LOGOUT name
    """

    def __init__(self, args):
        BasePacket.__init__(self, args)

        self.name = self.read_string()

        if not self.name:
            raise DecodingError('Missing name field ')


class PostPacket(BasePacket):
    """
    POST postref payload
    """

    def __init__(self, args):
        BasePacket.__init__(self, args)

        self.postref = self.read_positive_integer()
        self.payload = self.read_remaining()

        if not self.postref:
            raise DecodingError('Missing postref field')

        if not self.payload:
            raise DecodingError('Missing payload')


class RequestPacket(BasePacket):
    """
    REQUEST messageref|UNI name [timeout] payload
    """

    def __init__(self, args):
        BasePacket.__init__(self, args)

        self.messageref = self.read_positive_integer()

        self.unidirectional = False
        if not self.messageref:
            word = self.read_string()

            if word and word.upper() == b'UNI':
                self.unidirectional = True

            else:
                raise DecodingError('Missing messageref or UNI')

        self.name = self.read_string()

        if not self.name:
            raise DecodingError('Missing name')

        self.timeout = self.read_positive_integer()

        self.payload = self.read_remaining()

        if not self.payload:
            raise DecodingError('Missing payload')


class SubscribePacket(BasePacket):
    """
    SUBSCRIBE messageref name topic
    """

    def __init__(self, args):
        BasePacket.__init__(self, args)

        self.messageref = self.read_positive_integer()
        if not self.messageref:
            raise DecodingError('Missing messageref')

        self.name = self.read_string()
        if not self.name:
            raise DecodingError('Missing name')

        self.topic = self.read_remaining()
        if not self.topic:
            raise DecodingError('Missing topic')


class UnsubscribePacket(BasePacket):
    """
    UNSUBSCRIBE name topic
    """

    def __init__(self, args):
        BasePacket.__init__(self, args)

        self.name = self.read_string()

        if not self.name:
            raise DecodingError('Missing name')

        self.topic = self.read_remaining()

        if not self.topic:
            raise DecodingError('Missing topic')


class QuitPacket(BasePacket):
    """
    QUIT
    """

    def __init__(self, args):
        BasePacket.__init__(self, args)

        remaining = self.read_remaining()

        if remaining:
            raise DecodingError('Unexpected arguments: {}'.format(remaining))


class HelpPacket(BasePacket):
    """
    HELP [topic]
    """

    def __init__(self, args):
        BasePacket.__init__(self, args)

        self.topic = self.read_string()
