import unittest

from nervixd.main import main

from tests.helpers.sockmock import SockMock, Scenario

import tests.nxtcp_packet_definition as packets

LISTEN_ADDRESS = ('', 9999)
PEER_ADDRESSES = [
    ('peer1_address', 9001),
    ('peer2_address', 9002),
    ('peer3_address', 9003),
]

PEER1_ADDRESS = PEER_ADDRESSES[0]
PEER2_ADDRESS = PEER_ADDRESSES[1]
PEER3_ADDRESS = PEER_ADDRESSES[2]


def setup_clients(scenario, nr_clients):
    host = scenario.local_socket()
    host.listen(LISTEN_ADDRESS)

    clients = []

    for i in range(nr_clients):
        client = scenario.remote_socket(PEER_ADDRESSES[i])
        client.connect(LISTEN_ADDRESS)

        client.recv(packets.welcome())

        clients.append(client)

    return (host, *clients)


def close_clients(*clients):
    for client in clients:
        client.send(packets.quit())
        client.remote_closed()


class Test(unittest.TestCase):
    #
    # def test_1(self):
    #     s = Scenario()
    #
    #     host = s.local_socket()
    #     host.listen(LISTEN_ADDRESS)
    #
    #     c1 = s.remote_socket(PEER1_ADDRESS)
    #     c1.connect(LISTEN_ADDRESS)
    #
    #     c1.recv(packets.welcome())
    #
    #     s.end()
    #
    #     with SockMock(s):
    #         main(['--nxtcp', ':9999'])

    def test_keepalive_1(self):
        """ Test if a client will receive a ping client after 10 seconds, and will
        be disconnected after another 10 seconds.
        """

        s = Scenario()
        host, client = setup_clients(s, 1)

        s.timelapse(10.0)

        client.recv(packets.ping(b'ABCDEFGHIJKLMNOP'))

        s.timelapse(10.0)

        client.recv(packets.byebye())

        client.remote_closed()

        s.end()

        with SockMock(s):
            main(['--nxtcp', ':9999'])

    def test_keepalive_2(self):
        """ Test if the keepalive timer will be reset if the client sends a PONG packet
        """

        s = Scenario()
        host, client = setup_clients(s, 1)

        s.timelapse(10.0)

        client.recv(packets.ping(b'ABCDEFGHIJKLMNOP'))

        client.send(packets.pong(b'WHATEVER'))

        s.timelapse(10.0)

        client.recv(packets.ping(b'ABCDEFGHIJKLMNOP'))

        s.timelapse(10.0)

        client.recv(packets.byebye())

        client.remote_closed()

        s.end()

        with SockMock(s):
            main(['--nxtcp', ':9999'])

    def test_login_1(self):
        """ Test if the client will receive a active session on a login request.
        """

        s = Scenario()
        host, client = setup_clients(s, 1)

        client.send(packets.login(b'testname', False, False, False))

        client.recv(packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        close_clients(client)

        s.end()

        with SockMock(s):
            main(['--nxtcp', ':9999'])

    def test_login_two_clients_0(self):
        """ Test if thesecond client that logins on a name will receive a
        SESSION_ENDED packet.
        """

        s = Scenario()
        host, c1, c2 = setup_clients(s, 2)

        c1.send(packets.login(b'testname', False, False, False))
        c1.recv(packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        c2.send(packets.login(b'testname', False, False, False))
        c2.recv(packets.session(b'testname', packets.SESSION_STATE_ENDED))

        close_clients(c1, c2)

        s.end()

        with SockMock(s):
            main(['--nxtcp', ':9999'])

    def test_login_two_clients_1(self):
        """ Test if the first client's session will be ended and given to the
        second client if it logins with Force=True
        """

        s = Scenario()
        host, c1, c2 = setup_clients(s, 2)

        c1.send(packets.login(b'testname', False, False, False))
        c1.recv(packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        c2.send(packets.login(b'testname', False, False, True))
        c1.recv(packets.session(b'testname', packets.SESSION_STATE_ENDED))
        c2.recv(packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        close_clients(c1, c2)

        s.end()

        with SockMock(s):
            main(['--nxtcp', ':9999'])

    def test_login_two_client_2(self):
        """ Test if the login of the second client will result in a SESSION_ENDED
        regardless of its Force=True flag, because the first client logged in with
        the Persist=True flag
        """

        s = Scenario()
        host, c1, c2 = setup_clients(s, 2)

        c1.send(packets.login(b'testname', True, False, False))
        c1.recv(packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        c2.send(packets.login(b'testname', False, False, True))
        c2.recv(packets.session(b'testname', packets.SESSION_STATE_ENDED))

        close_clients(c1, c2)

        s.end()

        with SockMock(s):
            main(['--nxtcp', ':9999'])

    def test_login_two_clients_3(self):
        """ Test if the second client will receive SESSION_STANDBY packet, when
        logging in, and will receive the SESSION_ACTIVE packet once the first client
        logs out.
        """

        s = Scenario()
        host, c1, c2 = setup_clients(s, 2)

        c1.send(packets.login(b'testname', False, False, False))
        c1.recv(packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        c2.send(packets.login(b'testname', False, True, False))
        c2.recv(packets.session(b'testname', packets.SESSION_STATE_STANDBY))

        c1.send(packets.logout(b'testname'))
        c1.recv(packets.session(b'testname', packets.SESSION_STATE_ENDED))
        c2.recv(packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        close_clients(c1, c2)

        s.end()

        with SockMock(s):
            main(['--nxtcp', ':9999'])

    def test_login_two_clients_4(self):
        """ Test the second client will get a SESSION_STANDBY packet and an
        SESSION_ACTIVE packet once the first client logs out. Even with the Enforce
        Persist flags set.
        """

        s = Scenario()
        host, c1, c2 = setup_clients(s, 2)

        c1.send(packets.login(b'testname', True, False, False))
        c1.recv(packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        c2.send(packets.login(b'testname', False, True, True))
        c2.recv(packets.session(b'testname', packets.SESSION_STATE_STANDBY))

        c1.send(packets.logout(b'testname'))
        c1.recv(packets.session(b'testname', packets.SESSION_STATE_ENDED))
        c2.recv(packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        close_clients(c1, c2)

        s.end()

        with SockMock(s):
            main(['--nxtcp', ':9999'])

    def test_request_no_responder_1(self):
        """ Test if a MESSAGE_UNREACHABLE packet is received when trying to do a request
        to an un-owned session.
        """

        s = Scenario()
        host, c1 = setup_clients(s, 1)

        c1.send(packets.request(b'testname', False, 1234, 1000, b'thepayload'))

        c1.recv(packets.message(1234, packets.MESSAGE_STATUS_UNREACHABLE))

        close_clients(c1)

        s.end()

        with SockMock(s):
            main(['--nxtcp', ':9999'])

    def test_request_no_responder_2(self):
        """ Test if a Request packet is NOT responded to when send in unidirectional
        mode.
        """

        s = Scenario()
        host, c1 = setup_clients(s, 1)

        c1.send(packets.request(b'testname', True, 1234, 1000, b'thepayload'))

        s.timelapse(5.0)

        close_clients(c1)

        s.end()

        with SockMock(s):
            main(['--nxtcp', ':9999'])

    def test_request_timeout_1(self):
        """ Test if the second client will receive a MESSAGE_TIMEOUT packet when a
        request is done to an owned session, but not responded to by the first client.
        """

        s = Scenario()
        host, c1, c2 = setup_clients(s, 2)

        c1.send(packets.login(b'testname', False, False, False))
        c1.recv(packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        c2.send(packets.request(b'testname', False, 1234, 2222, b'thepayload'))
        c1.recv(packets.call(False, 1, b'testname', b'thepayload'))

        s.timelapse(2.222)

        c2.recv(packets.message(1234, packets.MESSAGE_STATUS_TIMEOUT))

        close_clients(c1, c2)

        s.end()

        with SockMock(s):
            main(['--nxtcp', ':9999'])

    def test_request_unidirectional_1(self):
        """ Test if the first client receives an unidirectional Call packet when the
        second client sends an unidirectional request.
        """

        s = Scenario()
        host, c1, c2 = setup_clients(s, 2)

        c1.send(packets.login(b'testname', False, False, False))
        c1.recv(packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        c2.send(packets.request(b'testname', True, 0, 0, b'thepayload'))
        c1.recv(packets.call(True, 0, b'testname', b'thepayload'))

        s.timelapse(5.0)

        close_clients(c1, c2)

        s.end()

        with SockMock(s):
            main(['--nxtcp', ':9999'])
