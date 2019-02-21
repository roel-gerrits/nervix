from unittest.mock import patch

from .systemstate import SystemState, Abort
from .calls import PatchedSocket, PatchedSelector


class SysMock:

    def __init__(self, story):

        self.systemstate = SystemState(story)

        # list of functions that should be patched
        self.patchers = [
            patch('socket.socket', side_effect=self.__get_patched_socket),
            patch('selectors.DefaultSelector', side_effect=self.__get_patched_selector),
            patch('time.monotonic', side_effect=self.systemstate.monotonic),
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

        if exc_type == Abort:
            return True

        if exc_type is None:
            raise RuntimeError("Program ended before story was finished")

    def __get_patched_socket(self, socket_fam, socket_type):
        return PatchedSocket(self.systemstate, socket_fam, socket_type)

    def __get_patched_selector(self):
        return PatchedSelector(self.systemstate)
