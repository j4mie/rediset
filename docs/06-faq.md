# FAQ

## Why not copy Python's existing set API?

Python's `set` API is based around performing operations *between* sets:

    >>> set(['a', 'b', 'c']).intersection(set(['a', 'b']))

This doesn't quite feel right when working with Redis, which works in terms
of *operations* performed on *multiple sets*. It felt more natural to treat
the operations themselves as first-class citizens, as well as the sets.

You can, optionally, use the more Python-like version of the API:

    >>> s1 = rs.Set('key1')
    >>> s2 = rs.Set('key2')
    >>> i = s1.intersection(s2)

## Urgh, why do those methods start with capital letters?

Just pretend you're instantiating a class instead of calling a method. If you
really hate the way it looks, start your program like this:

    from rediset import Rediset

    rs = Rediset()
    Set, Union, Intersection, Difference = rs.Set, rs.Union, rs.Intersection, rs.Difference

    result = Union(Set('key1'), Intersection('key2', 'key3'))
