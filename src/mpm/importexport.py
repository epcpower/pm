import itertools
import math
import os
import pathlib
import subprocess
import typing

import attr
import graham

import mpm.cantosym
import mpm.cantoxlsx
import mpm.canmodel
import mpm.importexportdialog
import mpm.parameterstobitfieldsc
import mpm.parameterstohierarchy
import mpm.parameterstointerface
import mpm.parameterstosil
import mpm.mpm_helper
import mpm.project
import mpm.smdxtosunspec
import mpm.staticmodbustoc
import mpm.staticmodbustoxls
import mpm.sunspecmodel
import mpm.sunspectocsv
import mpm.sunspectointerface
import mpm.sunspectotablesc
import mpm.sunspectomanualc
import mpm.sunspectomanualh
import mpm.sunspectoxlsx
import mpm.symtoproject
import mpm.anomaliestoc
import mpm.anomaliestoxlsx
import epyqlib.attrsmodel
import epyqlib.pm.parametermodel


def full_import(paths):
    with open(paths.can, "rb") as sym, open(paths.hierarchy) as hierarchy:
        parameters_root, can_root, sunspec_root = mpm.symtoproject.load_can_file(
            can_file=sym,
            file_type=str(pathlib.Path(sym.name).suffix[1:]),
            parameter_hierarchy_file=hierarchy,
        )

    project = mpm.project.Project()

    project.models.parameters = epyqlib.attrsmodel.Model(
        root=parameters_root,
        columns=epyqlib.pm.parametermodel.columns,
    )
    project.models.can = epyqlib.attrsmodel.Model(
        root=can_root,
        columns=mpm.canmodel.columns,
    )
    project.models.sunspec = epyqlib.attrsmodel.Model(
        root=sunspec_root,
        columns=mpm.sunspecmodel.columns,
    )

    mpm.project._post_load(project)

    # TODO: backmatching
    mpm.symtoproject.go_add_tables(
        parameters_root=project.models.parameters.root,
        can_root=project.models.can.root,
    )

    sunspec_types = mpm.sunspecmodel.build_sunspec_types_enumeration()
    enumerations = project.models.parameters.list_selection_roots["enumerations"]
    enumerations.append_child(sunspec_types)

    project.models.update_enumeration_roots()

    sunspec_models = []
    prefix = "smdx_"
    suffix = ".xml"
    for smdx_path in paths.smdx:
        models = mpm.smdxtosunspec.import_models(
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

    get_set = mpm.smdxtosunspec.import_get_set(paths.sunspec1_spreadsheet)

    for model, block, point in points:
        parameter = project.models.sunspec.node_from_uuid(
            point.parameter_uuid,
        )
        for direction in ("get", "set"):
            key = mpm.smdxtosunspec.GetSetKey(
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
    project.paths["anomalies"] = "anomalies.json"

    return project


def merge_can_models(dest, src):
    """
    Merges CAN root node src into dest.

    Args:
        dest: Destination CAN root node
        src: Source CAN root node
    Returns:
        None
    """
    for src_child in src.children:
        if src_child.name == "ParameterQuery":

            # Find destination ParameterQuery
            dest_param_query = None
            for c in dest.children:
                if c.name == "ParameterQuery":
                    dest_param_query = c
                    break

            # Append Multiplexers from source under it
            # Shift identifiers and add "BCU_" prefix to avoid conflicts
            for c in src_child.children:
                if isinstance(c, mpm.canmodel.Multiplexer):
                    c.name = "BCU_" + c.name
                    c.identifier += 1500
                    dest_param_query.append_child(c)

        # Add everything else except ParameterResponse with a "BCU_" prefix
        # One ParameterResponse definition is enough as it is a clone of ParameterQuery
        elif src_child.name != "ParameterResponse":
            dest.append_child(src_child)
            dest.children[-1].name = "BCU_" + dest.children[-1].name


def merge_parameter_models(dest, src):
    """
    Merges parameter root node src into dest.

    Args:
        dest: Destination parameter root node
        src: Source parameter root node
    Returns:
        None
    """
    for src_child in src.children:
        if src_child.name == "Parameters" or src_child.name == "Enumerations":
            for dest_child in dest.children:
                # BCU parameters are added under the Parameter group as a subgroup
                if dest_child.name == src_child.name == "Parameters":
                    dest_child.append_child(src_child)
                    dest_child.children[-1].name = "BCU_" + dest_child.children[-1].name
                # Enumerations are merged under the same group
                if dest_child.name == src_child.name == "Enumerations":
                    for enum in src_child.children:
                        dest_child.append_child(enum)
                    break
        else:
            # Others are added under Root as subgroups
            dest.append_child(src_child)
            dest.children[-1].name = "BCU_" + dest.children[-1].name


def can_hierarchy_export(
    project,
    bcu_project,
    paths,
) -> None:
    """
    Exports parameter hierarchy and CAN symbol files
    """

    # If BCU project is included, add its contents to CAN and Parameter models
    if bcu_project:

        # Before merging BCU and TCU models, export the TCU sym file without BCU parameters
        no_bcu_symfile = paths.can.with_name(
            paths.can.stem + "_NO_BCU" + paths.can.suffix
        )
        mpm.cantosym.export(
            path=no_bcu_symfile,
            can_model=project.models.can,
            parameters_model=project.models.parameters,
        )

        # Merge BCU parameters and CAN definitions into TCU models
        merge_parameter_models(
            project.models.parameters.root, bcu_project.models.parameters.root
        )
        merge_can_models(project.models.can.root, bcu_project.models.can.root)

    # Use extended models with BCU parameter info when exporing sym and
    # parameter hierarchies
    mpm.cantosym.export(
        path=paths.can,
        can_model=project.models.can,
        parameters_model=project.models.parameters,
    )

    mpm.parameterstohierarchy.export(
        path=paths.hierarchy,
        can_model=project.models.can,
        parameters_model=project.models.parameters,
    )


def interface_code_export(
    project,
    paths,
    skip_output=False,
    include_uuid_in_item=False,
):
    """
    Exports interface code
    """

    mpm.parameterstointerface.export(
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

    mpm.parameterstosil.export(
        c_path=paths.sil_c,
        h_path=paths.sil_c.with_suffix(".h"),
        parameters_model=project.models.parameters,
    )

    mpm.anomaliestoc.export(
        h_path=paths.anomalies_h,
        anomaly_model=project.models.anomalies,
        parameters_model=project.models.parameters,
    )

    mpm.anomaliestoxlsx.export(
        path=paths.anomalies_spreadsheet,
        anomaly_model=project.models.anomalies,
        parameters_model=project.models.parameters,
        skip_output=False,
    )


def full_export(
    project,
    bcu_project,
    paths,
    target_directory,
    first_time=False,
    skip_output=False,
    include_uuid_in_item=False,
):
    can_hierarchy_export(project, bcu_project, paths)
    interface_code_export(project, paths, skip_output, include_uuid_in_item)


def modification_time_or(path, alternative):
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return alternative


def get_sunspec_models(path):
    root_schema = graham.schema(mpm.sunspecmodel.Root)
    raw = path.read_bytes()
    root = root_schema.loads(raw).data

    return tuple(
        child.id for child in root.children if isinstance(child, mpm.sunspecmodel.Model)
    )


def is_stale(project, paths, skip_sunspec=False):
    loaded_project = mpm.project.loadp(project, post_load=False)

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
    project: mpm.project.Project,
    paths: mpm.importexportdialog.ImportPaths,
    pmvs_path: pathlib.Path,
    generate_formatted_output: bool,
    product_specific_defaults: typing.List[str],
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
    mpm.cantoxlsx.export(
        path=paths.spreadsheet_can,
        can_model=project.models.can,
        pmvs_path=pmvs_path,
    )

    if generate_formatted_output:
        mpm.cantoxlsx.format_for_manual(
            input_path=paths.spreadsheet_can,
            parameters_model=project.models.parameters,
            product_specific_defaults=product_specific_defaults,
        )
