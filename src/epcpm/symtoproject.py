import collections
import decimal
import functools
import itertools
import json
import pathlib
import re
import uuid

import attr
import canmatrix.formats

import epyqlib.attrsmodel
import epyqlib.pm.parametermodel
import epyqlib.utils.general

import epcpm.canmodel
import epcpm.sunspecmodel


imported_variants = []

def humanize_name(name):
    return name
#     name = name.replace('_', ' - ')
#     return epyqlib.utils.general.underscored_camel_to_title_spaced(name)


def load_can_path(can_path, hierarchy_path):
    with open(can_path, 'rb') as c, open(hierarchy_path) as h:
        return load_can_file(
            can_file=c,
            file_type=str(pathlib.Path(can_path).suffix[1:]),
            parameter_hierarchy_file=h,
        )


def get_other_name(hierarchy):
    other_names = [
        child['name']
        for child in hierarchy['children']
        if isinstance(child, dict) and child.get('unreferenced', False)
    ]

    if not other_names:
        other_name = '9. Other'
    else:
        other_name, = other_names

    return other_name


def load_can_file(
        can_file,
        file_type,
        parameter_hierarchy_file,
        add_tables=False,
):
    matrix, = canmatrix.formats.load(
        can_file,
        file_type,
        calc_min_for_none=False,
        calc_max_for_none=False,
        float_factory=decimal.Decimal,
    ).values()

    parameters_root = epyqlib.pm.parametermodel.Root()
    can_root = epcpm.canmodel.Root()

    enumerations = epyqlib.pm.parametermodel.Enumerations(name='Enumerations')
    parameters_root.append_child(enumerations)

    parameters = epyqlib.pm.parametermodel.Group(name='Parameters')
    parameters_root.append_child(parameters)

    parameter_hierarchy = json.load(
        parameter_hierarchy_file,
        object_pairs_hook=collections.OrderedDict,
    )

    other_name = get_other_name(parameter_hierarchy)
    other_parameters = epyqlib.pm.parametermodel.Group(name=other_name)
    parameters.append_child(other_parameters)

    ccp = epyqlib.pm.parametermodel.Group(name='CCP')
    parameters_root.append_child(ccp)

    process_to_inverter = epyqlib.pm.parametermodel.Group(
        name='Process To Inverter',
    )
    parameters_root.append_child(process_to_inverter)

    other = epyqlib.pm.parametermodel.Group(name='9. Other')
    parameters_root.append_child(other)

    read_nvs = epyqlib.pm.parametermodel.Group(name='ReadNV')
    other.append_child(read_nvs)

    nv_commands = epyqlib.pm.parametermodel.Group(name='NVCommands')
    other.append_child(nv_commands)

    ccp_counters = epyqlib.pm.parametermodel.Group(name='CCP Counters')
    other.append_child(ccp_counters)

    def traverse_hierarchy(children, parent, group_from_path):
        for child in children:
            if isinstance(child, dict):
                subchildren = child.get('children')
                if subchildren is None:
                    continue

                existing = {
                    group.name: group
                    for group in parent.children
                }

                group = existing.get(child['name'])
                if group is None:
                    group = epyqlib.pm.parametermodel.Group(
                        name=child['name'],
                    )
                    parent.append_child(group)

                traverse_hierarchy(
                    children=subchildren,
                    parent=group,
                    group_from_path=group_from_path,
                )
            else:
                group_from_path[('ParameterQuery',) + tuple(child)] = parent
                group_from_path[('ParameterResponse',) + tuple(child)] = parent

    group_from_path = {
        'other_parameters': other_parameters,
        'read_nvs': read_nvs,
        'nv_commands': nv_commands,
        'ccp': ccp,
        'ccp_counters': ccp_counters,
        'process_to_inverter': process_to_inverter,
        'other': other,
    }
    traverse_hierarchy(
        children=parameter_hierarchy['children'],
        parent=parameters,
        group_from_path=group_from_path,
    )

    enumeration_name_to_uuid = {}
    access_levels = None
    variants = None
    for name, values in sorted(matrix.valueTables.items()):
        if name == 'AccessLevel':
            enumeration = epyqlib.pm.parametermodel.AccessLevels(name=name)
            access_levels = enumeration
            enumerator_type = epyqlib.pm.parametermodel.AccessLevel
        else:
            enumeration = epyqlib.pm.parametermodel.Enumeration(name=name)
            enumerator_type = epyqlib.pm.parametermodel.Enumerator

        enumerations.append_child(enumeration)
        enumeration_name_to_uuid[name] = enumeration.uuid

        for value, gname in values.items():
            enumerator = enumerator_type(name=gname, value=value)
            enumeration.append_child(enumerator)

        if name == 'CmmControlsVariant':
            variants = [
                variant 
                for variant in enumeration.children 
                if variant.name != 'None'
            ]
            global imported_variants
            imported_variants = variants

    parameter_from_path = {}

    for frame in matrix.frames:
        if len(frame.mux_names) == 0:
            message = build_message(
                frame=frame,
                parameter_group=parameters_root,
                enumeration_name_to_uuid=enumeration_name_to_uuid,
                access_levels=access_levels,
                variants=variants,
            )
        else:
            message = build_multiplexed_message(
                enumeration_name_to_uuid=enumeration_name_to_uuid,
                frame=frame,
                group_from_path=group_from_path,
                parameter_from_path=parameter_from_path,
                access_levels=access_levels,
                variants=variants,
            )

            def interesting_signal_attributes(signal):
                return (
                     signal.name,
                     signal.bits,
                     signal.signed,
                     signal.factor,
                     signal.start_bit,
                 )

            multiplexers = [
                mux
                for mux in message.children
                if isinstance(mux, epcpm.canmodel.Multiplexer)
            ]

            common_signals_dict = functools.reduce(
                epyqlib.utils.general.intersect_dicts,
                 (
                     {
                         interesting_signal_attributes(signal): signal
                         for signal in mux.children
                     }
                     for mux in multiplexers
                 ),
            )

            common_signals = list(common_signals_dict.values())
            common_signals_check = list(common_signals_dict.keys())

            # TODO: maybe coming back...  maybe
            # for mux in multiplexers:
            #     for child in list(mux.children):
            #         if interesting_signal_attributes(child) in common_signals_check:
            #             mux.remove_child(child=child)

            for signal in reversed(common_signals):
                message.insert_child(1, attr.evolve(signal, uuid=attr.NOTHING))

        can_root.append_child(message)

    def reorder_children(node, names):
        children_by_name = {
            child.name: child
            for child in node.children
        }

        for name in names:
            child = children_by_name[name]
            node.remove_child(child=child)
            node.append_child(child)

    def traverse_hierarchy_to_reorder(children, parent):
        for child in children:
            if isinstance(child, dict):
                child_objects = parent.children_by_attribute(
                    name='name',
                    value=child['name'],
                )
                if len(child_objects) == 1:
                    child_object, = child_objects
                else:
                    # TODO: just get rid of this debugging if and adjust above
                    raise Exception()

                subchildren = child.get('children')
                if subchildren is None:
                    continue

                subchild_names = []
                for subchild in subchildren:
                    if isinstance(subchild, dict):
                        name = subchild['name']
                    else:
                        # Query and response point the same place
                        signal_path = ('ParameterQuery',) + tuple(subchild)
                        name = parameter_from_path[signal_path].name

                    subchild_names.append(name)

                reorder_children(node=child_object, names=subchild_names)

                traverse_hierarchy_to_reorder(
                    children=subchildren,
                    parent=child_object,
                )

    traverse_hierarchy_to_reorder(
        children=parameter_hierarchy['children'],
        parent=parameters,
    )

    sunspec_root = epcpm.sunspecmodel.Root()

    def stripped(parameter):
        prefix = '{} : '.format(parameter.original_multiplexer_name)
        if parameter.name.startswith(prefix):
            return parameter.name[len(prefix):]

        return parameter.name

    def strip_frame_name(node, payload):
        if isinstance(node, epyqlib.pm.parametermodel.Parameter):
            other_names = {
                stripped(other)
                for other in node.tree_parent.children
                if (
                    isinstance(other, epyqlib.pm.parametermodel.Parameter)
                    and other is not node
                )
            }
            stripped_name = stripped(node)
            if stripped_name not in other_names:
                node.name = stripped_name

    parameters_root.traverse(
        call_this=strip_frame_name,
        payload=None,
        internal_nodes=True,
    )

    return parameters_root, can_root, sunspec_root


