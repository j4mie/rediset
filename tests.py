from unittest import TestCase
from mock import Mock
from time import sleep
from rediset import Rediset, RedisConnection, Set, Intersection, Union


class KeyGenerationTestCase(TestCase):

    def test_key_generation(self):
        rc = RedisConnection(key_prefix='some-prefix')
        key = rc.create_key('foo')
        self.assertEqual(key, 'some-prefix:foo')


class RedisTestCase(TestCase):

    PREFIX = 'rediset-tests'

    def setUp(self):
        self.rediset = Rediset(key_prefix=self.PREFIX)
        self.rediset.connection = Mock(wraps=self.rediset.connection)

    def tearDown(self):
        redis = self.rediset.connection.redis
        keys = redis.keys('%s*' % self.PREFIX)
        if keys:
            redis.delete(*keys)


class SetTestCase(RedisTestCase):

    def test_basic_set(self):
        s = self.rediset.set('key')

        s.add('a')
        s.add('b')
        s.add('c')

        self.assertEqual(len(s), 3)
        self.assertEqual(s.members(), set(['a', 'b', 'c']))
        self.assertTrue(s.contains('a'))
        self.assertFalse(s.contains('d'))

        s.remove('a')
        self.assertFalse(s.contains('a'))
        s.remove('b', 'c')
        self.assertEqual(len(s), 0)


class IntersectionTestCase(RedisTestCase):

    def test_basic_intersection(self):
        s1 = self.rediset.set('key1')
        s2 = self.rediset.set('key2')

        s1.add('a', 'b')
        s2.add('b', 'c')

        i = self.rediset.intersection(s1, s2)
        self.assertEqual(len(i),1)
        self.assertEqual(i.members(), set(['b']))

    def test_intersection_tree(self):
        s1 = self.rediset.set('key1')
        s2 = self.rediset.set('key2')
        s3 = self.rediset.set('key3')

        s1.add('a', 'b', 'c')
        s2.add('b', 'c', 'd')
        s3.add('b', 'z', 'x')

        i1 = self.rediset.intersection(s1, s2)
        self.assertEqual(len(i1), 2)

        i2 = self.rediset.intersection(i1, s3)
        self.assertEqual(len(i2), 1)
        self.assertEqual(i2.members(), set(['b']))


class UnionTestCase(RedisTestCase):

    def test_basic_union(self):
        s1 = self.rediset.set('key1')
        s2 = self.rediset.set('key2')

        s1.add('a', 'b')
        s2.add('b', 'c')

        u = self.rediset.union(s1, s2)
        self.assertEqual(len(u), 3)
        self.assertEqual(u.members(), set(['a', 'b', 'c']))

    def test_union_tree(self):
        s1 = self.rediset.set('key1')
        s2 = self.rediset.set('key2')
        s3 = self.rediset.set('key3')

        s1.add('a', 'b', 'c')
        s2.add('b', 'c', 'd')
        s3.add('b', 'z', 'x')

        i1 = self.rediset.union(s1, s2)
        self.assertEqual(len(i1), 4)

        i2 = self.rediset.union(i1, s3)
        self.assertEqual(len(i2), 6)
        self.assertEqual(i2.members(), set(['a', 'b', 'c', 'd', 'z', 'x']))


class ShortcutTestCase(RedisTestCase):

    def test_string_shortcuts(self):
        s1 = self.rediset.set('key1')
        s2 = self.rediset.set('key2')

        s1.add('a', 'b')
        s2.add('b', 'c')

        intersection = self.rediset.intersection('key1', s2)

        for child in intersection.children:
            self.assertTrue(isinstance(child, Set))

        self.assertEqual(len(intersection), 1)

    def test_single_item(self):
        s1 = self.rediset.set('key1')
        s1.add('a', 'b')
        intersection = self.rediset.intersection(s1)
        self.assertTrue(isinstance(intersection, Set))

        intersection = self.rediset.intersection('key1')
        self.assertTrue(isinstance(intersection, Set))

        s2 = self.rediset.set('key2')
        s2.add('b', 'c')
        intersection = self.rediset.intersection(s1, s2)
        union = self.rediset.union(intersection)
        self.assertTrue(isinstance(union, Intersection))


class CombinationTestCase(RedisTestCase):

    def test_complex_tree(self):
        s1 = self.rediset.set('key1')
        s2 = self.rediset.set('key2')
        s3 = self.rediset.set('key3')
        s4 = self.rediset.set('key4')
        s5 = self.rediset.set('key5')

        s1.add('a', 'b')
        s2.add('b', 'c')
        s3.add('b', 'd')
        s4.add('e', 'f')
        s5.add('b', 'z')

        result = self.rediset.union(
            self.rediset.intersection(
                s1,
                s2,
                s3
            ),
            s4,
            s5
        )

        self.assertEqual(len(result), 4)
        self.assertEqual(result.members(), set(['b', 'e', 'f', 'z']))


class ConversionTestCase(RedisTestCase):

    def test_iterable(self):
        s1 = self.rediset.set('key1')
        s1.add('a', 'b', 'c')
        self.assertEqual(set(s1), set(['a', 'b', 'c']))

    def test_contains(self):
        s1 = self.rediset.set('key1')
        s1.add('a', 'b', 'c')
        self.assertTrue('a' in s1)
        self.rediset.connection.sismember.assert_called_with('key1', 'a')
        self.assertFalse('x' in s1)
        self.rediset.connection.sismember.assert_called_with('key1', 'x')


class CachingTestCase(RedisTestCase):

    def test_default_caching_and_override(self):
        self.rediset = Rediset(key_prefix=self.PREFIX, default_cache_seconds=10)
        s1 = self.rediset.set('key1')
        s2 = self.rediset.set('key2')

        intersection = self.rediset.intersection(s1, s2)
        self.assertEqual(intersection.cache_seconds, 10)

        intersection = self.rediset.intersection(s1, s2, cache_seconds=5)
        self.assertEqual(intersection.cache_seconds, 5)

    def test_caching(self):
        s1 = self.rediset.set('key1')
        s2 = self.rediset.set('key2')

        s1.add('a', 'b')
        s2.add('b', 'c')

        intersection = self.rediset.intersection(s1, s2, cache_seconds=1)

        len(intersection)
        len(intersection)

        self.assertEqual(intersection.connection.sinterstore.call_count, 1)

        sleep(2)

        len(intersection)

        self.assertEqual(intersection.connection.sinterstore.call_count, 2)
