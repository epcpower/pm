import json
import pathlib

import canmatrix.formats

import epyqlib.utils.general

import epcpm.parametermodel
import epcpm.symbolmodel


def humanize_name(name):
    name = name.replace('_', ' - ')
    return epyqlib.utils.general.underscored_camel_to_title_spaced(name)


def load_can_path(can_path, hierarchy_path):
    with open(can_path, 'rb') as c, open(hierarchy_path) as h:
        return load_can_file(
            can_file=c,
            file_type=str(pathlib.Path(can_path).suffix[1:]),
            parameter_hierarchy_file=h,
        )


def load_can_file(can_file, file_type, parameter_hierarchy_file):
    matrix, = canmatrix.formats.load(can_file, file_type).values()

    parameters_root = epcpm.parametermodel.Root()
    symbols_root = epcpm.symbolmodel.Root()

    enumerations = epcpm.parametermodel.Enumerations(name='Enumerations')
    parameters_root.append_child(enumerations)

    parameters = epcpm.parametermodel.Group(name='Parameters')
    parameters_root.append_child(parameters)

    other_parameters = epcpm.parametermodel.Group(name='Other')
    parameters.append_child(other_parameters)

    ccp = epcpm.parametermodel.Group(name='CCP')
    parameters_root.append_child(ccp)

    process_to_inverter = epcpm.parametermodel.Group(name='Process To Inverter')
    parameters_root.append_child(process_to_inverter)

    other = epcpm.parametermodel.Group(name='Other')
    parameters_root.append_child(other)

    read_nvs = epcpm.parametermodel.Group(name='ReadNV')
    other.append_child(read_nvs)

    ccp_counters = epcpm.parametermodel.Group(name='CCP Counters')
    other.append_child(ccp_counters)

    def traverse_hierarchy(children, parent, group_from_path):
        for child in children:
            if isinstance(child, dict):
                group = epcpm.parametermodel.Group(
                    name=child['name'],
                )
                parent.append_child(group)

                subchildren = child.get('children')
                if subchildren is not None:
                    traverse_hierarchy(
                        children=subchildren,
                        parent=group,
                        group_from_path=group_from_path,
                    )
                # if child.get('unreferenced'):
                #     traverse_hierarchy(child['children'], group)
            else:
                group_from_path[('ParameterQuery',) + tuple(child)] = parent
                group_from_path[('ParameterResponse',) + tuple(child)] = parent

    group_from_path = {
        'other_parameters': other_parameters,
        'read_nvs': read_nvs,
        'ccp': ccp,
        'ccp_counters': ccp_counters,
        'process_to_inverter': process_to_inverter,
        'other': other,
    }
    parameter_hierarchy = json.load(parameter_hierarchy_file)
    traverse_hierarchy(
        children=parameter_hierarchy['children'],
        parent=parameters,
        group_from_path=group_from_path,
    )

    enumeration_name_to_uuid = {}
    for name, values in sorted(matrix.valueTables.items()):
        enumeration = epcpm.parametermodel.Enumeration(
            name=name,
        )
        enumerations.append_child(enumeration)
        enumeration_name_to_uuid[name] = enumeration.uuid

        for value, name in values.items():
            enumerator = epcpm.parametermodel.Enumerator(
                name=name,
                value=value,
            )
            enumeration.append_child(enumerator)

    for frame in matrix.frames:
        if len(frame.mux_names) == 0:
            message = build_message(
                frame=frame,
                parameter_group=parameters_root,
                enumeration_name_to_uuid=enumeration_name_to_uuid,
            )
        else:
            message = build_multiplexed_message(
                enumeration_name_to_uuid=enumeration_name_to_uuid,
                frame=frame,
                group_from_path=group_from_path,
            )

        symbols_root.append_child(message)

    return parameters_root, symbols_root


