from collections import deque
import logging

from .verbs import *
from .state import State

logger = logging.getLogger(__name__)


class Reactor:

    def __init__(self, mainloop, tracer):

        self.mainloop = mainloop
        self.tracer = tracer

        self.channels = set()
        self.state = State()

        self.handlers = {
            LoginVerb: self.__process_login,
            LogoutVerb: self.__process_logout,
            RequestVerb: self.__process_request,
            PostVerb: self.__process_post,
            SubscribeVerb: self.__process_subscribe,
            UnsubscribeVerb: self.__process_unsubscribe,
        }

        self.watch_timeout_default = 4.0
        self.watch_timeout_max = 60.0
        self.watch_timeout_timers = dict()

    def channel(self, description=None):
        """
        Create a new channel object.
        """

        ch = Channel(self)

        if description:
            ch.set_description(description)

        self.channels.add(ch)

        return ch

    def _process_verb(self, sender, verb):
        """
        Process a verb that is send upstream.
        """

        # validate verb
        if not isinstance(verb, BaseVerb):
            self.tracer.invalid_upstream_verb(sender, verb, "Not an instance of BaseVerb")
            return

        try:
            verb.validate()

        except ValueError as e:
            self.tracer.invalid_upstream_verb(sender, verb, str(e))
            raise

        # retrieve verb handler
        handler = self.handlers.get(
            verb.__class__,
            self.__process_not_implemented
        )

        # handle the verb
        self.tracer.upstream_verb(sender, verb)
        handler(sender, verb)

    def _close_channel(self, channel):
        """
        Close a channel.
        """

        names = self.state.get_name_references_from_channel(channel)
        for name in list(names):

            # send no-interest on topics that are currently assigned to the name
            self.state.get_interest_on_name(name)

            # send a session-end verb to the channel
            session = SessionVerb()
            session.name = name
            session.state = SessionVerb.STATE_ENDED
            self.__put_downstream(channel, session)

            # remove any standby entries that may exist
            self.state.del_name_owner_candidate(name, channel)

            # if we are currently owning this channel, release it
            current_owner = self.state.get_name_owner(name)
            if current_owner == channel:
                self.state.clear_name_owner(name)

            # promote next name candidate
            candidate = self.state.pop_name_owner_candidate(name)

            if candidate:
                self.state.set_name_owner(name, candidate.channel, candidate.persist)

                self.__activate_session(candidate.channel, name)

        # unsubscribe all subscriptions done by this channel
        for name, topic in list(self.state.get_channel_subscriptions(channel)):

            postnr = self.state.get_interest_post(name, topic)

            # decrease interest
            level = self.state.dec_interest_level(name, topic)

            # if there is no longer any interest in the topic
            if level == 0:

                self.state.discard_post(postnr)

                name_owner = self.state.get_name_owner(name)

                if name_owner:
                    self.__put_downstream(name_owner, InterestVerb(
                        postref=postnr,
                        name=name,
                        status=InterestVerb.STATUS_NO_INTEREST,
                        topic=topic
                    ))

            # unregister the subscription of this channel
            self.state.del_channel_subscription(channel, name, topic)

        watches = self.state.get_post_watchers_from_channel(channel)
        for watch in list(watches):

            # remove this channel as postwatcher
            self.state.del_post_watcher(watch.postnr, watch.channel)

            # cancel timer (if any)
            timer = self.watch_timeout_timers.get(watch, None)

            if timer:
                timer.cancel()

        self.tracer.channel_closed(channel)
        self.channels.remove(channel)

    def __process_login(self, sender, verb):
        """
        Process LOGIN verbs
        """

        name = verb.name
        current_owner = self.state.get_name_owner(name)

        # in case the name is not used or the sender already owns the
        # name:
        if not current_owner or current_owner == sender:

            self.state.set_name_owner(name, sender, verb.persist)

            self.__activate_session(sender, name)

        # in case the name is not persistent and the sender used the
        # force flag:
        elif verb.enforce and not self.state.get_name_persistence(name):

            self.state.set_name_owner(name, sender, verb.persist)

            session = SessionVerb()
            session.name = name
            session.state = SessionVerb.STATE_ENDED
            self.__put_downstream(current_owner, session)

            self.__activate_session(sender, name)

        # in case the sender specified the standby flag:
        elif verb.standby:

            self.state.add_name_owner_candidate(name, sender, verb.persist)

            session = SessionVerb()
            session.name = name
            session.state = SessionVerb.STATE_STANDBY
            self.__put_downstream(sender, session)

        # otherwise we just cannot own this name:
        else:

            session = SessionVerb()
            session.name = name
            session.state = SessionVerb.STATE_ENDED
            self.__put_downstream(sender, session)

    def __process_logout(self, sender, verb):
        """
        Process LOGOUT verbs.
        """

        name = verb.name

        # send a session-end verb to the sender, even if it does not own
        # the name at this time
        session = SessionVerb()
        session.name = name
        session.state = SessionVerb.STATE_ENDED
        self.__put_downstream(sender, session)

        # if the sender is the current owner:
        if self.state.get_name_owner(name) == sender:

            self.state.clear_name_owner(name)

            candidate = self.state.pop_name_owner_candidate(name)

            if candidate:
                self.state.set_name_owner(name, candidate.channel, candidate.persist)

                self.__activate_session(candidate.channel, name)

        else:
            # the logout verb was NOT send by the owner, this is the
            # clients fault, log it for debugging purposes.
            self.tracer.improper_logout(name, verb)

        # remove any standby entries that may exist
        self.state.del_name_owner_candidate(name, sender)

    def __process_request(self, sender, request):
        """
        Process REQUEST verbs.
        """

        name = request.name

        owner = self.state.get_name_owner(name)

        # if there is no channel owning the name:
        if not owner:

            if not request.unidirectional:
                message = MessageVerb()
                message.messageref = request.messageref
                message.status = MessageVerb.STATUS_NOK
                message.reason = MessageVerb.REASON_UNREACHABLE
                self.__put_downstream(sender, message)

        # if there is an owner and the request is unidirectional:
        elif request.unidirectional:

            call = CallVerb()
            call.unidirectional = True
            call.postref = None
            call.name = name
            call.payload = request.payload
            self.__put_downstream(owner, call)

        # if there is an owner and the request expects an answer:
        else:

            post = self.state.new_post(name, request.payload)
            watch = self.state.add_post_watcher(post.nr, sender, request.messageref)

            # determine timeout
            if request.timeout:
                timeout = min(request.timeout, self.watch_timeout_max)
            else:
                timeout = self.watch_timeout_default

            # set timeout timer
            timer = self.mainloop.timer()
            timer.set_handler(self.__watch_timeout_handler, watch)
            timer.set(timeout)
            self.watch_timeout_timers[watch] = timer

            # send Call to targeted channel
            call = CallVerb()
            call.unidirectional = False
            call.postref = post.nr
            call.name = name
            call.payload = post.payload
            self.__put_downstream(owner, call)

    def __watch_timeout_handler(self, watch):
        """
        Handler for processing post timeouts.
        """

        postnr = watch.postnr
        channel = watch.channel

        self.state.del_post_watcher(postnr, channel)
        self.watch_timeout_timers.pop(watch)

        # send timeout message
        message = MessageVerb()
        message.messageref = watch.messageref
        message.status = MessageVerb.STATUS_NOK
        message.reason = MessageVerb.REASON_TIMEOUT
        message.payload = None

        self.__put_downstream(watch.channel, message)

        # discard of postref if there are no more watchers
        if self.state.get_post_watcher_count(postnr) <= 0:
            self.state.discard_post(postnr)

    def __process_post(self, sender, verb):
        """
        Process POST verbs.
        """

        postnr = verb.postref

        if self.state.check_post(postnr):

            owner = self.state.get_post_owner(postnr)

            if sender == owner:

                for watcher in self.state.get_post_watchers(postnr):

                    # cancel timeout timer
                    timer = self.watch_timeout_timers.pop(watcher, None)
                    if timer:
                        timer.cancel()

                    # send Message to each watcher
                    message = MessageVerb()
                    message.messageref = watcher.messageref
                    message.status = MessageVerb.STATUS_OK
                    message.reason = MessageVerb.REASON_NONE
                    message.payload = verb.payload

                    self.__put_downstream(watcher.channel, message)

                if not self.state.is_post_persistent(postnr):
                    self.state.discard_post(postnr)

            elif not owner:

                # the postref is not owned by any channel, this is because
                # this postref belongs to a subscription, but the targeted
                # name is not logged on
                self.tracer.unowned_post(postnr, sender, verb)

            else:

                # the postref is not owned by the channel that send the
                # post verb, we ignore this, but log it anyway
                self.tracer.unowned_post(postnr, sender, verb)

        else:

            # no postref found with the given postref.
            # this is the client's fault, but we should log it for
            # debugging purposes
            self.tracer.unknown_postref(sender, verb)

    def __process_subscribe(self, sender, subscribe):
        """
        Process SUBSCRIBE verbs.
        """

        name = subscribe.name
        topic = subscribe.topic

        level = self.state.inc_interest_level(name, topic)

        # if there were no interest in this topic before this 
        # subscription
        if level == 1:

            # create and set postnr
            post = self.state.new_post(name, topic, True)
            postnr = post.nr
            self.state.set_interest_post(name, topic, postnr)
            owner = self.state.get_post_owner(postnr)

            # send interest if a channel is owning the name
            if owner:
                self.__put_downstream(owner, InterestVerb(
                    postref=postnr,
                    name=name,
                    status=InterestVerb.STATUS_INTEREST,
                    topic=topic
                ))

        # if there was already interest in this topic before this 
        # subscription
        else:

            postnr = self.state.get_interest_post(name, topic)

        # add the subscribing as watcher to the post
        self.state.add_post_watcher(postnr, sender, subscribe.messageref)

        # register the subscription of this channel
        self.state.add_channel_subscription(sender, name, topic)

    def __process_unsubscribe(self, sender, unsubscribe):
        """
        Process UNSUBSCRIBE verbs.
        """

        name = unsubscribe.name
        topic = unsubscribe.topic

        postnr = self.state.get_interest_post(name, topic)

        # validate if the sender is actually subscribed
        if not self.state.is_post_watcher(postnr, sender):
            self.tracer.unwatched_unsubscribe(sender, name, topic)
            return

        # decrease interest
        level = self.state.dec_interest_level(name, topic)

        # if there is no longer any interest in the topic
        if level == 0:

            self.state.discard_post(postnr)

            name_owner = self.state.get_name_owner(name)

            if name_owner:
                self.__put_downstream(name_owner, InterestVerb(
                    postref=postnr,
                    name=name,
                    status=InterestVerb.STATUS_NO_INTEREST,
                    topic=topic
                ))

        # unregister the subscription of this channel
        self.state.del_channel_subscription(sender, name, topic)

    def __process_not_implemented(self, sender, verb):
        """
        Fallback handler for verbs that are not implmeneted yet.
        """

        print("No reactor handler implemented for {} verbs".format(
            verb.__class__.__name__
        ))

    def __activate_session(self, channel, name):
        """
        Activate a session for the given channel on the given name.
        This will also send all the interest if any.
        """

        # send session-active verb
        session = SessionVerb()
        session.name = name
        session.state = SessionVerb.STATE_ACTIVE
        self.__put_downstream(channel, session)

        # send any interest in this name
        for topic in self.state.get_interest_on_name(name):
            postnr = self.state.get_interest_post(name, topic)

            self.__put_downstream(channel, InterestVerb(
                postref=postnr,
                name=name,
                status=InterestVerb.STATUS_INTEREST,
                topic=topic,
            ))

        self.tracer.session_activated(channel, name)

    def __put_downstream(self, channel, verb):
        """
        Send a verb downstream.
        """

        # validate verb
        if not isinstance(verb, BaseVerb):
            self.tracer.invalid_downstream_verb(channel, verb, "Not an instance of BaseVerb")
            return

        try:
            verb.validate()

        except ValueError as e:
            self.tracer.invalid_downstream_verb(channel, verb, str(e))
            raise
            return

        self.tracer.downstream_verb(channel, verb)

        channel._put_downstream(verb)


