# Sorted Sets

Rediset can also manipulate *sorted* sets.

> Redis Sorted Sets are, similarly to Redis Sets, non repeating collections
> of Strings. The difference is that every member of a Sorted Set is associated
> with score, that is used in order to take the sorted set ordered, from the
> smallest to the greatest score. While members are unique, scores may be
> repeated.

The basic interface is very similar to the `Set` API:

    >>> from rediset import Rediset
    >>> rs = Rediset()
    >>> s = rs.SortedSet('somekey')

Members of a sorted set are represented as 2-tuples of `(element, score)`:

    >>> s.add(('a', 1))
    >>> s.add(('b', 2), ('c', 3))
    >>> s.remove('b')

Like unsorted sets, you can perform Pythonic operations on sorted sets:

    >>> len(s)
    2
    >>> 'a' in s
    True
    >>> 'b' in s
    False
    >>> set(s)
    set(['a', 'c'])
    >>>
    >>> [item for item in s]
    ['a', 'c']
    >>> item[0]
    ['a']

Sorted sets have some extra useful methods. These map closely to the equivalent
functions in redis-py, so please look at its documentation for more information.

    >>> s.range(0, 1)
    ['a', 'c']
    >>> s.members() # equivalent to s.range(0, -1)
    ['a', 'c']
    >>> s.members(desc=True)
    ['c', 'a']
    >>> s.members(withscores=True)
    [('a', 1.0), ('c', 3.0)]
    >>> s.members(withscores=True, score_cast_func=int)
    [('a', 1), ('c', 3)]

## Sorted set operations

You can perform operations on sorted sets, just as you can with ordinary sets.
Note that only `Intersection` and `Union` are supported, not `Difference` (this
is because these are the only sorted set operations supported by Redis).

    >>> s1 = rs.SortedSet('key1')
    >>> s1.add(('a', 1), ('b', 2))
    >>> s2 = rs.SortedSet('key2')
    >>> s2.add(('b', 3), ('c', 4))
    >>> i = rs.Intersection(s1, s2)
    >>> i.members()
    ['b']
    >>> i.members(withscores=True) # default aggregation is SUM
    [('b', 5.0)]
    >>> i2 = rs.Intersection(s1, s2, aggregate='MAX') # custom aggregation
    >>> i2.members(withscores=True)
    [('b', 3.0)]
    >>> i3 = rs.Intersection(s1, s2, aggregate='MIN') # custom aggregation
    >>> i3.members(withscores=True)
    [('b', 2.0)]
