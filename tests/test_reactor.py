from _json import make_encoder

import unittest

from collections import deque

from nervixd.reactor import Reactor
from nervixd.tracer import BaseTracer, PrintTracer

from nervixd.reactor.verbs import *


class TestReactor(unittest.TestCase):

    def test_login(self):

        reactor = self.get_test_reactor()
        ch1 = reactor.channel()
        name1 = b'name1'

        self.do_test_chain([
            (ch1, LoginVerb(name=name1, enforce=False, standby=False, persist=False)),
            (ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE)),
            (ch1, None),
        ])

    def test_login_dual(self):

        reactor = self.get_test_reactor()
        ch1 = reactor.channel()
        ch2 = reactor.channel()
        name1 = b'name1'

        self.do_test_chain([
            (ch1, LoginVerb(name=name1, enforce=False, standby=False, persist=False)),
            (ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE)),
            (ch1, None),

            (ch2, LoginVerb(name=name1, enforce=False, standby=False, persist=False)),
            (ch2, SessionVerb(name=name1, state=SessionVerb.STATE_ENDED)),
            (ch2, None),
        ])

    def test_login_enforce(self):

        reactor = self.get_test_reactor()
        ch1 = reactor.channel()
        ch2 = reactor.channel()
        name1 = b'name1'

        self.do_test_chain([
            (ch1, LoginVerb(name=name1, enforce=False, standby=False, persist=False)),
            (ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE)),

            (ch2, LoginVerb(name=name1, enforce=True, standby=False, persist=False)),
            (ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ENDED)),
            (ch2, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE)),

            (ch1, None),
            (ch2, None),
        ])

    def test_login_standby(self):

        reactor = self.get_test_reactor()
        ch1 = reactor.channel()
        ch2 = reactor.channel()
        name1 = b'name1'

        self.do_test_chain([
            (ch1, LoginVerb(name=name1, enforce=False, standby=False, persist=False)),
            (ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE)),

            (ch2, LoginVerb(name=name1, enforce=False, standby=True, persist=False)),
            (ch2, SessionVerb(name=name1, state=SessionVerb.STATE_STANDBY)),

            (ch1, LogoutVerb(name=name1)),
            (ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ENDED)),
            (ch2, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE)),

            (ch1, None),
            (ch2, None),
        ])

    def test_login_persist(self):

        reactor = self.get_test_reactor()
        ch1 = reactor.channel()
        ch2 = reactor.channel()
        name1 = b'name1'

        self.do_test_chain([
            (ch1, LoginVerb(name=name1, enforce=False, standby=False, persist=True)),
            (ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE)),

            (ch2, LoginVerb(name=name1, enforce=True, standby=False, persist=False)),
            (ch2, SessionVerb(name=name1, state=SessionVerb.STATE_ENDED)),

            (ch1, LogoutVerb(name=name1)),
            (ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ENDED)),

            (ch1, None),
            (ch2, None),
        ])

    def test_login_persist_standby_1(self):

        reactor = self.get_test_reactor()
        ch1 = reactor.channel()
        ch2 = reactor.channel()
        ch3 = reactor.channel()
        name1 = b'name1'

        self.do_test_chain([
            (ch1, LoginVerb(name=name1, enforce=False, standby=False, persist=True)),
            (ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE)),

            (ch2, LoginVerb(name=name1, enforce=False, standby=True, persist=False)),
            (ch2, SessionVerb(name=name1, state=SessionVerb.STATE_STANDBY)),

            (ch1, LogoutVerb(name=name1)),
            (ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ENDED)),
            (ch2, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE)),

            (ch3, LoginVerb(name=name1, enforce=True, standby=False, persist=False)),
            (ch2, SessionVerb(name=name1, state=SessionVerb.STATE_ENDED)),
            (ch3, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE)),

            (ch1, None),
            (ch2, None),
            (ch3, None),
        ])

    def test_login_persist_standby_2(self):

        reactor = self.get_test_reactor()
        ch1 = reactor.channel()
        ch2 = reactor.channel()
        ch3 = reactor.channel()
        name1 = b'name1'

        self.do_test_chain([
            (ch1, LoginVerb(name=name1, enforce=False, standby=False, persist=True)),
            (ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE)),

            (ch2, LoginVerb(name=name1, enforce=False, standby=True, persist=True)),
            (ch2, SessionVerb(name=name1, state=SessionVerb.STATE_STANDBY)),

            (ch1, LogoutVerb(name=name1)),
            (ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ENDED)),
            (ch2, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE)),

            (ch3, LoginVerb(name=name1, enforce=True, standby=False, persist=False)),
            (ch3, SessionVerb(name=name1, state=SessionVerb.STATE_ENDED)),

            (ch1, None),
            (ch2, None),
            (ch3, None),
        ])

    def test_request_uni(self):

        reactor = self.get_test_reactor()
        ch1 = reactor.channel()
        ch2 = reactor.channel()
        name1 = b'name1'

        self.do_test_chain([
            (ch1, LoginVerb(name=name1, enforce=False, standby=False, persist=False)),
            (ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE)),

            (ch2, RequestVerb(name=name1, unidirectional=True, messageref=1234, timeout=None, payload=b'payload')),
            (ch1, CallVerb(unidirectional=True, postref=None, name=name1, payload=b'payload')),

            (ch1, None),
            (ch2, None),
        ])

    def test_request_not_reachable(self):

        reactor = self.get_test_reactor()
        ch1 = reactor.channel()
        name1 = b'name1'

        self.do_test_chain([
            (ch1, RequestVerb(name=name1, unidirectional=False, messageref=1234, timeout=None, payload=b'payload')),
            (ch1, MessageVerb(messageref=1234, status=MessageVerb.STATUS_NOK, reason=MessageVerb.REASON_UNREACHABLE,
                              payload=None)),
            (ch1, None),
        ])

    def test_request_uni_not_reachable(self):

        reactor = self.get_test_reactor()
        ch1 = reactor.channel()
        name1 = b'name1'

        self.do_test_chain([
            (ch1, RequestVerb(name=name1, unidirectional=True, messageref=None, timeout=None, payload=b'payload')),
            (ch1, None),
        ])

    def test_request_reachable(self):

        reactor = self.get_test_reactor()
        ch1 = reactor.channel()
        ch2 = reactor.channel()
        name1 = b'name1'

        self.do_test_chain([
            (ch1, LoginVerb(name=name1, enforce=False, standby=False, persist=False)),
            (ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE)),

            (ch2, RequestVerb(name=name1, unidirectional=False, messageref=1234, timeout=None, payload=b'payload')),
            (ch1, CallVerb(unidirectional=False, postref=1, name=name1, payload=b'payload')),

            (ch1, PostVerb(postref=1, payload=b'the answer')),
            (ch2, MessageVerb(messageref=1234, status=MessageVerb.STATUS_OK, reason=MessageVerb.REASON_NONE,
                              payload=b'the answer')),

            (ch1, None),
            (ch2, None),
        ])

    def test_request_timeout(self):

        reactor = self.get_test_reactor()
        ch1 = reactor.channel()
        ch2 = reactor.channel()
        name1 = b'name1'

        self.do_test_chain([
            (ch1, LoginVerb(name=name1, enforce=False, standby=False, persist=False)),
            (ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE)),

            (ch2, RequestVerb(name=name1, unidirectional=False, messageref=1234, timeout=None, payload=b'payload')),
            (ch1, CallVerb(unidirectional=False, postref=1, name=name1, payload=b'payload')),
        ])

        reactor.mainloop.trigger_timers()

        self.do_test_chain([
            (ch2, MessageVerb(messageref=1234, status=MessageVerb.STATUS_NOK, reason=MessageVerb.REASON_TIMEOUT,
                              payload=None)),
            (ch2, None),

            (ch1, PostVerb(postref=1, payload=b'the answer')),
            (ch1, None),
        ])

    def test_post_twice(self):

        reactor = self.get_test_reactor()
        ch1 = reactor.channel()
        ch2 = reactor.channel()
        name1 = b'name1'
        payload1 = b'payload1'

        self.assertChannelSend(ch1, LoginVerb(name=name1, enforce=False, standby=False, persist=False))
        self.assertChannelRecv(ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE))

        self.assertChannelSend(ch2, RequestVerb(name=name1, unidirectional=False, messageref=1111, timeout=None,
                                                payload=payload1))
        self.assertChannelRecv(ch1, CallVerb(unidirectional=False, postref=1, name=name1, payload=payload1))

        self.assertChannelSend(ch1, PostVerb(postref=1, payload=b'answer'))
        self.assertChannelRecv(ch2, MessageVerb(messageref=1111, status=MessageVerb.STATUS_OK,
                                                reason=MessageVerb.REASON_NONE, payload=b'answer'))

        # second post should not yield any MessageVerbs
        self.assertChannelSend(ch1, PostVerb(postref=1, payload=b'answer'))
        self.assertChannelRecv(ch2, None)

    def test_subscribe_not_available(self):

        reactor = self.get_test_reactor()
        ch1 = reactor.channel()
        ch2 = reactor.channel()
        name1 = b'name1'

        self.do_test_chain([
            (ch1, SubscribeVerb(name=name1, messageref=1234, topic=b'topic1')),
            (ch1, None),
            (ch2, None),
        ])

    def test_subscribe_later_available(self):

        reactor = self.get_test_reactor()
        ch1 = reactor.channel()
        ch2 = reactor.channel()
        name1 = b'name1'
        topic1 = b'topic1'

        self.do_test_chain([
            (ch1, SubscribeVerb(name=name1, messageref=1234, topic=topic1)),
            (ch1, None),
            (ch2, None),

            (ch2, LoginVerb(name=name1, enforce=False, standby=False, persist=False)),
            (ch2, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE)),
            (ch2, InterestVerb(postref=1, name=name1, status=InterestVerb.STATUS_INTEREST, topic=topic1)),

            (ch1, None),
            (ch2, None),
        ])

    def test_unsubscribe(self):

        reactor = self.get_test_reactor()
        ch1 = reactor.channel()
        ch2 = reactor.channel()
        name1 = b'name1'
        topic1 = b'topic1'

        self.assertChannelSend(ch1, LoginVerb(name=name1, enforce=False, standby=False, persist=False))
        self.assertChannelRecv(ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE))

        self.assertChannelSend(ch2, SubscribeVerb(name=name1, messageref=1234, topic=topic1))
        self.assertChannelRecv(ch1,
                               InterestVerb(postref=1, name=name1, status=InterestVerb.STATUS_INTEREST, topic=topic1))

        self.assertChannelSend(ch2, UnsubscribeVerb(name=name1, topic=topic1))
        self.assertChannelRecv(ch1, InterestVerb(postref=1, name=name1, status=InterestVerb.STATUS_NO_INTEREST,
                                                 topic=topic1))

    def test_unsubscribe_multi(self):

        reactor = self.get_test_reactor()
        ch1 = reactor.channel()
        ch2 = reactor.channel()
        ch3 = reactor.channel()
        name1 = b'name1'
        topic1 = b'topic1'

        self.assertChannelSend(ch1, LoginVerb(name=name1, enforce=False, standby=False, persist=False))
        self.assertChannelRecv(ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE))

        self.assertChannelSend(ch2, SubscribeVerb(name=name1, messageref=1234, topic=topic1))
        self.assertChannelRecv(ch1,
                               InterestVerb(postref=1, name=name1, status=InterestVerb.STATUS_INTEREST, topic=topic1))

        self.assertChannelSend(ch3, SubscribeVerb(name=name1, messageref=1234, topic=topic1))
        self.assertChannelRecv(ch1, None)

        self.assertChannelSend(ch2, UnsubscribeVerb(name=name1, topic=topic1))
        self.assertChannelRecv(ch1, None)

        self.assertChannelSend(ch3, UnsubscribeVerb(name=name1, topic=topic1))
        self.assertChannelRecv(ch1, InterestVerb(postref=1, name=name1, status=InterestVerb.STATUS_NO_INTEREST,
                                                 topic=topic1))

    def test_post_on_interest(self):

        reactor = self.get_test_reactor()
        ch1 = reactor.channel()
        ch2 = reactor.channel()
        name1 = b'name1'
        topic1 = b'topic1'
        payload1 = b'post payload 1'

        self.assertChannelSend(ch1, LoginVerb(name=name1, enforce=False, standby=False, persist=False))
        self.assertChannelRecv(ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE))

        self.assertChannelSend(ch2, SubscribeVerb(name=name1, messageref=1234, topic=topic1))
        self.assertChannelRecv(ch1,
                               InterestVerb(postref=1, name=name1, status=InterestVerb.STATUS_INTEREST, topic=topic1))

        self.assertChannelSend(ch1, PostVerb(postref=1, payload=payload1))
        self.assertChannelRecv(ch2, MessageVerb(messageref=1234, status=MessageVerb.STATUS_OK,
                                                reason=MessageVerb.REASON_NONE, payload=payload1))

    def test_post_on_interest_multi(self):

        reactor = self.get_test_reactor()
        ch1 = reactor.channel()
        ch2 = reactor.channel()
        ch3 = reactor.channel()
        name1 = b'name1'
        topic1 = b'topic1'
        payload1 = b'post payload 1'
        payload2 = b'post payload 2'

        self.assertChannelSend(ch1, LoginVerb(name=name1, enforce=False, standby=False, persist=False))
        self.assertChannelRecv(ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE))

        self.assertChannelSend(ch2, SubscribeVerb(name=name1, messageref=1111, topic=topic1))
        self.assertChannelRecv(ch1,
                               InterestVerb(postref=1, name=name1, status=InterestVerb.STATUS_INTEREST, topic=topic1))

        self.assertChannelSend(ch3, SubscribeVerb(name=name1, messageref=2222, topic=topic1))

        self.assertChannelSend(ch1, PostVerb(postref=1, payload=payload1))
        self.assertChannelRecv(ch2, MessageVerb(messageref=1111, status=MessageVerb.STATUS_OK,
                                                reason=MessageVerb.REASON_NONE, payload=payload1))
        self.assertChannelRecv(ch3, MessageVerb(messageref=2222, status=MessageVerb.STATUS_OK,
                                                reason=MessageVerb.REASON_NONE, payload=payload1))

        self.assertChannelSend(ch1, PostVerb(postref=1, payload=payload2))
        self.assertChannelRecv(ch2, MessageVerb(messageref=1111, status=MessageVerb.STATUS_OK,
                                                reason=MessageVerb.REASON_NONE, payload=payload2))
        self.assertChannelRecv(ch3, MessageVerb(messageref=2222, status=MessageVerb.STATUS_OK,
                                                reason=MessageVerb.REASON_NONE, payload=payload2))

    def test_channel_close(self):

        reactor = self.get_test_reactor()
        ch1 = reactor.channel()
        ch2 = reactor.channel()
        ch3 = reactor.channel()
        name1 = b'name1'
        topic1 = b'topic1'

        self.assertChannelSend(ch1, LoginVerb(name=name1, enforce=False, standby=False, persist=False))
        self.assertChannelRecv(ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE))

        self.assertChannelSend(ch3, SubscribeVerb(name=name1, messageref=1111, topic=topic1))
        self.assertChannelRecv(ch1,
                               InterestVerb(postref=1, name=name1, status=InterestVerb.STATUS_INTEREST, topic=topic1))

        self.assertChannelSend(ch2, LoginVerb(name=name1, enforce=False, standby=True, persist=False))
        self.assertChannelRecv(ch2, SessionVerb(name=name1, state=SessionVerb.STATE_STANDBY))

        ch1.close()

        self.assertChannelRecv(ch2, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE))
        self.assertChannelRecv(ch2,
                               InterestVerb(postref=1, name=name1, status=InterestVerb.STATUS_INTEREST, topic=topic1))

    def test_channel_close_simple(self):

        reactor = self.get_test_reactor()
        ch1 = reactor.channel('ch1')
        ch2 = reactor.channel('ch2')
        name1 = b'name1'

        self.assertChannelSend(ch1, LoginVerb(name=name1, enforce=False, standby=False, persist=False))
        self.assertChannelRecv(ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE))

        self.assertChannelSend(ch2, LoginVerb(name=name1, enforce=False, standby=True, persist=False))
        self.assertChannelRecv(ch2, SessionVerb(name=name1, state=SessionVerb.STATE_STANDBY))

        ch1.close()

        self.assertChannelRecv(ch2, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE))

    def test_unknown_post(self):

        reactor = self.get_test_reactor()
        ch1 = reactor.channel()
        payload1 = b'test123'

        self.assertChannelSend(ch1, PostVerb(postref=1, payload=payload1))
        self.assertTrace(BaseTracer.channel_opened)
        self.assertTrace(BaseTracer.upstream_verb)
        self.assertTrace(BaseTracer.unknown_postref)

    def test_unowned_post(self):

        reactor = self.get_test_reactor()
        ch1 = reactor.channel('ch1')
        ch2 = reactor.channel('ch2')
        ch3 = reactor.channel('ch3')
        name1 = b'name1'

        self.assertTrace(BaseTracer.channel_opened)
        self.assertTrace(BaseTracer.channel_opened)
        self.assertTrace(BaseTracer.channel_opened)

        self.assertChannelSend(ch1, LoginVerb(name=name1, enforce=False, standby=False, persist=False))
        self.assertTrace(BaseTracer.upstream_verb)
        self.assertTrace(BaseTracer.downstream_verb)
        self.assertTrace(BaseTracer.session_activated)

        self.assertChannelSend(ch2, RequestVerb(name=name1, unidirectional=False, messageref=99, timeout=10.0,
                                                payload=b'aaa'))
        self.assertTrace(BaseTracer.upstream_verb)
        self.assertTrace(BaseTracer.downstream_verb)

        self.assertChannelSend(ch3, PostVerb(postref=1, payload=b'bbb'))
        self.assertTrace(BaseTracer.upstream_verb)
        self.assertTrace(BaseTracer.unowned_post)

    def test_unowned_post_with_subscription(self):

        reactor = self.get_test_reactor()
        ch1 = reactor.channel('ch1')
        ch2 = reactor.channel('ch2')
        name1 = b'name1'
        topic1 = b'topic1'

        self.assertTrace(BaseTracer.channel_opened)
        self.assertTrace(BaseTracer.channel_opened)

        self.assertChannelSend(ch1, SubscribeVerb(name=name1, messageref=99, topic=topic1))
        self.assertTrace(BaseTracer.upstream_verb)

        self.assertChannelSend(ch2, PostVerb(postref=1, payload=b'bbb'))
        self.assertTrace(BaseTracer.upstream_verb)
        self.assertTrace(BaseTracer.unowned_post)

    def test_login_after_close(self):

        reactor = self.get_test_reactor()
        ch1 = reactor.channel('ch1')
        ch2 = reactor.channel('ch2')
        name1 = b'name1'

        self.assertChannelSend(ch1, LoginVerb(name=name1, enforce=False, standby=True, persist=False))
        self.assertChannelRecv(ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE))

        ch1.close()

        self.assertChannelSend(ch2, LoginVerb(name=name1, enforce=False, standby=True, persist=False))
        self.assertChannelRecv(ch2, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE))

    def test_dual_login(self):
        reactor = self.get_test_reactor(True)
        ch1 = reactor.channel('ch1')
        ch2 = reactor.channel('ch2')
        name1 = b'name1'

        print('PHASE 1: login ch1')
        self.assertChannelSend(ch1, LoginVerb(name=name1, enforce=False, standby=True, persist=False))
        self.assertChannelRecv(ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE))

        print('PHASE 2: login ch2')
        self.assertChannelSend(ch2, LoginVerb(name=name1, enforce=False, standby=True, persist=False))
        self.assertChannelRecv(ch2, SessionVerb(name=name1, state=SessionVerb.STATE_STANDBY))

        print('PHASE 3: close ch2')
        ch2.close()
        self.assertChannelRecv(ch2, SessionVerb(name=name1, state=SessionVerb.STATE_ENDED))
        self.assertChannelRecv(ch2, None)

    def test_relogin(self):
        reactor = self.get_test_reactor(True)
        ch1 = reactor.channel('ch1')
        ch2 = reactor.channel('ch2')
        ch3 = reactor.channel('ch3')
        name1 = b'name1'

        print('PHASE 1: login ch1')
        self.assertChannelSend(ch1, LoginVerb(name=name1, enforce=False, standby=True, persist=False))
        self.assertChannelRecv(ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE))

        print('PHASE 2: login ch2')
        self.assertChannelSend(ch2, LoginVerb(name=name1, enforce=False, standby=True, persist=False))
        self.assertChannelRecv(ch2, SessionVerb(name=name1, state=SessionVerb.STATE_STANDBY))

        print('PHASE 3: close ch2')
        ch2.close()

        print('PHASE 4: re-login ch3')
        # after retrying to login we should still receive a standby session
        self.assertChannelSend(ch3, LoginVerb(name=name1, enforce=False, standby=True, persist=False))
        self.assertChannelRecv(ch3, SessionVerb(name=name1, state=SessionVerb.STATE_STANDBY))

    def test_logout_login(self):
        reactor = self.get_test_reactor(True)
        ch1 = reactor.channel('ch1')
        ch2 = reactor.channel('ch2')
        name1 = b'name1'

        self.assertChannelSend(ch1, LoginVerb(name=name1, enforce=False, standby=True, persist=False))
        self.assertChannelRecv(ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE))

        print("ch1 logout")
        self.assertChannelSend(ch1, LogoutVerb(name=name1))
        self.assertChannelRecv(ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ENDED))

        print("ch2 login")
        self.assertChannelSend(ch2, LoginVerb(name=name1, enforce=False, standby=True, persist=False))
        self.assertChannelRecv(ch2, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE))

    def test_topic_post_after_unsubscribe(self):
        reactor = self.get_test_reactor(True)
        ch1 = reactor.channel('ch1')
        ch2 = reactor.channel('ch2')
        name1 = b'name1'
        topic1 = b'topic'

        print("ch1 login")
        self.assertChannelSend(ch1, LoginVerb(name=name1, enforce=False, standby=False, persist=False))
        self.assertChannelRecv(ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE))

        print("ch2 subscribe")
        self.assertChannelSend(ch2, SubscribeVerb(name=name1, topic=topic1, messageref=9999))
        self.assertChannelRecv(ch1,
                               InterestVerb(postref=1, name=name1, status=InterestVerb.STATUS_INTEREST, topic=topic1))

        print("ch1 post on topic")
        self.assertChannelSend(ch1, PostVerb(postref=1, payload=b'payload1'))
        self.assertChannelRecv(ch2, MessageVerb(messageref=9999, status=MessageVerb.STATUS_OK,
                                                reason=MessageVerb.REASON_NONE, payload=b'payload1'))

        print("ch2 unsubscribe")
        self.assertChannelSend(ch2, UnsubscribeVerb(name=name1, topic=topic1))

        print("ch1 post on topic")
        self.assertChannelSend(ch1, PostVerb(postref=1, payload=b'payload2'))
        self.assertChannelRecv(ch2, None)

    def test_unsubscribe_with_close(self):
        reactor = self.get_test_reactor(True)
        ch1 = reactor.channel('ch1')
        ch2 = reactor.channel('ch2')
        name1 = b'name1'
        topic1 = b'topic'

        print("ch1 login")
        self.assertChannelSend(ch1, LoginVerb(name=name1, enforce=False, standby=False, persist=False))
        self.assertChannelRecv(ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE))

        print("ch2 subscribe")
        self.assertChannelSend(ch2, SubscribeVerb(name=name1, topic=topic1, messageref=9999))
        self.assertChannelRecv(ch1,
                               InterestVerb(postref=1, name=name1, status=InterestVerb.STATUS_INTEREST, topic=topic1))

        print("ch2 close")
        ch2.close()
        self.assertChannelRecv(ch1, InterestVerb(postref=1, name=name1, status=InterestVerb.STATUS_NO_INTEREST,
                                                 topic=topic1))

    def test_invalid_unsubscribe(self):

        reactor = self.get_test_reactor(True)
        ch1 = reactor.channel('ch1')
        name1 = b'name1'
        topic1 = b'topic'

        self.assertChannelSend(ch1, UnsubscribeVerb(name=name1, topic=topic1))
        self.assertChannelRecv(ch1, None)

    def test_double_subscription(self):

        reactor = self.get_test_reactor(True)
        ch1 = reactor.channel('ch1')
        ch2 = reactor.channel('ch2')
        name1 = b'name1'
        topic1 = b'topic'

        # do subscriptions
        self.assertChannelSend(ch1, SubscribeVerb(name=name1, messageref=1111, topic=topic1))
        self.assertChannelSend(ch1, SubscribeVerb(name=name1, messageref=2222, topic=topic1))

        # have a 2nd channel log in
        self.assertChannelSend(ch2, LoginVerb(name=name1, enforce=False, standby=False, persist=False))
        self.assertChannelRecv(ch2, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE))
        self.assertChannelRecv(ch2,
                               InterestVerb(postref=1, name=name1, status=InterestVerb.STATUS_INTEREST, topic=topic1))

        # have the 2nd channel post a message on the topic
        self.assertChannelSend(ch2, PostVerb(postref=1, payload=b'thepayload'))

        # ch1 should receive a message on the last used messageref
        self.assertChannelRecv(ch1, MessageVerb(messageref=2222, status=MessageVerb.STATUS_OK,
                                                reason=MessageVerb.REASON_NONE, payload=b'thepayload'))
        self.assertChannelRecv(ch1, None)

    def test_timeout_after_close(self):

        reactor = self.get_test_reactor(True)
        ch1 = reactor.channel('ch1')
        ch2 = reactor.channel('ch2')
        name1 = b'name1'

        # ch1 logs in
        self.assertChannelSend(ch1, LoginVerb(name=name1, enforce=False, standby=False, persist=False))
        self.assertChannelRecv(ch1, SessionVerb(name=name1, state=SessionVerb.STATE_ACTIVE))

        # ch2 does request on name1 and then closes the channel
        self.assertChannelSend(ch2, RequestVerb(name=name1, unidirectional=False, messageref=1234, timeout=5.0,
                                                payload=b'payload'))

        print("Ch2 closing")
        ch2.close()

        # the request timeout expires
        print("timout expires")
        reactor.mainloop.trigger_timers()

        # no exceptions should happen!

    def assertChannelSend(self, channel, verb):
        channel.put_upstream(verb)

    def assertChannelRecv(self, channel, verb):

        if verb is not None:
            # receive verb and check with given verb
            try:
                received_verb = channel.pop_downstream()

                self.assertEqual(verb.__class__, received_verb.__class__)
                self.assertDictEqual(verb.__dict__, received_verb.__dict__)

            except IndexError:
                raise ValueError('No verbs available but expected %s from channel %s' % (verb, channel))

        else:

            # check that the channel is empty
            with self.assertRaises(IndexError, msg="Channel has unprocessed verbs left"):
                channel.pop_downstream()

    def assertTrace(self, trace_func):

        current_func = self.tracequeue.popleft()
        func_name = trace_func.__name__

        if not current_func is func_name:
            raise ValueError('Expected %s but got %s' % (func_name, current_func))

    def do_test_chain(self, actions, must_be_empty=True):

        for channel, verb in actions:

            # if the action is an upstream verb, we just send it upstream
            if verb.__class__ in [LoginVerb, LogoutVerb, RequestVerb, PostVerb, SubscribeVerb]:
                channel.put_upstream(verb)

            # if the action is a downstream verb, we pop a verb from the
            # queue and check if it matches
            elif verb.__class__ in [SessionVerb, CallVerb, InterestVerb, MessageVerb]:

                try:
                    received_verb = channel.pop_downstream()

                    self.assertDictEqual(verb.__dict__, received_verb.__dict__)

                except IndexError:
                    raise ValueError('No verbs available but expected %s from channel %s' % (verb, channel))

            elif verb is None:

                # check that the channel is empty
                with self.assertRaises(IndexError, msg="Channel has unprocessed verbs left"):
                    channel.pop_downstream()

            else:
                raise ValueError('I dont know what to do with %s' % verb)

    def get_test_reactor(self, print_tracer=False):

        loop = DummyMainloop()

        if print_tracer:
            tracer = PrintTracer()
        else:
            self.tracequeue = deque()
            tracer = _TestTracer(self.tracequeue)

        reactor = Reactor(loop, tracer)

        return reactor


