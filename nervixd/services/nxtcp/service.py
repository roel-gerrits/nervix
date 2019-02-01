import socket

from nervixd.services import BaseService
from .connection import NxtcpConnection


class NxtcpService(BaseService):

    def __init__(self, controller, mainloop, reactor, tracer, address):
        self.controller = controller
        self.mainloop = mainloop
        self.reactor = reactor
        self.tracer = tracer
        self.address = address

        self.controller.register_service(self)

        self.__start()

    def __start(self):
        """
        Start serving.
        """

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(False)

        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.address)
        self.socket.listen()

        self.proxy = self.mainloop.register(self.socket)
        self.proxy.set_read_handler(self.__on_connect)
        self.proxy.set_interest(read=True)

    def __on_connect(self):
        """
        Called from the mainloop when a new connection is ready to be
        accepted.
        """

        client_sock, address = self.socket.accept()

        client = NxtcpConnection(self.controller, self.mainloop, self.reactor, self.tracer, client_sock)

        self.controller.register_client(client)

    def get_actual_address(self):
        """
        Get the actual address tuple that the socket listens on.
        """
        return self.socket.getsockname()
