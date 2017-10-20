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

        f = io.BytesIO()
        canmatrix.formats.dump(matrix, f, 'sym')
        f.seek(0)

        return f.read().decode('utf-8')


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

    def gen(self):
        signal = canmatrix.canmatrix.Signal(
            name=epyqlib.utils.general.spaced_to_upper_camel(self.wrapped.name),
        )

        return signal
