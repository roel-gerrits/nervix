import unittest

from nervixd.main import main

from tests.helpers.sysmock.story import Story, TcpPeer
from tests.helpers.sysmock.mock import SysMock

import tests.nxtcp_packet_definition as packets

LHOST = TcpPeer('', 9999)

REMOTE_PEERS = [
    TcpPeer('peer1', 9001),
    TcpPeer('peer2', 9002),
    TcpPeer('peer3', 9003),
]

PEER1 = REMOTE_PEERS[0]
PEER2 = REMOTE_PEERS[1]
PEER3 = REMOTE_PEERS[2]


def setup_story(nr_of_clients):
    """ Convenience function to quicly setup a story with n clients.
    """

    s = Story()

    s.expect_local_listen(LHOST)

    for i in range(nr_of_clients):
        peer = REMOTE_PEERS[i]
        s.do_remote_connect(peer, LHOST)
        s.expect_local_send(LHOST, peer, packets.welcome())

    return s


class Test(unittest.TestCase):

    def test_keepalive_1(self):
        """ Test if a client will receive a ping client after 10 seconds, and will
        be disconnected after another 10 seconds.
        """

        s = setup_story(1)

        s.expect_local_wait(10.0)
        s.expect_local_send(LHOST, PEER1, packets.ping())
        s.expect_local_wait(10.0)
        s.expect_local_send(LHOST, PEER1, packets.byebye())
        s.expect_local_close(LHOST, PEER1)
        s.expect_local_idle()

        with SysMock(s):
            main(['--nxtcp', ':9999'])

    def test_keepalive_2(self):
        """ Test if the keepalive timer will be reset if the client sends a PONG packet
        """
        s = setup_story(1)

        s.expect_local_wait(10.0)
        s.expect_local_send(LHOST, PEER1, packets.ping())
        s.expect_local_wait(9.0)

        s.do_remote_send(PEER1, LHOST, packets.pong())

        s.expect_local_wait(10.0)
        s.expect_local_send(LHOST, PEER1, packets.ping())

        with SysMock(s):
            main(['--nxtcp', ':9999'])

    def test_login_1(self):
        """ Test if the client will receive a active session on a login request.
        """

        s = setup_story(1)

        s.do_remote_send(PEER1, LHOST, packets.login(b'testname', False, False, False))
        s.expect_local_send(LHOST, PEER1, packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        # s.do_remote_kill()

        with SysMock(s):
            main(['--nxtcp', ':9999'])

    def test_login_two_clients_0(self):
        """ Test if the second client that logins on a name will receive a
        SESSION_ENDED packet.
        """

        s = setup_story(2)

        s.do_remote_send(PEER1, LHOST, packets.login(b'testname', False, False, False))
        s.expect_local_send(LHOST, PEER1, packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        s.do_remote_send(PEER2, LHOST, packets.login(b'testname', False, False, False))
        s.expect_local_send(LHOST, PEER2, packets.session(b'testname', packets.SESSION_STATE_ENDED))

        with SysMock(s):
            main(['--nxtcp', ':9999'])

    def test_login_two_clients_1(self):
        """ Test if the first client's session will be ended and given to the
        second client if it logins with Force=True
        """

        s = setup_story(2)

        s.do_remote_send(PEER1, LHOST, packets.login(b'testname', False, False, False))
        s.expect_local_send(LHOST, PEER1, packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        s.do_remote_send(PEER2, LHOST, packets.login(b'testname', False, False, True))
        s.expect_local_send(LHOST, PEER1, packets.session(b'testname', packets.SESSION_STATE_ENDED))
        s.expect_local_send(LHOST, PEER2, packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        with SysMock(s):
            main(['--nxtcp', ':9999'])

    def test_login_two_client_2(self):
        """ Test if the login of the second client will result in a SESSION_ENDED
        regardless of its Force=True flag, because the first client logged in with
        the Persist=True flag
        """

        s = setup_story(2)

        s.do_remote_send(PEER1, LHOST, packets.login(b'testname', True, False, False))
        s.expect_local_send(LHOST, PEER1, packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        s.do_remote_send(PEER2, LHOST, packets.login(b'testname', False, False, True))
        s.expect_local_send(LHOST, PEER2, packets.session(b'testname', packets.SESSION_STATE_ENDED))

        with SysMock(s):
            main(['--nxtcp', ':9999'])

    def test_login_two_clients_3(self):
        """ Test if the second client will receive SESSION_STANDBY packet, when
        logging in, and will receive the SESSION_ACTIVE packet once the first client
        logs out.
        """

        s = setup_story(2)

        s.do_remote_send(PEER1, LHOST, packets.login(b'testname', False, False, False))
        s.expect_local_send(LHOST, PEER1, packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        s.do_remote_send(PEER2, LHOST, packets.login(b'testname', False, True, False))
        s.expect_local_send(LHOST, PEER2, packets.session(b'testname', packets.SESSION_STATE_STANDBY))

        s.do_remote_send(PEER1, LHOST, packets.logout(b'testname'))
        s.expect_local_send(LHOST, PEER1, packets.session(b'testname', packets.SESSION_STATE_ENDED))
        s.expect_local_send(LHOST, PEER2, packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        with SysMock(s):
            main(['--nxtcp', ':9999'])

    def test_login_two_clients_4(self):
        """ Test the second client will get a SESSION_STANDBY packet and a
        SESSION_ACTIVE packet once the first client logs out. Even with the
        Enforce and Persist flags set.
        """

        s = setup_story(2)

        s.do_remote_send(PEER1, LHOST, packets.login(b'testname', True, False, False))
        s.expect_local_send(LHOST, PEER1, packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        s.do_remote_send(PEER2, LHOST, packets.login(b'testname', False, True, True))
        s.expect_local_send(LHOST, PEER2, packets.session(b'testname', packets.SESSION_STATE_STANDBY))

        s.do_remote_send(PEER1, LHOST, packets.logout(b'testname'))
        s.expect_local_send(LHOST, PEER1, packets.session(b'testname', packets.SESSION_STATE_ENDED))
        s.expect_local_send(LHOST, PEER2, packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        with SysMock(s):
            main(['--nxtcp', ':9999'])

    def test_logout_on_client_disconnect(self):
        """ Test if a client disconnect will be treated as a logout.
        """

        s = setup_story(2)

        s.do_remote_send(PEER1, LHOST, packets.login(b'testname', False, False, False))
        s.expect_local_send(LHOST, PEER1, packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        s.do_remote_send(PEER2, LHOST, packets.login(b'testname', False, True, False))
        s.expect_local_send(LHOST, PEER2, packets.session(b'testname', packets.SESSION_STATE_STANDBY))

        s.do_remote_close(PEER1, LHOST)
        s.expect_local_close(LHOST, PEER1)
        s.expect_local_send(LHOST, PEER2, packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        with SysMock(s):
            main(['--nxtcp', ':9999'])

    def test_request_no_responder_1(self):
        """ Test if a MESSAGE_UNREACHABLE packet is received when trying to do a request
        to an un-owned session.
        """

        s = setup_story(1)

        s.do_remote_send(PEER1, LHOST, packets.request(b'testname', False, 1234, 1000, b'thepayload'))
        s.expect_local_send(LHOST, PEER1, packets.message(1234, packets.MESSAGE_STATUS_UNREACHABLE))

        with SysMock(s):
            main(['--nxtcp', ':9999'])

    def test_request_no_responder_2(self):
        """ Test if a Request packet is NOT responded to when send in unidirectional
        mode. This is verified by expecting a ping packet because of the keepalive
        mechanism.
        """

        s = setup_story(1)

        s.do_remote_send(PEER1, LHOST, packets.request(b'testname', True, 1234, 1000, b'thepayload'))
        s.expect_local_wait(10.0)
        s.expect_local_send(LHOST, PEER1, packets.ping())

        with SysMock(s):
            main(['--nxtcp', ':9999'])

    def test_request_timeout_1(self):
        """ Test if the second client will receive a MESSAGE_TIMEOUT packet when a
        request is done to an owned session, but not responded to by the first client.
        """

        s = setup_story(2)

        s.do_remote_send(PEER1, LHOST, packets.login(b'testname', False, False, False))
        s.expect_local_send(LHOST, PEER1, packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        s.do_remote_send(PEER2, LHOST, packets.request(b'testname', False, 1234, 2222, b'thepayload'))
        s.expect_local_send(LHOST, PEER1, packets.call(False, 1, b'testname', b'thepayload'))

        s.expect_local_wait(2.222)

        s.expect_local_send(LHOST, PEER2, packets.message(1234, packets.MESSAGE_STATUS_TIMEOUT))

        with SysMock(s):
            main(['--nxtcp', ':9999'])

    def test_request_timeout_2(self):
        """ Test if the timeout will be the default if unspecified in the request.
        """

        s = setup_story(2)

        s.do_remote_send(PEER1, LHOST, packets.login(b'testname', False, False, False))
        s.expect_local_send(LHOST, PEER1, packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        s.do_remote_send(PEER2, LHOST, packets.request(b'testname', False, 1234, 0, b'thepayload'))
        s.expect_local_send(LHOST, PEER1, packets.call(False, 1, b'testname', b'thepayload'))

        s.expect_local_wait(4.0)

        s.expect_local_send(LHOST, PEER2, packets.message(1234, packets.MESSAGE_STATUS_TIMEOUT))

        with SysMock(s):
            main(['--nxtcp', ':9999'])

    def test_request_timeout_3(self):
        """ Test if the timeout will be limited if a too long timeout is specified.
        Because we are testing such a long timoeut, we have to account for the packets send by the keepalive
        mechanism as well, that is why it looks a bit messy.
        """

        s = setup_story(2)

        s.do_remote_send(PEER1, LHOST, packets.login(b'testname', False, False, False))
        s.expect_local_send(LHOST, PEER1, packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        s.do_remote_send(PEER2, LHOST, packets.request(b'testname', False, 1234, 60001, b'thepayload'))
        s.expect_local_send(LHOST, PEER1, packets.call(False, 1, b'testname', b'thepayload'))

        for _ in range(5):
            s.expect_local_wait(10.0)
            s.expect_local_send(LHOST, PEER1, packets.ping())
            s.expect_local_send(LHOST, PEER2, packets.ping())
            s.do_remote_send(PEER1, LHOST, packets.pong())
            s.do_remote_send(PEER2, LHOST, packets.pong())

        s.expect_local_wait(10.0)
        s.expect_local_send(LHOST, PEER1, packets.ping())
        s.expect_local_send(LHOST, PEER2, packets.message(1234, packets.MESSAGE_STATUS_TIMEOUT))
        s.expect_local_send(LHOST, PEER2, packets.ping())

        with SysMock(s):
            main(['--nxtcp', ':9999'])

    def test_request_unidirectional_1(self):
        """ Test if the first client receives an unidirectional Call packet when the
        second client sends an unidirectional request.
        """

        s = setup_story(2)

        s.do_remote_send(PEER1, LHOST, packets.login(b'testname', False, False, False))
        s.expect_local_send(LHOST, PEER1, packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        s.do_remote_send(PEER2, LHOST, packets.request(b'testname', True, 0, 0, b'thepayload'))
        s.expect_local_send(LHOST, PEER1, packets.call(True, 0, b'testname', b'thepayload'))

        with SysMock(s):
            main(['--nxtcp', ':9999'])

    def test_request_1(self):
        """ Test if the first client receives a message when the second client replies
        to the request.
        """

        s = setup_story(2)

        s.do_remote_send(PEER1, LHOST, packets.login(b'testname', False, False, False))
        s.expect_local_send(LHOST, PEER1, packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        s.do_remote_send(PEER2, LHOST, packets.request(b'testname', False, 1234, 1000, b'thepayload'))
        s.expect_local_send(LHOST, PEER1, packets.call(False, 1, b'testname', b'thepayload'))

        s.do_remote_send(PEER1, LHOST, packets.post(1, b'thepayload'))
        s.expect_local_send(LHOST, PEER2, packets.message(1234, packets.MESSAGE_STATUS_OK, b'thepayload'))

        with SysMock(s):
            main(['--nxtcp', ':9999'])

    def test_dual_post_1(self):
        """ Check if a second post to the same postref is ignored by the server, and will not
        result in a second Message packet to client.
        """

        s = setup_story(2)

        s.do_remote_send(PEER1, LHOST, packets.login(b'testname', False, False, False))
        s.expect_local_send(LHOST, PEER1, packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        s.do_remote_send(PEER2, LHOST, packets.request(b'testname', False, 1234, 1000, b'thepayload'))
        s.expect_local_send(LHOST, PEER1, packets.call(False, 1, b'testname', b'thepayload'))

        # 1st post
        s.do_remote_send(PEER1, LHOST, packets.post(1, b'thepayload'))
        s.expect_local_send(LHOST, PEER2, packets.message(1234, packets.MESSAGE_STATUS_OK, b'thepayload'))

        # 2nd post
        s.do_remote_send(PEER1, LHOST, packets.post(1, b'thepayload'))

        # no verify that it is indeed ignored by waiting for the keepalive packets
        s.expect_local_wait(10.0)
        s.expect_local_send(LHOST, PEER1, packets.ping())
        s.expect_local_send(LHOST, PEER2, packets.ping())

        with SysMock(s):
            main(['--nxtcp', ':9999'])

    def test_post_from_wrong_client(self):
        """ Test if a post placed by a third client instead of the first client is correctly handled,
        that is, the unlawfull post of c3 should be ignored, and eventually a timouet message will be
        received by c2.
        """

        s = setup_story(3)

        s.do_remote_send(PEER1, LHOST, packets.login(b'testname', False, False, False))
        s.expect_local_send(LHOST, PEER1, packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        s.do_remote_send(PEER2, LHOST, packets.request(b'testname', False, 1234, 1000, b'thepayload'))
        s.expect_local_send(LHOST, PEER1, packets.call(False, 1, b'testname', b'thepayload'))

        s.do_remote_send(PEER3, LHOST, packets.post(1, b'thepayload'))

        s.expect_local_wait(1.0)

        s.expect_local_send(LHOST, PEER2, packets.message(1234, packets.MESSAGE_STATUS_TIMEOUT))

        with SysMock(s):
            main(['--nxtcp', ':9999'])

    def test_post_after_timeout(self):
        """ Test if a post is ignored when the request timeout is already expired.
        """

        s = setup_story(2)

        s.do_remote_send(PEER1, LHOST, packets.login(b'testname', False, False, False))
        s.expect_local_send(LHOST, PEER1, packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        s.do_remote_send(PEER2, LHOST, packets.request(b'testname', False, 1234, 1000, b'thepayload'))
        s.expect_local_send(LHOST, PEER1, packets.call(False, 1, b'testname', b'thepayload'))

        s.expect_local_wait(1.0)

        s.expect_local_send(LHOST, PEER2, packets.message(1234, packets.MESSAGE_STATUS_TIMEOUT))

        s.do_remote_send(PEER2, LHOST, packets.post(1, b'thepayload'))

        # no verify that it is indeed ignored by waiting for the keepalive packets
        s.expect_local_wait(9.0)
        s.expect_local_send(LHOST, PEER1, packets.ping())
        s.expect_local_wait(1.0)
        s.expect_local_send(LHOST, PEER2, packets.ping())

        with SysMock(s):
            main(['--nxtcp', ':9999'])

    def test_subscribe_1(self):
        """ Test that a subscribe from c2 will result in a interest packet on c1.
        """

        s = setup_story(2)

        s.do_remote_send(PEER1, LHOST, packets.login(b'testname', False, False, False))
        s.expect_local_send(LHOST, PEER1, packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        s.do_remote_send(PEER2, LHOST, packets.subscribe(1234, b'testname', b'testtopic'))
        s.expect_local_send(LHOST, PEER1,
                            packets.interest(1, packets.INTEREST_STATUS_INTEREST, b'testtopic'))

        with SysMock(s):
            main(['--nxtcp', ':9999'])

    def test_subscribe_2(self):
        """ Test that multiple subscries will still result in just one interest packet.
        """

        s = setup_story(3)

        s.do_remote_send(PEER1, LHOST, packets.login(b'testname', False, False, False))
        s.expect_local_send(LHOST, PEER1, packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        s.do_remote_send(PEER2, LHOST, packets.subscribe(1234, b'testname', b'testtopic'))

        s.expect_local_send(LHOST, PEER1,
                            packets.interest(1, packets.INTEREST_STATUS_INTEREST, b'testtopic'))

        s.do_remote_send(PEER3, LHOST, packets.subscribe(1234, b'testname', b'testtopic'))

        s.expect_local_wait(10.0)
        s.expect_local_send(LHOST, PEER1, packets.ping())
        s.expect_local_send(LHOST, PEER2, packets.ping())
        s.expect_local_send(LHOST, PEER3, packets.ping())

        with SysMock(s):
            main(['--nxtcp', ':9999'])

    def test_unsubscribe_1(self):
        """ Test that a no-interest packet will be send when all subscribes have unsubscdribed.
        """

        s = setup_story(3)

        s.do_remote_send(PEER1, LHOST, packets.login(b'testname', False, False, False))
        s.expect_local_send(LHOST, PEER1, packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        s.do_remote_send(PEER2, LHOST, packets.subscribe(1234, b'testname', b'testtopic'))

        s.expect_local_send(LHOST, PEER1,
                            packets.interest(1, packets.INTEREST_STATUS_INTEREST, b'testtopic'))

        s.do_remote_send(PEER3, LHOST, packets.subscribe(1234, b'testname', b'testtopic'))

        s.do_remote_send(PEER2, LHOST, packets.unsubscribe(b'testname', b'testtopic'))
        s.do_remote_send(PEER3, LHOST, packets.unsubscribe(b'testname', b'testtopic'))

        s.expect_local_send(LHOST, PEER1,
                            packets.interest(1, packets.INTEREST_STATUS_NOINTEREST, b'testtopic'))

        with SysMock(s):
            main(['--nxtcp', ':9999'])

    def test_subscribe_post_1(self):
        """ Test if mulitple post on a topic will indeed result in multiple messages to all subscribers.
        """

        s = setup_story(3)

        s.do_remote_send(PEER1, LHOST, packets.login(b'testname', False, False, False))
        s.expect_local_send(LHOST, PEER1, packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        s.do_remote_send(PEER2, LHOST, packets.subscribe(1234, b'testname', b'testtopic'))

        s.expect_local_send(LHOST, PEER1,
                            packets.interest(1, packets.INTEREST_STATUS_INTEREST, b'testtopic'))

        s.do_remote_send(PEER3, LHOST, packets.subscribe(1234, b'testname', b'testtopic'))

        s.do_remote_send(PEER1, LHOST, packets.post(1, b'testpayload'))

        s.expect_local_send(LHOST, PEER2, packets.message(1234, packets.MESSAGE_STATUS_OK, b'testpayload'))
        s.expect_local_send(LHOST, PEER3, packets.message(1234, packets.MESSAGE_STATUS_OK, b'testpayload'))

        with SysMock(s):
            main(['--nxtcp', ':9999'])

    def test_subscriber_quit_1(self):
        """ Test if unexpected close of an client will result in an unsubscribe.
        """

        s = setup_story(2)

        s.do_remote_send(PEER1, LHOST, packets.login(b'testname', False, False, False))
        s.expect_local_send(LHOST, PEER1, packets.session(b'testname', packets.SESSION_STATE_ACTIVE))

        s.do_remote_send(PEER2, LHOST, packets.subscribe(1234, b'testname', b'testtopic'))

        s.expect_local_send(LHOST, PEER1,
                            packets.interest(1, packets.INTEREST_STATUS_INTEREST, b'testtopic'))

        s.do_remote_close(PEER2, LHOST)
        s.expect_local_close(LHOST, PEER2)

        s.expect_local_send(LHOST, PEER1,
                            packets.interest(1, packets.INTEREST_STATUS_NOINTEREST, b'testtopic'))

        with SysMock(s):
            main(['--nxtcp', ':9999'])

    def test_quit_byebye(self):
        """ Test if the server will close the connection when a quit packet is received.
        """

        s = setup_story(1)

        s.do_remote_send(PEER1, LHOST, packets.quit())

        s.expect_local_close(LHOST, PEER1)

        with SysMock(s):
            main(['--nxtcp', ':9999'])
