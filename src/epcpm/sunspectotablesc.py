import attr
import epyqlib.utils.general
import epyqlib.pm.parametermodel

import epcpm.cantotablesc
import epcpm.sunspecmodel


builders = epyqlib.utils.general.TypeMap()


def export(c_path, h_path, sunspec_model, skip_sunspec=False):
    builder = builders.wrap(
        wrapped=sunspec_model.root,
        parameter_uuid_finder=sunspec_model.node_from_uuid,
        skip_sunspec=skip_sunspec,
    )

    c_path.parent.mkdir(parents=True, exist_ok=True)
    c_content, h_content = builder.gen()

    template_context = {
        'definitions': c_content,
        'declarations': h_content,
    }

    epcpm.c.render(
        source=c_path.with_suffix(f'{c_path.suffix}_pm'),
        destination=c_path,
        context=template_context,
    )

    epcpm.c.render(
        source=h_path.with_suffix(f'{h_path.suffix}_pm'),
        destination=h_path,
        context=template_context,
    )


@builders(epcpm.sunspecmodel.Root)
@attr.s
class Root:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib()
    skip_sunspec = attr.ib(default=False)

    def gen(self):
        both_lines = [[], []]

        # table_results = []

        if not self.skip_sunspec:
            for child in self.wrapped.children:
                if not isinstance(child, epcpm.sunspecmodel.Model):
                    continue

                builder = builders.wrap(
                    wrapped=child,
                    parameter_uuid_finder=self.parameter_uuid_finder,
                )

                # table_results.append(builder.gen())
                # lines.extend(table_results[-1].table_lines)

                for lines, more_lines in zip(both_lines, builder.gen()):
                    lines.extend(more_lines)
                    lines.append('')

            # active_curves = parameter_query.child_by_name('ActiveCurves')
            #
            # for get_or_set in ('get', 'set'):
            #     active_lines = []
            #     for table_result in table_results:
            #         active_lines.extend(
            #             table_result.active_curves_lines[get_or_set],
            #         )
            #
            #     lines.extend([
            #         f'void {get_or_set}{active_curves.name}(void)',
            #         '{',
            #         active_lines,
            #         '}',
            #         '',
            #     ])

        return tuple(
            epyqlib.utils.general.format_nested_lists(lines)
            for lines in both_lines
        )


@builders(epcpm.sunspecmodel.Model)
@attr.s
class Model:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib()

    def gen(self):
        for child in self.wrapped.children:
            found = isinstance(
                child,
                epcpm.sunspecmodel.TableRepeatingBlockReference,
            )
            if found:
                break
        else:
            return [[], []]

        builder = builders.wrap(
            wrapped=child,
            parameter_uuid_finder=self.parameter_uuid_finder,
            model_id=self.wrapped.id,
        )

        return builder.gen()


@builders(epcpm.sunspecmodel.TableRepeatingBlockReference)
@attr.s
class TableRepeatingBlockReference:
    wrapped = attr.ib()
    model_id = attr.ib()
    parameter_uuid_finder = attr.ib()

    def gen(self):
        builder = builders.wrap(
            wrapped=self.wrapped.original,
            model_id=self.model_id,
            parameter_uuid_finder=self.parameter_uuid_finder,
        )

        return builder.gen()


@builders(epcpm.sunspecmodel.TableRepeatingBlock)
@attr.s
class TableRepeatingBlock:
    wrapped = attr.ib()
    model_id = attr.ib()
    parameter_uuid_finder = attr.ib()

    def gen(self):
        both_lines = [[], []]

        curve_group_string = ''.join(
            self.parameter_uuid_finder(uuid).name
            for uuid in self.wrapped.path[:-1]
        )
        curve_type = epcpm.cantotablesc.get_curve_type(curve_group_string)

        for curve_index in range(self.wrapped.repeats):
            for point in self.wrapped.children:
                builder = builders.wrap(
                    wrapped=point,
                    model_id=self.model_id,
                    curve_index=curve_index,
                    curve_type=curve_type,
                    parameter_uuid_finder=self.parameter_uuid_finder,
                )

                for lines, more_lines in zip(both_lines, builder.gen()):
                    lines.extend(more_lines)
                    lines.append('')

        return both_lines


