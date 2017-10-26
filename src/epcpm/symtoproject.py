import json
import pathlib

import canmatrix.formats

import epcpm.parametermodel
import epcpm.symbolmodel


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

    parameters = epcpm.parametermodel.Group(name='Parameters')
    parameters_root.append_child(parameters)

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

    group_from_path = {}
    parameter_hierarchy = json.load(parameter_hierarchy_file)
    traverse_hierarchy(
        children=parameter_hierarchy['children'],
        parent=parameters,
        group_from_path=group_from_path,
    )

    for frame in matrix.frames:
        if len(frame.mux_names) > 0:
            message = epcpm.symbolmodel.MultiplexedMessage(
                name=frame.name,
                identifier=frame.id,
                extended=frame.extended,
            )
            symbols_root.append_child(message)

            matrix_mux_signal, = (
                s
                for s in frame.signals
                if s.multiplex == 'Multiplexor'
            )

            mux_signal = epcpm.symbolmodel.Signal(
                name=matrix_mux_signal.name,
                bits=matrix_mux_signal.signalsize,
            )
            message.append_child(mux_signal)

            for value, name in sorted(frame.mux_names.items()):
                multiplexer = epcpm.symbolmodel.Multiplexer(
                    name=name,
                    identifier=value,
                    length=frame.size,
                )
                message.append_child(multiplexer)

                for matrix_signal in frame.signals:
                    if matrix_signal.multiplex != value:
                        continue

                    parameter_uuid = None
                    group = group_from_path.get(
                        (frame.name, name, matrix_signal.name),
                    )
                    if group is not None:
                        parameter = epcpm.parametermodel.Parameter(
                            name=f'{name}:{matrix_signal.name}',
                        )
                        group.append_child(parameter)
                        parameter_uuid = parameter.uuid

                    signal = epcpm.symbolmodel.Signal(
                        name=matrix_signal.name,
                        parameter_uuid=parameter_uuid,
                    )

                    multiplexer.append_child(signal)

    return parameters_root, symbols_root
