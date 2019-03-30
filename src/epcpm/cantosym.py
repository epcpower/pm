import collections
import io
import textwrap

import attr
import canmatrix.canmatrix
import canmatrix.formats

import epyqlib.pm.parametermodel
import epyqlib.utils.general

import epcpm.canmodel
import epcpm.symtoproject

builders = epyqlib.utils.general.TypeMap()


def dehumanize_name(name):
    return name
#     name = name.replace('-', '_')
#     return epyqlib.utils.general.spaced_to_upper_camel(name)


def export(path, can_model, parameters_model):
    finder = can_model.node_from_uuid
    access_levels = parameters_model.list_selection_roots['access level']
    builder = epcpm.cantosym.builders.wrap(
        wrapped=can_model.root,
        access_levels=access_levels,
        parameter_uuid_finder=finder,
        parameter_model=parameters_model,
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='\n') as f:
        f.write(builder.gen())


class SignalOutsideMessageError(Exception):
    @classmethod
    def build(cls, signal, message_length):
        path = [signal]

        while True:
            parent = path[0].tree_parent

            if parent.tree_parent is None:
                break

            path.insert(0, parent)

        path_string = ' : '.join(element.name for element in path)

        message_range = [0, max(0, (message_length * 8) - 1)]
        signal_range = [signal.start_bit, signal.start_bit + signal.bits - 1]

        message = (
              f'{path_string} spans bits'
              f' [{signal_range[0]}, {signal_range[1]}]'
              f' which is outside the range'
              f' [{message_range[0]}, {message_range[1]}]'
        )

        return cls(message)


@builders(epcpm.canmodel.Root)
@attr.s
class Root:
    wrapped = attr.ib()
    access_levels = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)
    parameter_model = attr.ib(default=None)

    def gen(self):
        matrix = canmatrix.canmatrix.CanMatrix()
        # TODO: this shouldn't need to be copied from:
        #           canmatrix.sym.load()
        matrix.addFrameDefines("GenMsgCycleTime", 'INT 0 65535')
        matrix.addFrameDefines("Receivable", 'BOOL False True')
        matrix.addFrameDefines("Sendable", 'BOOL False True')
        matrix.addSignalDefines("GenSigStartValue", 'FLOAT -3.4E+038 3.4E+038')
        matrix.addSignalDefines("HexadecimalOutput", 'BOOL False True')
        matrix.addSignalDefines("DisplayDecimalPlaces", 'INT 0 65535')
        matrix.addSignalDefines("LongName", 'STR')

        for child in self.wrapped.children:
            frame = builders.wrap(
                wrapped=child,
                access_levels=self.access_levels,
                parameter_uuid_finder=self.parameter_uuid_finder,
            ).gen()
            matrix.addFrame(frame)

        enumerations = self.collect_enumerations()
        used_enumerations = {
            signal.enumeration
            for frame in matrix.frames
            for signal in frame.signals
            if signal.enumeration is not None
        }

        for enumeration in enumerations:
            if enumeration.name not in used_enumerations:
                continue

            enumerators = collections.OrderedDict(
                (e.value, dehumanize_name(e.name))
                for e in enumeration.children
            )

            matrix.addValueTable(
                name=dehumanize_name(enumeration.name),
                valueTable=enumerators,
            )

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
            is_enumeration = isinstance(
                node,
                (
                    epyqlib.pm.parametermodel.Enumeration,
                    epyqlib.pm.parametermodel.AccessLevels,
                )
            )
            if is_enumeration:
                collected.append(node)

        self.parameter_model.root.traverse(
            call_this=collect,
            payload=collected,
            internal_nodes=True,
        )

        return collected


@builders(epcpm.canmodel.Message)
@attr.s
class Message:
    wrapped = attr.ib()
    access_levels = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

    def gen(self):
        frame = canmatrix.canmatrix.Frame(
            name=dehumanize_name(self.wrapped.name),
            id=self.wrapped.identifier,
            extended=self.wrapped.extended,
            size=self.wrapped.length,
            comment=self.wrapped.comment,
        )

        if self.wrapped.cycle_time is not None:
            frame.attributes['GenMsgCycleTime'] = str(self.wrapped.cycle_time)

        frame.attributes['Receivable'] = str(self.wrapped.receivable)
        frame.attributes['Sendable'] = str(self.wrapped.sendable)

        for child in self.wrapped.children:
            signal = builders.wrap(
                wrapped=child,
                message_length=self.wrapped.length,
                parameter_uuid_finder=self.parameter_uuid_finder,
            ).gen()
            frame.signals.append(signal)

        return frame


