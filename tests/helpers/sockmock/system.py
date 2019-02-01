from selectors import EVENT_READ, EVENT_WRITE
from socket import AF_INET, SOCK_STREAM
from collections import defaultdict, deque, namedtuple
from enum import Enum

from .scenario import ListenEvent, WriteEvent, ClosedEvent, TimelapseEvent, EndEvent


class EndOfSimulation(RuntimeError):
    pass


SocketState = namedtuple("SocketState", ['family', 'type', 'bound_address', 'peer_address', 'listening'])


def log_syscalls(func):
    def logged(*args, **kwargs):
        print(f"@ ---> {func.__name__}({', '.join([str(arg) for arg in args[1:]])})")

        res = func(*args, **kwargs)

        # print(f"@    < {res}")

        return res

    return logged


class System:

    def __init__(self, scenario):

        self.scenario = scenario

        self.next_fileno = 1000

        self.sockets = dict()

        # # map that stores the family and type of each socket
        # self.socket_family_type = dict()
        #
        # # map that stores to which address a socked is bound
        # self.socket_binds = dict()

        # # set that stores which sockets are listening
        # self.socket_listens = set()

        # # queue of incoming connections for listening sockets
        # self.pending_connections = defaultdict(deque)
        #
        # # queue of incoming data for sockets
        # self.pending_data = defaultdict(deque)

        # # stores the address of the remote end of a connection
        # self.socket_peer_address = dict()

        # current simulated time
        self.monotonic_time = 0.0

    """ 
    For sockets
    """

    # @log_syscalls
    def socket(self, family=AF_INET, type=SOCK_STREAM):
        fileno = self.__get_fileno()

        socket = Socket(family, type)

        self.sockets[fileno] = socket

        return fileno

    # @log_syscalls
    def bind(self, fileno, address):
        self.sockets[fileno].bind(address)

    # @log_syscalls
    def listen(self, fileno, backlog=0):

        socket = self.sockets[fileno]

        socket.listen()

        # self.scenario.verify_event(ListenEvent(socket.family, socket.type, socket.bound_address))
        self.scenario.verify(ListenEvent, socket.family, socket.type, socket.bound_address)

    # @log_syscalls
    def accept(self, fileno):

        socket = self.sockets[fileno]

        peer_address = socket.pop_pending_connection()

        # create socket for connection
        conn_socket = Socket(socket.family, socket.type)
        conn_socket.bound_address = socket.bound_address
        conn_socket.set_peer_address(peer_address)

        conn_fileno = self.__get_fileno()
        self.sockets[conn_fileno] = conn_socket

        return conn_fileno, peer_address

    # @log_syscalls
    def write(self, fileno, data):

        socket = self.sockets[fileno]

        self.scenario.verify(
            WriteEvent, socket.family, socket.type, socket.bound_address, socket.peer_address, data
        )

        return len(data)

    def send(self, fileno, data):
        return self.write(fileno, data)

    # @log_syscalls
    def read(self, fileno, limit):

        socket = self.sockets[fileno]

        chunk = socket.pop_pending_data()

        if len(chunk) > limit:
            raise SystemError("Chunk size is bigger then requested")

        return chunk

    def recv(self, fileno, limit):
        return self.read(fileno, limit)

    # @log_syscalls
    def close(self, fileno):

        socket = self.sockets[fileno]

        socket.close()

        self.scenario.verify(ClosedEvent, socket.family, socket.type, socket.bound_address, socket.peer_address)

    # @log_syscalls
    def getpeername(self, fileno):

        socket = self.sockets[fileno]

        if not socket.peer_address:
            raise SystemError(f"Socket {fileno} not connected")

        return socket.peer_address

    # @log_syscalls
    def has_connection_pending(self, fileno):

        if fileno not in self.sockets:
            return False

        return self.sockets[fileno].has_pending_connection()

    # @log_syscalls
    def add_connection(self, to_address, from_address, family, type):

        socket = None
        for fileno, socket in self.sockets.items():

            if not socket.listening:
                continue

            if socket.family != family:
                continue

            if socket.type != type:
                continue

            if socket.bound_address != to_address:
                continue

            break

        if not socket:
            raise SystemError(f"No socket listening on {to_address} family={family} type={type}")

        socket.add_pending_connection(from_address)

    # @log_syscalls
    def has_incoming_data(self, fileno):

        if fileno not in self.sockets:
            return False

        return self.sockets[fileno].has_pending_data()

    # @log_syscalls
    def add_incoming_data(self, to_address, from_address, family, type, data):

        socket = None
        for fileno, socket in self.sockets.items():

            if socket.listening:
                continue

            if socket.family != family:
                continue

            if socket.type != type:
                continue

            if socket.bound_address != to_address:
                continue

            if socket.peer_address != from_address:
                continue

            break

        if not socket:
            raise SystemError(f"No socket available for data on {to_address} family={family} type={type}")

        socket.add_pending_data(data)

    """
    Time functions
    """

    # @log_syscalls
    def monotonic(self):
        return self.monotonic_time

    # @log_syscalls
    def progress_time(self, seconds):
        self.monotonic_time += seconds

        self.scenario.verify(TimelapseEvent, seconds)

        # print(f"---> time is now {self.monotonic_time}")

        if self.monotonic_time > 30:
            exit(1)

    """
    """

    # @log_syscalls
    def evaluate(self):

        n = 0
        for event in self.scenario.fetch_external_events():
            event.execute(self)
            n += 1

        return n

    """
    """

    # @log_syscalls
    def end(self):
        self.scenario.verify(EndEvent)

        raise EndOfSimulation()

    """
    Helpers
    """

    def __get_fileno(self):
        fileno = self.next_fileno
        self.next_fileno += 1
        return fileno


class SystemError(RuntimeError):
    pass


class Socket:

    def __init__(self, family, type):
        self.family = family
        self.type = type

        self.bound_address = None
        self.peer_address = None

        self.listening = False

        self.pending_connections = deque()
        self.pending_data = deque()

        self.closed = False

    def bind(self, address):
        if self.bound_address:
            raise SystemError("Socket is already bound")

        self.bound_address = address

    def listen(self):
        self.listening = True

    def close(self):
        if self.closed:
            raise SystemError("Socket has already been closed")

        self.closed = True

    def set_peer_address(self, address):
        self.peer_address = address

    def add_pending_connection(self, peer_address):
        self.pending_connections.append(peer_address)

    def has_pending_connection(self):
        return bool(self.pending_connections)

    def pop_pending_connection(self):

        if not self.pending_connections:
            raise SystemError("No pending connections for socket")

        peer_address = self.pending_connections.popleft()

        return peer_address

    def add_pending_data(self, data):
        self.pending_data.append(data)

    def has_pending_data(self):
        return bool(self.pending_data)

    def pop_pending_data(self):

        if self.closed:
            return b''

        if not self.pending_data:
            raise SystemError("No pending data on socket")

        chunk = self.pending_data.popleft()
        return chunk
