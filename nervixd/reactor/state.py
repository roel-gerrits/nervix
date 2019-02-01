
import logging

from collections import defaultdict
from collections import deque
from collections import Counter

logger = logging.getLogger(__name__)


def log_call(fn):

    def wrapped(*args, **kwargs):

        retval = fn(*args, **kwargs)

        line = 'Call: ' + fn.__name__ + '('
        line += ', '.join([str(x) for x in args[1:]])
        line += ', '.join([key + '=' + str(value) for key, value in kwargs.items()])
        line += ') -> ' + str(retval)

        logger.debug(line)

        return retval

    return fn


class State:

    def __init__(self):
        
        # structures regarding names
        self.name_owners = dict()
        self.name_candidates = defaultdict(deque)
        self.name_candidates_set = defaultdict(set)
        self.name_references_from_channel = defaultdict(set)
        
        # structures regarding posts
        self.next_post_nr = 1
        self.posts = dict()
        self.posts_on_name = defaultdict(set)
        self.post_watchers = dict()
        self.post_watchers_from_channel = defaultdict(set)

        # structures regarding interest
        self.interest_counter = Counter()
        self.interest_posts = dict()
        self.interest_on_name = defaultdict(set)
        self.channel_subscriptions = defaultdict(set)

    @log_call
    def is_name_owned(self, name):
        """
        Return whether or not the name is owned.
        """
        
        owner = self.name_owners.get(name, None)
        
        return True if owner else False

    @log_call
    def get_name_owner(self, name):
        """
        Return the channel that is currently owning the name.
        """
        
        owner = self.name_owners.get(name, None)
        
        return owner.channel if owner else None

    @log_call
    def get_name_persistence(self, name):
        """
        Return wheather the current owner of the name is persistent in 
        keeping ownership.
        """
        
        return self.name_owners[name].persist

    @log_call
    def set_name_owner(self, name, channel, persist):
        """
        Set a new owner channel and returns previous owner.
        """
        
        candidate = NameCandidate(self, name, channel, persist)
        
        prev_candidate = self.name_owners.get(name)
        self.name_owners[name] = candidate
        
        self.name_references_from_channel[channel].add(name)
        
        if prev_candidate:
            self.name_references_from_channel[prev_candidate.channel].discard(name)
        
        return prev_candidate.channel if prev_candidate else False

    @log_call
    def clear_name_owner(self, name):
        """
        Free a name.
        """

        self.name_owners.pop(name)

    @log_call
    def add_name_owner_candidate(self, name, channel, persist):
        """
        Add a channel as a potential candidate for the name.
        """
        
        assert(name in self.name_owners)
        
        candidate = NameCandidate(self, name, channel, persist)
        
        if candidate in self.name_candidates_set[name]:
            raise ValueError('The channel is already a candidate')
            
        self.name_candidates[name].append(candidate)
        self.name_candidates_set[name].add(candidate)
        
        self.name_references_from_channel[channel].add(name)
        
        return candidate

    @log_call
    def del_name_owner_candidate(self, name, channel):
        """
        Remove a channel as a potential candidate for a name.
        """
        
        newqueue = deque()
        
        for candidate in self.name_candidates[name]:
            if candidate.channel != channel:
                newqueue.append(candidate)
            
            else:
                self.name_candidates_set[name].remove(candidate)
                
        self.name_candidates[name] = newqueue
        
        self.name_references_from_channel[channel].discard(name)

    @log_call
    def pop_name_owner_candidate(self, name):
        """
        Pop the next candidate from the queue and return it.
        """

        if name not in self.name_candidates:
            return None
    
        if not self.name_candidates_set[name]:
            return None
            
        candidate = self.name_candidates[name].popleft()
    
        self.name_candidates_set[name].remove(candidate)
        self.name_references_from_channel[candidate.channel].remove(name)
            
        return candidate

    @log_call
    def get_name_references_from_channel(self, channel):
        """
        Return list of names that have references to the given channel.
        """
        
        return self.name_references_from_channel.get(channel, [])

    @log_call
    def new_post(self, name, payload, persist=False):
        """
        Create a new post on the given name, returning the new Post 
        object.
        """
        
        nr = self.next_post_nr
        self.next_post_nr += 1
        
        post = Post(self, name, nr, payload, persist)
                
        self.posts[nr] = post
        self.post_watchers[nr] = dict()
        self.posts_on_name[name].add(post)
        
        return post

    @log_call
    def check_post(self, postnr):
        """
        Check if the given postnr exists.
        """
        
        return postnr in self.posts

    @log_call
    def get_posts_on_name(self, name):
        """
        Return posts that are active on the given name.
        """
        
        return self.posts_on_name[name]

    @log_call
    def get_post_owner(self, postnr):
        """
        Returns the owning channel of the post specified by postnr.
        """
        
        post = self.posts[postnr]
        
        owner = self.get_name_owner(post.name)
        
        return owner

    @log_call
    def is_post_persistent(self, postnr):
        """
        Return wheather or not the post is persistent.
        """
        
        post = self.posts.get(postnr)
        
        return post.persist

    @log_call
    def discard_post(self, postnr):
        """
        Discard the post specified by postnr.
        """
        post = self.posts[postnr]
        
        self.posts_on_name[post.name].remove(post)
        self.posts.pop(postnr)
        del post

    @log_call
    def add_post_watcher(self, postnr, channel, messageref):
        """
        Add a watcher to the post indentified by postnr.
        """
        
        watcher = self.post_watchers[postnr].get(channel, None)
        
        if not watcher:
            watcher = PostWatcher(self, postnr, channel, messageref)
            self.post_watchers[postnr][channel] = watcher
            
            self.post_watchers_from_channel[channel].add(watcher)
        
        else:
            # if the channel was already watching, update the messageref
            watcher.messageref = messageref
        
        return watcher

    @log_call
    def del_post_watcher(self, postnr, channel):
        """
        Remove a watcher from the given post identified by postnr.
        """
        
        watcher = self.post_watchers[postnr].pop(channel)
        
        self.post_watchers_from_channel[channel].remove(watcher)
        
        # delete if the channel is not watching anything anymore
        if not self.post_watchers_from_channel[channel]:
            del self.post_watchers_from_channel[channel]

    @log_call
    def get_post_watchers_from_channel(self, channel):
        """
        Return the posts that the given channel is watching.
        """
        
        return self.post_watchers_from_channel.get(channel, [])

    @log_call
    def get_post_watcher_count(self, postnr):
        """
        Return the number of watchers that are watching the post 
        identified by postnr.
        """
        
        return len(self.post_watchers[postnr])

    @log_call
    def get_post_watchers(self, postnr):
        """
        Return the watchers watching the post identified by postnr.
        """
        
        return set(self.post_watchers[postnr].values())

    def is_post_watcher(self, postnr, channel):
        """
        Returns whether or not the given channel is watching the given
        post.
        """
        
        watchers = self.post_watchers.get(postnr, dict()).keys()
        
        return channel in watchers

    @log_call
    def get_interest_level(self, name,  topic):
        """
        Get the level of interest for the given name/topic combination.
        """
        
        key = (name, topic)
        
        return self.interest_counter[key]

    @log_call
    def inc_interest_level(self, name, topic):
        """
        Increase the level of interest for the given name/topic 
        combination returning the new level.
        """
        
        key = (name, topic)
        self.interest_counter[key] += 1
        
        # if this is a newly created interest
        if self.interest_counter[key] == 1:

            self.interest_on_name[name].add(topic)
            
        
        return self.interest_counter[key]

    @log_call
    def dec_interest_level(self, name, topic):
        """
        Decrease the level of interest in the given name/topic 
        combination returning the new level.
        """
        
        key = (name, topic)
        
        if self.interest_counter[key] <= 0:
            raise ValueError('Cannot decrease interest because it is '
                'already at level zero')
            
        self.interest_counter[key] -= 1
        
        # if all interest is gone
        if self.interest_counter[key] == 0:
            
            self.interest_counter.pop(key)
            
            self.interest_posts.pop(key, None)
            
            self.interest_on_name[name].remove(topic)
            
            if not self.interest_on_name[name]:
                self.interest_on_name.pop(name)
        
        return self.interest_counter[key]

    @log_call
    def set_interest_post(self, name, topic, postnr):
        """
        Set the postnr that belongs to the given name/topic interest.
        """
        
        key = (name, topic)
        
        self.interest_posts[key] = postnr

    @log_call
    def get_interest_post(self, name, topic):
        """
        Return the postnr that is set for the given name/topic interest.
        """
        
        key = (name, topic)
        
        return self.interest_posts.get(key, None)

    @log_call
    def get_interest_on_name(self, name):
        """
        Return all interest on a given name.
        """
        
        return self.interest_on_name.get(name, set())

    @log_call
    def add_channel_subscription(self, channel, name, topic):
        """
        Register a new subscription for a channel
        """

        self.channel_subscriptions[channel].add((name, topic))

    @log_call
    def del_channel_subscription(self, channel, name, topic):
        """
        Remove a subscription for a channel
        """

        subscriptions = self.channel_subscriptions.get(channel, None)

        if subscriptions:
            subscriptions.discard((name, topic))

            if not subscriptions:
                self.channel_subscriptions.pop(channel)

    @log_call
    def get_channel_subscriptions(self, channel):
        """
        Return all subscriptions that a channel is subscribed to
        """

        return self.channel_subscriptions.get(channel, set())


class NameCandidate:
    
    def __init__(self, state, name, channel, persist):
        self.state = state
        self.name = name
        self.channel = channel
        self.persist = persist

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __hash__(self):
        return hash((self.name, self.channel))

    def __repr__(self):
        return 'NameCandidate({name}, {channel}, {persist})'.format(
            name=self.name,
            channel=self.channel,
            persist='persist' if self.persist else 'no-persist',
        )


class Post:
    
    def __init__(self, state, name, nr, payload, persist):
        self.state = state
        self.name = name
        self.nr = nr
        self.payload = payload
        self.persist = persist
        self.owner = None


class PostWatcher:
    
    def __init__(self, state, postnr, channel, messageref):
        self.state = state
        self.postnr = postnr
        self.channel = channel
        self.messageref = messageref