@builders(epcpm.canmodel.Signal)
@attr.s
class Signal:
    wrapped = attr.ib()
    message_length = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

    def gen(
            self,
            multiplex_id=None,
            skip_access_level=False,
            skip_configuration=False,
    ):
        if (
                self.message_length is not None
                and (
                    self.wrapped.start_bit < 0
                    or (
                        self.message_length * 8
                        < self.wrapped.start_bit + self.wrapped.bits
                    )
                )
        ):
            raise SignalOutsideMessageError.build(
                signal=self.wrapped,
                message_length=self.message_length,
            )

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
                comment = parameter.comment.strip()
                if len(comment) > 0:
                    extras['comment'] = comment

            handle_access_level = (
                    not skip_access_level
                    and parameter.access_level_uuid is not None
            )
            if handle_access_level:
                access_level = self.parameter_uuid_finder(
                    parameter.access_level_uuid
                )
                if access_level != access_level.tree_parent.default():
                    extras['comment'] = '{} <{}>'.format(
                        extras.get('comment', ''),
                        access_level.name.casefold(),
                    ).strip()

            handle_configuration = (
                    not skip_configuration
                    and parameter.visibility is not None
            )
            if handle_configuration:
                configurations = [
                    self.parameter_uuid_finder(u) for u in parameter.visibility
                ]
                imported_variants = epcpm.symtoproject.imported_variants
                if all(v in configurations  for v in imported_variants):
                    configurations = None #don't spam sym with variants
                if configurations is not None:
                    for cfg in configurations:
                        if cfg is not None:
                            extras['comment'] = '{} <{}>'.format(
                                extras.get('comment', ''),
                                cfg.name,
                            ).strip()

            if parameter.nv_format is not None:
                segments = ['nv']

                nv_flags = ''
                if parameter.nv_cast:
                    nv_flags += 'c'

                segments.append(nv_flags)

                if parameter.nv_factor is not None:
                    segments.append('f{}'.format(parameter.nv_factor))

                segments.append(parameter.nv_format)

                extras['comment'] = '{}  <{}>'.format(
                    extras.get('comment', ''),
                    ':'.join(segments),
                ).strip()

            if parameter.units is not None:
                extras['unit'] = parameter.units

            if self.wrapped.enumeration_uuid is not None:
                enumeration = self.parameter_uuid_finder(
                    self.wrapped.enumeration_uuid,
                )

                extras['enumeration'] = dehumanize_name(enumeration.name)
                extras['values'] = {v: k for k, v in enumeration.items()}

        signal = canmatrix.canmatrix.Signal(
            name=dehumanize_name(self.wrapped.name),
            multiplex=multiplex_id,
            size=self.wrapped.bits,
            is_signed=self.wrapped.signed,
            factor=self.wrapped.factor,
            startBit=self.wrapped.start_bit,
            calc_min_for_none=False,
            calc_max_for_none=False,
            **extras,
        )

        if parameter is not None:
            attributes = signal.attributes

            attributes['LongName'] = parameter.name
            attributes['HexadecimalOutput'] = parameter.display_hexadecimal

            if parameter.default is not None:
                # TODO: it seems this shouldn't be needed...  0754397432978432
                attributes['GenSigStartValue'] = (
                    parameter.default / self.wrapped.factor
                )

            if parameter.decimal_places is not None:
                attributes['DisplayDecimalPlaces'] = parameter.decimal_places

        return signal


