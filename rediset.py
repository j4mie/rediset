import redis


class Rediset(object):

    def __init__(self, key_prefix=None, default_cache_seconds=60):
        self.connection = RedisConnection(key_prefix)
        self.default_cache_seconds = default_cache_seconds

    def set(self, key):
        return Set(self.connection, key)

    def _operation(self, cls, *items, **kwargs):
        if len(items) == 1:
            item = items[0]
            if isinstance(item, basestring):
                return self.set(item)
            else:
                return item
        cache_seconds = kwargs.get('cache_seconds') or self.default_cache_seconds
        return cls(self.connection, items, cache_seconds=cache_seconds)

    def intersection(self, *items, **kwargs):
        return self._operation(Intersection, *items, **kwargs)

    def union(self, *items, **kwargs):
        return self._operation(Union, *items, **kwargs)


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

    def __init__(self, connection, children, cache_seconds=None):
        self.connection = connection

        children = children or []
        processed_children = []
        for child in children:
            if isinstance(child, basestring):
                processed_children.append(Set(connection, child))
            else:
                processed_children.append(child)

        self.children = processed_children
        self.cache_seconds = cache_seconds

    def cardinality(self):
        self.create()
        return self.connection.scard(self.key)

    def __len__(self):
        return self.cardinality()

    def __repr__(self):
        return "<%s.%s %s>" % (__name__, self.__class__.__name__, self.key)

    def members(self):
        self.create()
        return self.connection.smembers(self.key)

    def __iter__(self):
        return iter(self.members())

    def contains(self, item):
        self.create()
        return self.connection.sismember(self.key, item)

    def __contains__(self, item):
        return self.contains(item)

    def create_children(self):
        [child.create() for child in self.children]

    def child_keys(self):
        return sorted(child.key for child in self.children)

    def create(self):
        if not self.connection.exists(self.key):
            self.create_children()
            self.really_create()
            self.connection.expire(self.key, self.cache_seconds)


class Set(Node):

    def __init__(self, connection, key):
        self.key = key
        super(Set, self).__init__(connection, None)

    def add(self, *values):
        self.connection.sadd(self.key, *values)

    def remove(self, *values):
        self.connection.srem(self.key, *values)

    def create(self):
        pass


class Intersection(Node):

    @property
    def key(self):
        return "intersection(%s)" % ",".join(self.child_keys())

    def really_create(self):
        return self.connection.sinterstore(self.key, self.child_keys())


class Union(Node):

    @property
    def key(self):
        return "union(%s)" % ",".join(self.child_keys())

    def really_create(self):
        return self.connection.sunionstore(self.key, self.child_keys())
