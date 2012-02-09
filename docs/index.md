<img src="http://redis.io/images/redis.png" style="display: block; margin: 30px auto;" alt="Redis logo" title="Redis logo" />

**<span style="display: block; text-align: center; margin-bottom: 20px;">Composable, cachable, lazy trees of Redis set operations.</span>**

    from rediset import Rediset
    rs = Rediset()

    result = rs.Intersection('key1', rs.Union('key2', 'key3'))

#### What is it good for?:

* High-speed statistics
* Faceted search
* Inverted indexes
* Just a nice way of working with persisent sets in Python
* ...any other suggestions?

Get the code at [GitHub](https://github.com/j4mie/rediset).

#### Installation

You can install Rediset from PyPI:

    pip install rediset
