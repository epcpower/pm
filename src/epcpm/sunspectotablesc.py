import attr
import typing
import epyqlib.utils.general
import epyqlib.pm.parametermodel

import epcpm.pm_helper
import epcpm.sunspecmodel


builders = epyqlib.utils.general.TypeMap()


def export(c_path, h_path, sunspec_model, sunspec_id, skip_sunspec=False):
    builder = builders.wrap(
        wrapped=sunspec_model.root,
        parameter_uuid_finder=sunspec_model.node_from_uuid,
        sunspec_id=sunspec_id,
        skip_sunspec=skip_sunspec,
    )

    c_path.parent.mkdir(parents=True, exist_ok=True)
    c_content, h_content = builder.gen()

    auto_gen_line = '/* Generated by "sunspectotablesc.py" */\n\n'
    c_lines = [
        '# include "interfaceGen.h"\n',
        f'# include "sunspec{sunspec_id.value}InterfaceGen.h"\n',
        f'# include "sunspec{sunspec_id.value}InterfaceGenTables.h"\n',
        '# include "interfaceAccessors.h"\n',
        '# include "IEEE1547.h"\n',
        '# include "gridMonitor.h"\n',
        # '# include "fanControl.h"\n',
        "\n",
        auto_gen_line,
        '# pragma SET_CODE_SECTION("SUNSPEC_TABLE_FUNCTIONS")\n',
    ]
    c_lines.extend(c_content)
    c_lines.extend(["#pragma SET_CODE_SECTION()\n"])

    h_lines = [auto_gen_line]
    h_lines.extend(h_content)

    with c_path.open("w", newline="\n") as f:
        for c_line in c_lines:
            f.write(c_line)

    with h_path.open("w", newline="\n") as f:
        for h_line in h_lines:
            f.write(h_line)


# TODO: CAMPid 079549750417808543178043180
def get_curve_type(combination_string):
    # TODO: backmatching
    return {
        "LowRideThrough": "IEEE1547_CURVE_TYPE_LRT",
        "HighRideThrough": "IEEE1547_CURVE_TYPE_HRT",
        "LowTrip": "IEEE1547_CURVE_TYPE_LTRIP",
        "HighTrip": "IEEE1547_CURVE_TYPE_HTRIP",
    }.get(combination_string)


@builders(epcpm.sunspecmodel.Root)
@attr.s
class Root:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib()
    sunspec_id = attr.ib(default=None)
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
                    sunspec_id=self.sunspec_id,
                )

                # table_results.append(builder.gen())
                # lines.extend(table_results[-1].table_lines)

                for lines, more_lines in zip(both_lines, builder.gen()):
                    lines.extend(more_lines)
                    lines.append("")

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
            epyqlib.utils.general.format_nested_lists(lines) for lines in both_lines
        )


@builders(epcpm.sunspecmodel.Model)
@attr.s
class Model:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib()
    sunspec_id = attr.ib()

    def gen(self):
        for child in self.wrapped.children:
            found = isinstance(
                child,
                (
                    epcpm.sunspecmodel.TableRepeatingBlockReference,
                    epcpm.sunspecmodel.TableBlock,
                ),
            )
            if found:
                break
        else:
            return [[], []]

        builder = builders.wrap(
            wrapped=child,
            parameter_uuid_finder=self.parameter_uuid_finder,
            model_id=self.wrapped.id,
            sunspec_id=self.sunspec_id,
        )

        return builder.gen()


@builders(epcpm.sunspecmodel.TableRepeatingBlockReference)
@attr.s
class TableRepeatingBlockReference:
    wrapped = attr.ib()
    model_id = attr.ib()
    parameter_uuid_finder = attr.ib()
    sunspec_id = attr.ib()

    def gen(self):
        builder = builders.wrap(
            wrapped=self.wrapped.original,
            model_id=self.model_id,
            parameter_uuid_finder=self.parameter_uuid_finder,
            sunspec_id=self.sunspec_id,
        )

        return builder.gen()


@builders(epcpm.sunspecmodel.TableRepeatingBlock)
@attr.s
class TableRepeatingBlock:
    wrapped = attr.ib()
    model_id = attr.ib()
    parameter_uuid_finder = attr.ib()
    sunspec_id = attr.ib()

    def gen(self):
        both_lines = [[], []]

        curve_group_string = "".join(
            self.parameter_uuid_finder(uuid).name for uuid in self.wrapped.path[:-1]
        )
        curve_type = get_curve_type(curve_group_string)

        for curve_index in range(self.wrapped.repeats):
            for point in self.wrapped.children:
                builder = builders.wrap(
                    wrapped=point,
                    model_id=self.model_id,
                    sunspec_id=self.sunspec_id,
                    curve_index=curve_index,
                    curve_type=curve_type,
                    parameter_uuid_finder=self.parameter_uuid_finder,
                )

                for lines, more_lines in zip(both_lines, builder.gen()):
                    lines.extend(more_lines)
                    lines.append("")

        return both_lines


