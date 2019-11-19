from operator import attrgetter


def get_obj_attr(obj, path, default=None, raise_exception=False):
    """
    A helper function to get attribute for a field identified by path.
    Use default and raise_exception to control desired error handling behavior.

      Ex:
        class A(pydantic.BaseModel):
          a_1: str
          a_2: Optional[str]

        class B(pydantic.BaseModel):
          b_1: str
          b_2: Optional[A]

        x = B(b_1='x')
        get_obj_attr(x, 'b_2.a_1', default='default')
        # output: 'default'

    :param obj:
    :param path:
    :param default:
    :param raise_exception:
    :return:
    """
    try:
        return attrgetter(path)(obj)
    except AttributeError as e:
        if raise_exception:
            raise e
        return default
