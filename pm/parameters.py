import decimal

import attr

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


def to_decimal(s):
    if s is None:
        return None

    return decimal.Decimal(s)


@attr.s
class Parameter:
    name = attr.ib()
    minimum = attr.ib(default=None, convert=to_decimal)
    maximum = attr.ib(default=None, convert=to_decimal)


@attr.s
class Group:
    name = attr.ib()
    children = attr.ib(default=attr.Factory(list), metadata={'ignore': True})
