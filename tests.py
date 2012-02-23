from unittest import TestCase
from mock import Mock
from time import sleep
from rediset import (
    Rediset,
    SetNode,
    IntersectionNode,
    SortedIntersectionNode,
    SortedUnionNode,
)


class KeyGenerationTestCase(TestCase):

    def test_key_generation(self):
        rs = Rediset(key_prefix='some-prefix')
        key = rs.create_key('foo')
        self.assertEqual(key, 'some-prefix:foo')

    def test_key_hashing(self):

        # hashing disabled
        rs = Rediset(hash_generated_keys=False)
        key = rs.create_key('foo')
        self.assertEqual(key, 'foo')
        key = rs.create_key('foo', generated=True)
        self.assertEqual(key, 'rediset:foo')

        # hashing enabled
        rs = Rediset(hash_generated_keys=True)
        key = rs.create_key('foo')
        self.assertEqual(key, 'foo')
        key = rs.create_key('foo', generated=True)
        self.assertEqual(key, 'rediset:acbd18db4cc2f85cedef654fccc4a4d8')


class RedisTestCase(TestCase):

    PREFIX = 'rediset-tests'

    def setUp(self):
        self.rediset = Rediset(key_prefix=self.PREFIX)
        self.rediset.redis = Mock(wraps=self.rediset.redis)

    def tearDown(self):
        redis = self.rediset.redis
        keys = redis.keys('%s*' % self.PREFIX)
        if keys:
            redis.delete(*keys)


class HashingTestCase(RedisTestCase):

    def setUp(self):
        super(HashingTestCase, self).setUp()
        self.rediset.hash_generated_keys = True

    def test_sets_are_not_hashed(self):
        s = self.rediset.Set('key')
        self.assertEqual(s.key, 'key')
        self.assertEqual(s.prefixed_key, 'rediset-tests:key')

    def test_operations_are_hashed(self):
        i = self.rediset.Intersection('key1', 'key2')
        self.assertEqual(i.key, 'intersection(key1,key2)')
        self.assertEqual(i.prefixed_key, 'rediset-tests:rediset:e98e8da811c3c5597e0d48f47010bf91')
        self.assertEqual(i.prefixed_cache_key, 'rediset-tests:rediset:cached:e98e8da811c3c5597e0d48f47010bf91')

class SetTestCase(RedisTestCase):

    def test_basic_set(self):
        s = self.rediset.Set('key')

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


