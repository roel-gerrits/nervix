from operator import itemgetter
from collections import deque
from . import story


def log_call(func):
    def logged(*args, **kwargs):

        try:
            res = func(*args, **kwargs)

        except Exception as e:
            res = 'E:' + repr(e)
            raise e

        finally:

            print(f"---> {func.__name__}({', '.join([str(arg) for arg in args[1:]])}): {res}")

        # print(f"@    < {res}")

        return res

    return logged


class Abort(RuntimeError):
    """Called to abort the simulation
    """
    pass


class Socket:
    def __init__(self, fileno, socket_fam, socket_type):
        self.fileno = fileno
        self.socket_fam = socket_fam
        self.socket_type = socket_type
        self.local_address = None
        self.remote_address = None
        self.listen = False
        self.closed = False

        self.pending_connections = deque()
        self.pending_data = deque()
        self.remote_closed = False

        self.event_seqno = None
        self.__update_event_seqno()

    def add_incoming_connection(self, from_address):
        self.__update_event_seqno()

        self.pending_connections.append(from_address)

    def add_incoming_data(self, data):
        self.__update_event_seqno()

        self.pending_data.append(data)

    def remote_close(self):
        self.remote_closed = True
        self.closed = True

    def pop_pending_connection(self):
        connection = self.pending_connections.popleft()

        return connection

    def pop_chunk(self, limit):

        if not self.pending_data:
            raise RuntimeError("No data pending...!!! :/")

        data = self.pending_data.popleft()

        if len(data) > limit:
            chunk = data[:limit]
            self.pending_data.appendleft(data[limit:])

        else:
            chunk = data

        return chunk

    def can_read(self):
        if self.pending_connections:
            return True

        if self.pending_data:
            return True

        if self.remote_closed:
            return True

        return False

    def can_write(self):
        """ In the current implementation sockets are always
        writable
        """
        self.__update_event_seqno()

        return True

    __next_event_seqno = 1

    def __update_event_seqno(self):

        # if there was still something to be read before this was called
        if self.pending_connections or self.pending_data:
            return

        # there was nothing to be read before this function was called,
        # so update the seqno
        self.event_seqno = Socket.__next_event_seqno
        Socket.__next_event_seqno += 1

        # print(f"socket {self.fileno} seqno is now {self.event_seqno}")