def build_message(
        frame,
        parameter_group,
        enumeration_name_to_uuid,
        access_levels,
        variants,
):
    extras = {}

    cycle_time = frame.attributes.get('GenMsgCycleTime')
    if cycle_time is not None:
        extras['cycle_time'] = cycle_time

    message = message_from_matrix(
        frame=frame,
        factory=epcpm.canmodel.Message,
        length=frame.size,
        **extras,
    )
    group = epyqlib.pm.parametermodel.Group(
        name=humanize_name(frame.name),
    )
    parameter_group.append_child(group)
    
    variant_cfgs = strip_variant_parameter_tag(string='', variants=variants)[1]

    for matrix_signal in frame.signals:
        parameter = parameter_from_signal(
            frame=frame,
            frame_access_level=access_levels.default(),
            matrix_signal=matrix_signal,
            enumeration_name_to_uuid=enumeration_name_to_uuid,
            access_levels=access_levels,
            variants=variants,
            frame_variants=variant_cfgs
        )
        group.append_child(parameter)

        signal = signal_from_matrix(
            matrix_signal=matrix_signal,
            factory=epcpm.canmodel.Signal,
            enumeration_name_to_uuid=enumeration_name_to_uuid,
            parameter_uuid=parameter.uuid,
        )
        message.append_child(signal)

    return message