@builders(epcpm.canmodel.MultiplexedMessage)
@attr.s
class MultiplexedMessage:
    wrapped = attr.ib()
    access_levels = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

    def gen(self):
        common_signals = []
        not_signals = []
        table_multiplexers = set()
        for child in self.wrapped.children[1:]:
            if isinstance(child, epcpm.canmodel.Signal):
                common_signals.append(child)
            elif isinstance(child, epcpm.canmodel.CanTable):
                for subchild in child.children:
                    if isinstance(subchild, epcpm.canmodel.Multiplexer):
                        not_signals.append(subchild)
                        table_multiplexers.add(subchild)
            else:
                not_signals.append(child)

        frame = canmatrix.canmatrix.Frame(
            name=dehumanize_name(self.wrapped.name),
            id=self.wrapped.identifier,
            extended=self.wrapped.extended,
            size=not_signals[0].length,
            comment=self.wrapped.comment,
            attributes={
                'Receivable': str(self.wrapped.receivable),
                'Sendable': str(self.wrapped.sendable),
            }
        )

        cycle_time = not_signals[0].cycle_time
        if cycle_time is not None:
            frame.attributes['GenMsgCycleTime'] = str(cycle_time)

        if len(self.wrapped.children) == 0:
            return frame

        mux_signal = builders.wrap(
            wrapped=self.wrapped.children[0],
            message_length=None,
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

            # TODO: backmatching
            if multiplexer in table_multiplexers:
                mux_signal.comments[multiplexer.identifier] = (
                    '{} <{}>'.format(
                        mux_signal.comments.get(multiplexer.identifier, ''),
                        'table',
                    ).strip()
                )

            name = multiplexer.name
            if isinstance(multiplexer.tree_parent, epcpm.canmodel.CanTable):
                name = multiplexer.tree_parent.name + name
            frame.mux_names[multiplexer.identifier] = (
                dehumanize_name(name)
            )

            def param_special(signal):
                folded = signal.name.casefold()

                return folded.startswith('read param - ') or folded == 'meta'

            signal_access_levels = set()

            for signal in multiplexer.children:
                if param_special(signal):
                    continue

                parameter = self.parameter_uuid_finder(signal.parameter_uuid)
                uuid = parameter.access_level_uuid

                if uuid is None:
                    access_level = self.access_levels.default()
                else:
                    access_level = self.parameter_uuid_finder(uuid)

                signal_access_levels.add(access_level)

            all_access_levels_match = len(signal_access_levels) == 1

            if all_access_levels_match:
                access_level = signal_access_levels.pop()
                if access_level != access_level.tree_parent.default():
                    mux_signal.comments[multiplexer.identifier] = (
                        '{} <{}>'.format(
                            mux_signal.comments.get(multiplexer.identifier, ''),
                            access_level.name.casefold(),
                        ).strip()
                    )

            for signal in multiplexer.children:
                signal = builders.wrap(
                    wrapped=signal,
                    message_length=multiplexer.length,
                    parameter_uuid_finder=self.parameter_uuid_finder,
                ).gen(
                    multiplex_id=multiplexer.identifier,
                    skip_access_level=all_access_levels_match,
                )

                frame.signals.append(signal)

            frame_signal_names = [
                signal.name
                for signal in frame.signals
                if signal.multiplex == multiplexer.identifier
            ]

            for signal in reversed(common_signals):
                if signal.name in frame_signal_names:
                    continue

                matrix_signal = builders.wrap(
                    wrapped=signal,
                    message_length=multiplexer.length,
                    parameter_uuid_finder=self.parameter_uuid_finder,
                ).gen(
                    multiplex_id=multiplexer.identifier,
                )
                frame.signals.insert(0, matrix_signal)

        return frame


def tweak_reply_signal(sig):
    if sig.name.endswith('_command'):
        sig.name = sig.name.replace('_command', '_status')
        sig.attributes['LongName'] = sig.name
    return sig


@builders(epcpm.canmodel.MultiplexedMessageClone)
@attr.s
class MultiplexedMessageClone:
    wrapped = attr.ib()
    access_levels = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

    def gen(self):
        frame = builders.wrap(
            wrapped=self.wrapped.original,
            access_levels=self.access_levels,
            parameter_uuid_finder=self.parameter_uuid_finder,
        ).gen()
 
        frame.name = self.wrapped.name
        frame.id = self.wrapped.identifier
        frame.comment = self.wrapped.comment
        frame.attributes={
            'Receivable': str(self.wrapped.receivable),
            'Sendable': str(self.wrapped.sendable),
        }
        for sig in frame.signals[:]:
            sig = tweak_reply_signal(sig)

        return frame


