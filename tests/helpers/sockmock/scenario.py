import sys
from enum import Enum, auto
from collections import deque
from socket import AF_INET, SOCK_STREAM

# class Events(Enum):
#     # local events
#     LISTEN = auto()
#     WRITE = auto()
#     END = auto()
#     TIMELAPSE = auto()
#     CLOSED = auto()
#
#     # remote events
#     CONNECT = auto()
#     RECV = auto()
#     SEND = auto()
#     CLIENT_CLOSE = auto()


"""

These are the interal events.

It corespondents with the code under test calling certain syscalls.


Some definitions:

internal_address: an address that is owned by the OS that is running the code under test
external_address: an address that is owned by simulated remote hosts.

all events are named from the local perspective

"""


class InternalEvent:

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def verify(self, *args, **kwargs):
        """ The implementation of this function verifies the vent. It should return the following:
        In case the event verifies so far, but is not fully verified yet: return False
        In case the event is fully verifies: return True
        In case the verification failed: raise EventVerifyError
        """

        raise NotImplementedError("Verify function is not yet implemented for this event...")

    def verify_field(self, desired, actual):
        if desired != actual:
            raise EventVerifyError(f"Event fields mismatch, expected {desired}, but got{actual}")


class ListenEvent(InternalEvent):
    """ A local socket starts listening on an address.
    """

    def verify(self, family, type, address):
        self.verify_field(self.family, family)
        self.verify_field(self.type, type)
        self.verify_field(self.address, address)

        return True

    def __str__(self):
        return f'ListenEvent({self.address})'


class WriteEvent(InternalEvent):
    """ A local socket wirtes something.
    """

    def __init__(self, family, type, remote_address, client_address, data):
        self.family = family
        self.type = type
        self.remote_address = remote_address
        self.client_address = client_address
        self.data_original = data
        self.data = data
        self.data_verified = b''

    def verify(self, family, type, remote_address, client_address, data):
        self.verify_field(self.family, family)
        self.verify_field(self.type, type)
        self.verify_field(self.remote_address, remote_address)
        self.verify_field(self.client_address, client_address)

        if self.data.startswith(data):
            self.data = self.data[len(data):]
            self.data_verified += data

        else:
            print(data)
            print(self.data)
            raise EventVerifyError(f"Verified data ({data}) does not match desired data ({self.data})")

        return len(self.data) == 0

    def __str__(self):
        return f"WriteEvent({self.data_original}, {self.client_address})"


class ClosedEvent(InternalEvent):
    """ A local socket is being locally closed.
    """

    def verify(self, family, type, bound_address, remote_address):
        self.verify_field(self.family, family)
        self.verify_field(self.type, type)
        self.verify_field(self.bound_address, bound_address)
        self.verify_field(self.remote_address, remote_address)
        return True

    def __str__(self):
        return f"ClosedEvent()"


class TimelapseEvent(InternalEvent):
    """ Some time elapsed on the local host.
    """

    def __init__(self, seconds):
        self.seconds = seconds
        self.seconds_verified = 0.0

    def verify(self, seconds):

        self.seconds_verified += seconds

        if self.seconds_verified < self.seconds:
            return False

        elif self.seconds_verified == self.seconds:
            return True

        else:
            raise EventVerifyError(f"Unexpected to lapse {self.seconds_verified}, expected {self.seconds} instead")

    def __str__(self):
        return f"TimelapseEvent({self.seconds_verified:04.1f}/{self.seconds:04.1f})"


class EndEvent(InternalEvent):
    """ The local code under test is finished.
    """

    def verify(self):
        return True

    def __str__(self):
        return f"EndEvent()"


class ExternalEvent:

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def execute(self, system):
        """ The implementation of this function should do its thing on the given system object.
        """

        raise NotImplementedError("The execute function is not implemented for this action...")


class ConnectEvent(ExternalEvent):
    """ A simulated remote socket makes a connection, resulting in a local accept call eventually.
    """

    def execute(self, system):
        system.add_connection(
            self.remote_address,
            self.client_address,
            self.family,
            self.type
        )

    def __str__(self):
        return f"ConnectEvent(to={self.remote_address}, from={self.client_address})"