def message_from_matrix(frame, factory, **extras):
    extras.setdefault('name', humanize_name(frame.name))
    extras.setdefault('identifier', frame.id)
    extras.setdefault('extended', frame.extended)
    extras.setdefault('comment', frame.comment)
    extras.setdefault('sendable', frame.attributes['Sendable'] == 'True')
    extras.setdefault('receivable', frame.attributes['Receivable'] == 'True')

    return factory(
        **extras
    )


def signal_from_matrix(
        matrix_signal,
        factory,
        enumeration_name_to_uuid,
        **extras,
):
    extras.setdefault('name', humanize_name(matrix_signal.name))
    extras.setdefault('bits', matrix_signal.size)
    extras.setdefault('factor', matrix_signal.factor)
    extras.setdefault('signed', matrix_signal.is_signed)
    extras.setdefault('start_bit', matrix_signal.getStartbit())

    extras.setdefault(
        'enumeration_uuid',
        enumeration_name_to_uuid.get(matrix_signal.enumeration),
    )

    return factory(
        **extras
    )


def build_multiplexed_message(
        enumeration_name_to_uuid,
        frame,
        group_from_path,
        parameter_from_path,
        access_levels,
        variants,
):
    message = message_from_matrix(
        frame=frame,
        factory=epcpm.canmodel.MultiplexedMessage,
    )
    matrix_mux_signal, = (
        s
        for s in frame.signals
        if s.multiplex == 'Multiplexor'
    )
    mux_signal = signal_from_matrix(
        factory=epcpm.canmodel.Signal,
        matrix_signal=matrix_mux_signal,
        enumeration_name_to_uuid=enumeration_name_to_uuid,
        signed=False,
    )
    message.append_child(mux_signal)
    for value, mux_name in sorted(frame.mux_names.items()):
        extras = {}

        mux_comment = matrix_mux_signal.comments.get(value)
        if mux_comment is not None:
            mux_comment, access_level = strip_access_level(
                string=mux_comment,
                access_levels=access_levels,
            )
            
            mux_comment, variant_cfgs = strip_variant_parameter_tag(
                string=mux_comment,
                variants=variants,
            )

            if len(mux_comment) > 0:
                extras['comment'] = mux_comment

        cycle_time = frame.attributes.get('GenMsgCycleTime')
        if cycle_time is not None:
            extras['cycle_time'] = cycle_time

        multiplexer = epcpm.canmodel.Multiplexer(
            name=humanize_name(mux_name),
            identifier=value,
            length=frame.size,
            **extras,
        )
        message.append_child(multiplexer)

        for matrix_signal in frame.signals:
            if matrix_signal.multiplex != value:
                continue

            parameter = parameter_from_signal(
                frame=frame,
                frame_access_level=access_level,
                matrix_signal=matrix_signal,
                mux_name=mux_name,
                enumeration_name_to_uuid=enumeration_name_to_uuid,
                access_levels=access_levels,
                variants=variants,
                frame_variants=variant_cfgs,
            )

            group = group_from_path.get(
                (frame.name, mux_name, matrix_signal.name),
            )

            if group is None:
                if frame.name.startswith('Parameter'):
                    if matrix_signal.enumeration in {'ReadNV', 'Meta'}:
                        group = 'read_nvs'
                    elif matrix_signal.name.startswith('SaveToEE'):
                        group = 'nv_commands'
                    else:
                        group = 'other_parameters'
                elif frame.name.startswith('CCP'):
                    if matrix_signal.name == 'CommandCounter':
                        group = 'ccp_counters'
                    else:
                        group = 'ccp'
                elif frame.name.startswith('Process'):
                    group = 'process_to_inverter'
                else:
                    group = 'other'

                group = group_from_path[group]

            same_name_parameters = [
                node
                for node in group.children
                if node.name == parameter.name
            ]

            if len(same_name_parameters) == 0:
                group.append_child(parameter)
            else:
                parameter, = same_name_parameters

            signal_path = (frame.name, mux_name, matrix_signal.name)
            parameter_from_path[signal_path] = parameter

            signal = signal_from_matrix(
                matrix_signal=matrix_signal,
                factory=epcpm.canmodel.Signal,
                enumeration_name_to_uuid=enumeration_name_to_uuid,
                parameter_uuid=parameter.uuid,
            )

            multiplexer.append_child(signal)

    return message


