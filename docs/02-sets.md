# Sets

The basic data structure Rediset operates on is the *set*. Here's an extract
from the Redis documentation on the
[set data type](http://redis.io/topics/data-types):

> Redis Sets are an unordered collection of Strings. It is possible to add,
> remove, and test for existence of members in O(1) (constant time
> regardless of the number of elements contained inside the Set).
>
> Redis Sets have the desirable property of not allowing repeated members.
> Adding the same element multiple times will result in a set having a single
> copy of this element. Practically speaking this means that adding a member
> does not require a check if exists then add operation.
>
> A very interesting thing about Redis Sets is that they support a number of
> server side commands to compute sets starting from existing sets, so you
> can do unions, intersections, differences of sets in very short time.

Sets are instantiated as follows:

    >>> from rediset import Rediset
    >>> rs = Rediset()
    >>> s = rs.Set('somekey')

Note that you can't pass an initial iterable of items when instantiating a new
Set (like you can for native Python sets). This is because the set *might
already exist* in Redis. You are instantiating a *wrapper* around a Redis
set containing zero or more elements.

You can add and remove items from the set:

    >>> s.add('a', 'b', 'c')
    >>> s.remove('b')

You can get its size, check if an item is in the set, and get all of its
members by converting it to a native Python set (or by iterating over it):

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

All of these operations are performed in Redis:

    >>> s.add('b')     # "SADD" "somekey" "b"
    >>> len(s)         # "SCARD" "somekey"
    >>> 'a' in s       # "SISMEMBER" "somekey" "a"
    >>> set(s)         # "SMEMBERS" "somekey"
