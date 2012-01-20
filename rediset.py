import redis


class Rediset(object):

    """
    Main class responsible for creating instances of sets and operators
    """

    def __init__(self, key_prefix=None, default_cache_seconds=60, redis_client=None):
        self.redis = RedisWrapper(key_prefix, client=redis_client)
        self.default_cache_seconds = default_cache_seconds

    def Set(self, key):
        return SetNode(self.redis, key)

    def _operation(self, cls, *items, **kwargs):
        if len(items) == 1:
            item = items[0]
            if isinstance(item, basestring):
                return self.Set(item)
            else:
                return item
        cache_seconds = kwargs.get('cache_seconds') or self.default_cache_seconds
        return cls(self.redis, items, cache_seconds=cache_seconds)

    def Intersection(self, *items, **kwargs):
        return self._operation(IntersectionNode, *items, **kwargs)

    def Union(self, *items, **kwargs):
        return self._operation(UnionNode, *items, **kwargs)

    def Difference(self, *items, **kwargs):
        return self._operation(DifferenceNode, *items, **kwargs)


class RedisWrapper(object):

    """
    Simple wrapper around a Redis client instance

    Supports only the set operations we need, and automatically
    prefixes all keys with key_prefix if set.
    """

    def __init__(self, key_prefix=None, client=None):
        self.redis = client or redis.Redis()
        self.key_prefix = key_prefix

    def create_key(self, original_key):
        key = original_key
        if self.key_prefix:
            key = "%s:%s" % (self.key_prefix, key)
        return key

    def scard(self, key):
        key = self.create_key(key)
        return self.redis.scard(key)

    def sadd(self, key, *values):
        key = self.create_key(key)
        return self.redis.sadd(key, *values)

    def srem(self, key, *values):
        key = self.create_key(key)
        return self.redis.srem(key, *values)

    def smembers(self, key):
        key = self.create_key(key)
        return self.redis.smembers(key)

    def sinterstore(self, dest, keys):
        dest = self.create_key(dest)
        keys = [self.create_key(key) for key in keys]
        return self.redis.sinterstore(dest, keys)

    def sunionstore(self, dest, keys):
        dest = self.create_key(dest)
        keys = [self.create_key(key) for key in keys]
        return self.redis.sunionstore(dest, keys)

    def sdiffstore(self, dest, keys):
        dest = self.create_key(dest)
        keys = [self.create_key(key) for key in keys]
        return self.redis.sdiffstore(dest, keys)

    def sismember(self, key, item):
        key = self.create_key(key)
        return self.redis.sismember(key, item)

    def exists(self, key):
        key = self.create_key(key)
        return self.redis.exists(key)

    def expire(self, key, time):
        key = self.create_key(key)
        return self.redis.expire(key, time)


class Node(object):

    """
    Represents a node in a a tree of set operations.

    This class provides read-only operations on sets stored in
    Redis, such as cardinality and containment. It does not provide
    operations that mutate the set, because these are only supported
    by leaf nodes and not intermediate operation nodes.
    """

    def __repr__(self):
        return "<%s.%s %s>" % (__name__, self.__class__.__name__, self.key)

    def cardinality(self):
        self.create()
        return self.redis.scard(self.key)

    def __len__(self):
        return self.cardinality()

    def members(self):
        self.create()
        return self.redis.smembers(self.key)

    def __iter__(self):
        return iter(self.members())

    def contains(self, item):
        self.create()
        return self.redis.sismember(self.key, item)

    def __contains__(self, item):
        return self.contains(item)

    def create(self):
        pass


class SetNode(Node):

    """
    Represents a Redis set

    Note that this class does *not* try too hard to look like a Python
    set. For example, you cannot pass an iterable into its constructor
    to provide the members of the set. This is because a set in Redis
    may or may not already contain elements. A non-existent set in Redis
    is equivalent to an existing set with zero items. So this class should
    be thought of as an interface to an *existing* Redis set, providing
    an API to add or remove elements.
    """

    def __init__(self, redis, key):
        self.redis = redis
        self.key = key

    def add(self, *values):
        self.redis.sadd(self.key, *values)

    def remove(self, *values):
        self.redis.srem(self.key, *values)


class OperationNode(Node):

    """
    Represents a set in Redis that is the computed result of an operation

    Subclasses of this class provide operations over one or more other
    sets in Redis. The sets they operate on may be leaf nodes in the tree
    (ie instances of Set that have been created and updated directly) or
    may represent the result of another operation.
    """

    def __init__(self, redis, children, cache_seconds=None):
        self.redis = redis

        children = children or []
        processed_children = []
        for child in children:
            if isinstance(child, basestring):
                processed_children.append(SetNode(redis, child))
            else:
                processed_children.append(child)

        self.children = processed_children
        self.cache_seconds = cache_seconds

    def create_children(self):
        for child in self.children:
            child.create()

    def child_keys(self):
        return [child.key for child in self.children]

    def create(self):
        if not self.redis.exists(self.key):
            self.create_children()
            self.perform_operation()
            self.redis.expire(self.key, self.cache_seconds)


class IntersectionNode(OperationNode):

    """
    Represents the result of an intersection of one or more other sets
    """

    @property
    def key(self):
        return "intersection(%s)" % ",".join(sorted(self.child_keys()))

    def perform_operation(self):
        return self.redis.sinterstore(self.key, self.child_keys())


class UnionNode(OperationNode):

    """
    Represents the result of a union of one or more other sets
    """

    @property
    def key(self):
        return "union(%s)" % ",".join(sorted(self.child_keys()))

    def perform_operation(self):
        return self.redis.sunionstore(self.key, self.child_keys())


class DifferenceNode(OperationNode):

    """
    Represents the result of the difference between the first set
    and all the successive sets
    """

    @property
    def key(self):
        child_keys = self.child_keys()
        child_keys = child_keys[0:1] + sorted(child_keys[1:])
        return "difference(%s)" % ",".join(child_keys)

    def perform_operation(self):
        return self.redis.sdiffstore(self.key, self.child_keys())