# TODO: backmatching
def enumeration_definition(name, value_names):
    enumeration = epyqlib.pm.parametermodel.Enumeration(
        name=name,
    )
    for value, value_name in enumerate(value_names):
        enumerator = epyqlib.pm.parametermodel.Enumerator(
            name=value_name,
            value=value,
        )
        enumeration.append_child(enumerator)

    return enumeration


def array_definition(name, length, parameter):
    array = epyqlib.pm.parametermodel.Array(
        name=name,
    )
    array.append_child(parameter)
    array.length = length

    name_length = len('{}'.format(length))

    for i, node in enumerate(array.children, start=1):
        node.name = '_{:0{}}'.format(i, name_length)

    return array


def group_definition(name, parameters):
    group = epyqlib.pm.parametermodel.Group(
        name=name,
    )
    for parameter in parameters:
        group.append_child(parameter)

    return group


def table_definition(
        parent,
        name,
        enumerations,
        can_getter,
        can_setter,
        active_curve_getter,
        active_curve_setter,
        arrays,
        groups=(),
):
    table = epyqlib.pm.parametermodel.Table(
        name=name,
        can_getter=can_getter,
        can_setter=can_setter,
        active_curve_getter=active_curve_getter,
        active_curve_setter=active_curve_setter,
    )
    parent.append_child(table)

    for enumeration in enumerations:
        reference = epyqlib.pm.parametermodel.TableEnumerationReference(
            name=enumeration.name,
            enumeration_uuid=enumeration.uuid,
        )

        table.append_child(reference)

    for group in groups:
        table.append_child(group)

    for array in arrays:
        table.append_child(array)

    return table


@attr.s(frozen=True, slots=True)
class CanTableDefinition:
    signals = attr.ib()
    range = attr.ib()


