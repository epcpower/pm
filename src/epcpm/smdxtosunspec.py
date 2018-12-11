import contextlib
import os

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


def import_model(model_id, parameter_model, paths=()):
    model = sunspec.core.device.Model(mid=model_id)
    if len(paths) == 0:
        model.load()
    else:
        with fresh_smdx_path(*paths):
            model.load()

    points = []
    scale_factors = {}

    for name, point in model.points_sf.items():
        epc_point = epc_point_from_pysunspec_point(
            point=point,
            parameter_model=parameter_model,
        )
        scale_factors[name] = epc_point

    for point in model.points_list:
        epc_point = epc_point_from_pysunspec_point(
            point=point,
            parameter_model=parameter_model,
            scale_factors=scale_factors,
        )

        points.append(epc_point)

    our_model = epcpm.sunspecmodel.Model(
        id=model.id,
        length=model.len,
    )

    id_point = our_model.children[0].children[0]
    id_point.id = model.model_type.id
    id_point.description = model.model_type.description
    id_point.label = model.model_type.label
    id_point.notes = model.model_type.notes

    imported_points = sorted(
        points + list(scale_factors.values()),
        key=lambda point: point.block_offset,
    )

    for point in imported_points:
        our_model.children[1].append_child(point)

    return our_model