@builders(epcpm.sunspecmodel.DataPoint)
@attr.s
class DataPoint:
    """Table generator for the SunSpec DataPoint class."""

    wrapped = attr.ib()
    model_id = attr.ib()
    sunspec_id = attr.ib()
    curve_index = attr.ib()
    curve_type = attr.ib()
    parameter_uuid_finder = attr.ib()

    def gen(self) -> typing.List[typing.List[str]]:
        """
        C table generator for the SunSpec DataPoint class.

        Returns:
            list of lists of strings: C output for table generation
        """
        table_element = self.parameter_uuid_finder(self.wrapped.parameter_uuid)
        curve_parent = table_element.tree_parent.tree_parent.tree_parent
        table_element = curve_parent.descendent(
            str(self.curve_index + 1),
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
                "get": array_or_group_element.can_getter,
                "set": array_or_group_element.can_setter,
            }
        elif is_array:
            getter_setter = {
                "get": parameter_table.can_getter,
                "set": parameter_table.can_setter,
            }

        if getter_setter["get"] is None:
            getter_setter["get"] = ""

        if getter_setter["set"] is None:
            getter_setter["set"] = ""

        return self._gen_common(table_element, parameter, getter_setter)

    def gen_for_table_block(self) -> typing.List[typing.List[str]]:
        """
        TableBlock specific generator for DataPoint table code generation.

        Returns:
            list of lists of strings: C output for table generation
        """
        table_element = self.parameter_uuid_finder(self.wrapped.parameter_uuid)
        common_parameter = self.parameter_uuid_finder(
            self.wrapped.common_table_parameter_uuid
        )

        getter_setter = {
            "get": common_parameter.can_getter,
            "set": common_parameter.can_setter,
        }

        return self._gen_common(table_element, table_element, getter_setter)

    def _gen_common(
        self,
        table_element: epyqlib.pm.parametermodel.TableArrayElement,
        parameter: epyqlib.pm.parametermodel.Parameter,
        getter_setter: typing.Dict,
    ) -> typing.List[typing.List[str]]:
        """
        Common generator for DataPoint table code generation.

        Args:
            table_element: table array element node to be output
            parameter: parameter node to be output
            getter_setter: dict of getter/setter output

        Returns:
            list of lists of strings: C output for table generation
        """
        axis = table_element.tree_parent.axis
        if axis is None:
            axis = "<no axis>"

        interface_variable = (
            f"sunspec{self.sunspec_id.value}Interface"
            f".model{self.model_id}"
            f".Curve_{self.curve_index + 1:02}_{table_element.abbreviation}"
        )

        both_lines = [[], []]

        for get_set, embedded in getter_setter.items():
            # TODO: CAMPid 075780541068182645821856068542023499
            converter = {
                "uint32": {
                    "get": "sunspecUint32ToSSU32_returns",
                    "set": "sunspecSSU32ToUint32",
                },
                "int32": {
                    # TODO: add this to embedded?
                    # 'get': 'sunspecInt32ToSSS32',
                    "set": "sunspecSSS32ToInt32",
                },
                "uint64": {
                    "get": "sunspecUint64ToSSU64_returns",
                    "set": "sunspecSSU64ToUint64",
                },
            }.get(self.parameter_uuid_finder(self.wrapped.type_uuid).name)

            body_lines = []

            if parameter.uses_interface_item():
                item_uuid_string = epcpm.pm_helper.convert_uuid_to_variable_name(
                    table_element.uuid
                )
                item_name = f"interfaceItem_{item_uuid_string}"

                if True:  # is_group:
                    if get_set == "get":
                        body_lines.extend(
                            [
                                f"{item_name}.table_common->common.sunspec{self.sunspec_id.value}.getter(",
                                [
                                    f"(InterfaceItem_void *) &{item_name},",
                                    f"Meta_Value",
                                ],
                                f");",
                            ]
                        )
                    elif get_set == "set":
                        body_lines.extend(
                            [
                                f"{item_name}.table_common->common.sunspec{self.sunspec_id.value}.setter(",
                                [
                                    f"(InterfaceItem_void *) &{item_name},",
                                    f"true,",
                                    f"Meta_Value",
                                ],
                                f");",
                            ]
                        )
            elif converter is not None:
                converter = converter[get_set]
                if get_set == "get":
                    formatted = embedded.format(
                        curve_type=self.curve_type,
                        interface_signal=interface_variable,
                        point_index=table_element.index,
                        axis=axis,
                        upper_axis=axis.upper(),
                        curve_index=self.curve_index,
                    )
                    left, equals, right = (
                        element.strip() for element in formatted.partition("=")
                    )

                    right = right.rstrip(";")

                    if equals != "=":
                        raise Exception("do not yet know how to handle this")

                    body_lines.append(
                        f"{left} = {converter}({right});",
                    )
                elif get_set == "set":
                    body_lines.append(
                        embedded.format(
                            curve_type=self.curve_type,
                            interface_signal=f"{converter}(&{interface_variable})",
                            point_index=table_element.index,
                            axis=axis,
                            upper_axis=axis.upper(),
                            curve_index=self.curve_index,
                        )
                    )
            else:
                body_lines.append(
                    embedded.format(
                        curve_type=self.curve_type,
                        interface_signal=interface_variable,
                        point_index=table_element.index,
                        axis=axis,
                        upper_axis=axis.upper(),
                        curve_index=self.curve_index,
                    )
                )

            function_name = "_".join(
                [
                    f"{get_set}Sunspec{self.sunspec_id.value}Model{self.model_id}",
                    "Curve",
                    f"{self.curve_index + 1:02}",
                    table_element.abbreviation,
                ]
            )
            function_signature = f"void {function_name} (void)"

            both_lines[0].extend(
                [
                    f"{function_signature} {{",
                    body_lines,
                    "}",
                    "",
                ]
            )

            both_lines[1].append(
                f"{function_signature};",
            )

        return both_lines


