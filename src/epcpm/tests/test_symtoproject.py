import pytest

import epcpm.symtoproject
import epyqlib.pm


@pytest.fixture
def access_levels():
    access_levels = epyqlib.pm.parametermodel.AccessLevels()
    user_level = epyqlib.pm.parametermodel.AccessLevel(name='User', value=0)
    factory_level = epyqlib.pm.parametermodel.AccessLevel(name='Factory', value=1)
    
    access_levels.append_child(user_level)
    access_levels.append_child(factory_level)

    return access_levels

@pytest.fixture
def variant_cfgs():
    variants = epyqlib.pm.parametermodel.Enumeration()
    enumerator_type = epyqlib.pm.parametermodel.Enumerator
    
    cfgs = ['None', 'MG3', 'MG4', 'DG', 'HY', 'DC']
    val = 0
    for cfg in cfgs:
        e = enumerator_type(name=cfg, value=val)
        variants.append_child(e)
        val=val+1

    variants = [
        variant 
        for variant in variants.children 
        if variant.name != 'None'
    ]

    return variants


def test_strip_access_level_factory(access_levels):
    comment = 'abc <factory> def'
    
    stripped, level = epcpm.symtoproject.strip_access_level(comment, access_levels)
    
    assert stripped.split() == ['abc', 'def']
    assert level == access_levels.by_name('factory')


def test_strip_access_level_normal(access_levels):
    comment = 'abc def'
    
    stripped, level = epcpm.symtoproject.strip_access_level(comment, access_levels)
    
    assert stripped == comment
    assert level == access_levels.by_name('user')


def test_strip_variant_parameter_specific(variant_cfgs):
    comment = 'abc <HY> <DG> <MG4> def'
      
    stripped, variants = epcpm.symtoproject.strip_variant_parameter_tag(comment, variant_cfgs)
    variant_names = [
        variant.name 
        for variant in variants
    ]
    assert stripped.split() == ['abc', 'def']
    assert variant_names == ['MG4', 'DG', 'HY']


def test_strip_variant_parameter_normal(variant_cfgs):
    comment = 'abc def'
      
    stripped, variants = epcpm.symtoproject.strip_variant_parameter_tag(comment, variant_cfgs)
    variant_names = [
        variant.name 
        for variant in variants
    ]
    assert stripped == comment
    assert variant_names == ['MG3', 'MG4', 'DG', 'HY', 'DC']
