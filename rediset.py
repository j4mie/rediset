import redis


class Rediset(object):

    def __init__(self, key_prefix=None):
        self.connection = RedisConnection(key_prefix)

    def set(self, key):
        return Set(self.connection, key)

    def intersection(self, *items):
        return Intersection(self.connection, items)

    def union(self, *items):
        return Union(self.connection, items)


class RedisConnection(object):

    def __init__(self, key_prefix=None):
        self.redis = redis.Redis()
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


class Node(object):

    def __init__(self, connection, children):
        self.connection = connection
        self.children = children

    def cardinality(self):
        return self.connection.scard(self.key)

    def __len__(self):
        self.create()
        return self.cardinality()

    def __repr__(self):
        return "<%s.%s %s>" % (__name__, self.__class__.__name__, self.key)

    def members(self):
        self.create()
        return self.connection.smembers(self.key)

    def create_children(self):
        [child.create() for child in self.children]

    def child_keys(self):
        return sorted(child.key for child in self.children)


class Set(Node):

    def __init__(self, connection, key):
        self.key = key
        super(Set, self).__init__(connection, None)

    def add(self, *values):
        self.connection.sadd(self.key, *values)

    def create(self):
        pass


class Intersection(Node):

    @property
    def key(self):
        return "intersection(%s)" % ",".join(self.child_keys())

    def create(self):
        self.create_children()
        return self.connection.sinterstore(self.key, self.child_keys())


class Union(Node):

    @property
    def key(self):
        return "union(%s)" % ",".join(self.child_keys())

    def create(self):
        self.create_children()
        return self.connection.sunionstore(self.key, self.child_keys())
