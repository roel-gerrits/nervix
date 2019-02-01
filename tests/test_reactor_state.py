#!/usr/bin/env python3

import unittest

from nervixd.reactor.state import State


class TestState(unittest.TestCase):

    def test_name_1(self):
        s = State()

        name = 'non-existing'

        self.assertFalse(s.is_name_owned(name))

        self.assertIsNone(s.get_name_owner(name))

        self.assertIsNone(s.pop_name_owner_candidate(name))

        name = 'testname'
        channel1 = self.get_dummy_channel()

        s.set_name_owner(name, channel1, True)

        self.assertTrue(s.is_name_owned(name))

        self.assertEqual(channel1, s.get_name_owner(name))

        channel2 = self.get_dummy_channel()

        prev = s.set_name_owner(name, channel2, True)
        self.assertEqual(prev, channel1)

    def test_name_2(self):
        s = State()
        name = 'testname'

        channel0 = self.get_dummy_channel()
        s.set_name_owner(name, channel0, True)

        channel1 = self.get_dummy_channel()
        candidate1 = s.add_name_owner_candidate(name, channel1, True)
        self.assertEqual(candidate1.channel, channel1)

        candidate = s.pop_name_owner_candidate(name)
        self.assertEqual(candidate, candidate1)
        self.assertEqual(candidate1.channel, channel1)

    def test_name_3(self):
        s = State()
        name = 'testname'

        channel0 = self.get_dummy_channel()
        s.set_name_owner(name, channel0, True)

        channel1 = self.get_dummy_channel()
        candidate1 = s.add_name_owner_candidate(name, channel1, True)

        with self.assertRaises(ValueError):
            s.add_name_owner_candidate(name, channel1, True)

        candidate2 = s.pop_name_owner_candidate(name)

        self.assertEqual(candidate1, candidate2)

        s.add_name_owner_candidate(name, channel1, True)

        channel3 = self.get_dummy_channel()
        candidate3 = s.add_name_owner_candidate(name, channel3, True)

        s.del_name_owner_candidate(name, channel1)

        candidate = s.pop_name_owner_candidate(name)
        self.assertEqual(candidate, candidate3)
        self.assertEqual(candidate.channel, channel3)

        candidate = s.pop_name_owner_candidate(name)
        self.assertIsNone(candidate)

    def test_name_references_1(self):
        s = State()
        name = 'testname1'

        channel1 = self.get_dummy_channel()
        channel2 = self.get_dummy_channel()
        channel3 = self.get_dummy_channel()

        # first check references with empty state
        refs = s.get_name_references_from_channel(channel1)
        self.assertEqual(refs, [])

        refs = s.get_name_references_from_channel(channel2)
        self.assertEqual(refs, [])

        # now set a name owner and expect a reference
        s.set_name_owner(name, channel1, True)

        self.assertEqual(
            s.get_name_references_from_channel(channel1),
            set([name]),
        )

        # now change the name owner and expect changed references
        s.set_name_owner(name, channel2, True)

        self.assertEqual(
            s.get_name_references_from_channel(channel2),
            set([name]),
        )

        # the other channel should have no references left
        self.assertEqual(
            s.get_name_references_from_channel(channel1),
            set(),
        )

        # now add channel3 as candidate
        s.add_name_owner_candidate(name, channel3, True)

        self.assertEqual(
            s.get_name_references_from_channel(channel3),
            set([name]),
        )

        self.assertEqual(
            s.get_name_references_from_channel(channel2),
            set([name]),
        )

        # now pop the next candidate and set the new candiate as owner

        candidate = s.pop_name_owner_candidate(name)

        s.set_name_owner(name, candidate.channel, candidate.persist)

        self.assertEqual(
            s.get_name_references_from_channel(channel2),
            set(),
        )

        self.assertEqual(
            s.get_name_references_from_channel(channel3),
            set([name]),
        )

    def test_name_references_2(self):
        s = State()
        name = 'testname1'

        channel0 = self.get_dummy_channel()
        channel1 = self.get_dummy_channel()
        channel2 = self.get_dummy_channel()
        channel3 = self.get_dummy_channel()

        s.set_name_owner(name, channel0, True)
        s.add_name_owner_candidate(name, channel1, True)
        s.add_name_owner_candidate(name, channel2, True)
        s.add_name_owner_candidate(name, channel3, True)

        # validate references for all 4 channels

        self.assertEqual(
            s.get_name_references_from_channel(channel0),
            set([name]),
        )

        self.assertEqual(
            s.get_name_references_from_channel(channel1),
            set([name]),
        )

        self.assertEqual(
            s.get_name_references_from_channel(channel2),
            set([name]),
        )

        self.assertEqual(
            s.get_name_references_from_channel(channel3),
            set([name]),
        )

        # now remove channel2 

        s.del_name_owner_candidate(name, channel2)

        # re-validate references for all 4 channels

        self.assertEqual(
            s.get_name_references_from_channel(channel0),
            set([name]),
        )

        self.assertEqual(
            s.get_name_references_from_channel(channel1),
            set([name]),
        )

        self.assertEqual(
            s.get_name_references_from_channel(channel2),
            set(),
        )

        self.assertEqual(
            s.get_name_references_from_channel(channel3),
            set([name]),
        )

        # while we are here, check if the candidate mechanism still works

        candidate = s.pop_name_owner_candidate(name)
        self.assertEqual(
            candidate.channel,
            channel1,
        )

        candidate = s.pop_name_owner_candidate(name)
        self.assertEqual(
            candidate.channel,
            channel3,
        )

        candidate = s.pop_name_owner_candidate(name)
        self.assertEqual(
            candidate,
            None,
        )

    def test_new_post(self):
        s = State()
        name = 'testname'

        post = s.new_post(name, 'payload')

        self.assertTrue(s.check_post(post.nr))

        s.discard_post(post.nr)

        self.assertFalse(s.check_post(post.nr))

    def test_posts_on_name(self):
        s = State()
        name1 = 'testname1'
        name2 = 'testname2'

        # create a new post
        post1 = s.new_post(name1, 'payload')

        # check if it is correctly stored
        posts = s.get_posts_on_name(name1)
        self.assertEqual(
            posts,
            set([post1]),
        )

        # add some more
        post2 = s.new_post(name1, 'payload')

        # check if it is correctly stored
        posts = s.get_posts_on_name(name1)
        self.assertEqual(
            posts,
            set([post1, post2]),
        )

        # now remove post1
        s.discard_post(post1.nr)

        # check if it is correctly stored
        posts = s.get_posts_on_name(name1)
        self.assertEqual(
            posts,
            set([post2]),
        )

    def test_get_post_owner(self):
        s = State()
        name = 'testname'

        post = s.new_post(name, 'payload')

        # the name is not yet owned, so it should return None
        self.assertIsNone(s.get_post_owner(post.nr))

        # now own the name
        channel = self.get_dummy_channel()
        s.set_name_owner(name, channel, True)

        # now call it again
        self.assertEqual(
            s.get_post_owner(post.nr),
            channel,
        )

    def test_post_watchers(self):
        s = State()
        name = 'testname'
        channel1 = self.get_dummy_channel()
        channel2 = self.get_dummy_channel()

        post = s.new_post(name, 'payload')

        # add a  post watcher
        watch1 = s.add_post_watcher(post.nr, channel1, 1111)

        # check return value
        self.assertEqual(watch1.channel, channel1)
        self.assertEqual(watch1.messageref, 1111)

        # check watcher count
        self.assertEqual(s.get_post_watcher_count(post.nr), 1)

        # check get_watchers method
        self.assertEqual(
            s.get_post_watchers(post.nr),
            set([watch1]),
        )

        # add again
        watch2 = s.add_post_watcher(post.nr, channel1, 2222)

        # this should have no effect, as each channel may only be added
        # once
        self.assertEqual(
            s.get_post_watchers(post.nr),
            set([watch1]),
        )

        # add a new one
        watch3 = s.add_post_watcher(post.nr, channel2, 3333)

        # check get_watchers method
        self.assertEqual(
            s.get_post_watchers(post.nr),
            set([watch1, watch3]),
        )

    def test_get_post_watchers_from_channel(self):
        s = State()
        name = 'testname'
        channel1 = self.get_dummy_channel()
        channel2 = self.get_dummy_channel()

        post1 = s.new_post(name, 'payload1')
        post2 = s.new_post(name, 'payload2')

        # check before adding watcher
        self.assertEqual(
            s.get_post_watchers_from_channel(channel1),
            [],
        )

        watch1 = s.add_post_watcher(post1.nr, channel1, 1111)

        # check after adding watcher
        self.assertEqual(
            s.get_post_watchers_from_channel(channel1),
            set([watch1])
        )

        # watch another post
        watch2 = s.add_post_watcher(post2.nr, channel1, 2222)

        self.assertEqual(
            s.get_post_watchers_from_channel(channel1),
            set([watch1, watch2])
        )

        # remove watcher
        s.del_post_watcher(post1.nr, channel1)

        self.assertEqual(
            s.get_post_watchers_from_channel(channel1),
            set([watch2])
        )

        # remove watcher
        s.del_post_watcher(post2.nr, channel1)

        self.assertEqual(
            s.get_post_watchers_from_channel(channel1),
            []
        )

    def test_del_post_watcher(self):
        s = State()
        name = 'testname'
        channel1 = self.get_dummy_channel()
        channel2 = self.get_dummy_channel()

        post = s.new_post(name, 'payload')

        # add a  post watcher
        watch1 = s.add_post_watcher(post.nr, channel1, 1111)

        # check get_watchers method
        self.assertEqual(
            s.get_post_watchers(post.nr),
            set([watch1]),
        )

        # delete a post watcher
        s.del_post_watcher(post.nr, channel1)

        # check watcher count
        self.assertEqual(s.get_post_watcher_count(post.nr), 0)

        # check get_watchers method
        self.assertEqual(
            s.get_post_watchers(post.nr),
            set(),
        )

        # add a  post watcher
        watch2 = s.add_post_watcher(post.nr, channel1, 2222)
        watch3 = s.add_post_watcher(post.nr, channel2, 3333)

        # check watcher count
        self.assertEqual(s.get_post_watcher_count(post.nr), 2)

        # check get_watchers method
        self.assertEqual(
            s.get_post_watchers(post.nr),
            set([watch2, watch3]),
        )

        # delete a post watcher
        s.del_post_watcher(post.nr, channel1)

        # check watcher count
        self.assertEqual(s.get_post_watcher_count(post.nr), 1)

        # check get_watchers method
        self.assertEqual(
            s.get_post_watchers(post.nr),
            set([watch3]),
        )

    def test_interest_counter(self):
        s = State()

        name = 'testname'

        # at first the interest should be 0
        self.assertEqual(
            s.get_interest_level(name, 'topic'),
            0
        )

        # now increase the interest and test
        s.inc_interest_level(name, 'topic')

        self.assertEqual(
            s.get_interest_level(name, 'topic'),
            1
        )

        # now increase the interest again and test
        s.inc_interest_level(name, 'topic')

        self.assertEqual(
            s.get_interest_level(name, 'topic'),
            2
        )

        # now decrease and test again
        s.dec_interest_level(name, 'topic')

        self.assertEqual(
            s.get_interest_level(name, 'topic'),
            1
        )

        # now again and it should be zero
        s.dec_interest_level(name, 'topic')

        self.assertEqual(
            s.get_interest_level(name, 'topic'),
            0
        )

        # going below zero should raise an exception
        with self.assertRaises(ValueError):
            s.dec_interest_level(name, 'topic')

    def test_interest_return_values(self):
        s = State()
        name = 'testname'

        self.assertEqual(
            s.inc_interest_level(name, 'topic'),
            s.get_interest_level(name, 'topic'),
        )

        self.assertEqual(
            s.inc_interest_level(name, 'topic'),
            s.get_interest_level(name, 'topic'),
        )

        self.assertEqual(
            s.inc_interest_level(name, 'topic'),
            s.get_interest_level(name, 'topic'),
        )

        self.assertEqual(
            s.dec_interest_level(name, 'topic'),
            s.get_interest_level(name, 'topic'),
        )

        self.assertEqual(
            s.dec_interest_level(name, 'topic'),
            s.get_interest_level(name, 'topic'),
        )

        self.assertEqual(
            s.dec_interest_level(name, 'topic'),
            s.get_interest_level(name, 'topic'),
        )

    def test_interest_post(self):
        s = State()

        name = 'testname'
        topic = 'topic'

        post = s.new_post(name, 'payload')

        s.inc_interest_level(name, topic)
        s.set_interest_post(name, topic, post.nr)

        postnr = s.get_interest_post(name, topic)

        self.assertEqual(post.nr, postnr)

        s.dec_interest_level(name, topic)

        self.assertIsNone(s.get_interest_post(name, topic))

    def test_interest_on_name(self):
        s = State()

        name1 = 'testname1'
        topic1 = 'topic1'
        topic2 = 'topic2'

        # inc topic1
        s.inc_interest_level(name1, topic1)

        self.assertEqual(
            s.get_interest_on_name(name1),
            set([topic1]),
        )

        # inc topic2
        s.inc_interest_level(name1, topic2)

        self.assertEqual(
            s.get_interest_on_name(name1),
            set([topic1, topic2]),
        )

        # dec topic1
        s.dec_interest_level(name1, topic1)

        self.assertEqual(
            s.get_interest_on_name(name1),
            set([topic2]),
        )

        # dec topic2
        s.dec_interest_level(name1, topic2)

        self.assertEqual(
            s.get_interest_on_name(name1),
            set(),
        )

        # check resources usage
        self.assertFalse(s.interest_on_name)
        self.assertFalse(s.interest_counter)

    def test_channel_subscriptions(self):
        s = State()
        ch = self.get_dummy_channel()
        name1 = 'testname1'
        name2 = 'testname2'
        topic1 = 'topic1'
        topic2 = 'topic2'

        self.assertEqual(set(), s.get_channel_subscriptions(ch))

        s.add_channel_subscription(ch, name1, topic1)
        self.assertSetEqual(set([(name1, topic1)]), s.get_channel_subscriptions(ch))

        s.add_channel_subscription(ch, name2, topic2)
        self.assertSetEqual(set([(name1, topic1), (name2, topic2)]), s.get_channel_subscriptions(ch))

        s.del_channel_subscription(ch, name1, topic1)
        self.assertSetEqual(set([(name2, topic2)]), s.get_channel_subscriptions(ch))

        s.del_channel_subscription(ch, name2, topic2)
        self.assertEqual(set(), s.get_channel_subscriptions(ch))

    dummy_channel_follownr = 1

    def get_dummy_channel(self):
        obj = 'DummyChannel' + str(self.dummy_channel_follownr)
        self.dummy_channel_follownr += 1

        return obj


if __name__ == '__main__':
    unittest.main()