class ReadEvent(ExternalEvent):
    """ A simulated remote socket sends some data, resulting in a local read call eventually.
    """

    def execute(self, system):
        system.add_incoming_data(
            self.remote_address,
            self.client_address,
            self.family,
            self.type,
            self.data
        )

    def __str__(self):
        return f"ReadEvent({self.data}, {self.client_address})"


class ClientCloseEvent(ExternalEvent):
    """ A simulated remote socket closes a connection, resulting in a local empty read eventully.
    """

    def execute(self, system):
        raise NotImplementedError()


class EventVerifyError(AssertionError):
    pass


class Scenario:

    def __init__(self):
        self.eventlist = deque()
        self.event_index = 0

    def local_socket(self, family=AF_INET, type=SOCK_STREAM):
        return LocalSocket(self, family, type)

    def remote_socket(self, peer_address, family=AF_INET, type=SOCK_STREAM):
        return RemoteSocket(self, peer_address, family, type)

    def timelapse(self, seconds):
        self.add_event(TimelapseEvent(seconds=seconds))

    def end(self):
        self.add_event(EndEvent())

    def add_event(self, event):
        index = self.event_index
        self.event_index += 1

        self.eventlist.append((index, event))

        print(f"[{index:02d}] {'IN' if isinstance(event, InternalEvent) else 'EX'} {event}")

    def verify(self, event_cls, *args, **kwargs):

        if not self.eventlist:
            raise EventVerifyError("No events on the eventlist! Your scenario seems incomplete...")

        index, next_event = self.eventlist[0]
        next_event_cls = type(next_event)

        if next_event_cls != event_cls:
            raise EventVerifyError(
                f"Mismatching event class, expected {next_event_cls.__name__}, but got {event_cls.__name__}"
            )

        result = next_event.verify(*args, **kwargs)

        print(f"[{index:02d}] IN {'X' if result else '-'} Verified {next_event}")

        if result:
            self.eventlist.popleft()

    def fetch_external_events(self):
        while self.eventlist:

            index, event = self.eventlist[0]
            if isinstance(event, ExternalEvent):
                self.eventlist.popleft()

                print(f"[{index:02d}] EX Executed {event}")

                yield event

            else:
                break

    def print(self):
        print("===== SCENARIO =====")
        for index, event in self.eventlist:
            print(f"[{index:02d}] {'IN' if isinstance(event, InternalEvent) else 'EX'} {event}")
        print("======== END =======")


class LocalSocket:

    def __init__(self, scenario, family=AF_INET, type=SOCK_STREAM):
        self.scenario = scenario
        self.family = family
        self.type = type

    def listen(self, address):
        self.scenario.add_event(ListenEvent(family=self.family, type=self.type, address=address))


class RemoteSocket:

    def __init__(self, scenario, client_address=None, family=AF_INET, type=SOCK_STREAM):
        self.scenario = scenario
        self.family = family
        self.type = type
        self.remote_address = None
        self.client_address = client_address

    def connect(self, remote_address):
        self.remote_address = remote_address
        self.scenario.add_event(ConnectEvent(
            family=self.family,
            type=self.type,
            remote_address=self.remote_address,
            client_address=self.client_address)
        )

    def recv(self, data):
        self.scenario.add_event(WriteEvent(
            family=self.family,
            type=self.type,
            remote_address=self.remote_address,
            client_address=self.client_address,
            data=data
        ))

    def send(self, data):
        self.scenario.add_event(ReadEvent(
            family=self.family,
            type=self.type,
            remote_address=self.remote_address,
            client_address=self.client_address,
            data=data
        ))

    def close(self):
        self.scenario.add_event(ClientCloseEvent(
            family=self.family,
            type=self.type,
            bound_address=self.remote_address,
            remote_address=self.client_address
        ))

    def remote_closed(self):
        self.scenario.add_event(ClosedEvent(
            family=self.family,
            type=self.type,
            bound_address=self.remote_address,
            remote_address=self.client_address
        ))