class DummyMainloop:

    def __init__(self):
        self.timer_handlers = dict()

    def now(self):
        return 1234.5

    def timer(self):
        timer = DummyTimer(self)
        return timer

    def trigger_timers(self):
        for handler in self.timer_handlers.values():
            handler()

    def _update_timer_handler(self, timerid, handler):
        if handler:
            self.timer_handlers[timerid] = handler

        else:
            self.timer_handlers.pop(timerid, None)


class DummyTimer:
    next_timer_id = 1

    def __init__(self, mainloop):
        self.mainloop = mainloop
        self.handler = None
        self.next_timer_id += 1

    def set_handler(self, handler=None, *args, **kwargs):
        self.handler = handler
        self.handler_args = args
        self.handler_kwargs = kwargs

    def set(self, timeout):
        self.timer_id = self.next_timer_id
        self.next_timer_id += 1

        self.mainloop._update_timer_handler(self.timer_id, self.__handler)

    def cancel(self):
        if self.timer_id is None:
            raise ValueError("Timer is not activated")

        self.mainloop._update_timer_handler(self.timer_id, None)
        self.timer_id = None

    def __handler(self):
        self.handler(*self.handler_args, **self.handler_kwargs)


class _TestTracer:

    def __init__(self, queue):
        self.tracer = PrintTracer()
        self.queue = queue

    def __getattr__(self, name):
        func = getattr(self.tracer, name)

        self.queue.append(name)

        return func


if __name__ == '__main__':
    unittest.main()