@builders(epcpm.sunspecmodel.TableBlock)
@attr.s
class TableBlock:
    """Table generator for the SunSpec TableBlock class."""

    wrapped = attr.ib()
    model_id = attr.ib()
    parameter_uuid_finder = attr.ib()
    sunspec_id = attr.ib()

    def gen(self) -> typing.List[typing.List[str]]:
        """
        C table generator for the SunSpec TableBlock class.

        Returns:
            list of lists of strings: C output for table generation
        """
        both_lines = [[], []]
        for child_index, point in enumerate(self.wrapped.children):
            # Should always be a TableGroup.
            builder = builders.wrap(
                wrapped=point,
                model_id=self.model_id,
                sunspec_id=self.sunspec_id,
                parameter_uuid_finder=self.parameter_uuid_finder,
                curve_index=child_index,
            )

            for lines, more_lines in zip(both_lines, builder.gen()):
                lines.extend(more_lines)
                lines.append("")

        return both_lines


@builders(epcpm.sunspecmodel.TableGroup)
@attr.s
class TableGroup:
    """Table generator for the SunSpec TableGroup class."""

    wrapped = attr.ib()
    model_id = attr.ib()
    parameter_uuid_finder = attr.ib()
    sunspec_id = attr.ib()
    curve_index = attr.ib()

    def gen(self) -> typing.List[typing.List[str]]:
        """
        C table generator for the SunSpec TableGroup class.

        Returns:
            list of lists of strings: C output for table generation
        """
        both_lines = [[], []]
        for point in self.wrapped.children:
            # A bit hacky. Assumption is being made that TableGroup's will only be two deep maximum.
            if isinstance(point, epcpm.sunspecmodel.TableGroup):
                builder = builders.wrap(
                    wrapped=point,
                    model_id=self.model_id,
                    sunspec_id=self.sunspec_id,
                    parameter_uuid_finder=self.parameter_uuid_finder,
                    curve_index=self.curve_index,
                )

                for lines, more_lines in zip(both_lines, builder.gen()):
                    lines.extend(more_lines)
                    lines.append("")
            else:
                if point.common_table_parameter_uuid:
                    builder = builders.wrap(
                        wrapped=point,
                        model_id=self.model_id,
                        sunspec_id=self.sunspec_id,
                        curve_index=self.curve_index,
                        curve_type="",
                        parameter_uuid_finder=self.parameter_uuid_finder,
                    )

                    for lines, more_lines in zip(
                        both_lines, builder.gen_for_table_block()
                    ):
                        lines.extend(more_lines)
                        lines.append("")

        return both_lines
