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
        frame = canmatrix.canmatrix.Frame(
            name=epyqlib.utils.general.spaced_to_upper_camel(self.wrapped.name),
            Id=int(self.wrapped.identifier, 0),
            extended=self.wrapped.extended,
        )

        if len(self.wrapped.children) == 0:
            return frame

        signal = builders.wrap(self.wrapped.children[0]).gen(
            multiplex_id='Multiplexor',
        )
        frame.signals.append(signal)

        for multiplexer in self.wrapped.children[1:]:
            frame.mux_names[multiplexer.id] = (
                epyqlib.utils.general.spaced_to_upper_camel(multiplexer.name)
            )

            for signal in multiplexer.children:
                signal = builders.wrap(signal).gen(
                    multiplex_id=multiplexer.id,
                )

                frame.signals.append(signal)

        return frame
