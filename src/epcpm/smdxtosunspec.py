import collections
import contextlib
import os

import attr
import epyqlib.pm.parametermodel
import sunspec.core.device

import epcpm.sunspecmodel


def epc_point_from_pysunspec_point(point, parameter_model, scale_factors=None):
    if scale_factors is not None and point.point_type.sf is not None:
        scale_factor_uuid = scale_factors[point.point_type.sf].uuid
    else:
        scale_factor_uuid = None

    sunspec_type_uuid = point.point_type.type
    if sunspec_type_uuid is not None:
        root = parameter_model.list_selection_roots['sunspec types']
        sunspec_type_uuid = root.child_by_name(sunspec_type_uuid).uuid

    return epcpm.sunspecmodel.DataPoint(
        factor_uuid=scale_factor_uuid,
        units=point.point_type.units,
        # parameter_uuid=,
        type_uuid=sunspec_type_uuid,
        # enumeration_uuid=,
        block_offset=point.point_type.offset,
        name=point.point_type.id,
        label=point.point_type.label,
        description=point.point_type.description,
        notes=point.point_type.notes,
        size=point.point_type.len,
        # uuid=,
    )


def import_models(*model_ids, parameter_model, paths):
    return [
        import_model(model_id=id, parameter_model=parameter_model, paths=paths)
        for id in model_ids
    ]


@contextlib.contextmanager
def fresh_smdx_path(*paths):
    original_pathlist = sunspec.core.device.file_pathlist
    sunspec.core.device.file_pathlist = sunspec.core.util.PathList()

    for path in paths:
        sunspec.core.device.file_pathlist.add(os.fspath(path))

    try:
        yield sunspec.core.device.file_pathlist
    finally:
        sunspec.core.device.file_pathlist = original_pathlist


def none_to_empty_string(value):
    if value is None:
        return ''

    return value


@attr.s(frozen=True)
class Symbol:
    value = attr.ib(converter=int)
    id = attr.ib()
    label = attr.ib()
    description = attr.ib(converter=none_to_empty_string)
    notes = attr.ib(converter=none_to_empty_string)

    @classmethod
    def from_sunspec(cls, symbol):
        return cls(
            description=symbol.description,
            id=symbol.id,
            label=symbol.label,
            notes=symbol.notes,
            value=symbol.value,
        )


def import_model(model_id, parameter_model, paths=()):
    model = sunspec.core.device.Model(mid=model_id)
    if len(paths) == 0:
        model.load()
    else:
        with fresh_smdx_path(*paths):
            model.load()

    imported_points = []
    scale_factors = {}

    for name, point in model.points_sf.items():
        epc_point = epc_point_from_pysunspec_point(
            point=point,
            parameter_model=parameter_model,
        )
        scale_factors[name] = epc_point

    enumerations = collections.defaultdict(list)

    for point in model.points_list:
        epc_point = epc_point_from_pysunspec_point(
            point=point,
            parameter_model=parameter_model,
            scale_factors=scale_factors,
        )

        imported_points.append(epc_point)

        if point.point_type.type.startswith('enum'):
            enumeration = tuple(sorted(
                Symbol.from_sunspec(symbol=symbol)
                for symbol in point.point_type.symbols
            ))
            enumerations[enumeration].append(epc_point)

    enumerations_root = parameter_model.list_selection_roots['enumerations']
    for enumeration, points in enumerations.items():
        # TODO: just using the first point?  hmm
        epc_enumeration = epyqlib.pm.parametermodel.Enumeration(
            name='SunSpec{}'.format(points[0].label),
        )

        for symbol in enumeration:
            enumerator = epyqlib.pm.parametermodel.Enumerator(
                name=symbol.label,
                value=symbol.value,
            )
            epc_enumeration.append_child(enumerator)

        for point in points:
            point.enumeration_uuid = epc_enumeration.uuid

        enumerations_root.append_child(epc_enumeration)

    our_model = epcpm.sunspecmodel.Model(
        id=model.id,
        length=model.len,
    )

    types = parameter_model.list_selection_roots['sunspec types']
    our_model.children[0].add_data_points(
        uint16_uuid=types.child_by_name('uint16').uuid,
    )

    id_point = our_model.children[0].children[0]
    id_point.id = model.model_type.id
    id_point.description = model.model_type.description
    id_point.label = model.model_type.label
    id_point.notes = model.model_type.notes

    imported_points = sorted(
        imported_points + list(scale_factors.values()),
        key=lambda point: point.block_offset,
    )

    for point in imported_points:
        our_model.children[1].append_child(point)

    return our_model
