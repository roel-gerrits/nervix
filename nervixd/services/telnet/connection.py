from .decoder import *
from .encoder import *

from nervixd.reactor.verbs import *


class TelnetConnection:

    def __init__(self, controller, mainloop, reactor, tracer, client_sock):

        self.controller = controller
        self.mainloop = mainloop
        self.reactor = reactor
        self.tracer = tracer
        self.socket = client_sock

        self.packet_handlers = {
            LoginPacket: self.__handle_packet_login,
            LogoutPacket: self.__handle_packet_logout,
            RequestPacket: self.__handle_packet_request,
            PostPacket: self.__handle_packet_post,
            SubscribePacket: self.__handle_packet_subscribe,
            UnsubscribePacket: self.__handle_packet_unsubscribe,
            PingPacket: self.__handle_packet_ping,
            QuitPacket: self.__handle_packet_quit,
            HelpPacket: self.__handle_packet_help,
        }

        self.verb_handlers = {
            SessionVerb: self.__handle_session_verb,
            CallVerb: self.__handle_call_verb,
            MessageVerb: self.__handle_message_verb,
            InterestVerb: self.__handle_interest_verb,
        }

        self.__start()

    def __start(self):
        """
        Start handling the connection.
        """

        # init socket
        self.socket.setblocking(False)

        self.proxy = self.mainloop.register(self.socket)
        self.proxy.set_read_handler(self.__on_read)
        self.proxy.set_write_handler(self.__on_write)
        self.proxy.set_interest(read=True)
        self.__close_connection = False

        # init protocol handlers
        self.encoder = Encoder()
        self.decoder = Decoder()

        # init channel
        self.channel = self.reactor.channel()

        sock_port = self.socket.getpeername()[1]
        description = 'TELNET_{:05d}'.format(sock_port)
        self.channel.set_description(description)
        self.channel.set_downstream_handler(self.__on_downstream)

        # send welcome
        self.encoder.encode(WelcomePacket(1, 1))
        self.proxy.start_writing()

    def __on_read(self):
        """
        Called from the mainloop when there is data from the socket to
        be read.
        """

        n = self.decoder.read_from_socket(self.socket)

        while True:

            try:
                packet = self.decoder.decode()

            except DecodingError as e:
                packet = None

                self.__handle_invalid_request(e.args[0].encode())

            if not packet:
                break

            self.__handle_packet(packet)

        if n == 0:
            # if zero bytes were read from the server, it means that
            # the client has closed the connection

            self.__do_close_connection()

    def __on_write(self):
        """
        Called from the mainloop when we should writ data to the socket.
        """

        n = self.encoder.write_to_socket(self.socket)

        if n == 0:
            self.proxy.stop_writing()

        if self.__close_connection:
            self.__do_close_connection()

    def __on_downstream(self):
        """
        Called from the reactor when there are pending verbs to be
        processed by us.
        """

        verb = self.channel.pop_downstream()

        if verb:
            self.__handle_verb(verb)

    def __handle_packet(self, packet):
        """
        Called when we have decoded an incoming packet from the client.
        """

        handler = self.packet_handlers.get(
            packet.__class__,
            None
        )

        if not handler:
            raise NotImplementedError("No handler implemented for {} packets".format(packet.__class__.__name__))

        handler(packet)

    def __handle_verb(self, verb):
        """
        Called when we receive a verb from the reactor.
        """

        handler = self.verb_handlers.get(
            verb.__class__,
            None
        )

        if not handler:
            raise NotImplementedError("No handler implemented for {} verbs".format(verb.__class__.__name__))

        handler(verb)

    def __do_close_connection(self):
        """
        Called when the client has closed the connection.
        """

        # close channel
        self.channel.close()

        # close proxy
        self.proxy.unregister()

        # close socket
        self.socket.close()

        # unregister from controller
        self.controller.unregister_client(self)

        # send trace
        # TODO

    def __handle_invalid_request(self, reason):
        """
        Handle an invalid request.
        """

        self.encoder.encode(InvalidRequestPacket(reason))
        self.proxy.start_writing()

    def __handle_packet_login(self, packet):
        """
        Handle a LOGIN packet.
        """

        self.channel.put_upstream(LoginVerb(
            name=packet.name,
            enforce=packet.enforce,
            standby=packet.standby,
            persist=packet.persist
        ))

    def __handle_packet_logout(self, packet):
        """
        Handle a LOGOUT packet.
        """

        self.channel.put_upstream(LogoutVerb(
            name=packet.name
        ))

    def __handle_packet_request(self, packet):
        """
        Handle a REQUEST packet.
        """

        self.channel.put_upstream(RequestVerb(
            name=packet.name,
            unidirectional=packet.unidirectional,
            messageref=packet.messageref,
            timeout=packet.timeout,
            payload=packet.payload
        ))

    def __handle_packet_post(self, packet):
        """
        Handle a POST packet.
        """

        self.channel.put_upstream(PostVerb(
            postref=packet.postref,
            payload=packet.payload
        ))

    def __handle_packet_subscribe(self, packet):
        """
        Handle a SUBSCRIBE packet.
        """

        self.channel.put_upstream(SubscribeVerb(
            name=packet.name,
            messageref=packet.messageref,
            topic=packet.topic
        ))

    def __handle_packet_unsubscribe(self, packet):
        """
        Handle a UNSUBSCRIBE packet.
        """

        self.channel.put_upstream(UnsubscribeVerb(
            name=packet.name,
            topic=packet.topic
        ))

    def __handle_packet_ping(self, packet):
        """
        Handle a PING packet.
        """

        self.encoder.encode(PongPacket(
            packet.payload
        ))

        self.proxy.start_writing()

    def __handle_packet_quit(self, packet):
        """
        Handle a QUIT packet.
        """

        self.__do_close_connection()

    def __handle_packet_help(self, packet):
        """
        Handle a HELP packet
        """

        self.encoder.encode(InfoPacket(
            packet.topic
        ))

        self.proxy.start_writing()

    def __handle_session_verb(self, verb):
        """
        Handle a SESSION verb.
        """

        # the telnet encoder uses other numbers for states
        if verb.state == SessionVerb.STATE_ACTIVE:
            packet_state = 2
        elif verb.state == SessionVerb.STATE_STANDBY:
            packet_state = 1
        elif verb.state == SessionVerb.STATE_ENDED:
            packet_state = 0
        else:
            raise RuntimeError("Verb has unknown state '{}'".format(verb.state))

        self.encoder.encode(SessionPacket(
            name=verb.name,
            state=packet_state,
        ))

        self.proxy.start_writing()

    def __handle_call_verb(self, verb):
        """
        Handle a CALL verb.
        """

        self.encoder.encode(CallPacket(
            unidirectional=verb.unidirectional,
            postref=verb.postref,
            name=verb.name,
            payload=verb.payload
        ))

        self.proxy.start_writing()

    def __handle_message_verb(self, verb):
        """
        Handle a MESSAGE verb.
        """

        self.encoder.encode(MessagePacket(
            messageref=verb.messageref,
            status=verb.reason,
            payload=verb.payload
        ))

        self.proxy.start_writing()

    def __handle_interest_verb(self, verb):
        """
        Handle an INTEREST verb.
        """

        self.encoder.encode(InterestPacket(
            postref=verb.postref,
            status=verb.status,
            name=verb.name,
            topic=verb.topic,
        ))

        self.proxy.start_writing()
