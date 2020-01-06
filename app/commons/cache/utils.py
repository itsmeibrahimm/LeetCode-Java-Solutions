import hashlib
import inspect

import six
from pydantic import BaseModel

from app.commons.cache.Cacheable import CacheKeyAware


def safe_unicode(value, encoding="utf-8"):
    if isinstance(value, six.text_type):
        return value
    elif isinstance(value, six.binary_type):
        try:
            value = six.text_type(value, encoding)
        except UnicodeDecodeError:
            value = value.decode("utf-8", "replace")

    return value


def compose_cache_key(key, args=None, kwargs=None, use_hash=True, is_method=True):
    """
    Turn functions args into some sort of string. It doesn't matter too much what it looks like,
    since we are going to hash it anyway, so long as it is predictable and unique.
    NOTE: using 'args' is kind of deprecated, since @cached won't use it. It might still be useful
    for other stuff though.
    """
    print("here entering  compose_cache_key")
    components = [key]

    # remove self from the args because we don't want to include it into the cache key calculation
    # we can always assume self is the first arg in the args tuple
    if is_method:
        if len(args) > 0:
            new_args = [args[idx] for idx in range(1, len(args))]
        else:
            new_args = []
        if new_args:
            args_fixed = [safe_unicode(arg) for arg in new_args]
            args_str = safe_unicode(repr(args_fixed))
            components.append(args_str)
    elif args:
        args_fixed = [safe_unicode(arg) for arg in args]
        args_str = safe_unicode(repr(args_fixed))
        print("here append " + args_str)
        components.append(args_str)

    # Note that repr() returns UTF-8 strings
    if kwargs:
        kwargs_fixed = {}
        kwargs = sorted(kwargs.items())
        for key, val in kwargs:
            if isinstance(val, CacheKeyAware):
                cache_key = val.get_cache_key()
                kwargs_fixed.update(cache_key)
            else:
                kwargs_fixed.update({key: safe_unicode(val)})
        kwargs_str = safe_unicode(repr(kwargs_fixed))
        components.append(kwargs_str)

    # This is unicode
    arg_str = "".join(components)
    print("here arg_str " + arg_str)
    if use_hash:
        # Convert to utf-8 for hashlib to work
        arg_str = arg_str.encode("utf-8")
        arg_str = hashlib.sha256(arg_str).hexdigest()

    # Return unicode again
    print("here cache key: " + safe_unicode(arg_str))
    return safe_unicode(arg_str)


def is_cacheable(data):
    return isinstance(data, str) or isinstance(data, int) or isinstance(data, BaseModel)


def is_instance_method(func):
    spec = inspect.getfullargspec(func)
    return spec.args and spec.args[0] == "self"