def go_add_tables(parameters_root, can_root):
    def is_a_table(node):
        comment = getattr(node, 'comment', None)
        if comment is None:
            return False

        return '<table>' in comment

    can_table_stuff = can_root.nodes_by_filter(filter=is_a_table)
    for node in can_table_stuff:
        node.tree_parent.remove_child(child=node)

    line_monitoring = parameters_root.descendent(
        'Parameters',
        '1. AC',
        '10. Line Monitoring',
    )
    enumerations_group = parameters_root.descendent('Enumerations')
    existing_tables = line_monitoring.descendent('Tables')
    line_monitoring.remove_child(child=existing_tables)

    low_high = enumeration_definition(
        name='LowHigh',
        value_names=(
            'Low',
            'High',
        )
    )

    ridethrough_trip = enumeration_definition(
        name='RideThroughTrip',
        value_names=(
            'RideThrough',
            'Trip',
        )
    )

    curves = enumeration_definition(
        name='Curves',
        value_names=(
            '0',
            '1',
            '2',
            '3',
        )
    )

    volt_var_y_scale = enumeration_definition(
        name='VoltVarYScale',
        value_names=(
            "rated reactive power with vars precedence",
            "rated reactive power with watts precedence",
            "available reactive power with watts precedence",
        ),
    )

    enumerations = (
        low_high,
        ridethrough_trip,
        curves,
        volt_var_y_scale
    )

    for enumeration in enumerations:
        enumerations_group.append_child(enumeration)

    curve_points = 10

    tables_group = epyqlib.pm.parametermodel.Group(
        name='Tables',
    )
    line_monitoring.append_child(tables_group)

    frequency_table = table_definition(
        parent=tables_group,
        name='Frequency',
        enumerations=(
            low_high,
            ridethrough_trip,
            curves,
        ),
        can_getter='{interface_signal} = lineMonitorParams->fMonitorTables[{curve_type}].curves[{curve_index}].tbl[{point_index}].{axis};',
        can_setter='gridMonitor_setFrequencyZoneCurve{upper_axis}Point({curve_type}, {curve_index}, {point_index}, {interface_signal});',
        active_curve_getter='{interface_signal} = lineMonitorParams->fMonitorTables[{curve_type}].activeCurve;',
        active_curve_setter='gridMonitor_setFrequencyZoneActiveCurve({curve_type}, {interface_signal});',
        arrays=(
            array_definition(
                name='seconds',
                length=curve_points,
                parameter=epyqlib.pm.parametermodel.Parameter(
                    units='seconds',
                    decimal_places=2,
                ),
            ),
            array_definition(
                name='hertz',
                length=curve_points,
                parameter=epyqlib.pm.parametermodel.Parameter(
                    units='Hz',
                    decimal_places=2,
                ),
            ),
        ),
    )

    voltage_table = table_definition(
        parent=tables_group,
        name='Voltage',
        enumerations=(
            low_high,
            ridethrough_trip,
            curves,
        ),
        can_getter='{interface_signal} = lineMonitorParams->vMonitorTables[{curve_type}].curves[{curve_index}].tbl[{point_index}].{axis};',
        can_setter='gridMonitor_setVoltageZoneCurve{upper_axis}Point({curve_type}, {curve_index}, {point_index}, {interface_signal});',
        active_curve_getter='{interface_signal} = lineMonitorParams->vMonitorTables[{curve_type}].activeCurve;',
        active_curve_setter='gridMonitor_setVoltageZoneActiveCurve({curve_type}, {interface_signal});',
        arrays=(
            array_definition(
                name='seconds',
                length=curve_points,
                parameter=epyqlib.pm.parametermodel.Parameter(
                    units='seconds',
                    decimal_places=2,
                ),
            ),
            array_definition(
                name='percent',
                length=curve_points,
                parameter=epyqlib.pm.parametermodel.Parameter(
                    units='%',
                    decimal_places=1,
                ),
            ),
        ),
    )

    settings = group_definition(
        name='Settings',
        parameters=(
            epyqlib.pm.parametermodel.Parameter(
                name='YScale',
                maximum=3,
                can_getter='{interface_signal} = lineMonitorParams->voltVar.yScale[{curve_index}];',
                can_setter='lineMonitorParams->voltVar.yScale[{curve_index}] = (VoltVar_YScale) {interface_signal};',
            ),
            epyqlib.pm.parametermodel.Parameter(
                name='RampRateIncrement',
                units='%/minute',
                can_getter='{interface_signal} = lineMonitorParams->voltVar.droopTable.modes[{curve_index}].rampRateInc;',
                can_setter='gridMonitor_setVoltVarCurveRampInc({curve_index}, {interface_signal});',
            ),
            epyqlib.pm.parametermodel.Parameter(
                name='RampRateDecrement',
                units='%/minute',
                can_getter='{interface_signal} = lineMonitorParams->voltVar.droopTable.modes[{curve_index}].rampRateDec;',
                can_setter='gridMonitor_setVoltVarCurveRampDec({curve_index}, {interface_signal});',
            ),
        ),
    )

    volt_var_table = table_definition(
        parent=tables_group,
        name='VoltVar',
        enumerations=(curves,),
        can_getter='{interface_signal} = lineMonitorParams->voltVar.droopTable.modes[{curve_index}].tbl[{point_index}].{axis};',
        can_setter='gridMonitor_setVoltVarCurve{upper_axis}Point({curve_index}, {point_index}, {interface_signal});',
        active_curve_getter='{interface_signal} = lineMonitorParams->voltVar.droopTable.activeMode;',
        active_curve_setter='gridMonitor_setVoltVarActiveMode({interface_signal});',
        arrays=(
            settings,
            array_definition(
                name='percent_nominal_volts',
                length=curve_points,
                parameter=epyqlib.pm.parametermodel.Parameter(
                    units='% nominal V',
                    decimal_places=1,
                ),
            ),
            array_definition(
                name='percent_nominal_var',
                length=curve_points,
                parameter=epyqlib.pm.parametermodel.Parameter(
                    units='% nominal VAr',
                    decimal_places=1,
                ),
            ),
        ),
    )

    settings = group_definition(
        name='Settings',
        parameters=(
            epyqlib.pm.parametermodel.Parameter(
                name='RampRateIncrement',
                units='%/minute',
                can_getter='{interface_signal} = lineMonitorParams->hzWatts.modes[{curve_index}].rampRateInc;',
                can_setter='gridMonitor_setHzWattsCurveRampInc({curve_index}, {interface_signal});',
            ),
            epyqlib.pm.parametermodel.Parameter(
                name='RampRateDecrement',
                units='%/minute',
                can_getter='{interface_signal} = lineMonitorParams->hzWatts.modes[{curve_index}].rampRateDec;',
                can_setter='gridMonitor_setHzWattsCurveRampDec({curve_index}, {interface_signal});',
            ),
        ),
    )

    hertz_watts_table = table_definition(
        parent=tables_group,
        name='HzWatts',
        enumerations=(curves,),
        can_getter='{interface_signal} = lineMonitorParams->hzWatts.modes[{curve_index}].tbl[{point_index}].{axis};',
        can_setter='gridMonitor_setHzWattsCurve{upper_axis}Point({curve_index}, {point_index}, {interface_signal});',
        active_curve_getter='{interface_signal} = lineMonitorParams->hzWatts.activeMode;',
        active_curve_setter='gridMonitor_setHzWattsActiveMode({interface_signal});',
        groups=(settings,),
        arrays=(
            array_definition(
                name='hertz',
                length=curve_points,
                parameter=epyqlib.pm.parametermodel.Parameter(
                    units='Hz',
                    decimal_places=2,
                ),
            ),
            array_definition(
                name='percent_nominal_pwr',
                length=curve_points,
                parameter=epyqlib.pm.parametermodel.Parameter(
                    units='% nominal Power',
                    decimal_places=1,
                ),
            ),
        ),
    )

    settings = group_definition(
        name='Settings',
        parameters=(
            epyqlib.pm.parametermodel.Parameter(
                name='RampRateIncrement',
                units='%/minute',
                can_getter='{interface_signal} = lineMonitorParams->voltWatts.modes[{curve_index}].rampRateInc;',
                can_setter='gridMonitor_setVoltWattsCurveRampInc({curve_index}, {interface_signal});',
            ),
            epyqlib.pm.parametermodel.Parameter(
                name='RampRateDecrement',
                units='%/minute',
                can_getter='{interface_signal} = lineMonitorParams->voltWatts.modes[{curve_index}].rampRateDec;',
                can_setter='gridMonitor_setVoltWattsCurveRampDec({curve_index}, {interface_signal});',
            ),
        ),
    )

    volt_watts_table = table_definition(
        parent=tables_group,
        name='VoltWatts',
        enumerations=(curves,),
        can_getter='{interface_signal} = lineMonitorParams->voltWatts.modes[{curve_index}].tbl[{point_index}].{axis};',
        can_setter='gridMonitor_setVoltWattsCurve{upper_axis}Point({curve_index}, {point_index}, {interface_signal});',
        active_curve_getter='{interface_signal} = lineMonitorParams->voltWatts.activeMode;',
        active_curve_setter='gridMonitor_setVoltWattsActiveMode({interface_signal});',
        groups=(settings,),
        arrays=(
            array_definition(
                name='percent_nominal_volts',
                length=curve_points,
                parameter=epyqlib.pm.parametermodel.Parameter(
                    units='% nominal V',
                    decimal_places=1,
                ),
            ),
            array_definition(
                name='percent_nominal_pwr',
                length=curve_points,
                parameter=epyqlib.pm.parametermodel.Parameter(
                    units='% nominal Power',
                    decimal_places=1,
                ),
            ),
        ),
    )

    tables = {
        frequency_table: CanTableDefinition(
            range=range(0x195, 0x215),
            signals={
                'seconds': {
                    'bits': 16,
                    'signed': False,
                    'factor': '0.01',
                },
                'hertz': {
                    'bits': 16,
                    'signed': False,
                    'factor': '0.01',
                },
            },
        ),
        voltage_table: CanTableDefinition(
            range=range(0x215, 0x295),
            signals={
                'seconds': {
                    'bits': 16,
                    'signed': False,
                    'factor': '0.01',
                },
                'percent': {
                    'bits': 16,
                    'signed': False,
                    'factor': '0.1',
                },
            },
        ),
        volt_var_table: CanTableDefinition(
            range=range(0x295, 0x2b9),
            signals={
                'YScale': {
                    'bits': 2,
                    'signed': False,
                    'enumeration_uuid': volt_var_y_scale.uuid,
                },
                'RampRateIncrement': {
                    'bits': 16,
                    'signed': False,
                },
                'RampRateDecrement': {
                    'bits': 16,
                    'signed': False,
                },
                'percent_nominal_volts': {
                    'bits': 16,
                    'signed': False,
                    'factor': '0.1',
                },
                'percent_nominal_var': {
                    'bits': 16,
                    'signed': True,
                    'factor': '0.1',
                },
            },
        ),
        hertz_watts_table: CanTableDefinition(
            range=range(0x2b9, 0x2dd),
            signals={
                'RampRateIncrement': {
                    'bits': 16,
                    'signed': False,
                    'factor': '1',
                },
                'RampRateDecrement': {
                    'bits': 16,
                    'signed': False,
                    'factor': '1',
                },
                'hertz': {
                    'bits': 16,
                    'signed': False,
                    'factor': '0.01',
                },
                'percent_nominal_pwr': {
                    'bits': 16,
                    'signed': True,
                    'factor': '0.1',
                },
            },
        ),
        volt_watts_table: CanTableDefinition(
            range=range(0x2dd, 0x300),
            signals={
                'RampRateIncrement': {
                    'bits': 16,
                    'signed': False,
                    'factor': '1',
                },
                'RampRateDecrement': {
                    'bits': 16,
                    'signed': False,
                    'factor': '1',
                },
                'percent_nominal_volts': {
                    'bits': 16,
                    'signed': False,
                    'factor': '0.1',
                },
                'percent_nominal_pwr': {
                    'bits': 16,
                    'signed': True,
                    'factor': '0.1',
                },
            },
        ),
    }

    for table, can_table_definition in tables.items():
        table.update()

        for name in ('ParameterQuery', 'ParameterResponse'):
            can_group = can_root.descendent(name)

            can_table = can_group.child_from(table)
            can_table.name = table.name
            can_table.multiplexer_range_first = can_table_definition.range[0]
            can_table.multiplexer_range_second = can_table_definition.range[-1]
            can_group.append_child(can_table)
            can_table.update(warn=False)

            for signal, values in can_table_definition.signals.items():
                signal = can_table.descendent(signal)
                for name, value in values.items():
                    setattr(signal, name, value)

            can_table.update()

    active_curve_names = (
        'FrequencyLowRideThrough',
        'FrequencyHighRideThrough',
        'FrequencyLowTrip',
        'FrequencyHighTrip',
        'VoltageLowRideThrough',
        'VoltageHighRideThrough',
        'VoltageLowTrip',
        'VoltageHighTrip',
        'VoltVar',
        'HzWatts',
        'VoltWatts',
    )

    generated_active_curve_names = tuple(
        table.name + ''.join(enumerator.name for enumerator in combination)
        for table in tables
        for combination in table.curve_group_combinations
    )

    # TODO: backmatching
    if set(active_curve_names) != set(generated_active_curve_names):
        raise Exception(
            '{}, {}'.format(active_curve_names, generated_active_curve_names),
        )

    start_bit = 16
    bits = 4

    for name in ('ParameterQuery', 'ParameterResponse'):
        can_group = can_root.descendent(name)

        multiplexer = epcpm.canmodel.Multiplexer(
            name='ActiveCurves',
            identifier=can_table.children[-1].identifier + 1,
            comment='<table>'
        )
        can_group.append_child(multiplexer)

    for name in active_curve_names:
        parameter = epyqlib.pm.parametermodel.Parameter(
            name=name,
            maximum=3,
        )
        tables_group.append_child(parameter)

        for name in ('ParameterQuery', 'ParameterResponse'):
            active_curves_multiplexer = can_root.descendent(name, 'ActiveCurves')

            signal = active_curves_multiplexer.child_from(parameter)
            signal.bits = bits
            signal.start_bit = start_bit

            active_curves_multiplexer.append_child(signal)

        start_bit += bits


