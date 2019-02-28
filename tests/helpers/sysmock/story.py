from collections import deque

from socket import AF_INET, SOCK_STREAM


class Peer:

    def __init__(self, socket_fam, socket_type, address):
        self.socket_fam = socket_fam
        self.socket_type = socket_type
        self.address = address

    def verify(self, socket_fam, socket_type, address):
        if self.socket_fam != socket_fam:
            return False

        if self.socket_type != socket_type:
            return False

        if self.address != address:
            return False

        return True


class TcpPeer(Peer):
    def __init__(self, host, port):
        Peer.__init__(self, socket_fam=AF_INET, socket_type=SOCK_STREAM, address=(host, port))


def _get_address(peer_or_address):
    """ This is just a helper function to make sure an address is returned, event if
    an Peer object was given.
    """

    if isinstance(peer_or_address, Peer):
        return peer_or_address.address
    else:
        return peer_or_address


class _LocalEvent:

    def verify(self, *args, **kwargs):
        raise NotImplementedError(f"{self.__class__.__name__} event hasn't implemented the verify method yet!!!")

    def verify_field(self, desired, actual, field_name=None):
        if desired != actual:
            raise StoryError(
                f"Field {field_name + ' ' if field_name else ''}mismatch "
                f"on {self.__class__.__name__} event. "
                f"expected {desired}, but got {actual}"
            )


class _RemoteEvent:

    def execute(self, systemstate):
        raise NotImplementedError(f"{self.__class__.__name__} event hasn't implemented the execute method yet!!!")


class LocalListen(_LocalEvent):
    """ The local process starts listening on a certain address
    """

    def __init__(self, local_peer):
        self.local_peer = local_peer

    def verify(self, socket_fam, socket_type, address):
        self.verify_field(self.local_peer.socket_fam, socket_fam, 'socket_fam')
        self.verify_field(self.local_peer.socket_type, socket_type, 'socket_type')
        self.verify_field(self.local_peer.address, address, 'address')
        return True


class LocalSend(_LocalEvent):
    """ The local process sends a packet to some peer
    """

    def __init__(self, local_peer, to_address, data):
        self.local_peer = local_peer
        self.to_address = _get_address(to_address)
        self.data = data

    def verify(self, socket_fam, socket_type, from_address, to_address, data):
        self.verify_field(self.local_peer.socket_fam, socket_fam, 'socket_fam')
        self.verify_field(self.local_peer.socket_type, socket_type, 'socket_type')
        self.verify_field(self.local_peer.address, from_address, 'from_address')
        self.verify_field(self.to_address, to_address, 'to_address')
        self.verify_field(self.data, data, 'data')
        return True


class LocalClose(_LocalEvent):
    """ The local process closes a socket
    """

    def __init__(self, local_peer, to_address=None):
        self.local_peer = local_peer
        self.to_address = _get_address(to_address)

    def verify(self, socket_fam, socket_type, from_address, to_address):
        self.verify_field(self.local_peer.socket_fam, socket_fam, 'socket_fam')
        self.verify_field(self.local_peer.socket_type, socket_type, 'socket_type')
        self.verify_field(self.local_peer.address, from_address, 'from_address')
        self.verify_field(self.to_address, to_address, 'to_address')
        return True


class LocalConnect(_LocalEvent):
    """ The local process attempts to open a connection to a peer
    """

    def __init__(self, local_peer, to_address):
        self.local_peer = local_peer
        self.to_address = _get_address(to_address)


class LocalWait(_LocalEvent):
    """ The local process does nothing for a certain amount of time
    """

    def __init__(self, duration):
        self.duration = duration
        self.duration_done = 0.0

    def verify(self, duration):
        self.duration_done += duration

        if self.duration_done > self.duration:
            raise StoryError(
                f"local_wait duration overshot, "
                f"waited {self.duration_done} "
                f"instead of {self.duration}"
            )

        elif self.duration_done == self.duration:
            # print(f"DONE WAITING!!")
            return True

        else:
            # print(f"WAITED {self.duration_done}/{self.duration}")
            return False


class LocalIdle(_LocalEvent):
    """ The local process does has no pending timers or writers
    """

    def __init__(self):
        pass

    def verify(self):
        return True


class RemoteConnect(_RemoteEvent):
    """ A remote process tries to setup a connection to the local proces
    """

    def __init__(self, remote_peer, to_address):
        self.remote_peer = remote_peer
        self.to_address = _get_address(to_address)

    def execute(self, systemstate):
        systemstate.add_incoming_connection(
            self.remote_peer.socket_fam,
            self.remote_peer.socket_type,
            self.remote_peer.address,
            self.to_address
        )


