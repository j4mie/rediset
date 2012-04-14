from .base import Node, OperationNode


class SortedNode(Node):

    """
    Represents a node in a tree of sorted sets and sorted set operations
    """

    class RangeView(object):

        """
        Instances of this class are used to access ranges of a sorted
        set. This is so we can easily support Pythonic slicing, while
        passing arguments to the underlying zrange calls. This approach
        was borrowed from github.com/ask/redish/
        """

        def __init__(self, proxied, **overrides):
            self.proxied = proxied
            self.overrides = overrides or {}

        def range(self, *args, **kwargs):
            """
            Get a range of items from the sorted set. See redis-py docs for details
            """
            self.proxied.create()

            for key, value in self.overrides.items():
                kwargs.setdefault(key, value)

            return self.proxied.rs.redis.zrange(self.proxied.prefixed_key, *args, **kwargs)

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
                if arg.stop == 0:
                    return []
                if arg.stop is None:
                    end = -1
                else:
                    end = arg.stop - 1
                return self.range(start, end)
            else:
                results = self.get(arg)
                if results is None:
                    raise IndexError('list index out of range')
                return results

        def members(self, *args, **kwargs):
            return self.range(start=0, end=-1, *args, **kwargs)

        def __getattr__(self, attr):
            return getattr(self.proxied, attr)

        def __len__(self):
            return len(self.proxied)

        def __contains__(self, item):
            return item in self.proxied

        def __iter__(self):
            return iter(self.members())

        @property
        def withscores(self):
            self.overrides['withscores'] = True
            return self

        @property
        def descending(self):
            self.overrides['desc'] = True
            return self

    def range_view(self, **overrides):
        return SortedNode.RangeView(self, **overrides)

    def cardinality(self):
        self.create()
        return self.rs.redis.zcard(self.prefixed_key)

    def members(self, *args, **kwargs):
        return self.range_view().members(*args, **kwargs)

    def contains(self, item):
        """
        There is no "zismember" so we use zscore
        """
        return self.score(item) is not None

    def range(self, *args, **kwargs):
        return self.range_view().range(*args, **kwargs)

    def get(self, index, *args, **kwargs):
        return self.range_view().get(index, *args, **kwargs)

    def __getitem__(self, arg):
        return self.range_view().__getitem__(arg)

    def score(self, item):
        """
        Get the score for the given sorted set member
        """
        self.create()
        return self.rs.redis.zscore(self.prefixed_key, item)

    def rank(self, item, reverse=False):
        """
        Get the score for the given sorted set member
        """
        self.create()
        if reverse:
            return self.rs.redis.zrevrank(self.prefixed_key, item)
        else:
            return self.rs.redis.zrank(self.prefixed_key, item)

    @property
    def withscores(self):
        return self.range_view().withscores

    @property
    def descending(self):
        return self.range_view().descending


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


class SortedOperationNode(OperationNode, SortedNode):

    """
    Represents a set in Redis that is the computed result of an operation
    on sorted sets
    """

    def __init__(self, *args, **kwargs):
        self.aggregate = kwargs.pop('aggregate', 'SUM')
        self.weights = kwargs.pop('weights',None)
        super(SortedOperationNode, self).__init__(*args, **kwargs)

    def extra_key_components(self):
        """
        Return a key component based on the variable options passed
        to this operation, such as aggregate
        """
        return "aggregate=%s&weights=%s" % (self.aggregate, self.weights)
    
    def weighted_child_keys(self):
        if self.weights:
            return dict(zip(self.prefixed_child_keys(), self.weights))
        else:
            return self.prefixed_child_keys()


class SortedIntersectionNode(SortedOperationNode):

    """
    Represents the result of an intersection of one or more sorted sets
    """

    @property
    def key(self):
        return "sortedintersection(%s)(%s)" % (
            ",".join(sorted(self.weighted_child_keys())),
            self.extra_key_components(),
        )

    def perform_operation(self):
        return self.rs.redis.zinterstore(self.prefixed_key, self.weighted_child_keys(),
                                              aggregate=self.aggregate)


class SortedUnionNode(SortedOperationNode):

    """
    Represents the result of a union of one or more sorted sets
    """

    @property
    def key(self):
        return "sortedunion(%s)(%s)" % (
            ",".join(sorted(self.weighted_child_keys())),
            self.extra_key_components(),
        )

    def perform_operation(self):
        return self.rs.redis.zunionstore(self.prefixed_key, self.weighted_child_keys(),
                                              aggregate=self.aggregate)


class SortedDifferenceNode(SortedOperationNode):

    """
    Represents the result of the difference between the first sorted
    set and all the successive sorted sets

    THIS OPERATION IS NOT SUPPORTED BY REDIS
    """

    def __new__(cls, *args, **kwargs):
        raise TypeError("Difference operation not supported for sorted sets")
