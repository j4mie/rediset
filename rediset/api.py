import hashlib
import redis


from . import sets
from . import sortedsets


class Rediset(object):

    """
    Main class responsible for creating instances of sets and operators
    """

    # All volatile keys produced by Rediset will be prefixed with this string
    GENERATED_KEY_PREFIX = 'rediset'

    # All cache keys will be prefixed with this string
    CACHE_KEY_PREFIX = 'cached'

    def __init__(self, key_prefix=None, default_cache_seconds=60,
                 redis_client=None, hash_generated_keys=False):
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
        return sets.SetNode(self, key)

    def SortedSet(self, key):
        return sortedsets.SortedSetNode(self, key)

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
        return isinstance(item, sortedsets.SortedNode)

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
            return self._operation(sortedsets.SortedIntersectionNode,
                                   *items, **kwargs)
        else:
            return self._operation(sets.IntersectionNode,
                                   *items, **kwargs)

    def Union(self, *items, **kwargs):
        self._check_types(items)
        if self._is_sorted(items[0]):
            return self._operation(sortedsets.SortedUnionNode,
                                   *items, **kwargs)
        else:
            return self._operation(sets.UnionNode,
                                   *items, **kwargs)

    def Difference(self, *items, **kwargs):
        self._check_types(items)
        if self._is_sorted(items[0]):
            return self._operation(sortedsets.SortedDifferenceNode,
                                   *items, **kwargs)
        else:
            return self._operation(sets.DifferenceNode,
                                   *items, **kwargs)