class SystemState:

    def __init__(self, story):
        self.story = story

        self.next_fileno = 1000

        self.monotonic_time = 0.0

        self.sockets = dict()

    # @log_call
    def monotonic(self):
        return self.monotonic_time

    # @log_call
    def socket(self, socket_fam, socket_type):
        fileno = self.__get_fileno()

        socket = Socket(fileno, socket_fam, socket_type)
        self.sockets[fileno] = socket

        return fileno

    # @log_call
    def bind(self, fileno, address):
        self.sockets[fileno].local_address = address

    @log_call
    def listen(self, fileno, _backlog):

        socket = self.sockets[fileno]

        socket.listen = True

        self.story.verify(
            story.LocalListen,
            socket.socket_fam,
            socket.socket_type,
            socket.local_address
        )

    @log_call
    def accept(self, fileno):

        socket = self.sockets[fileno]

        peer_address = socket.pop_pending_connection()

        # create socket for connection
        conn_fileno = self.__get_fileno()
        conn_socket = Socket(conn_fileno, socket.socket_fam, socket.socket_type)
        conn_socket.local_address = socket.local_address
        conn_socket.remote_address = peer_address

        self.sockets[conn_fileno] = conn_socket

        return conn_fileno, peer_address

    def getpeername(self, fileno):
        socket = self.sockets[fileno]
        return socket.remote_address

    def getsockname(self, fileno):
        raise NotImplementedError()

    @log_call
    def send(self, fileno, data):
        socket = self.sockets[fileno]

        if socket.closed:
            raise RuntimeError("Socket is closed")

        self.story.verify(
            story.LocalSend,
            socket.socket_fam,
            socket.socket_type,
            socket.local_address,
            socket.remote_address,
            data
        )

        return len(data)

    @log_call
    def recv(self, fileno, limit):
        socket = self.sockets[fileno]

        if socket.closed:
            return b''

        chunk = socket.pop_chunk(limit)

        return chunk

    @log_call
    def close(self, fileno):
        socket = self.sockets[fileno]

        socket.closed = True

        self.story.verify(
            story.LocalClose,
            socket.socket_fam,
            socket.socket_type,
            socket.local_address,
            socket.remote_address,
        )

    # @log_call
    def select(self, interest_table, timeout):

        events_list = list()

        # iterate over sockets to see if any of them can read or write
        for fd, interest in interest_table.items():

            if fd not in self.sockets:
                continue

            fd_events = set()

            if 'r' in interest and self.sockets[fd].can_read():
                fd_events.add('r')

            if 'w' in interest and self.sockets[fd].can_write():
                fd_events.add('w')

            if fd_events:
                events_list.append((
                    self.sockets[fd].event_seqno,
                    fd,
                    fd_events
                ))

        if not events_list:
            # if there were no pending events execute remote events (if any),
            # this will have no effect on the return value of of this call, but
            # may any executed remote events will reflect on the return value of
            # the next call.
            n = self.__execute_remote_events()

            # if there were no remote events executed
            if not n:

                if timeout is None:
                    # the process has no timers running, so the process
                    # is now idle

                    self.story.verify(story.LocalIdle)

                else:
                    # there are no events to be returned but there was an
                    # timeout given, so we will now just 'wait' for the
                    # given duration and return
                    self.__increment_time(timeout)

                    # also verify this waiting with the story
                    self.story.verify(story.LocalWait, timeout)

        sorted_events = [
            (fd, events)
            for _, fd, events
            in sorted(events_list, key=itemgetter(0))
        ]

        return sorted_events

    """
    These functions are called when executing remote events
    """

    def add_incoming_connection(self, socket_fam, socket_type, from_address, to_address):

        fileno, socket = self.__find_socket(
            socket_fam=socket_fam,
            socket_type=socket_type,
            local_address=to_address,
            listen=True
        )

        socket.add_incoming_connection(from_address)

    def add_incoming_data(self, socket_fam, socket_type, from_address, to_address, data):

        fileno, socket = self.__find_socket(
            socket_fam=socket_fam,
            socket_type=socket_type,
            local_address=to_address,
            remote_address=from_address,
            listen=False
        )

        socket.add_incoming_data(data)

    def remote_close(self, socket_fam, socket_type, from_address, to_address):

        fileno, socket = self.__find_socket(
            socket_fam=socket_fam,
            socket_type=socket_type,
            local_address=to_address,
            remote_address=from_address,
            listen=False
        )

        socket.remote_close()

    def kill(self):
        """ Called as the result of the remote_kill event.
        """

        raise Abort()

    """
    Helper functions
    """

    def __get_fileno(self):
        """ Generate a new fileno
        """

        fileno = self.next_fileno
        self.next_fileno += 1
        return fileno

    def __execute_remote_events(self):
        """ Execute all remote events that are currently pending in
        the story.
        """

        n = 0

        for event in self.story.fetch_remote_events():
            event.execute(self)

            n += 1

        # print(f"---> executed {n} remote events")

        return n

    def __increment_time(self, amount):
        """ Increment the virtual time of the process.
        """
        self.monotonic_time += amount

        print(f"sleep({amount})")

        # print(f"### time incremented with {amount}, "
        #       f"is now {self.monotonic_time}")

    def __find_socket(self, **fields):
        """ Helper function to find a socket from the socket dict by
        looking at its fields.
        """

        matches = list()

        for fileno, socket in self.sockets.items():

            for field, value in fields.items():

                if getattr(socket, field) != value:
                    break

            else:
                matches.append((fileno, socket))

        if len(matches) > 1:
            raise RuntimeError("Found more then 1 socket matching the criteria...")

        if not matches:
            return -1, None

        return matches[0]
