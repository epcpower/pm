import itertools
import math
import os
import pathlib
import subprocess

import attr
import graham

import epcpm.cantosym
import epcpm.cantoxlsx
import epcpm.importexportdialog
import epcpm.parameterstobitfieldsc
import epcpm.parameterstohierarchy
import epcpm.parameterstointerface
import epcpm.parameterstosil
import epcpm.pm_helper
import epcpm.project
import epcpm.smdxtosunspec
import epcpm.staticmodbustoc
import epcpm.staticmodbustoxls
import epcpm.sunspecmodel
import epcpm.sunspectocsv
import epcpm.sunspectointerface
import epcpm.sunspectotablesc
import epcpm.sunspectomanualc
import epcpm.sunspectomanualh
import epcpm.sunspectoxlsx
import epcpm.symtoproject
import epyqlib.attrsmodel


def full_import(paths):
    with open(paths.can, "rb") as sym, open(paths.hierarchy) as hierarchy:
        parameters_root, can_root, sunspec_root = epcpm.symtoproject.load_can_file(
            can_file=sym,
            file_type=str(pathlib.Path(sym.name).suffix[1:]),
            parameter_hierarchy_file=hierarchy,
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
    enumerations = project.models.parameters.list_selection_roots["enumerations"]
    enumerations.append_child(sunspec_types)

    project.models.update_enumeration_roots()

    sunspec_models = []
    prefix = "smdx_"
    suffix = ".xml"
    for smdx_path in paths.smdx:
        models = epcpm.smdxtosunspec.import_models(
            int(smdx_path.name[len(prefix) : -len(suffix)]),
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

    get_set = epcpm.smdxtosunspec.import_get_set(paths.sunspec1_spreadsheet)

    for model, block, point in points:
        parameter = project.models.sunspec.node_from_uuid(
            point.parameter_uuid,
        )
        for direction in ("get", "set"):
            key = epcpm.smdxtosunspec.GetSetKey(
                model=model.id,
                name=parameter.abbreviation,
                get_set=direction,
            )
            accessor = get_set.get(key)
            if accessor is not None:
                setattr(point, direction, accessor)

    project.paths["parameters"] = "parameters.json"
    project.paths["can"] = "can.json"
    project.paths["sunspec1"] = "sunspec1.json"
    project.paths["sunspec2"] = "sunspec2.json"
    project.paths["staticmodbus"] = "staticmodbus.json"

    return project


def full_export(
    project,
    paths,
    target_directory,
    first_time=False,
    skip_output=False,
    include_uuid_in_item=False,
):
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

    epcpm.parameterstointerface.export(
        c_path=paths.interface_c,
        h_path=paths.interface_c.with_suffix(".h"),
        c_path_rejected_callback=paths.rejected_callback_c,
        can_model=project.models.can,
        sunspec1_model=project.models.sunspec1,
        sunspec2_model=project.models.sunspec2,
        staticmodbus_model=project.models.staticmodbus,
        parameters_model=project.models.parameters,
        skip_output=skip_output,
        include_uuid_in_item=include_uuid_in_item,
    )

    epcpm.sunspectocsv.export(
        path=paths.sunspec1_spreadsheet,
        sunspec_model=project.models.sunspec1,
        sunspec_id=epcpm.pm_helper.SunSpecSection.SUNSPEC_ONE,
        parameters_model=project.models.parameters,
        skip_output=skip_output,
        column_filter=attr.evolve(
            epcpm.pm_helper.attr_fill(epcpm.sunspectocsv.Fields, False),
            model_id=True,
            size=True,
            name=True,
            label=True,
            type=True,
            units=True,
            bit_offset=True,
            bit_length=True,
            modbus_address=True,
            parameter_uuid=True,
            parameter_uses_interface_item=True,
            scale_factor_uuid=True,
            enumeration_uuid=True,
            type_uuid=True,
            access_level=True,
            not_implemented=True,
            uuid=True,
            class_name=True,
        ),
    )

    epcpm.sunspectocsv.export(
        path=paths.sunspec2_spreadsheet,
        sunspec_model=project.models.sunspec2,
        sunspec_id=epcpm.pm_helper.SunSpecSection.SUNSPEC_TWO,
        parameters_model=project.models.parameters,
        skip_output=skip_output,
        column_filter=attr.evolve(
            epcpm.pm_helper.attr_fill(epcpm.sunspectocsv.Fields, False),
            model_id=True,
            size=True,
            name=True,
            label=True,
            type=True,
            units=True,
            bit_offset=True,
            bit_length=True,
            modbus_address=True,
            parameter_uuid=True,
            parameter_uses_interface_item=True,
            scale_factor_uuid=True,
            enumeration_uuid=True,
            type_uuid=True,
            access_level=True,
            not_implemented=True,
            uuid=True,
            class_name=True,
        ),
    )

    epcpm.sunspectoxlsx.export(
        path=paths.sunspec1_spreadsheet,
        sunspec_model=project.models.sunspec1,
        sunspec_id=epcpm.pm_helper.SunSpecSection.SUNSPEC_ONE,
        parameters_model=project.models.parameters,
        skip_sunspec=skip_output,
    )

    epcpm.sunspectoxlsx.export(
        path=paths.sunspec2_spreadsheet,
        sunspec_model=project.models.sunspec2,
        sunspec_id=epcpm.pm_helper.SunSpecSection.SUNSPEC_TWO,
        parameters_model=project.models.parameters,
        skip_sunspec=skip_output,
    )

    epcpm.sunspectoxlsx.export(
        path=paths.sunspec1_spreadsheet_user,
        sunspec_model=project.models.sunspec1,
        sunspec_id=epcpm.pm_helper.SunSpecSection.SUNSPEC_ONE,
        parameters_model=project.models.parameters,
        skip_sunspec=skip_output,
        column_filter=attr.evolve(
            epcpm.pm_helper.attr_fill(epcpm.sunspectoxlsx.Fields, True),
            get=False,
            set=False,
            item=False,
        ),
    )

    epcpm.sunspectoxlsx.export(
        path=paths.sunspec2_spreadsheet_user,
        sunspec_model=project.models.sunspec2,
        sunspec_id=epcpm.pm_helper.SunSpecSection.SUNSPEC_TWO,
        parameters_model=project.models.parameters,
        skip_sunspec=skip_output,
        column_filter=attr.evolve(
            epcpm.pm_helper.attr_fill(epcpm.sunspectoxlsx.Fields, True),
            get=False,
            set=False,
            item=False,
        ),
    )

    epcpm.staticmodbustoxls.export(
        path=paths.staticmodbus_spreadsheet,
        staticmodbus_model=project.models.staticmodbus,
        parameters_model=project.models.parameters,
        skip_output=skip_output,
    )

    # TODO: put this into importexportdialog.py
    tmp_path = pathlib.Path(r"C:\Projects\grid-tied_SC-835")
    tmp_embedded = tmp_path / "embedded-library"
    tmp_sunspec_path = tmp_embedded / "system" / "sunspec"
    tmp_sunspec1_interface_c = tmp_sunspec_path / "sunspec1InterfaceGen.c"
    epcpm.sunspectointerface.export(
        c_path=tmp_sunspec1_interface_c,
        h_path=tmp_sunspec1_interface_c.with_suffix(".h"),
        sunspec_model=project.models.sunspec1,
        sunspec_id=epcpm.pm_helper.SunSpecSection.SUNSPEC_ONE,
        skip_sunspec=skip_output,
    )

    # TODO: put this into importexportdialog.py
    tmp_sunspec2_interface_c = tmp_sunspec_path / "sunspec2InterfaceGen.c"
    epcpm.sunspectointerface.export(
        c_path=tmp_sunspec2_interface_c,
        h_path=tmp_sunspec2_interface_c.with_suffix(".h"),
        sunspec_model=project.models.sunspec2,
        sunspec_id=epcpm.pm_helper.SunSpecSection.SUNSPEC_TWO,
        skip_sunspec=skip_output,
    )

    epcpm.sunspectotablesc.export(
        c_path=paths.sunspec1_tables_c,
        h_path=paths.sunspec1_tables_c.with_suffix(".h"),
        sunspec_model=project.models.sunspec1,
        sunspec_id=epcpm.pm_helper.SunSpecSection.SUNSPEC_ONE,
        skip_sunspec=skip_output,
    )

    epcpm.sunspectotablesc.export(
        c_path=paths.sunspec2_tables_c,
        h_path=paths.sunspec2_tables_c.with_suffix(".h"),
        sunspec_model=project.models.sunspec2,
        sunspec_id=epcpm.pm_helper.SunSpecSection.SUNSPEC_TWO,
        skip_sunspec=skip_output,
    )

    epcpm.parameterstosil.export(
        c_path=paths.sil_c,
        h_path=paths.sil_c.with_suffix(".h"),
        parameters_model=project.models.parameters,
    )

    epcpm.staticmodbustoc.export(
        c_path=paths.staticmodbus_c,
        h_path=paths.staticmodbus_c.with_suffix(".h"),
        staticmodbus_model=project.models.staticmodbus,
        skip_output=skip_output,
    )

    epcpm.parameterstobitfieldsc.export(
        c_path=paths.bitfields_c,
        h_path=paths.bitfields_c.with_suffix(".h"),
        parameters_model=project.models.parameters,
        staticmodbus_model=project.models.staticmodbus,
        sunspec1_model=project.models.sunspec1,
        sunspec2_model=project.models.sunspec2,
        skip_output=skip_output,
    )

    if first_time and not skip_output:
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
    scripts = base_path / ".venv" / "Scripts"
    interface = base_path / "interface"

    subprocess.run(
        [
            os.fspath(scripts / "generatestripcollect"),
            os.fspath(interface / "EPC_DG_ID247_FACTORY.sym"),
            "-o",
            os.fspath(interface / "EPC_DG_ID247.sym"),
            "--hierarchy",
            os.fspath(interface / "EPC_DG_ID247_FACTORY.parameters.json"),
            "--hierarchy-out",
            os.fspath(interface / "EPC_DG_ID247.parameters.json"),
            "--device-file",
            os.fspath(interface / "devices.json"),
            "--output-directory",
            os.fspath(interface / "devices"),
        ],
        check=True,
    )

    emb_lib = base_path / "embedded-library"
    subprocess.run(
        [
            os.fspath(scripts / "sunspecparser"),
            os.fspath(emb_lib / "MODBUS_SunSpec1-EPC.xlsx"),
            str(epcpm.pm_helper.SunSpecSection.SUNSPEC_ONE.value),
        ],
        check=True,
    )

    emb_lib = base_path / "embedded-library"
    subprocess.run(
        [
            os.fspath(scripts / "sunspecparser"),
            os.fspath(emb_lib / "MODBUS_SunSpec2-EPC.xlsx"),
            str(epcpm.pm_helper.SunSpecSection.SUNSPEC_TWO.value),
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


def is_stale(project, paths, skip_sunspec=False):
    loaded_project = epcpm.project.loadp(project, post_load=False)

    source_paths = (
        project,
        *(project.parent / path for path in attr.astuple(loaded_project.paths)),
    )

    source_modification_time = max(path.stat().st_mtime for path in source_paths)

    if skip_sunspec:
        sunspec1_models = []
        sunspec2_models = []
    else:
        sunspec1_models = get_sunspec_models(
            project.parent / loaded_project.paths.sunspec1,
        )
        sunspec2_models = get_sunspec_models(
            project.parent / loaded_project.paths.sunspec2,
        )

    smdx1 = tuple(
        paths.sunspec_c / f"smdx1_{model:05}.xml" for model in sunspec1_models
    )
    smdx2 = tuple(
        paths.sunspec_c / f"smdx2_{model:05}.xml" for model in sunspec2_models
    )

    sunspec1_c_h = tuple(
        paths.sunspec_c / f"sunspec1InterfaceGen{model}.{extension}"
        for model, extension in itertools.product(sunspec1_models, ("c", "h"))
    )
    sunspec2_c_h = tuple(
        paths.sunspec_c / f"sunspec2InterfaceGen{model}.{extension}"
        for model, extension in itertools.product(sunspec2_models, ("c", "h"))
    )

    sil_c_h = (paths.sil_c, paths.sil_c.with_suffix(".h"))

    destination_paths = [
        paths.can,
        paths.hierarchy,
        *paths.smdx,
        paths.sunspec1_spreadsheet,
        paths.sunspec2_spreadsheet,
        paths.sunspec1_spreadsheet_user,
        paths.sunspec2_spreadsheet_user,
        *smdx1,
        *smdx2,
        *sunspec1_c_h,
        *sunspec2_c_h,
        paths.sunspec1_tables_c,
        paths.sunspec2_tables_c,
        *sil_c_h,
    ]

    destination_modification_time = min(
        modification_time_or(path=path, alternative=-math.inf)
        for path in destination_paths
    )

    destination_newer_by = destination_modification_time - source_modification_time

    return destination_newer_by < 1


def generate_docs(
    project: epcpm.project.Project,
    paths: epcpm.importexportdialog.ImportPaths,
    pmvs_path: pathlib.Path,
    generate_formatted_output: bool,
) -> None:
    """
    Generate the CAN model parameter data documentation.

    Args:
        project: PM project (pmp)
        paths: import/export dialog paths
        pmvs_path: PMVS output path
        generate_formatted_output: generate formatted output (takes a long time)

    Returns:

    """
    epcpm.cantoxlsx.export(
        path=paths.spreadsheet_can,
        can_model=project.models.can,
        pmvs_path=pmvs_path,
    )

    if generate_formatted_output:
        epcpm.cantoxlsx.format_for_manual(
            input_path=paths.spreadsheet_can,
        )
