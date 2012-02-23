import hashlib
import redis


class Rediset(object):

    """
    Main class responsible for creating instances of sets and operators
    """

    # All volatile keys produced by Rediset will be prefixed with this string
    GENERATED_KEY_PREFIX = 'rediset'

    # All cache keys will be prefixed with this string
    CACHE_KEY_PREFIX = 'cached'

    def __init__(self, key_prefix=None, default_cache_seconds=60, redis_client=None, hash_generated_keys=False):
        self.key_prefix = key_prefix
        self.hash_generated_keys = hash_generated_keys
        self.redis = redis_client or redis.Redis()
        self.default_cache_seconds = default_cache_seconds

    def hash_key(self, key):
        return hashlib.md5(key).hexdigest()

    def create_key(self, original_key, generated=False, is_cache_key=False):
        key = original_key

        if generated and self.hash_generated_keys:
            key = self.hash_key(key)

        if is_cache_key:
            key = "%s:%s" % (self.CACHE_KEY_PREFIX, key)

        if generated:
            key = "%s:%s" % (self.GENERATED_KEY_PREFIX, key)

        if self.key_prefix:
            key = "%s:%s" % (self.key_prefix, key)

        return key

    def Set(self, key):
        return SetNode(self, key)

    def SortedSet(self, key):
        return SortedSetNode(self, key)

    def _operation(self, cls, *items, **kwargs):
        if len(items) == 1:
            item = items[0]
            if isinstance(item, basestring):
                return self.Set(item)
            else:
                return item
        kwargs.setdefault('cache_seconds', self.default_cache_seconds)
        return cls(self, items, **kwargs)

    def _is_sorted(self, item):
        return isinstance(item, SortedNode)

    def _check_types(self, items):
        """
        Check all items are sorted, or all items are unsorted (not mixed)
        """
        first_is_sorted = self._is_sorted(items[0])
        for item in items:
            item_is_sorted = self._is_sorted(item)
            if first_is_sorted != item_is_sorted:
                raise TypeError('Sets and SortedSets cannot be mixed')

    def Intersection(self, *items, **kwargs):
        self._check_types(items)
        if self._is_sorted(items[0]):
            return self._operation(SortedIntersectionNode, *items, **kwargs)
        else:
            return self._operation(IntersectionNode, *items, **kwargs)

    def Union(self, *items, **kwargs):
        self._check_types(items)
        if self._is_sorted(items[0]):
            return self._operation(SortedUnionNode, *items, **kwargs)
        else:
            return self._operation(UnionNode, *items, **kwargs)

    def Difference(self, *items, **kwargs):
        self._check_types(items)
        if self._is_sorted(items[0]):
            return self._operation(SortedDifferenceNode, *items, **kwargs)
        else:
            return self._operation(DifferenceNode, *items, **kwargs)


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
        return self.rs.redis.scard(self.prefixed_key)

    def __len__(self):
        return self.cardinality()

    def members(self):
        self.create()
        return self.rs.redis.smembers(self.prefixed_key)

    def __iter__(self):
        return iter(self.members())

    def contains(self, item):
        self.create()
        return self.rs.redis.sismember(self.prefixed_key, item)

    def __contains__(self, item):
        return self.contains(item)

    def intersection(self, *others, **kwargs):
        sets = (self,) + others
        return self.rs.Intersection(*sets, **kwargs)

    def union(self, *others, **kwargs):
        sets = (self,) + others
        return self.rs.Union(*sets, **kwargs)

    def difference(self, *others, **kwargs):
        sets = (self,) + others
        return self.rs.Difference(*sets, **kwargs)

    def create(self):
        pass

    @property
    def prefixed_key(self):
        return self.rs.create_key(self.key)


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

    def __init__(self, rediset, key):
        self.rs = rediset
        self.key = key

    def add(self, *values):
        self.rs.redis.sadd(self.prefixed_key, *values)

    def remove(self, *values):
        self.rs.redis.srem(self.prefixed_key, *values)


class SortedNode(Node):

    """
    Represents a node in a tree of sorted sets and sorted set operations
    """

    def cardinality(self):
        self.create()
        return self.rs.redis.zcard(self.prefixed_key)

    def members(self, *args, **kwargs):
        return self.range(start=0, end=-1, *args, **kwargs)

    def contains(self, item):
        """
        There is no "zismember" so we use zscore
        """
        return self.score(item) is not None

    def range(self, *args, **kwargs):
        """
        Get a range of items from the sorted set. See redis-py docs for details
        """
        self.create()
        return self.rs.redis.zrange(self.prefixed_key, *args, **kwargs)

    def get(self, index, *args, **kwargs):
        """
        Get a single item from the set by index. Equivalent to s[3] but
        returns None if the index is out of range.
        """
        result = self.range(start=index, end=index, *args, **kwargs)
        if result:
            return result[0]

    def __getitem__(self, arg):
        if isinstance(arg, slice):
            start = arg.start or 0
            end = arg.stop or -1
            return self.range(start, end)
        else:
            results = self.get(arg)
            if results is None:
                raise IndexError('list index out of range')
            return results[0]

    def score(self, item):
        """
        Get the score for the given sorted set member
        """
        self.create()
        return self.rs.redis.zscore(self.prefixed_key, item)


