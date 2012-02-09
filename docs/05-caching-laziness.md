# Caching & laziness

## Caching

These generated keys are *volatile* - they are set to `EXPIRE` after some
number of seconds. The result sets can be thought of as *caches*. Every time
you attempt to perform an operation, Rediset will first check whether the key
representing the cached result already exists. If it does, it won't bother
actually asking Redis to perform the operation.

Rediset provides very fine-grained control over caching. The top-level
`Rediset` class accepts a `default_cache_seconds` constructor argument, whose
value is used for all of the objects it produces. If this argument is not
supplied, it defaults to 60 seconds:

    >>> rs = Rediset()
    >>> u1 = rs.Union('key1', 'key2')
    >>> u1.cache_seconds
    60
    >>> rs = Rediset(default_cache_seconds=600)
    >>> u2 = rs.Union('key1', 'key2')
    >>> u2.cache_seconds
    600

You can also override this default cache timeout by passing the `cache_seconds`
argument to any of the operation functions.

    >>> rs = Rediset(default_cache_seconds=600)
    >>> u3 = rs.Union('key1', 'key2', cache_seconds=6000)
    >>> u3.cache_seconds
    6000

## Laziness

When you create a tree of operations with Rediset, *nothing happens*. The
operations are only performed in Redis when you actually attempt to inspect
the contents of the result set - by calling `len(result)` or `'foo' in
result` for example.

Rediset starts to shine when you need to manipulate trees of sets and
operations:

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

At this stage, *zero* calls to Redis have been made. When you ask for some
information about the result (eg `len(result)`), Rediset walks the tree,
performing each operation in turn. If it reaches a node representing an
operation whose result is already cached, it stops walking down and moves on
to the next branch.

## Benefits

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