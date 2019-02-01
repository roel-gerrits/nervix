class BasePacket:

    def __repr__(self):
        return "<{cls}>".format(
            cls=self.__class__.__name__
        )


class PingPacket(BasePacket):

    def __init__(self):
        self.payload = None


class PongPacket(BasePacket):
    pass


class ShutdownPacket(BasePacket):
    pass


class ExitPacket(BasePacket):
    pass


class ByebyePacket(BasePacket):
    pass


class InvalidPacket(BasePacket):

    def __init__(self, reason):
        self.reason = reason


class ErrorPacket(BasePacket):

    def __init__(self, reason):
        self.reason = reason


class LoginPacket(BasePacket):

    def __init__(self):
        self.name = None
        self.enforce = None
        self.standby = None
        self.persist = None


class LogoutPacket(BasePacket):

    def __init__(self):
        self.name = None


class SessionPacket(BasePacket):
    STATE_ACTIVE = 1
    STATE_STANDBY = 2
    STATE_ENDED = 3

    def __init__(self):
        self.name = None
        self.state = None


class RequestPacket(BasePacket):

    def __init__(self):
        self.name = None
        self.unidirectional = None
        self.messageref = None
        self.timeout = None
        self.payload = None


class CallPacket(BasePacket):

    def __init__(self):
        self.unidirectional = None
        self.postref = None
        self.payload = None


class PostPacket(BasePacket):

    def __init__(self):
        self.postref = None
        self.payload = None


class MessagePacket(BasePacket):
    STATUS_NOK = 0
    STATUS_OK = 1

    REASON_NONE = 0
    REASON_TIMEOUT = 1
    REASON_UNREACHABLE = 2

    def __init__(self):
        self.messageref = None
        self.status = None
        self.reason = None
        self.payload = None


class SubscribePacket(BasePacket):

    def __init__(self):
        self.name = None
        self.messageref = None
        self.topic = None


class InterestPacket(BasePacket):
    STATUS_NO_INTEREST = 0
    STATUS_INTEREST = 1

    def __init__(self):
        self.postref = None
        self.status = None
        self.topic = None


class UnkownPacket(BasePacket):
    pass