def strip_tag(string, tag):
    present = tag in string

    if present:
        string = string.replace(tag, '').strip()

    return string, present


def strip_access_level(string, access_levels):
    factory_tag = '<factory>'

    string, present = strip_tag(string, factory_tag)

    access_level = access_levels.default()

    if present:
        access_level = access_levels.by_name('factory')

    return string, access_level


def strip_variant_parameter_tag(string, variants):
    selected_variants = []
    
    for variant in variants:
        string, present = strip_tag(string, f'<{variant.name}>')
        if present:
            selected_variants.append(variant)
    
    if len(selected_variants) == 0:
        selected_variants = variants
        
    return string, selected_variants


@attr.s
class NvMeta:
    format = attr.ib()
    factor = attr.ib(default=None)
    cast = attr.ib(default=False)


nv_pattern = re.compile('<nv:(.*?)>')


def strip_nv(string):
    tags = nv_pattern.search(string)

    if tags is None:
        return string, None

    flags, *tags, format = tags[1].split(':')

    extras = {}

    flags = set(flags)
    if 'c' in flags:
        flags.remove('c')
        extras['cast'] = True

    if len(flags) > 0:
        raise Exception('Unknown flags found {}'.format(''.join(sorted(flags))))

    for tag in tags:
        if tag.startswith('f'):
            extras['factor'] = tag[1:]
        else:
            raise Exception('Unknown tag found {}'.format(repr(tag)))

    return (
        nv_pattern.sub('', string),
        NvMeta(
            format=format,
            **extras,
        ),
    )