class SortedSetTestCase(RedisTestCase):

    def test_basic_sorted_set(self):
        s = self.rediset.SortedSet('key')

        s.add(('a', 1))
        s.add(('b', 2), ('c', 3))

        self.assertEqual(len(s), 3)
        self.assertEqual(s.members(), ['a', 'b', 'c'])
        self.assertEqual(set(s), set(['a', 'b', 'c']))
        self.assertTrue('a' in s)
        self.assertFalse('d' in s)

        s.remove('a')
        self.assertFalse(s.contains('a'))
        s.remove('b', 'c')
        self.assertEqual(len(s), 0)

    def test_get_members(self):
        s = self.rediset.SortedSet('key')
        s.add(('a', 1), ('b', 2), ('c', 3))
        self.assertEqual(s.members(), ['a', 'b', 'c'])
        self.assertEqual(s.members(withscores=True), [('a', 1), ('b', 2), ('c', 3)])

    def test_get_item(self):
        s = self.rediset.SortedSet('key')
        s.add(('a', 1), ('b', 2), ('c', 3))

        self.assertEqual(s.get(0), 'a')
        self.assertEqual(s.get(2), 'c')
        self.assertTrue(s.get(3) is None)
        self.assertEqual(s.get(0, withscores=True), ('a', 1.0))

        self.assertEqual(s[0], 'a')
        self.assertEqual(s[2], 'c')
        with self.assertRaises(IndexError):
            s[3]

    def test_get_range(self):
        s = self.rediset.SortedSet('key')
        s.add(('a', 1), ('b', 2), ('c', 3))

        self.assertEqual(s.range(0, 1), ['a', 'b'])
        self.assertEqual(s.range(1, 2), ['b', 'c'])
        self.assertEqual(s.range(2, 10), ['c'])

        self.assertEqual(s.range(0, 2, withscores=True), [('a', 1), ('b', 2), ('c', 3)])

        self.assertEqual(s[0:1], ['a', 'b'])

        self.assertEqual(s[1:], ['b', 'c'])
        self.assertEqual(s[:1], ['a', 'b'])
        self.assertEqual(s[0:10], ['a', 'b', 'c'])

    def test_big_slice(self):
        s = self.rediset.SortedSet('key')
        for counter in range(100):
            s.add((str(counter), counter))

        middle = s[25:74]
        self.assertEqual(len(middle), 50)

        for item in middle:
            pass

        self.assertEqual(self.rediset.redis.zrange.call_count, 1)

    def test_iteration(self):
        s = self.rediset.SortedSet('key')
        s.add(('a', 1), ('b', 2), ('c', 3))

        results = [item for item in s]
        self.assertEqual(results, ['a', 'b', 'c'])

        self.assertEqual(self.rediset.redis.zrange.call_count, 1)

    def test_get_score(self):
        s = self.rediset.SortedSet('key')
        s.add(('a', 1), ('b', 2))
        self.assertEqual(s.score('a'), 1)
        self.assertEqual(s.score('b'), 2)
        self.assertTrue(s.score('notmember') is None)

    def test_increment_and_decrement(self):
        s = self.rediset.SortedSet('key')
        s.add(('a', 1))

        s.increment('a')
        self.assertEqual(s.score('a'), 2)

        s.increment('a', 3)
        self.assertEqual(s.score('a'), 5)

        s.increment('b')
        self.assertEqual(s.score('b'), 1)

        s.decrement('a')
        self.assertEqual(s.score('a'), 4)

        s.decrement('a', amount=2)
        self.assertEqual(s.score('a'), 2)

        result = s.increment('a')
        self.assertEqual(result, 3)

    def test_remrangebyrank(self):
        s = self.rediset.SortedSet('key')
        s.add(('a', 1), ('b', 2), ('c', 3), ('d', 4), ('e', 5), ('f', 6), ('g', 7))

        s.remrangebyrank(0, 1)
        self.assertEqual(s.members(), ['c', 'd', 'e', 'f', 'g'])

        s.remrangebyrank(0, -3)
        self.assertEqual(s.members(), ['f', 'g'])

    def test_remrangebyrank(self):
        s = self.rediset.SortedSet('key')
        s.add(('a', 1), ('b', 2), ('c', 3), ('d', 4), ('e', 5), ('f', 6), ('g', 7))

        s.remrangebyscore(3, 5)
        self.assertEqual(s.members(), ['a', 'b', 'f', 'g'])

        s.remrangebyscore('(6', 'inf')
        self.assertEqual(s.members(), ['a', 'b', 'f'])


class SortedSetOperationTestCase(RedisTestCase):

    def test_sorted_set_intersection(self):
        s1 = self.rediset.SortedSet('key1')
        s2 = self.rediset.SortedSet('key2')

        i = self.rediset.Intersection(s1, s2)
        self.assertTrue(isinstance(i, SortedIntersectionNode))

    def test_sorted_set_union(self):
        s1 = self.rediset.SortedSet('key1')
        s2 = self.rediset.SortedSet('key2')

        u = self.rediset.Union(s1, s2)
        self.assertTrue(isinstance(u, SortedUnionNode))

    def test_sorted_set_difference(self):
        s1 = self.rediset.SortedSet('key1')
        s2 = self.rediset.SortedSet('key2')

        with self.assertRaises(TypeError):
            d = self.rediset.Difference(s1, s2)

    def test_mixing_types(self):
        s1 = self.rediset.Set('key1')
        s1.add('a', 'b')
        s2 = self.rediset.SortedSet('key2')
        s2.add(('a', 1))

        with self.assertRaises(TypeError):
            i = self.rediset.Intersection(s1, s2)

        with self.assertRaises(TypeError):
            u = self.rediset.Union(s1, s2)

        with self.assertRaises(TypeError):
            d = self.rediset.Difference(s1, s2)


