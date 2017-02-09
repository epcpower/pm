import attr

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


@attr.s
class Parameter:
    name = attr.ib()
    minimum = attr.ib(default=None)
    maximum = attr.ib(default=None)


@attr.s
class Group:
    name = attr.ib()
    children = attr.ib(default=attr.Factory(list), metadata={'ignore': True})
