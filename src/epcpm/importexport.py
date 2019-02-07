import itertools
import math
import os
import pathlib
import subprocess

import attr
import graham

import epcpm.cantosym
import epcpm.cantotablesc
import epcpm.parameterstohierarchy
import epcpm.project
import epcpm.smdxtosunspec
import epcpm.sunspecmodel
import epcpm.sunspecmodel
import epcpm.sunspectotablesc
import epcpm.sunspectomanualc
import epcpm.sunspectomanualh
import epcpm.sunspectoxlsx
import epcpm.symtoproject
import epyqlib.attrsmodel


def full_import(paths):
    with open(paths.can, 'rb') as sym, open(paths.hierarchy) as hierarchy:
        parameters_root, can_root, sunspec_root = (
            epcpm.symtoproject.load_can_file(
                can_file=sym,
                file_type=str(pathlib.Path(sym.name).suffix[1:]),
                parameter_hierarchy_file=hierarchy,
            )
        )

    project = epcpm.project.Project()

    project.models.parameters = epyqlib.attrsmodel.Model(
        root=parameters_root,
        columns=epyqlib.pm.parametermodel.columns,
    )
    project.models.can = epyqlib.attrsmodel.Model(
        root=can_root,
        columns=epcpm.canmodel.columns,
    )
    project.models.sunspec = epyqlib.attrsmodel.Model(
        root=sunspec_root,
        columns=epcpm.sunspecmodel.columns,
    )

    epcpm.project._post_load(project)

    # TODO: backmatching
    epcpm.symtoproject.go_add_tables(
        parameters_root=project.models.parameters.root,
        can_root=project.models.can.root,
    )

    sunspec_types = epcpm.sunspecmodel.build_sunspec_types_enumeration()
    enumerations = (
        project.models.parameters.list_selection_roots['enumerations']
    )
    enumerations.append_child(sunspec_types)

    project.models.update_enumeration_roots()

    sunspec_models = []
    prefix = 'smdx_'
    suffix = '.xml'
    for smdx_path in paths.smdx:
        models = epcpm.smdxtosunspec.import_models(
            int(smdx_path.name[len(prefix):-len(suffix)]),
            parameter_model=project.models.parameters,
            paths=[smdx_path.parent],
        )
        sunspec_models.extend(models)

    for sunspec_model in sunspec_models:
        project.models.sunspec.root.append_child(sunspec_model)

    points = (
        (model, block, point)
        for model in project.models.sunspec.root.children
        for block in model.children
        for point in block.children
    )

    get_set = epcpm.smdxtosunspec.import_get_set(paths.spreadsheet)

    for model, block, point in points:
        parameter = project.models.sunspec.node_from_uuid(
            point.parameter_uuid,
        )
        for direction in ('get', 'set'):
            key = epcpm.smdxtosunspec.GetSetKey(
                model=model.id,
                name=parameter.abbreviation,
                get_set=direction,
            )
            accessor = get_set.get(key)
            if accessor is not None:
                setattr(point, direction, accessor)

    project.paths['parameters'] = 'parameters.json'
    project.paths['can'] = 'can.json'
    project.paths['sunspec'] = 'sunspec.json'

    return project


def full_export(project, paths, target_directory, first_time=False):
    epcpm.cantosym.export(
        path=paths.can,
        can_model=project.models.can,
        parameters_model=project.models.parameters,
    )

    epcpm.parameterstohierarchy.export(
        path=paths.hierarchy,
        can_model=project.models.can,
        parameters_model=project.models.parameters,
    )

    epcpm.sunspectoxlsx.export(
        path=paths.spreadsheet,
        sunspec_model=project.models.sunspec,
        parameters_model=project.models.parameters,
    )

    epcpm.cantotablesc.export(
        path=paths.tables_c,
        can_model=project.models.can,
    )

    epcpm.sunspectotablesc.export(
        c_path=paths.sunspec_tables_c,
        h_path=paths.sunspec_tables_c.with_suffix('.h'),
        sunspec_model=project.models.sunspec,
    )

    if first_time:
        epcpm.sunspectomanualc.export(
            path=paths.sunspec_c,
            sunspec_model=project.models.sunspec,
        )

        epcpm.sunspectomanualh.export(
            path=paths.sunspec_c,
            sunspec_model=project.models.sunspec,
        )

    run_generation_scripts(target_directory)


def run_generation_scripts(base_path):
    scripts = base_path/'venv'/'Scripts'
    interface = base_path/'interface'

    subprocess.run(
        [
            os.fspath(scripts/'generatestripcollect'),
            os.fspath(interface/'EPC_DG_ID247_FACTORY.sym'),
            '-o',
            os.fspath(interface/'EPC_DG_ID247.sym'),
            '--hierarchy',
            os.fspath(interface/'EPC_DG_ID247_FACTORY.parameters.json'),
            '--hierarchy-out',
            os.fspath(interface/'EPC_DG_ID247.parameters.json'),
            '--device-file',
            os.fspath(interface/'devices.json'),
            '--output-directory',
            os.fspath(interface/'devices'),
        ],
        check=True,
    )

    emb_lib = base_path/'embedded-library'
    subprocess.run(
        [
            os.fspath(scripts/'sunspecparser'),
            os.fspath(emb_lib/'MODBUS_SunSpec-EPC.xlsx'),
        ],
        check=True,
    )


def modification_time_or(path, alternative):
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return alternative


def get_sunspec_models(path):
    root_schema = graham.schema(epcpm.sunspecmodel.Root)
    raw = path.read_bytes()
    root = root_schema.loads(raw).data

    return tuple(
        child.id
        for child in root.children
        if isinstance(child, epcpm.sunspecmodel.Model)
    )


def is_stale(project, paths):
    loaded_project = epcpm.project.loadp(project, post_load=False)

    source_paths = (
        project,
        *(
            project.parent / path
            for path in attr.astuple(loaded_project.paths)
        ),
    )

    source_modification_time = max(
        path.stat().st_mtime
        for path in source_paths
    )

    sunspec_models = get_sunspec_models(
        project.parent / loaded_project.paths.sunspec,
    )

    smdx = tuple(
        paths.sunspec_c/f'smdx_{model:05}.xml'
        for model in sunspec_models
    )

    sunspec_c_h = tuple(
        paths.sunspec_c/f'sunspecInterfaceGen{model}.{extension}'
        for model, extension in itertools.product(sunspec_models, ('c', 'h'))
    )

    destination_paths = [
        paths.can,
        paths.hierarchy,
        *paths.smdx,
        paths.spreadsheet,
        *smdx,
        *sunspec_c_h,
        paths.tables_c,
    ]

    destination_modification_time = min(
        modification_time_or(path=path, alternative=-math.inf)
        for path in destination_paths
    )

    destination_newer_by = (
            destination_modification_time - source_modification_time
    )

    return destination_newer_by < 1
