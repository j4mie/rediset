# rediset

**Composable, cachable, lazy trees of Redis set operations**

**Author:** Jamie Matthews. [Follow me on Twitter](http://twitter.com/j4mie).

## Changelog

#### 0.1.0

* Initial release. Very experimental.

## Installation

You can install Rediset from PyPI:

    pip install rediset

## Overview

Rediset is an abstraction of Redis sets and set operations.

## API

All objects are created through an instance of the `Rediset` class.

```python
>>> from rediset import Rediset
>>> rs = Rediset()
```

You can optionally provide a `key_prefix` argument to the constructor,
which will be prepended to all keys Rediset generates. This is useful for
namespacing your data in Redis.

```python
>>> from rediset import Rediset
>>> rs = Rediset(key_prefix='myprefix')
```

If you need to customise things further, you can override the Redis client
instance Rediset uses:

```python
>>> from rediset import Rediset
>>> from redis import Redis
>>> r = Redis(host='localhost', port=6379, db=0)
>>> rs = Rediset(key_prefix='myprefix', redis_client=r)
```

### Sets

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

```python
>>> from rediset import Rediset
>>> rs = Rediset()
>>> s = rs.Set('somekey')
```

Note that you can't pass an initial iterable of items when instantiating a new
Set (like you can for native Python sets). This is because the set *might
already exist* in Redis. You are instantiating a *wrapper* around a Redis
set containing zero or more elements.

You can add and remove items from the set:

```python
>>> s.add('a', 'b', 'c')
>>> s.remove('b')
```

You can get its size, check if an item is in the set, and get all of its
members by converting it to a native Python set (or by iterating over it):

```python
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
```

All of these operations are performed in Redis:

```python
>>> s.add('b')     # "SADD" "somekey" "b"
>>> len(s)         # "SCARD" "somekey"
>>> 'a' in s       # "SISMEMBER" "somekey" "a"
>>> set(s)         # "SMEMBERS" "somekey"
```

### Set operations

Rediset's main purpose is to perform operations on sets, and then compose the
results. The operations that Rediset provides are *Union*, *Intersection* and
*Difference*. See the [Redis documentation](http://redis.io/commands#set) for
full details on the semantics of these operations.

```python
>>> rs = Rediset()
>>>
>>> nirvana = rs.Set('nirvana')
>>> nirvana.add('kurt', 'krist', 'dave')
>>>
>>> foo_fighters = rs.Set('foo_fighters')
>>> foo_fighters.add('dave', 'nate', 'taylor', 'chris', 'pat')
>>>
>>> nirvana_and_ff = rs.Intersection(nirvana, foo_fighters)
>>> set(nirvana_and_ff)
set(['dave'])
```

Simple so far. But what if we wanted to know everyone who has been in either
Nirvana *and* the Foo Fighters, **or** Blur *and* Gorillaz? We need to create
a Union of the two Intersections:

```python
>>> blur = rs.Set('blur')
>>> blur.add('damon', 'graham', 'alex', 'dave')
>>>
>>> gorillaz = rs.Set('gorillaz')
>>> gorillaz.add('damon', 'jamie')
>>>
>>> result = rs.Union(
...     rs.Intersection(nirvana, foo_fighters),
...     rs.Intersection(blur, gorillaz)
... )
>>> set(result)
set(['dave', 'damon'])
```

You can nest these operations as deeply as you like (see below for details).

#### Notes on operations

You can't mutate an operation (Union, Intersection or Difference) directly:

```python
>>> u = rs.Union(rs.Set('key1'), rs.Set('bar'))
>>> u.add('a')
Traceback (most recent call last):
  File "<input>", line 1, in <module>
AttributeError: 'UnionNode' object has no attribute 'add'
```

As a shortcut, if you pass a bare string to any of the operation functions, they
will assume this is the name of a key and wrap a `Set` around it. So these three
versions are equivalent:

```python
>>> result = rs.Union(rs.Set('key1'), rs.Set('key2'))
>>> result = rs.Union(rs.Set('key1'), 'key2')
>>> result = rs.Union('key1', 'key2')
```

## How does it work?

Set operations are performed using the `SUNIONSTORE`, `SINTERSTORE` and
`SDIFFSTORE` commands provided by Redis. The result of an operation on
multiple sets is stored in another set in Redis, under a key generated
by Rediset.

### Caching

These generated keys are *volatile* - they are set to `EXPIRE` after some
number of seconds. The result sets can be thought of as *caches*. Every time
you attempt to perform an operation, Rediset will first check whether the key
representing the result already exists. If it does, it won't bother actually
asking Redis to perform the operation.

Rediset provides very fine-grained control over caching. The top-level
`Rediset` class accepts a `default_cache_seconds` constructor argument, whose
value is used for all of the objects it produces. If this argument is not
supplied, it defaults to 60 seconds:

```python
>>> rs = Rediset()
>>> u1 = rs.Union('key1', 'key2')
>>> u1.cache_seconds
60
>>> rs = Rediset(default_cache_seconds=600)
>>> u2 = rs.Union('key1', 'key2')
>>> u2.cache_seconds
600
```

You can also override this default cache timeout by passing the `cache_seconds`
argument to any of the operation functions.

```python
>>> rs = Rediset(default_cache_seconds=600)
>>> u3 = rs.Union('key1', 'key2', cache_seconds=6000)
>>> u3.cache_seconds
6000
```

### Laziness

When you create a tree of operations with Rediset, *nothing happens*. The
operations are only performed in Redis when you actually attempt to inspect
the contents of the result set - by calling `len(result)` or `'foo' in
result` for example.

Rediset starts to shine when you need to manipulate trees of sets and
operations:

```python
result = rs.Union(
    rs.Intersection(
        rs.Difference(
            rs.Set('key1'),
            rs.Set('key2')
        ),
        rs.Set('key3')
    ),
    rs.Difference(
        rs.Intersection(
            rs.Union(
                rs.Difference(
                    rs.Set('key4'),
                    rs.Intersection(
                        rs.Set('key5'),
                        rs.Set('key6'),
                        rs.Set('key7')
                    )
                ),
                rs.Set('key8'),
                rs.Set('key9')
            ),
            rs.Set('key10'),
        ),
        rs.Union(
            rs.Set('key11'),
            rs.Set('key12')
        ),
        rs.Set('key13')
    )
)
```

At this stage, *zero* calls to Redis have been made. When you ask for some
information about the result (eg `len(result)`), Rediset walks the tree,
performing each operation in turn. If it reaches a node representing an
operation whose result is already cached, it stops walking down and moves on
to the next branch.

The combination of caching and lazy evaluation means you can carefully decide
exactly how long to cache particular *parts* of your operations tree for.
Imagine you have one big subtree that performs a large number of complex
operations on data that change very rarely. You can set a long cache timeout
for this branch, meaning that Redis will only need to perform the operations
occasionally. You can then create a Union of this branch with a single Set (or
perhaps a smaller tree) containing data that changes more rapidly, and give it
a shorter cache timeout. This means you can easily avoid most of the work
involved in generating your data, but still keep the final result nice and
fresh.

## What is it good for?

* A nice way of working with persisent sets in Python
* High-speed statistics
* Faceted search
* Inverted indexes
* ...any other suggestions?

## FAQ

### Why doesn't the API look more like Python's built-in set type?

Python's `set` API is based around performing operations *between* sets:

```python
>>> set(['a', 'b', 'c']).intersection(set(['a', 'b']))
```

This doesn't quite feel right when working with Redis, which works in terms
of *operations* performed on *multiple sets*. It felt more natural to treat
the operations themselves as first-class citizens, as well as the sets.

If you disagree, probably wouldn't be too hard to move the API closer to that
of built-in sets. Feel free to open a pull request!

### Urgh, why do those methods start with capital letters?

Just pretend you're instantiating a class instead of calling a method. If you
really hate the way it looks, start your program like this:

```python
from rediset import Rediset

rs = Rediset()
Set, Union, Intersection, Difference = rs.Set, rs.Union, rs.Intersection, rs.Difference

result = Union(Set('key1'), Intersection('key2', 'key3'))
```

## Development

To contribute: fork the repository, make your changes, add some tests, commit,
push to a feature branch, and open a pull request.

### How to run the tests

Rediset is tested with [nose](http://nose.readthedocs.org). Clone the repository,
create a virtualenv, then run `pip install -r requirements.txt`. Then, simply type
`nosetests` to find and run all the tests.

## (Un)license

This is free and unencumbered software released into the public domain.

Anyone is free to copy, modify, publish, use, compile, sell, or distribute this
software, either in source code form or as a compiled binary, for any purpose,
commercial or non-commercial, and by any means.

In jurisdictions that recognize copyright laws, the author or authors of this
software dedicate any and all copyright interest in the software to the public
domain. We make this dedication for the benefit of the public at large and to
the detriment of our heirs and successors. We intend this dedication to be an
overt act of relinquishment in perpetuity of all present and future rights to
this software under copyright law.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

For more information, please refer to <http://unlicense.org/>