class RemoteSend(_RemoteEvent):
    """ A remote process sends a packet to the local process
    """

    def __init__(self, remote_peer, to_address, data):
        self.remote_peer = remote_peer
        self.to_address = _get_address(to_address)
        self.data = data

    def execute(self, systemstate):
        systemstate.add_incoming_data(
            self.remote_peer.socket_fam,
            self.remote_peer.socket_type,
            self.remote_peer.address,
            self.to_address,
            self.data
        )


class RemoteClose(_RemoteEvent):
    """ A remote process closes a connection with the local process
    """

    def __init__(self, remote_peer, to_address):
        self.remote_peer = remote_peer
        self.to_address = _get_address(to_address)

    def execute(self, systemstate):
        systemstate.remote_close(
            self.remote_peer.socket_fam,
            self.remote_peer.socket_type,
            self.remote_peer.address,
            self.to_address
        )


class RemoteListen(_RemoteEvent):
    """ A remote process starts listening on an address
    """

    def __init__(self, remote_peer):
        self.remote_peer = remote_peer


class RemoteKill(_RemoteEvent):
    """ The local process is killed, used only to end a simulation.
    """

    def __init__(self):
        pass

    def execute(self, systemstate):
        systemstate.kill()


class RemoteSignal(_RemoteEvent):

    def __init__(self, signo):
        self.signo = signo

    def execute(self, systemstate):
        systemstate.signal(self.signo)


class StoryBase:

    def __init__(self):
        self.storyqueue = deque()

        self.next_index = 0

    def do(self, event):
        if not isinstance(event, _RemoteEvent):
            raise ValueError("Expected remote event")

        self.add(event)

    def expect(self, event):
        if not isinstance(event, _LocalEvent):
            raise ValueError("Expected local event")

        self.add(event)

    def add(self, event):
        index = self.next_index
        self.next_index += 1
        self.storyqueue.append((index, event))

    def verify(self, event_type, *args, **kwargs):
        """ Verify the pending event. First the event type will be checked,
        if that mathces then the verify function of the vent will be called.

        Raises StoryError if validation failes.
        """

        if not self.storyqueue:
            raise StoryError("Story has ended but program apearently not...")

        index, pending_event = self.storyqueue[0]

        # verify event type
        if type(pending_event) != event_type:
            raise StoryError(
                f"{type(pending_event).__name__} is pending "
                f"but got {event_type.__name__} instead."
            )

        # verify event itself
        result = pending_event.verify(*args, **kwargs)

        # verification went ok, lets pop the event of the queue
        # if the verify method returned True it means that the event is
        # fully evalueated and may be popped of the queue
        if result:
            self.storyqueue.popleft()

    def fetch_remote_events(self):
        """ Pop any pending remote events from the queue and return them
        """

        if self.storyqueue:

            index, event = self.storyqueue[0]
            if isinstance(event, _RemoteEvent):
                self.storyqueue.popleft()
                yield event

        else:
            yield RemoteKill()


class Story(StoryBase):

    def expect_local_listen(self, *args, **kwargs):
        self.expect(LocalListen(*args, **kwargs))

    def expect_local_send(self, *args, **kwargs):
        self.expect(LocalSend(*args, **kwargs))

    def expect_local_close(self, *args, **kwargs):
        self.expect(LocalClose(*args, **kwargs))

    def expect_local_connect(self, *args, **kwargs):
        self.expect(LocalConnect(*args, **kwargs))

    def expect_local_wait(self, *args, **kwargs):
        self.expect(LocalWait(*args, **kwargs))

    def expect_local_idle(self, *args, **kwargs):
        self.expect(LocalIdle())

    def do_remote_connect(self, *args, **kwargs):
        self.do(RemoteConnect(*args, **kwargs))

    def do_remote_send(self, *args, **kwargs):
        self.do(RemoteSend(*args, **kwargs))

    def do_remote_close(self, *args, **kwargs):
        self.do(RemoteClose(*args, **kwargs))

    def do_remote_listen(self, *args, **kwargs):
        self.do(RemoteListen(*args, **kwargs))

    def do_remote_signal(self, *args, **kwargs):
        self.do(RemoteSignal(*args, **kwargs))


class StoryError(AssertionError):
    pass
