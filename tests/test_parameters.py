import pm.parameters

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


def test_default_ranges():
    p = pm.parameters.Parameter(name='default_min_max')
    assert p.minimum is None
    assert p.maximum is None
