
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
                processed_children.append(self.rs.Set(child))
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
        pipe.setex(self.prefixed_cache_key, 1, self.cache_seconds)
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

