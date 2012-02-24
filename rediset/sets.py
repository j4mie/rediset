from .base import Node, OperationNode


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
