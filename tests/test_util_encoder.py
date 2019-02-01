#!/usr/bin/env python3

import unittest

from nervixd.util.encoder import BaseEncoder

class TestState(unittest.TestCase):

    def test_add_chunk_single(self):
        
        e = BaseEncoder()
        e.add_encoded_chunk(b'123456789')
        
        self.assertEqual(
            e.fetch_chunk(),
            b'123456789'
        )
        
        e.commit(9)
        
        self.assertEqual(
            e.fetch_chunk(),
            None
        )

    def test_add_chunk_multiple_fetch(self):
        
        e = BaseEncoder()
        e.add_encoded_chunk(b'123456789')
        
        self.assertEqual(
            e.fetch_chunk(4),
            b'1234'
        )
        
        e.commit(4)
        
        self.assertEqual(
            e.fetch_chunk(4),
            b'5678'
        )
        
        e.commit(4)
        
        self.assertEqual(
            e.fetch_chunk(4),
            b'9'
        )
        
        e.commit(1)
        
        self.assertEqual(
            e.fetch_chunk(4),
            None
        )
    
    def test_add_chunk_multiple_add(self):
        
        e = BaseEncoder()
        e.add_encoded_chunk(b'1234')
        e.add_encoded_chunk(b'5678')
        
        self.assertEqual(
            e.fetch_chunk(),
            b'1234'
        )
        
        e.commit(4)
        
        self.assertEqual(
            e.fetch_chunk(),
            b'5678'
        )
        
        e.commit(4)
        
        self.assertEqual(
            e.fetch_chunk(),
            None
        )
    
    def test_empty(self):
        
        e = BaseEncoder()
        
        self.assertEqual(
            e.fetch_chunk(),
            None
        )
        
    def test_commit(self):
        
        e = BaseEncoder()
        e.add_encoded_chunk(b'123456789')
        
        self.assertEqual(
            e.fetch_chunk(4),
            b'1234'
        )
        
        e.commit(4)
        
        self.assertEqual(
            e.fetch_chunk(2),
            b'56'
        )
        
        e.commit(2)
        
        self.assertEqual(
            e.fetch_chunk(),
            b'789'
        )
        
        e.commit(3)
        
        self.assertEqual(
            e.fetch_chunk(4),
            None
        )
        
    def test_commit_2(self):
        
        e = BaseEncoder()
        e.add_encoded_chunk(b'123456789')
        
        self.assertEqual(
            e.fetch_chunk(1024),
            b'123456789'
        )
        
        e.commit(5)
        
        self.assertEqual(
            e.fetch_chunk(1024),
            b'6789'
        )
        
        
    def test_add_chunk_type_error(self):
        
        e = BaseEncoder()
        
        with self.assertRaises(TypeError):
            e.add_encoded_chunk('123456789')
        
    def test_over_commit(self):
        
        e = BaseEncoder()
        e.add_encoded_chunk(b'123456789')
        
        self.assertEqual(
            e.fetch_chunk(),
            b'123456789'
        )
        
        with self.assertRaises(ValueError):
            e.commit(10)
    
    
    def test_add_empty(self):
        
        e = BaseEncoder()
        e.add_encoded_chunk(b'')
        
        self.assertEqual(
            e.fetch_chunk(),
            b'',
        )
        
        self.assertEqual(
            e.fetch_chunk(),
            None,
        )
    
    def test_write_socket(self):
        
        s = DummySocket()
        e = BaseEncoder()
        
        e.add_encoded_chunk(b'123456789')
        
        s.prepare(5)
        n = e.write_to_socket(s)
        
        self.assertEqual(n, 5)
        
        self.assertEqual(
            s.buff,
            b'12345'
        )
        
        s.prepare(5)
        n = e.write_to_socket(s)
        
        self.assertEqual(n, 4)
        
        self.assertEqual(
            s.buff,
            b'123456789'
        )
        
        


class DummySocket:
    
    def __init__(self):
        self.buff = b''
        
    def prepare(self, amount):
        self.size = amount
    
    def send(self, data):
        chunk = data[0:self.size]
        
        self.buff += chunk
        
        return len(chunk)




    
    
if __name__ == '__main__':
    unittest.main()