class IntersectionTestCase(RedisTestCase):

    def test_basic_intersection(self):
        s1 = self.rediset.Set('key1')
        s2 = self.rediset.Set('key2')

        s1.add('a', 'b')
        s2.add('b', 'c')

        i = self.rediset.Intersection(s1, s2)
        self.assertEqual(len(i), 1)
        self.assertEqual(i.members(), set(['b']))

        i2 = s1.intersection(s2)
        self.assertEqual(i.members(), i2.members())

    def test_intersection_tree(self):
        s1 = self.rediset.Set('key1')
        s2 = self.rediset.Set('key2')
        s3 = self.rediset.Set('key3')

        s1.add('a', 'b', 'c')
        s2.add('b', 'c', 'd')
        s3.add('b', 'z', 'x')

        i1 = self.rediset.Intersection(s1, s2)
        self.assertEqual(len(i1), 2)

        i2 = self.rediset.Intersection(i1, s3)
        self.assertEqual(len(i2), 1)
        self.assertEqual(i2.members(), set(['b']))

    def test_key_generation(self):
        i1 = self.rediset.Intersection('a', 'b', 'c')
        i2 = self.rediset.Intersection('c', 'b', 'a')
        i3 = self.rediset.Intersection('b' ,'c', 'a')
        self.assertTrue(i1.key == i2.key == i3.key)

    def test_sorted_set_intersection(self):
        s1 = self.rediset.SortedSet('key1')
        s2 = self.rediset.SortedSet('key2')

        s1.add(('a', 2), ('b', 2))
        s2.add(('b', 1), ('c', 2))

        i = self.rediset.Intersection(s1, s2)
        self.assertEqual(len(i), 1)
        self.assertEqual(i.members(), ['b'])

        i2 = s1.intersection(s2)
        self.assertEqual(i.members(), i2.members())

        i3 = self.rediset.Intersection(s1, s2, aggregate='SUM')
        self.assertEqual(i3.members(withscores=True), [('b', 3)])

        i4 = self.rediset.Intersection(s1, s2, aggregate='MAX')
        self.assertEqual(i4.members(withscores=True), [('b', 2)])

        i5 = self.rediset.Intersection(s1, s2, aggregate='MIN')
        self.assertEqual(i5.members(withscores=True), [('b', 1)])


class UnionTestCase(RedisTestCase):

    def test_basic_union(self):
        s1 = self.rediset.Set('key1')
        s2 = self.rediset.Set('key2')

        s1.add('a', 'b')
        s2.add('b', 'c')

        u = self.rediset.Union(s1, s2)
        self.assertEqual(len(u), 3)
        self.assertEqual(u.members(), set(['a', 'b', 'c']))

        u2 = s1.union(s2)
        self.assertEqual(u.members(), u2.members())

    def test_union_tree(self):
        s1 = self.rediset.Set('key1')
        s2 = self.rediset.Set('key2')
        s3 = self.rediset.Set('key3')

        s1.add('a', 'b', 'c')
        s2.add('b', 'c', 'd')
        s3.add('b', 'z', 'x')

        i1 = self.rediset.Union(s1, s2)
        self.assertEqual(len(i1), 4)

        i2 = self.rediset.Union(i1, s3)
        self.assertEqual(len(i2), 6)
        self.assertEqual(i2.members(), set(['a', 'b', 'c', 'd', 'z', 'x']))

    def test_key_generation(self):
        i1 = self.rediset.Union('a', 'b', 'c')
        i2 = self.rediset.Union('c', 'b', 'a')
        i3 = self.rediset.Union('b' ,'c', 'a')
        self.assertTrue(i1.key == i2.key == i3.key)

    def test_sorted_set_union(self):
        s1 = self.rediset.SortedSet('key1')
        s2 = self.rediset.SortedSet('key2')

        s1.add(('a', 1), ('b', 2))
        s2.add(('b', 3), ('c', 6))

        u = self.rediset.Union(s1, s2)
        self.assertEqual(len(u), 3)
        self.assertEqual(u.members(), ['a', 'b', 'c'])

        u2 = s1.union(s2)
        self.assertEqual(u.members(), u2.members())

        u3 = self.rediset.Union(s1, s2, aggregate='SUM')
        self.assertEqual(u3.members(withscores=True), [('a', 1), ('b', 5), ('c', 6)])

        u4 = self.rediset.Union(s1, s2, aggregate='MAX')
        self.assertEqual(u4.members(withscores=True), [('a', 1), ('b', 3), ('c', 6)])

        u5 = self.rediset.Union(s1, s2, aggregate='MIN')
        self.assertEqual(u5.members(withscores=True), [('a', 1), ('b', 2), ('c', 6)])


