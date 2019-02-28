import socket

from .connection import TelnetConnection


class TelnetService:

    def __init__(self, controller, mainloop, reactor, tracer, address):
        self.controller = controller
        self.mainloop = mainloop
        self.reactor = reactor
        self.tracer = tracer
        self.address = address

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

        # let the controller know that a new service is running
        description = f'TELNET_SERVICE_{self.address[0]}:{self.address[1]}'
        self.controller.register(self, description, self.__on_shutdown)

    def __on_connect(self):
        """
        Called from the mainloop when a new connection is ready to be
        accepted.
        """

        client_sock, address = self.socket.accept()

        TelnetConnection(self.controller, self.mainloop, self.reactor, self.tracer, client_sock)

    def __on_shutdown(self, action):
        """ Called from controller when the service should shut down. The action parameter
        indicates weather the service should shutdown immediatly (SHUTDOWN_NOW) or
        soon (SHUTDOWN_SOON).
        """

        self.proxy.unregister()
        self.socket.close()

        self.controller.unregister(self)
