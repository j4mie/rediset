# Set operations

Rediset's main purpose is to perform operations on sets, and then compose the
results. The operations that Rediset provides are *Union*, *Intersection* and
*Difference*. See the [Redis documentation](http://redis.io/commands#set) for
full details on the semantics of these operations.

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

Simple so far. But what if we wanted to know everyone who has been in either
Nirvana *and* the Foo Fighters, **or** Blur *and* Gorillaz? We need to create
a Union of the two Intersections:

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

You can nest these operations as deeply as you like (see below for details).

## Notes on operations

You can't mutate an operation (Union, Intersection or Difference) directly:

    >>> u = rs.Union(rs.Set('key1'), rs.Set('bar'))
    >>> u.add('a')
    Traceback (most recent call last):
      File "<input>", line 1, in <module>
    AttributeError: 'UnionNode' object has no attribute 'add'

As a shortcut, if you pass a bare string to any of the operation functions, they
will assume this is the name of a key and wrap a `Set` around it. So these three
versions are equivalent:

    >>> result = rs.Union(rs.Set('key1'), rs.Set('key2'))
    >>> result = rs.Union(rs.Set('key1'), 'key2')
    >>> result = rs.Union('key1', 'key2')

Rediset also supports an optional "Python-set-like" interface for operations between sets
(and other operations):

    >>> s1 = rs.Set('key1')
    >>> s2 = rs.Set('key2')
    >>> s3 = rs.Set('key3')
    >>> i = s1.intersection(s2, s3)
    >>> u = s1.union(s2, s3)
    >>> d = s1.difference(s2, s3)

## How does it work?

Set operations are performed using the `SUNIONSTORE`, `SINTERSTORE` and
`SDIFFSTORE` commands provided by Redis. The result of an operation on
multiple sets is stored in another set in Redis, under a key generated
by Rediset.