@builders(epcpm.sunspecmodel.DataPoint)
@attr.s
class DataPoint:
    wrapped = attr.ib()
    model_id = attr.ib()
    curve_index = attr.ib()
    curve_type = attr.ib()
    parameter_uuid_finder = attr.ib()

    def gen(self):
        table_element = self.parameter_uuid_finder(self.wrapped.parameter_uuid)
        curve_parent = table_element.tree_parent.tree_parent.tree_parent
        table_element = curve_parent.descendent(
            str(self.curve_index),
            table_element.tree_parent.name,
            table_element.name,
        )

        parameter_table = self.parameter_uuid_finder(
            self.wrapped.tree_parent.tree_parent.parameter_table_uuid,
        )

        array_or_group_element = table_element.original

        is_a_parameter = isinstance(
            array_or_group_element,
            epyqlib.pm.parametermodel.Parameter,
        )
        if is_a_parameter:
            parameter = array_or_group_element
        else:
            parameter = array_or_group_element.original

        is_group = isinstance(
            array_or_group_element.tree_parent,
            epyqlib.pm.parametermodel.Group,
        )
        is_array = isinstance(
            array_or_group_element.tree_parent,
            epyqlib.pm.parametermodel.Array,
        )

        if is_group:
            getter_setter = {
                'get': array_or_group_element.can_getter,
                'set': array_or_group_element.can_setter,
            }
        elif is_array:
            getter_setter = {
                'get': parameter_table.can_getter,
                'set': parameter_table.can_setter,
            }

        if getter_setter['get'] is None:
            getter_setter['get'] = ''

        if getter_setter['set'] is None:
            getter_setter['set'] = ''

        axis = table_element.tree_parent.axis
        if axis is None:
            axis = '<no axis>'

        interface_variable = (
            f'sunspecInterface'
            f'.model{self.model_id}'
            f'.Curve_{self.curve_index + 1:02}_{table_element.abbreviation}'
        )

        both_lines = [[], []]

        for get_set, embedded in getter_setter.items():
            # TODO: CAMPid 075780541068182645821856068542023499
            converter = {
                'uint32': {
                    'get': 'sunspecUint32ToSSU32_returns',
                    'set': 'sunspecSSU32ToUint32',
                },
                'int32': {
                    # TODO: add this to embedded?
                    # 'get': 'sunspecInt32ToSSS32',
                    'set': 'sunspecSSS32ToInt32',
                },
                'uint64': {
                    'get': 'sunspecUint64ToSSU64_returns',
                    'set': 'sunspecSSU64ToUint64',
                },
            }.get(self.parameter_uuid_finder(self.wrapped.type_uuid).name)

            body_lines = []

            if parameter.uses_interface_item():
                # TODO: CAMPid 9685439641536675431653179671436
                item_uuid_string = str(table_element.uuid).replace('-', '_')
                item_name = f'interfaceItem_{item_uuid_string}'

                if True:#is_group:
                    if get_set == 'get':
                        body_lines.extend([
                            f'{item_name}.table_common->common.sunspec.getter(',
                            [
                                f'(InterfaceItem_void *) &{item_name},',
                                f'Meta_Value',
                            ],
                            f');',
                        ])
                    elif get_set == 'set':
                        body_lines.extend([
                            f'{item_name}.table_common->common.sunspec.setter(',
                            [
                                f'(InterfaceItem_void *) &{item_name},',
                                f'true,',
                                f'Meta_Value',
                            ],
                            f');',
                        ])
            elif converter is not None:
                converter = converter[get_set]
                if get_set == 'get':
                    formatted = embedded.format(
                        curve_type=self.curve_type,
                        interface_signal=interface_variable,
                        point_index=table_element.index,
                        axis=axis,
                        upper_axis=axis.upper(),
                        curve_index=self.curve_index,
                    )
                    left, equals, right = (
                        element.strip()
                        for element in formatted.partition('=')
                    )

                    right = right.rstrip(';')

                    if equals != '=':
                        raise Exception('do not yet know how to handle this')

                    body_lines.append(
                        f'{left} = {converter}({right});',
                    )
                elif get_set == 'set':
                    body_lines.append(embedded.format(
                        curve_type=self.curve_type,
                        interface_signal=f'{converter}(&{interface_variable})',
                        point_index=table_element.index,
                        axis=axis,
                        upper_axis=axis.upper(),
                        curve_index=self.curve_index,
                    ))
            else:
                body_lines.append(embedded.format(
                    curve_type=self.curve_type,
                    interface_signal=interface_variable,
                    point_index=table_element.index,
                    axis=axis,
                    upper_axis=axis.upper(),
                    curve_index=self.curve_index,
                ))

            function_name = '_'.join([
                f'{get_set}SunspecModel{self.model_id}',
                'Curve',
                f'{self.curve_index + 1:02}',
                table_element.abbreviation,
            ])
            function_signature = f'void {function_name} (void)'

            both_lines[0].extend([
                f'{function_signature} {{',
                body_lines,
                '}',
                '',
            ])

            both_lines[1].append(
                f'{function_signature};',
            )

        return both_lines