class Channel:
    """
    The Channel class.

    This class is used by services to interact with the reactor.
    """

    def __init__(self, reactor):

        self.reactor = reactor

        self.description = ''

        self.downstream_queue = deque()
        self.downstream_handler = None

        self.reactor.tracer.channel_opened(self)

        self.is_closed = False

    def set_description(self, description):
        """
        Set a textual description that describes this channel. This is
        will only be used for logging purposes.
        """

        self.description = description

    def set_downstream_handler(self, handler):
        """
        Set the function that will be called when there are verbs to be
        processed in this channel's downstream queue.
        """

        self.downstream_handler = handler

    def put_upstream(self, verb):
        """
        Put a verb into the upstream queue.
        """

        if self.is_closed:
            raise RuntimeError('Cannot put verb upstream on a closed channel')

        self.reactor._process_verb(self, verb)

    def pop_downstream(self):
        """
        Pop a verb from the downstream queue. This function is typically
        called from the downstream handler set via the
        set_downstream_handler() method.
        """

        return self.downstream_queue.popleft()

    def close(self):
        """
        Close the channel. Disowning any owned names.
        """

        self.reactor._close_channel(self)
        self.is_closed = True

    def _put_downstream(self, verb):
        """
        Put a verb downstream. Called from the reactor.
        """

        self.downstream_queue.append(verb)

        if self.downstream_handler:

            while self.downstream_queue:
                self.downstream_handler()

    def __repr__(self):
        return "<{cls} {description}>".format(
            cls=self.__class__.__name__,
            description=self.description,
        )