def parameter_from_signal(
        frame,
        frame_access_level,
        matrix_signal,
        enumeration_name_to_uuid,
        access_levels,
        variants,
        frame_variants,
        mux_name=None,
):
    extras = {}

    attributes = matrix_signal.attributes

    signal_name = attributes.get('LongName')
    if signal_name is None:
        if mux_name is not None:
            signal_name = '{} : {}'.format(
                humanize_name(mux_name),
                humanize_name(matrix_signal.name),
            )
        else:
            signal_name = humanize_name(matrix_signal.name)

    hexadecimal = matrix_signal.attributes.get('HexadecimalOutput')
    if hexadecimal is not None:
        extras['display_hexadecimal'] = hexadecimal == 'True'

    if matrix_signal.min is not None:
        extras['minimum'] = matrix_signal.min

    if matrix_signal.max is not None:
        extras['maximum'] = matrix_signal.max

    access_level = access_levels.default()

    if matrix_signal.comment is not None:
        comment = matrix_signal.comment
        comment, signal_access_level = strip_access_level(
            string=comment,
            access_levels=access_levels,
        )
        
        comment, variant_cfgs = strip_variant_parameter_tag(
            string=comment,
            variants=variants,
        )

        #only variants in both lists:
        vis_list = list(set(frame_variants).intersection(variant_cfgs))
        extras['visibility'] = vis_list
        
        comment, nv_meta = strip_nv(string=comment)

        folded = matrix_signal.name.casefold()

        if folded.startswith('readparam') or folded == 'meta':
            access_level = access_levels.default()
        else:
            access_level = max(
                (
                    access_level,
                    signal_access_level,
                    frame_access_level,
                ),
                key=lambda x: x.value,
            )

            if nv_meta is not None:
                extras['nv_format'] = nv_meta.format
                extras['nv_factor'] = nv_meta.factor
                extras['nv_cast'] = nv_meta.cast

        if len(comment) > 0:
            extras['comment'] = comment

    if access_level is not None:
        extras['access_level_uuid'] = access_level.uuid

    if matrix_signal.unit is not None:
        if len(matrix_signal.unit) > 0:
            extras['units'] = matrix_signal.unit

    default = attributes.get('GenSigStartValue')
    if default is not None:
        if matrix_signal.factor is not None:
            default = decimal.Decimal(default)
            # TODO: it seems this shouldn't be needed...  0754397432978432
            default *= decimal.Decimal(matrix_signal.factor)
        extras['default'] = default

    decimal_places = attributes.get('DisplayDecimalPlaces')
    if decimal_places is not None:
        extras['decimal_places'] = decimal_places

    if mux_name is not None:
        extras['original_multiplexer_name'] = mux_name

    return epyqlib.pm.parametermodel.Parameter(
        name=signal_name,
        original_frame_name=frame.name,
        original_signal_name=matrix_signal.name,
        **extras,
    )
