from unittest.mock import patch

from selectors import EVENT_READ, EVENT_WRITE, SelectorKey

from .system import System, EndOfSimulation


class SockMock:

    def __init__(self, scenario):
        self.scenario = scenario

        self.system = System(self.scenario)

        # list of modules that should be patched
        self.patchers = [
            patch('socket.socket', side_effect=self.__get_patched_socket),
            patch('selectors.DefaultSelector', side_effect=self.__get_patched_selector),
            patch('time.monotonic', side_effect=self.system.monotonic),
        ]

    def __enter__(self):
        print("=== ENTERING MOCKED ENVIRONMENT ===")
        for patcher in self.patchers:
            patcher.start()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):

        print("=== LEAVING MOCKED ENVIRONMENT ===")

        for patcher in self.patchers:
            patcher.stop()

        if exc_type == EndOfSimulation:
            return True

        if exc_type is None:
            raise RuntimeError("Program ended without finishing program")

    def __get_patched_socket(self, family, type):
        return PatchedSocket(self.system, family, type)

    def __get_patched_selector(self):
        return PatchedSelector(self.system)


class PatchedSocket:

    def __init__(self, system, family=None, type=None, fileno=None):
        self.system = system

        if fileno:
            self._fileno = fileno
        else:
            self._fileno = self.system.socket(family, type)

    def setblocking(self, _):
        pass

    def setsockopt(self, *_):
        pass

    def bind(self, address):

        return self.system.bind(self._fileno, address)

    def listen(self, backlog=0):

        return self.system.listen(self._fileno, backlog)

    def accept(self):

        fileno, address = self.system.accept(self._fileno)

        socket = PatchedSocket(self.system, fileno=fileno)

        return socket, address

    def send(self, data):
        n = self.system.send(self._fileno, data)
        return n

    def recv(self, n):
        res = self.system.recv(self._fileno, n)
        return res

    def close(self):
        self.system.close(self._fileno)

    def fileno(self):
        return self._fileno

    def getpeername(self):
        return self.system.getpeername(self._fileno)

    def __getattr__(self, item):
        raise NotImplementedError("'{}' is not implemented".format(item))


class PatchedSelector:

    def __init__(self, system):
        self.system = system

        self.keys = dict()

    def register(self, fd, events, data=None):
        # print(f"# register {fd}, {events}")

        key = SelectorKey(None, fd, events, data)

        self.keys[fd] = key

        return key

    def modify(self, fd, events, data=None):
        # print(f"# modify {fd}, {events}")

        key = SelectorKey(None, fd, events, data)

        self.keys[fd] = key

        return key

    def unregister(self, fd):
        self.keys.pop(fd)

    def select(self, timeout):
        # print(f"#!! select {timeout}")

        events = []

        while True:

            # iterate over all interest, see if there is any events ready to return
            for fd, key in self.keys.items():

                if EVENT_READ & key.events:
                    if self.system.has_connection_pending(fd):
                        events.append((key, EVENT_READ))

                    elif self.system.has_incoming_data(fd):
                        events.append((key, EVENT_READ))

                # writes are always possible in this mockup
                if EVENT_WRITE & key.events:
                    events.append((key, EVENT_WRITE))

            # yay, we got some events, lets return them
            if events:
                break

            # no events ready, lets evualuate, and see if there is something new
            n = self.system.evaluate()

            # yeah new events, lets start at the top
            if n:
                continue

            if timeout is None:
                pass
                # hmm it appears that the program is waiting for external events, but there are no events left...
                # this must be the end of the simulation

                self.system.end()

            else:
                self.system.progress_time(timeout)

            break

        # print("#!!", [(x[0].fd, x[1]) for x in events])

        return events

    def __getattr__(self, item):
        raise NotImplementedError("'{}' is not implemented".format(item))
