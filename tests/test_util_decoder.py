#!/usr/bin/env python3

import unittest

from nervixd.util.decoder import BaseDecoder

class TestState(unittest.TestCase):

    def test_add_chunk_single(self):
        
        e = BaseDecoder()
        
        e.add_chunk(b'123456789')
        
        self.assertEqual(
            e.get(4),
            b'1234'
        )
        
        self.assertEqual(
            e.get(4, 4),
            b'5678'
        )
        
        self.assertEqual(
            e.get(9),
            b'123456789'
        )
  
    def test_get_to_much(self):
        
        e = BaseDecoder()
        
        e.add_chunk(b'123456789')
        
        self.assertEqual(
            e.get(10),
            None
        )
        
        self.assertEqual(
            e.get(5, 5),
            None
        )
        
    def test_add_multiple(self):
        
        e = BaseDecoder()
        
        e.add_chunk(b'abcdefg')
        e.add_chunk(b'hijklmn')
        
        self.assertEqual(
            e.get(5),
            b'abcde'
        )
        
        self.assertEqual(
            e.get(5, 5),
            b'fghij'
        )
        
        self.assertEqual(
            e.get(4, 10),
            b'klmn'
        )
        
    def test_commit(self):
        
        e = BaseDecoder()
        
        e.add_chunk(b'abcdefg')
        e.add_chunk(b'hijklmn')
        
        self.assertEqual(
            e.get(5),
            b'abcde'
        )
        
        e.commit(5)
        
        self.assertEqual(
            e.get(5),
            b'fghij'
        )
        
        e.commit(5)
        
        self.assertEqual(
            e.get(4),
            b'klmn'
        )
        
        e.commit(4)
        
        self.assertEqual(
            e.get(1),
            None
        )
        
    def test_get_until(self):
        
        e = BaseDecoder()
        
        e.add_chunk(b'abcdefg')
        e.add_chunk(b'hijklmn')
        
        self.assertEqual(
            e.get_until(b'de', 1024),
            b'abcde'
        )
        
        self.assertEqual(
            e.get_until(b'gh', 1024),
            b'abcdefgh'
        )
        
        self.assertEqual(
            e.get_until(b'gh', 1024, 3),
            b'defgh'
        )
        
        with self.assertRaises(IndexError):
            e.get_until(b'de', 5)
        
        self.assertEqual(
            e.get_until(b'mno', 1024),
            None
        )
        
    def test_autocommit_get(self):
        
        e = BaseDecoder()
        
        e.add_chunk(b'abcdefg')
        e.add_chunk(b'hijklmn')
        
        self.assertEqual(
            e.get(4),
            b'abcd'
        )
        
        e.commit()
        
        self.assertEqual(
            e.get(4),
            b'efgh'
        )
        
        e.commit(2)
        
        self.assertEqual(
            e.get(2),
            b'gh'
        )
        
        e.commit()
        
        self.assertEqual(
            e.get(4),
            b'ijkl'
        )
        
    def test_autocommit_get_until(self):
        
        e = BaseDecoder()
        
        e.add_chunk(b'abcdefg')
        e.add_chunk(b'hijklmn')
        
        self.assertEqual(
            e.get_until(b'cd', 1024),
            b'abcd'
        )
        
        e.commit()
        
        self.assertEqual(
            e.get_until(b'gh', 1024),
            b'efgh'
        )
        
        e.commit(2)
        
        self.assertEqual(
            e.get_until(b'gh', 1024),
            b'gh'
        )
        
        e.commit()
        
        self.assertEqual(
            e.get(4),
            b'ijkl'
        )
    
    def test_read_from_socket(self):
        
        e = BaseDecoder()
        s = DummySocket()
        
        s.prepare(b'abcdefghijklmn')
        
        n = e.read_from_socket(s, 5)
        
        self.assertEqual(n, 5)
        
        self.assertEqual(
            e.get(5),
            b'abcde'
        )
        
        e.commit()
        
        n = e.read_from_socket(s)
        
        self.assertEqual(n, 9)
        
        self.assertEqual(
            e.get(9),
            b'fghijklmn'
        )

class DummySocket:
    
    def __init__(self):
        self.buff = bytearray()
        
    def prepare(self, data):
        self.buff.extend(data)
    
    def recv(self, maxlen):
        
        chunk = self.buff[0:maxlen]
        
        del self.buff[0:maxlen]
        
        return chunk



    
    
if __name__ == '__main__':
    unittest.main()