class DifferenceTestCase(RedisTestCase):

    def test_basic_difference(self):
        s1 = self.rediset.Set('key1')
        s2 = self.rediset.Set('key2')
        s3 = self.rediset.Set('key3')

        s1.add('a', 'b', 'c', 'x')
        s2.add('b')
        s3.add('c', 'd')

        d = self.rediset.Difference(s1, s2, s3)
        self.assertEqual(len(d), 2)
        self.assertEqual(d.members(), set(['a', 'x']))

        d2 = s1.difference(s2, s3)
        self.assertEqual(d.members(), d2.members())

    def test_difference_tree(self):
        s1 = self.rediset.Set('key1')
        s2 = self.rediset.Set('key2')
        s3 = self.rediset.Set('key3')

        s1.add('a', 'b', 'c')
        s2.add('b', 'd', 'e')
        s3.add('c', 'z', 'x')

        d1 = self.rediset.Difference(s1, s2)
        self.assertEqual(len(d1), 2)
        self.assertEqual(d1.members(), set(['a', 'c']))

        d2 = self.rediset.Difference(d1, s3)
        self.assertEqual(len(d2), 1)
        self.assertEqual(d2.members(), set(['a']))

    def test_key_generation(self):
        d1 = self.rediset.Difference('a', 'b', 'c')
        d2 = self.rediset.Difference('a', 'c', 'b')
        d3 = self.rediset.Difference('b' ,'c', 'a')
        self.assertEqual(d1.key, d2.key)
        self.assertNotEqual(d1.key, d3.key)


class ShortcutTestCase(RedisTestCase):

    def test_string_shortcuts(self):
        s1 = self.rediset.Set('key1')
        s2 = self.rediset.Set('key2')

        s1.add('a', 'b')
        s2.add('b', 'c')

        intersection = self.rediset.Intersection('key1', s2)

        for child in intersection.children:
            self.assertTrue(isinstance(child, SetNode))

        self.assertEqual(len(intersection), 1)

    def test_single_item(self):
        s1 = self.rediset.Set('key1')
        s1.add('a', 'b')
        intersection = self.rediset.Intersection(s1)
        self.assertTrue(isinstance(intersection, SetNode))

        intersection = self.rediset.Intersection('key1')
        self.assertTrue(isinstance(intersection, SetNode))

        s2 = self.rediset.Set('key2')
        s2.add('b', 'c')
        intersection = self.rediset.Intersection(s1, s2)
        union = self.rediset.Union(intersection)
        self.assertTrue(isinstance(union, IntersectionNode))


class CombinationTestCase(RedisTestCase):

    def test_complex_tree(self):
        s1 = self.rediset.Set('key1')
        s2 = self.rediset.Set('key2')
        s3 = self.rediset.Set('key3')
        s4 = self.rediset.Set('key4')
        s5 = self.rediset.Set('key5')

        s1.add('a', 'b')
        s2.add('b', 'c')
        s3.add('b', 'd')
        s4.add('e', 'f')
        s5.add('b', 'z')

        result = self.rediset.Union(
            self.rediset.Intersection(
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
        s1 = self.rediset.Set('key1')
        s1.add('a', 'b', 'c')
        self.assertEqual(set(s1), set(['a', 'b', 'c']))

    def test_contains(self):
        s1 = self.rediset.Set('key1')
        s1.add('a', 'b', 'c')
        self.assertTrue('a' in s1)
        self.rediset.redis.sismember.assert_called_with('%s:key1' % self.PREFIX, 'a')
        self.assertFalse('x' in s1)
        self.rediset.redis.sismember.assert_called_with('%s:key1' % self.PREFIX, 'x')


class CachingTestCase(RedisTestCase):

    def test_default_caching_and_override(self):
        self.rediset = Rediset(key_prefix=self.PREFIX, default_cache_seconds=10)
        s1 = self.rediset.Set('key1')
        s2 = self.rediset.Set('key2')

        intersection = self.rediset.Intersection(s1, s2)
        self.assertEqual(intersection.cache_seconds, 10)

        intersection = self.rediset.Intersection(s1, s2, cache_seconds=5)
        self.assertEqual(intersection.cache_seconds, 5)

    def test_caching(self):
        s1 = self.rediset.Set('key1')
        s2 = self.rediset.Set('key2')

        s1.add('a', 'b')
        s2.add('b', 'c')

        intersection = self.rediset.Intersection(s1, s2, cache_seconds=1)

        len(intersection)
        len(intersection)

        self.assertEqual(intersection.rs.redis.sinterstore.call_count, 1)

        sleep(2)

        len(intersection)

        self.assertEqual(intersection.rs.redis.sinterstore.call_count, 2)

    def test_caching_empty_sets(self):
        s1 = self.rediset.Set('key1')
        s2 = self.rediset.Set('key2')

        s1.add('a', 'b')
        s2.add('c', 'd')

        intersection = self.rediset.Intersection(s1, s2, cache_seconds=1)

        len(intersection)
        len(intersection)

        self.assertEqual(intersection.rs.redis.sinterstore.call_count, 1)
