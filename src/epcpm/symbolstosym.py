import io
import textwrap

import attr
import canmatrix.canmatrix
import canmatrix.formats
import epcpm.symbolmodel
import epyqlib.utils.general

builders = epyqlib.utils.general.TypeMap()


@builders(epcpm.symbolmodel.Root)
@attr.s
class Root:
    wrapped = attr.ib()

    def gen(self):
        matrix = canmatrix.canmatrix.CanMatrix()

        for child in self.wrapped.children:
            frame = builders.wrap(child).gen()
            matrix.frames.addFrame(frame)

        codec = 'utf-8'

        f = io.BytesIO()
        canmatrix.formats.dump(matrix, f, 'sym', symExportEncoding=codec)
        f.seek(0)

        return f.read().decode(codec)


@builders(epcpm.symbolmodel.Message)
@attr.s
class Message:
    wrapped = attr.ib()

    def gen(self):
        frame = canmatrix.canmatrix.Frame(
            name=epyqlib.utils.general.spaced_to_upper_camel(self.wrapped.name),
            Id=int(self.wrapped.identifier[2:], 16),
            extended=self.wrapped.extended,
            dlc=self.wrapped.length,
        )

        for child in self.wrapped.children:
            signal = builders.wrap(child).gen()
            frame.signals.append(signal)

        return frame


@builders(epcpm.symbolmodel.Signal)
@attr.s
class Signal:
    wrapped = attr.ib()

    def gen(self, multiplex_id=None):
        signal = canmatrix.canmatrix.Signal(
            name=epyqlib.utils.general.spaced_to_upper_camel(self.wrapped.name),
            multiplex=multiplex_id,
            signalSize=self.wrapped.bits,
        )

        return signal


@builders(epcpm.symbolmodel.MultiplexedMessage)
@attr.s
class MultiplexedMessage:
    wrapped = attr.ib()

    def gen(self):
        common_signals = []
        not_signals = []
        for child in self.wrapped.children[1:]:
            if isinstance(child, epcpm.symbolmodel.Signal):
                common_signals.append(child)
            else:
                not_signals.append(child)

        frame = canmatrix.canmatrix.Frame(
            name=epyqlib.utils.general.spaced_to_upper_camel(self.wrapped.name),
            Id=int(self.wrapped.identifier, 0),
            extended=self.wrapped.extended,
            dlc=not_signals[0].length,
        )

        if len(self.wrapped.children) == 0:
            return frame

        signal = builders.wrap(self.wrapped.children[0]).gen(
            multiplex_id='Multiplexor',
        )
        frame.signals.append(signal)

        for multiplexer in not_signals:
            for signal in common_signals:
                matrix_signal = builders.wrap(signal).gen(
                    multiplex_id=multiplexer.identifier,
                )
                frame.signals.append(matrix_signal)

            frame.mux_names[multiplexer.identifier] = (
                epyqlib.utils.general.spaced_to_upper_camel(multiplexer.name)
            )

            for signal in multiplexer.children:
                signal = builders.wrap(signal).gen(
                    multiplex_id=multiplexer.identifier,
                )

                frame.signals.append(signal)

        return frame