def build_message(frame, parameter_group, enumeration_name_to_uuid):
    extras = {}

    cycle_time = frame.attributes.get('GenMsgCycleTime')
    if cycle_time is not None:
        extras['cycle_time'] = cycle_time

    message = message_from_matrix(
        frame=frame,
        factory=epcpm.symbolmodel.Message,
        **extras,
    )
    group = epcpm.parametermodel.Group(
        name=humanize_name(frame.name),
    )
    parameter_group.append_child(group)

    for matrix_signal in frame.signals:
        parameter = parameter_from_signal(
            frame=frame,
            matrix_signal=matrix_signal,
            enumeration_name_to_uuid=enumeration_name_to_uuid,
        )
        group.append_child(parameter)

        signal = signal_from_matrix(
            matrix_signal=matrix_signal,
            factory=epcpm.symbolmodel.Signal,
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


def signal_from_matrix(matrix_signal, factory, **extras):
    extras.setdefault('name', humanize_name(matrix_signal.name))
    extras.setdefault('bits', matrix_signal.signalsize)
    extras.setdefault('factor', matrix_signal.factor)
    extras.setdefault('signed', matrix_signal.is_signed)
    extras.setdefault('start_bit', matrix_signal.getStartbit())

    return factory(
        **extras
    )


def build_multiplexed_message(enumeration_name_to_uuid, frame, group_from_path):
    message = message_from_matrix(
        frame=frame,
        factory=epcpm.symbolmodel.MultiplexedMessage,
    )
    matrix_mux_signal, = (
        s
        for s in frame.signals
        if s.multiplex == 'Multiplexor'
    )
    mux_signal = signal_from_matrix(
        factory=epcpm.symbolmodel.Signal,
        matrix_signal=matrix_mux_signal,
        signed=False,
    )
    message.append_child(mux_signal)
    for value, mux_name in sorted(frame.mux_names.items()):
        extras = {}

        mux_comment = matrix_mux_signal.comments.get(value)
        if mux_comment is not None:
            extras['comment'] = mux_comment

        cycle_time = frame.attributes.get('GenMsgCycleTime')
        if cycle_time is not None:
            extras['cycle_time'] = cycle_time

        multiplexer = epcpm.symbolmodel.Multiplexer(
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
                matrix_signal=matrix_signal,
                mux_name=mux_name,
                enumeration_name_to_uuid=enumeration_name_to_uuid,
            )

            group = group_from_path.get(
                (frame.name, mux_name, matrix_signal.name),
            )

            if group is None:
                if frame.name.startswith('Parameter'):
                    if matrix_signal.enumeration == 'ReadNV':
                        group = 'read_nvs'
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

            group.append_child(parameter)

            signal = signal_from_matrix(
                matrix_signal=matrix_signal,
                factory=epcpm.symbolmodel.Signal,
                parameter_uuid=parameter.uuid,
            )

            multiplexer.append_child(signal)

    return message


def parameter_from_signal(frame, matrix_signal, enumeration_name_to_uuid,
                          mux_name=None):
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

    if matrix_signal.calcMin() != matrix_signal.min:
        extras['minimum'] = matrix_signal.min

    if matrix_signal.calcMax() != matrix_signal.max:
        extras['maximum'] = matrix_signal.max

    if matrix_signal.comment is not None:
        comment = matrix_signal.comment.strip()
        if len(comment) > 0:
            extras['comment'] = comment

    if matrix_signal.unit is not None:
        if len(matrix_signal.unit) > 0:
            extras['units'] = matrix_signal.unit

    default = attributes.get('GenSigStartValue')
    if default is not None:
        extras['default'] = default

    decimal_places = attributes.get('DisplayDecimalPlaces')
    if decimal_places is not None:
        extras['decimal_places'] = decimal_places

    if matrix_signal.enumeration is not None:
        extras['enumeration_uuid'] = enumeration_name_to_uuid[
            matrix_signal.enumeration
        ]

    return epcpm.parametermodel.Parameter(
        name=signal_name,
        **extras,
    )
