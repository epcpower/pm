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
    parameter_uuid_finder = attr.ib(default=None)

    def gen(self):
        matrix = canmatrix.canmatrix.CanMatrix()

        for child in self.wrapped.children:
            frame = builders.wrap(
                wrapped=child,
                parameter_uuid_finder=self.parameter_uuid_finder,
            ).gen()
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
    parameter_uuid_finder = attr.ib(default=None)

    def gen(self):
        frame = canmatrix.canmatrix.Frame(
            name=epyqlib.utils.general.spaced_to_upper_camel(self.wrapped.name),
            Id=int(self.wrapped.identifier[2:], 16),
            extended=self.wrapped.extended,
            dlc=self.wrapped.length,
        )

        for child in self.wrapped.children:
            signal = builders.wrap(
                wrapped=child,
                parameter_uuid_finder=self.parameter_uuid_finder,
            ).gen()
            frame.signals.append(signal)

        return frame


@builders(epcpm.symbolmodel.Signal)
@attr.s
class Signal:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

    def gen(self, multiplex_id=None):
        extras = {}
        can_find_parameter = (
            self.wrapped.parameter_uuid is not None
            and self.parameter_uuid_finder is not None
        )
        parameter = None
        if can_find_parameter:
            parameter = self.parameter_uuid_finder(self.wrapped.parameter_uuid)

            if parameter.minimum is not None:
                extras['min'] = parameter.minimum

            if parameter.maximum is not None:
                extras['max'] = parameter.maximum

            if parameter.comment is not None:
                extras['comment'] = parameter.comment

        signal = canmatrix.canmatrix.Signal(
            name=epyqlib.utils.general.spaced_to_upper_camel(self.wrapped.name),
            multiplex=multiplex_id,
            signalSize=self.wrapped.bits,
            is_signed=self.wrapped.signed,
            **extras,
        )

        if parameter is not None:
            if parameter.default is not None:
                signal.attributes['GenSigStartValue'] = parameter.default

        return signal


@builders(epcpm.symbolmodel.MultiplexedMessage)
@attr.s
class MultiplexedMessage:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

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

        signal = builders.wrap(
            wrapped=self.wrapped.children[0],
            parameter_uuid_finder=self.parameter_uuid_finder,
        ).gen(
            multiplex_id='Multiplexor',
        )
        frame.signals.append(signal)

        for multiplexer in not_signals:
            for signal in common_signals:
                matrix_signal = builders.wrap(
                    wrapped=signal,
                    parameter_uuid_finder=self.parameter_uuid_finder,
                ).gen(
                    multiplex_id=multiplexer.identifier,
                )
                frame.signals.append(matrix_signal)

            frame.mux_names[multiplexer.identifier] = (
                epyqlib.utils.general.spaced_to_upper_camel(multiplexer.name)
            )

            for signal in multiplexer.children:
                signal = builders.wrap(
                    wrapped=signal,
                    parameter_uuid_finder=self.parameter_uuid_finder,
                ).gen(
                    multiplex_id=multiplexer.identifier,
                )

                frame.signals.append(signal)

        return frame
