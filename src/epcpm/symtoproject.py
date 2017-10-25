import pathlib

import canmatrix.formats

import epcpm.parametermodel
import epcpm.symbolmodel


def load_can_path(path):
    with open(path, 'rb') as f:
        return load_can_file(
            f=f,
            file_type=str(pathlib.Path(path).suffix[1:]),
        )


def load_can_file(f, file_type):
    matrix, = canmatrix.formats.load(f, file_type).values()

    parameters_root = epcpm.parametermodel.Root()
    symbols_root = epcpm.symbolmodel.Root()

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
            )
            message.append_child(mux_signal)

            for value, name in sorted(frame.mux_names.items()):
                multiplexer = epcpm.symbolmodel.Multiplexer(
                    name=name,
                )
                message.append_child(multiplexer)

                for matrix_signal in frame.signals:
                    if matrix_signal.multiplex != value:
                        continue

                    signal = epcpm.symbolmodel.Signal(
                        name=matrix_signal.name,
                    )

                    multiplexer.append_child(signal)

    return parameters_root, symbols_root
