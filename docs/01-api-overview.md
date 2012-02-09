# API Overview

All objects are created through an instance of the `Rediset` class.

    >>> from rediset import Rediset
    >>> rs = Rediset()

You can optionally provide a `key_prefix` argument to the constructor,
which will be prepended to all keys Rediset generates. This is useful for
namespacing your data in Redis.

    >>> from rediset import Rediset
    >>> rs = Rediset(key_prefix='myprefix')

If you need to customise things further, you can override the Redis client
instance Rediset uses:

    >>> from rediset import Rediset
    >>> from redis import Redis
    >>> r = Redis(host='localhost', port=6379, db=0)
    >>> rs = Rediset(key_prefix='myprefix', redis_client=r)