class SortedSetNode(SortedNode):

    """
    Represents a Redis sorted set
    """

    def __init__(self, rediset, key):
        self.rs = rediset
        self.key = key

    def add(self, *values):
        values = dict(values)
        self.rs.redis.zadd(self.prefixed_key, **values)

    def remove(self, *values):
        self.rs.redis.zrem(self.prefixed_key, *values)

    def increment(self, item, amount=1):
        return self.rs.redis.zincrby(self.prefixed_key, item, amount)

    def decrement(self, item, amount=1):
        return self.increment(item, amount=amount * -1)

    def remrangebyrank(self, min, max):
        return self.rs.redis.zremrangebyrank(self.prefixed_key, min, max)

    def remrangebyscore(self, min, max):
        return self.rs.redis.zremrangebyscore(self.prefixed_key, min, max)


class OperationNode(Node):

    """
    Represents a set in Redis that is the computed result of an operation

    Subclasses of this class provide operations over one or more other
    sets in Redis. The sets they operate on may be leaf nodes in the tree
    (ie instances of Set that have been created and updated directly) or
    may represent the result of another operation.
    """

    def __init__(self, rediset, children, cache_seconds=None):
        self.rs = rediset

        children = children or []
        processed_children = []
        for child in children:
            if isinstance(child, basestring):
                processed_children.append(SetNode(rediset, child))
            else:
                processed_children.append(child)

        self.children = processed_children
        self.cache_seconds = cache_seconds

    @property
    def prefixed_key(self):
        """
        Operation keys (those generated automatically by Rediset) should
        all have a common prefix, to distinguish them from user-specified
        keys representing sets or sorted sets
        """
        return self.rs.create_key(self.key, generated=True)

    @property
    def prefixed_cache_key(self):
        return self.rs.create_key(self.key, generated=True, is_cache_key=True)

    def setup_cache(self):
        pipe = self.rs.redis.pipeline()
        pipe.setex(self.prefixed_cache_key, self.cache_seconds, 1)
        pipe.expire(self.prefixed_key, self.cache_seconds)
        pipe.execute()

    def create_children(self):
        for child in self.children:
            child.create()

    def child_keys(self):
        return [child.key for child in self.children]

    def prefixed_child_keys(self):
        results = []
        for child in self.children:
            key = child.key
            if isinstance(child, OperationNode):
                key = self.rs.create_key(key, generated=True)
            else:
                key = self.rs.create_key(key)
            results.append(key)
        return results

    def create(self):
        if not self.rs.redis.exists(self.prefixed_cache_key):
            self.create_children()
            self.perform_operation()
            self.setup_cache()


class IntersectionNode(OperationNode):

    """
    Represents the result of an intersection of one or more other sets
    """

    @property
    def key(self):
        return "intersection(%s)" % ",".join(sorted(self.child_keys()))

    def perform_operation(self):
        return self.rs.redis.sinterstore(self.prefixed_key, self.prefixed_child_keys())


class UnionNode(OperationNode):

    """
    Represents the result of a union of one or more other sets
    """

    @property
    def key(self):
        return "union(%s)" % ",".join(sorted(self.child_keys()))

    def perform_operation(self):
        return self.rs.redis.sunionstore(self.prefixed_key, self.prefixed_child_keys())


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
        return self.rs.redis.sdiffstore(self.prefixed_key, self.prefixed_child_keys())


class SortedOperationNode(OperationNode, SortedNode):

    """
    Represents a set in Redis that is the computed result of an operation
    on sorted sets
    """

    def __init__(self, *args, **kwargs):
        self.aggregate = kwargs.pop('aggregate', 'SUM')
        super(SortedOperationNode, self).__init__(*args, **kwargs)

    def extra_key_components(self):
        """
        Return a key component based on the variable options passed
        to this operation, such as aggregate
        """
        return "aggregate=%s" % self.aggregate


class SortedIntersectionNode(SortedOperationNode):

    """
    Represents the result of an intersection of one or more sorted sets
    """

    @property
    def key(self):
        return "sortedintersection(%s)(%s)" % (
            ",".join(sorted(self.child_keys())),
            self.extra_key_components(),
        )

    def perform_operation(self):
        return self.rs.redis.zinterstore(self.prefixed_key, self.prefixed_child_keys(),
                                              aggregate=self.aggregate)


class SortedUnionNode(SortedOperationNode):

    """
    Represents the result of a union of one or more sorted sets
    """

    @property
    def key(self):
        return "sortedunion(%s)(%s)" % (
            ",".join(sorted(self.child_keys())),
            self.extra_key_components(),
        )

    def perform_operation(self):
        return self.rs.redis.zunionstore(self.prefixed_key, self.prefixed_child_keys(),
                                              aggregate=self.aggregate)


class SortedDifferenceNode(SortedOperationNode):

    """
    Represents the result of the difference between the first sorted
    set and all the successive sorted sets

    THIS OPERATION IS NOT SUPPORTED BY REDIS
    """

    def __new__(cls, *args, **kwargs):
        raise TypeError("Difference operation not supported for sorted sets")