# from socket import AF_INET, SOCK_STREAM
# from collections import deque, namedtuple
#
# ListenEvent = namedtuple('ListenEvent', ['family', 'type', 'address'])
# WriteEvent = namedtuple('WriteEvent', ['todo'])
# EndEvent = namedtuple('EndEvent', [])
# TimelapseEvent = namedtuple('TimelapseEvent', ['seconds'])
# ClosedEvent = namedtuple('ClosedEvent', ['family', 'type', 'remote_address', 'client_address'])
# local_events = {ListenEvent, WriteEvent, EndEvent, TimelapseEvent, ClosedEvent}
#
# ConnectEvent = namedtuple('ConnectEvent', ['family', 'type', 'remote_address', 'client_address'])
# RecvEvent = namedtuple('RecvEvent', ['family', 'type', 'remote_address', 'client_address', 'data'])
# SendEvent = namedtuple('SendEvent', ['family', 'type', 'remote_address', 'client_address', 'data'])
# ClientCloseEvent = namedtuple('ClientCloseEventl', ['family', 'type', 'remote_address', 'client_address'])
# external_events = {ConnectEvent, SendEvent, ClientCloseEvent, EndEvent}
#
#
# class Scenario:
#
#     def __init__(self):
#         self.eventlist = deque()
#
#     def local_socket(self, family=AF_INET, type=SOCK_STREAM):
#         return LocalSocket(self, family, type)
#
#     def remote_socket(self, peer_address, family=AF_INET, type=SOCK_STREAM):
#         return RemoteSocket(self, peer_address, family, type)
#
#     def timelapse(self, seconds):
#         self.add_event(TimelapseEvent(seconds))
#
#     def end(self):
#         self.add_event(EndEvent())
#
#     def add_event(self, event):
#
#         self.eventlist.append(event)
#
#     def verify_event(self, verify_event):
#
#         expected_event = self.eventlist.popleft()
#
#         if type(verify_event) != type(expected_event):
#             raise VerifyError(
#                 f"{type(verify_event).__name__} was not expected, "
#                 f"expected {type(expected_event).__name__} instead"
#             )
#
#         if type(verify_event) == TimelapseEvent:
#             self.verify_timelapse(expected_event, verify_event)
#
#         else:
#             self.verify_general(expected_event, verify_event)
#
#     def verify_timelapse(self, expected_event, verify_event):
#
#         seconds_left = expected_event.seconds - verify_event.seconds
#
#         if seconds_left > 0:
#             new_event = TimelapseEvent(seconds_left)
#             self.eventlist.appendleft(new_event)
#
#     def verify_general(self, expected_event, verify_event):
#         for field in expected_event._fields:
#
#             expected_value = getattr(expected_event, field)
#             verify_value = getattr(verify_event, field)
#
#             if expected_value != verify_value:
#                 raise VerifyError(
#                     f"Verification of '{type(verify_event).__name__}' failed because field '{field}' "
#                     f"has value '{verify_value}' instead of '{expected_value}'"
#                 )
#
#     def get_external_events(self):
#
#         events = list()
#
#         while self.eventlist:
#             event = self.eventlist[0]
#
#             if type(event) not in external_events:
#                 break
#
#             events.append(event)
#
#             self.eventlist.popleft()
#
#         return events
#
#
# class LocalSocket:
#
#     def __init__(self, scenario, family=AF_INET, type=SOCK_STREAM):
#         self.scenario = scenario
#         self.family = family
#         self.type = type
#
#     def listen(self, address):
#         self.scenario.add_event(ListenEvent(self.family, self.type, address))
#
#
# class RemoteSocket:
#
#     def __init__(self, scenario, client_address=None, family=AF_INET, type=SOCK_STREAM):
#         self.scenario = scenario
#         self.family = family
#         self.type = type
#         self.remote_address = None
#         self.client_address = client_address
#
#     def connect(self, remote_address):
#         self.remote_address = remote_address
#         self.scenario.add_event(ConnectEvent(self.family, self.type, self.remote_address, self.client_address))
#
#     def recv(self, data):
#         self.scenario.add_event(RecvEvent(self.family, self.type, self.remote_address, self.client_address, data))
#
#     def send(self, data):
#         self.scenario.add_event(SendEvent(self.family, self.type, self.remote_address, self.client_address, data))
#
#     def close(self):
#         self.scenario.add_event(ClientCloseEvent(self.family, self.type, self.remote_address, self.client_address))
#
#     def remote_closed(self):
#         self.scenario.add_event(ClosedEvent(self.family, self.type, self.remote_address, self.client_address))
#
#
# class VerifyError(AssertionError):
#     pass
