import collections
import io
import textwrap

import attr
import canmatrix.canmatrix
import canmatrix.formats
import epcpm.symbolmodel
import epyqlib.utils.general

builders = epyqlib.utils.general.TypeMap()


def dehumanize_name(name):
    name = name.replace('-', '_')
    return epyqlib.utils.general.spaced_to_upper_camel(name)


@builders(epcpm.symbolmodel.Root)
@attr.s
class Root:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)
    parameter_model = attr.ib(default=None)

    def gen(self):
        matrix = canmatrix.canmatrix.CanMatrix()

        enumerations = self.collect_enumerations()

        for enumeration in enumerations:
            enumerators = collections.OrderedDict(
                (e.value, dehumanize_name(e.name))
                for e in enumeration.children
            )

            matrix.addValueTable(
                name=dehumanize_name(enumeration.name),
                valueTable=enumerators,
            )

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

    def collect_enumerations(self):
        collected = []

        if self.parameter_model is None:
            return collected

        def collect(node, collected):
            if isinstance(node, epcpm.parametermodel.Enumeration):
                collected.append(node)

        self.parameter_model.root.traverse(
            call_this=collect,
            payload=collected,
            internal_nodes=True,
        )

        return collected


@builders(epcpm.symbolmodel.Message)
@attr.s
class Message:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

    def gen(self):
        frame = canmatrix.canmatrix.Frame(
            name=dehumanize_name(self.wrapped.name),
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
            is_enumerated = isinstance(
                parameter,
                epcpm.parametermodel.EnumeratedParameter,
            )

            if not is_enumerated:
                if parameter.minimum is not None:
                    extras['min'] = parameter.minimum

                if parameter.maximum is not None:
                    extras['max'] = parameter.maximum

                if parameter.comment is not None:
                    extras['comment'] = parameter.comment

                if parameter.units is not None:
                    extras['unit'] = parameter.units
            else:
                if parameter.enumeration_uuid is not None:
                    enumeration = self.parameter_uuid_finder(
                        parameter.enumeration_uuid,
                    )

                    extras['enumeration'] = dehumanize_name(enumeration.name)
                    extras['values'] = {v: k for k, v in enumeration.items()}

        signal = canmatrix.canmatrix.Signal(
            name=dehumanize_name(self.wrapped.name),
            multiplex=multiplex_id,
            signalSize=self.wrapped.bits,
            is_signed=self.wrapped.signed,
            factor=self.wrapped.factor,
            **extras,
        )

        if parameter is not None and not is_enumerated:
            attributes = signal.attributes

            attributes['LongName'] = parameter.name

            if parameter.default is not None:
                attributes['GenSigStartValue'] = parameter.default

            if parameter.decimal_places is not None:
                attributes['DisplayDecimalPlaces'] = parameter.decimal_places

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
            name=dehumanize_name(self.wrapped.name),
            Id=int(self.wrapped.identifier, 0),
            extended=self.wrapped.extended,
            dlc=not_signals[0].length,
        )

        cycle_time = not_signals[0].cycle_time
        if cycle_time is not None:
            frame.attributes['GenMsgCycleTime'] = str(cycle_time)

        if len(self.wrapped.children) == 0:
            return frame

        mux_signal = builders.wrap(
            wrapped=self.wrapped.children[0],
            parameter_uuid_finder=self.parameter_uuid_finder,
        ).gen(
            multiplex_id='Multiplexor',
        )
        frame.signals.append(mux_signal)

        for multiplexer in not_signals:
            if multiplexer.comment is not None:
                mux_signal.comments[multiplexer.identifier] = (
                    multiplexer.comment
                )

            for signal in common_signals:
                matrix_signal = builders.wrap(
                    wrapped=signal,
                    parameter_uuid_finder=self.parameter_uuid_finder,
                ).gen(
                    multiplex_id=multiplexer.identifier,
                )
                frame.signals.append(matrix_signal)

            frame.mux_names[multiplexer.identifier] = (
                dehumanize_name(multiplexer.name)
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
