from selectors import EVENT_READ, EVENT_WRITE, SelectorKey
from collections import defaultdict


class PatchedSocket:

    def __init__(self, systemstate, socket_fam=None, socket_type=None, fileno=None):
        self.systemstate = systemstate

        if fileno:
            self._fileno = fileno
        else:
            self._fileno = self.systemstate.socket(socket_fam, socket_type)

    def setblocking(self, _):
        pass

    def setsockopt(self, *_):
        pass

    def bind(self, address):

        return self.systemstate.bind(self._fileno, address)

    def listen(self, backlog=0):

        return self.systemstate.listen(self._fileno, backlog)

    def accept(self):

        fileno, address = self.systemstate.accept(self._fileno)

        socket = PatchedSocket(self.systemstate, fileno=fileno)

        return socket, address

    def send(self, data):
        n = self.systemstate.send(self._fileno, data)
        return n

    def recv(self, n):
        res = self.systemstate.recv(self._fileno, n)
        return res

    def close(self):
        self.systemstate.close(self._fileno)

    def fileno(self):
        return self._fileno

    def getpeername(self):
        return self.systemstate.getpeername(self._fileno)

    def __getattr__(self, item):
        raise NotImplementedError("'{}' is not implemented".format(item))


class PatchedSelector:

    def __init__(self, systemstate):
        self.systemstate = systemstate

        self.keys = dict()

    def register(self, fd, events, data=None):
        key = SelectorKey(None, fd, events, data)

        self.keys[fd] = key
        # print(f"interest for {fd} is now {events}")

        return key

    def modify(self, fd, events, data=None):
        key = SelectorKey(None, fd, events, data)

        self.keys[fd] = key
        # print(f"interest for {fd} is now {events}")

        return key

    def unregister(self, fd):
        self.keys.pop(fd)

    def select(self, timeout):

        interest_table = defaultdict(set)

        for key in self.keys.values():

            if key.events & EVENT_READ:
                interest_table[key.fd].add('r')

            if key.events & EVENT_WRITE:
                interest_table[key.fd].add('w')

        event_list = self.systemstate.select(interest_table, timeout)
        selected_keys = list()

        for fd, event_mask in event_list:
            key_events = 0
            key_events |= EVENT_READ if 'r' in event_mask else 0
            key_events |= EVENT_WRITE if 'w' in event_mask else 0

            selected_keys.append((self.keys[fd], key_events))

        return selected_keys

    def __getattr__(self, item):
        raise NotImplementedError("'{}' is not implemented".format(item))
