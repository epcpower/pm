from __future__ import (
    annotations,
)  # See PEP 563, check to remove in future Python version higher than 3.7
import attr
import decimal
import openpyxl
import pathlib
import typing
import uuid
import epcpm.pm_helper
import epyqlib.treenode
import epyqlib.utils.general
from tqdm import tqdm
from time import sleep


PMVS_UUID_TO_DECIMAL_LIST = typing.List[typing.Dict[uuid.UUID, decimal.Decimal]]

builders = epyqlib.utils.general.TypeMap()


@attr.s
class Fields(epcpm.pm_helper.FieldsInterface):
    """The fields defined for a given row in the output XLS file."""

    parameter_name = attr.ib(default=None, type=typing.Union[str, bool])
    can_parameter_name = attr.ib(default=None, type=typing.Union[str, bool])
    description = attr.ib(default=None, type=typing.Union[str, bool])
    access_level = attr.ib(default=None, type=typing.Union[str, bool, int])
    units = attr.ib(default=None, type=typing.Union[str, bool])
    minimum = attr.ib(default=None, type=typing.Union[str, bool, decimal.Decimal])
    maximum = attr.ib(default=None, type=typing.Union[str, bool, decimal.Decimal])
    c1k_2l_2700_default = attr.ib(
        default=None, type=typing.Union[str, bool, decimal.Decimal]
    )
    c1k_2l_3500_default = attr.ib(
        default=None, type=typing.Union[str, bool, decimal.Decimal]
    )
    c1k_3l1_2700_default = attr.ib(
        default=None, type=typing.Union[str, bool, decimal.Decimal]
    )
    c1k_3l1_3500_default = attr.ib(
        default=None, type=typing.Union[str, bool, decimal.Decimal]
    )
    c1k_3l2_default = attr.ib(
        default=None, type=typing.Union[str, bool, decimal.Decimal]
    )
    pd250_default = attr.ib(default=None, type=typing.Union[str, bool, decimal.Decimal])
    pd500_default = attr.ib(default=None, type=typing.Union[str, bool, decimal.Decimal])
    hy_default = attr.ib(default=None, type=typing.Union[str, bool, decimal.Decimal])
    can_path = attr.ib(default=None, type=typing.Union[str, bool])
    parameter_path = attr.ib(default=None, type=typing.Union[str, bool])
    enumerator_list = attr.ib(default=None, type=typing.Union[str, bool])
    parameter_uuid = attr.ib(default=None, type=typing.Union[str, bool])


field_names = Fields(
    parameter_name="Parameter Name",
    can_parameter_name="CAN Parameter Name",
    description="Description",
    units="Units",
    access_level="Access Level",
    minimum="Minimum",
    maximum="Maximum",
    c1k_2l_2700_default="C1k 2L 2700Hz Default",
    c1k_2l_3500_default="C1k 2L 3500Hz Default",
    c1k_3l1_2700_default="C1k 3L1 2700Hz Default",
    c1k_3l1_3500_default="C1k 3L1 3500Hz Default",
    c1k_3l2_default="C1k 3L2 Default",
    pd250_default="PD250 Default",
    pd500_default="PD500 Default",
    hy_default="Hydra Default",
    can_path="CAN Path",
    parameter_path="Parameter Path",
    enumerator_list="Enumerator List",
    parameter_uuid="Parameter UUID",
)


def create_pmvs_uuid_to_value_list(
    pmvs_path: pathlib.Path,
) -> PMVS_UUID_TO_DECIMAL_LIST:
    """
    Creates the pmvs_uuid_to_value_list,
    which is a list of dict's for each pmvs,
    each containing a key -> value of UUID to decimal value

    Args:
        pmvs_path: directory path to the pmvs files

    Returns:
        list of PMVS UUID to decimal dict's
    """
    pmvs_list = []
    pmvs_file_path = pathlib.Path(pmvs_path) / "DG_Defaults-C1k_2L-2700Hz.pmvs"
    pmvs_list.append(epyqlib.pm.valuesetmodel.loadp(pmvs_file_path))
    pmvs_file_path = pathlib.Path(pmvs_path) / "DG_Defaults-C1k_2L-3500Hz.pmvs"
    pmvs_list.append(epyqlib.pm.valuesetmodel.loadp(pmvs_file_path))
    pmvs_file_path = pathlib.Path(pmvs_path) / "DG_Defaults-C1k_3L1-2700Hz.pmvs"
    pmvs_list.append(epyqlib.pm.valuesetmodel.loadp(pmvs_file_path))
    pmvs_file_path = pathlib.Path(pmvs_path) / "DG_Defaults-C1k_3L1-3500Hz.pmvs"
    pmvs_list.append(epyqlib.pm.valuesetmodel.loadp(pmvs_file_path))
    pmvs_file_path = pathlib.Path(pmvs_path) / "DG_Defaults-C1k_3L2.pmvs"
    pmvs_list.append(epyqlib.pm.valuesetmodel.loadp(pmvs_file_path))
    pmvs_file_path = pathlib.Path(pmvs_path) / "DG_Defaults-PD250.pmvs"
    pmvs_list.append(epyqlib.pm.valuesetmodel.loadp(pmvs_file_path))
    pmvs_file_path = pathlib.Path(pmvs_path) / "DG_Defaults-PD500.pmvs"
    pmvs_list.append(epyqlib.pm.valuesetmodel.loadp(pmvs_file_path))
    pmvs_file_path = pathlib.Path(pmvs_path) / "HY_Defaults.pmvs"
    pmvs_list.append(epyqlib.pm.valuesetmodel.loadp(pmvs_file_path))

    pmvs_uuid_to_value_list = []
    for pmvs in pmvs_list:
        pmvs_uuid_to_value = {}
        for child in pmvs.model.root.children:
            pmvs_uuid_to_value.update({child.parameter_uuid: child.value})
        pmvs_uuid_to_value_list.append(pmvs_uuid_to_value)

    return pmvs_uuid_to_value_list


def export(
    path: pathlib.Path,
    can_model: epyqlib.attrsmodel.Model,
    pmvs_path: pathlib.Path,
    column_filter: epcpm.pm_helper.FieldsInterface = None,
) -> None:
    """
    Generate the CAN model parameter data in Excel format (.xlsx).

    Args:
        path: path and filename for .xlsx file
        can_model: CAN model
        parameters_model: parameters model
        pmvs_path: directory path to the pmvs files
        column_filter: columns to be output to .xls file

    Returns:

    """
    pmvs_uuid_to_value_list = create_pmvs_uuid_to_value_list(pmvs_path)

    if column_filter is None:
        column_filter = epcpm.pm_helper.attr_fill(Fields, True)

    builder = epcpm.cantoxlsx.builders.wrap(
        wrapped=can_model.root,
        parameter_uuid_finder=can_model.node_from_uuid,
        column_filter=column_filter,
        pmvs_uuid_to_value_list=pmvs_uuid_to_value_list,
    )

    workbook = builder.gen()

    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


@builders(epcpm.canmodel.Root)
@attr.s
class Root:
    """Excel spreadsheet generator for the CAN Root class."""

    wrapped = attr.ib(type=epcpm.canmodel.Root)
    column_filter = attr.ib(type=Fields)
    parameter_uuid_finder = attr.ib(default=None, type=typing.Callable)
    # parameter_model = attr.ib(default=None, type=epyqlib.attrsmodel.Model)
    pmvs_uuid_to_value_list = attr.ib(default=None, type=PMVS_UUID_TO_DECIMAL_LIST)

    def gen(self) -> openpyxl.workbook.workbook.Workbook:
        """
        Excel spreadsheet generator for the CAN Root class.

        Returns:
            workbook: generated Excel workbook
        """
        workbook = openpyxl.Workbook()
        workbook.remove(workbook.active)
        worksheet = workbook.create_sheet("Parameters")
        worksheet.append(field_names.as_filtered_tuple(self.column_filter))

        for child in self.wrapped.children:
            rows = builders.wrap(
                wrapped=child,
                parameter_uuid_finder=self.parameter_uuid_finder,
                pmvs_uuid_to_value_list=self.pmvs_uuid_to_value_list,
            ).gen()

            for row in rows:
                worksheet.append(row.as_filtered_tuple(self.column_filter))

        return workbook


@builders(epcpm.canmodel.Signal)
@attr.s
class Signal:
    """Excel spreadsheet generator for the CAN Signal class."""

    wrapped = attr.ib(type=epcpm.canmodel.Signal)
    parameter_uuid_finder = attr.ib(default=None, type=typing.Callable)
    pmvs_uuid_to_value_list = attr.ib(default=None, type=PMVS_UUID_TO_DECIMAL_LIST)

    def gen(self) -> typing.List[Fields]:
        """
        Excel spreadsheet generator for the CAN Signal class.

        Returns:
            list of a single Fields row for Signal
        """
        if self.wrapped.parameter_uuid:
            row = Fields()
            parameter = self.parameter_uuid_finder(self.wrapped.parameter_uuid)
            self._set_pmvs_row_defaults(
                row, self.pmvs_uuid_to_value_list, self.wrapped.parameter_uuid
            )
            row.can_parameter_name = self.wrapped.name
            row.parameter_name = parameter.name
            row.parameter_uuid = str(self.wrapped.parameter_uuid)
            if isinstance(
                parameter,
                (
                    epyqlib.pm.parametermodel.Parameter,
                    epyqlib.pm.parametermodel.TableArrayElement,
                ),
            ):
                row.units = parameter.units
                row.description = parameter.comment
                access_level = self.parameter_uuid_finder(parameter.access_level_uuid)
                row.access_level = access_level.name
                if parameter.minimum is not None:
                    row.minimum = parameter.minimum
                if parameter.maximum is not None:
                    row.maximum = parameter.maximum

                if parameter.enumeration_uuid is not None:
                    enumeration = self.parameter_uuid_finder(parameter.enumeration_uuid)
                    child_enum_list = []
                    for child_enum in enumeration.children:
                        child_enum_list.append(
                            f"[{child_enum.value}] {child_enum.name}; "
                        )
                    row.enumerator_list = " ".join(child_enum_list)

            parameter_path_list = self._generate_path_list(parameter)
            row.parameter_path = " -> ".join(parameter_path_list)
            can_path_list = self._generate_path_list(self.wrapped)
            row.can_path = " -> ".join(can_path_list)

            return [row]
        return []

    @staticmethod
    def _generate_path_list(node: epyqlib.treenode.TreeNode) -> typing.List[str]:
        """
        Generate the node's path list.

        Args:
            node: tree node (from CAN model or Parameters model)

        Returns:
            node's path list
        """
        path_list = []
        node_parent = node
        while True:
            if node_parent.tree_parent is not None:
                path_list.insert(0, node_parent.tree_parent.name)
                node_parent = node_parent.tree_parent
            else:
                break
        if len(path_list) > 1:
            # Remove the unnecessary Parameters root element.
            path_list.pop(0)

        return path_list

    @staticmethod
    def _set_pmvs_row_defaults(
        row: Fields,
        pmvs_uuid_to_value_list: PMVS_UUID_TO_DECIMAL_LIST,
        parameter_uuid: uuid.UUID,
    ) -> None:
        """
        Local method to set the PMVS defaults for the given Fields row.

        Args:
            row: single Fields row for Signal
            pmvs_uuid_to_value_list: list of PMVS UUID to decimal dict's
            parameter_uuid: parameter UUID

        Returns:

        """
        default_vals = []
        for pmvs in pmvs_uuid_to_value_list:
            value = pmvs.get(parameter_uuid)
            default_vals.append(value)

        row.c1k_2l_2700_default = default_vals[0]
        row.c1k_2l_3500_default = default_vals[1]
        row.c1k_3l1_2700_default = default_vals[2]
        row.c1k_3l1_3500_default = default_vals[3]
        row.c1k_3l2_default = default_vals[4]
        row.pd250_default = default_vals[5]
        row.pd500_default = default_vals[6]
        row.hy_default = default_vals[7]


@builders(epcpm.canmodel.CanTable)
@builders(epcpm.canmodel.Message)
@builders(epcpm.canmodel.Multiplexer)
@builders(epcpm.canmodel.MultiplexedMessage)
@builders(epcpm.canmodel.MultiplexedMessageClone)
@attr.s
class GenericNode:
    """Excel spreadsheet generator for various CAN model classes."""

    wrapped = attr.ib(
        type=typing.Union[
            epcpm.canmodel.CanTable,
            epcpm.canmodel.Message,
            epcpm.canmodel.Multiplexer,
            epcpm.canmodel.MultiplexedMessage,
            epcpm.canmodel.MultiplexedMessageClone,
        ]
    )
    parameter_uuid_finder = attr.ib(default=None, type=typing.Callable)
    pmvs_uuid_to_value_list = attr.ib(default=None, type=PMVS_UUID_TO_DECIMAL_LIST)

    def gen(self) -> typing.List[Fields]:
        """
        Excel spreadsheet generator for various CAN model classes.

        Returns:
            list of Fields rows
        """
        output_list = []
        for child in self.wrapped.children:
            frame = builders.wrap(
                wrapped=child,
                parameter_uuid_finder=self.parameter_uuid_finder,
                pmvs_uuid_to_value_list=self.pmvs_uuid_to_value_list,
            ).gen()
            output_list.extend(frame)

        return output_list


def format_for_manual(
    input_path: pathlib.Path,
) -> None:
    """
    Translate the CAN model parameter data to formatted Excel format (.xlsx)
    for the purpose of insertion into the controls manual documentation.

    Args:
        input_path: path and filename for input .xlsx file

    Returns:

    """
    # The parameter query prefix on a large portion of the CAN parameter paths.
    PARAMETER_QUERY_PREFIX = "ParameterQuery -> "

    input_workbook = openpyxl.load_workbook(filename=input_path)
    input_worksheet = input_workbook.active
    input_worksheet_row_count = input_worksheet.max_row
    input_worksheet_col_count = input_worksheet.max_column

    output_path = input_path.with_name(
        input_path.stem + "_for_manual" + input_path.suffix
    )
    print(f"input spreadsheet: {input_path}")
    print(f"output spreadsheet: {output_path}")

    output_workbook = openpyxl.Workbook()
    output_workbook.remove(output_workbook.active)
    output_worksheet = output_workbook.create_sheet("Parameters")

    # Track the current row in the output worksheet.
    current_row = 1

    # Display a progress bar since the generation of the output takes a long time.
    print("Be patient. Generation of the output spreadsheet takes a long time.")
    with tqdm(total=input_worksheet_row_count) as progress_bar:
        for row in input_worksheet.iter_rows(
            min_row=2, max_col=input_worksheet_col_count
        ):
            can_parameter_path = row[15].value
            if can_parameter_path.startswith(PARAMETER_QUERY_PREFIX):
                # Chop off the parameter query prefix to match what is seen in the EPyQ parameters tab.
                can_parameter_path = can_parameter_path[len(PARAMETER_QUERY_PREFIX) :]
            parameter_name_out = f"{can_parameter_path}: {row[1].value}"
            description_out = row[2].value
            access_level_out = row[3].value
            units_out = row[4].value
            minimum_out = row[5].value
            maximum_out = row[6].value
            pd250_out = row[12].value
            pd500_out = row[13].value
            hy_out = row[14].value
            cab1k_2l_2700hz_out = row[7].value
            cab1k_2l_3500hz_out = row[8].value
            cab1k_3l1_2700hz_out = row[9].value
            enumerator_list = row[17].value

            if units_out:
                # If there is a units value, append it to the end of the numeric default value.
                if minimum_out is not None:
                    minimum_out = str(minimum_out) + units_out
                if maximum_out is not None:
                    maximum_out = str(maximum_out) + units_out
                if pd250_out is not None:
                    pd250_out = str(pd250_out) + units_out
                if pd500_out is not None:
                    pd500_out = str(pd500_out) + units_out
                if hy_out is not None:
                    hy_out = str(hy_out) + units_out
                if cab1k_2l_2700hz_out is not None:
                    cab1k_2l_2700hz_out = str(cab1k_2l_2700hz_out) + units_out
                if cab1k_2l_3500hz_out is not None:
                    cab1k_2l_3500hz_out = str(cab1k_2l_3500hz_out) + units_out
                if cab1k_3l1_2700hz_out is not None:
                    cab1k_3l1_2700hz_out = str(cab1k_3l1_2700hz_out) + units_out

            # Discover if all the product defaults are equal.
            all_defaults = [
                pd250_out,
                pd500_out,
                hy_out,
                cab1k_2l_2700hz_out,
                cab1k_2l_3500hz_out,
                cab1k_3l1_2700hz_out,
            ]
            all_defaults_same = len(set(all_defaults)) == 1

            # Track the rows used for each parameter entry.
            rows_used = 0

            # Add the parameter name and description cells.
            output_worksheet.append([parameter_name_out, description_out])
            if enumerator_list:
                # Add the enumerator list cell / row.
                output_worksheet.append(["", enumerator_list])
                rows_used += 1
            if all_defaults_same:
                # Output single Default cells section.
                output_worksheet.append(
                    [
                        "",
                        field_names.access_level,
                        "",
                        "",
                        field_names.minimum,
                        field_names.maximum,
                        "Default",
                    ]
                )
                output_worksheet.append(
                    ["", access_level_out, "", "", minimum_out, maximum_out, pd250_out]
                )
                rows_used += 2
            else:
                # Output multiple Default cells sections.
                output_worksheet.append(
                    [
                        "",
                        field_names.access_level,
                        "",
                        field_names.minimum,
                        "",
                        field_names.maximum,
                        "",
                    ]
                )
                output_worksheet.append(
                    ["", access_level_out, "", minimum_out, "", maximum_out, ""]
                )
                output_worksheet.append(
                    [
                        "",
                        field_names.pd250_default,
                        field_names.pd500_default,
                        field_names.hy_default,
                        field_names.c1k_2l_2700_default,
                        field_names.c1k_2l_3500_default,
                        field_names.c1k_3l1_2700_default,
                    ]
                )
                output_worksheet.append(
                    [
                        "",
                        pd250_out,
                        pd500_out,
                        hy_out,
                        cab1k_2l_2700hz_out,
                        cab1k_2l_3500hz_out,
                        cab1k_3l1_2700hz_out,
                    ]
                )
                rows_used += 4

            # Merge cells for parameter name.
            output_worksheet.merge_cells(
                start_row=current_row,
                start_column=1,
                end_row=current_row + rows_used,
                end_column=1,
            )
            # Set horizontal & vertical alignment for parameter name.
            output_worksheet[
                "A" + str(current_row)
            ].alignment = openpyxl.styles.alignment.Alignment(
                horizontal="left", vertical="top"
            )
            # Merge cells for description.
            output_worksheet.merge_cells(
                start_row=current_row, start_column=2, end_row=current_row, end_column=7
            )
            if enumerator_list:
                # Merge cells for enumerator list cell.
                output_worksheet.merge_cells(
                    start_row=current_row + 1,
                    start_column=2,
                    end_row=current_row + 1,
                    end_column=7,
                )

            if all_defaults_same:
                # Merge access level is 3 columns; minimum, maximum, and default stay at 1 column.
                if enumerator_list:
                    output_worksheet.merge_cells(
                        start_row=current_row + 2,
                        start_column=2,
                        end_row=current_row + 2,
                        end_column=4,
                    )
                    output_worksheet.merge_cells(
                        start_row=current_row + 3,
                        start_column=2,
                        end_row=current_row + 3,
                        end_column=4,
                    )
                else:
                    output_worksheet.merge_cells(
                        start_row=current_row + 1,
                        start_column=2,
                        end_row=current_row + 1,
                        end_column=4,
                    )
                    output_worksheet.merge_cells(
                        start_row=current_row + 2,
                        start_column=2,
                        end_row=current_row + 2,
                        end_column=4,
                    )
            else:
                # Merge each of access level, minimum, maximum, to 2 columns; no default column.
                # The product specific defaults each get their own column.
                if enumerator_list:
                    output_worksheet.merge_cells(
                        start_row=current_row + 2,
                        start_column=2,
                        end_row=current_row + 2,
                        end_column=3,
                    )
                    output_worksheet.merge_cells(
                        start_row=current_row + 2,
                        start_column=4,
                        end_row=current_row + 2,
                        end_column=5,
                    )
                    output_worksheet.merge_cells(
                        start_row=current_row + 2,
                        start_column=6,
                        end_row=current_row + 2,
                        end_column=7,
                    )
                    output_worksheet.merge_cells(
                        start_row=current_row + 3,
                        start_column=2,
                        end_row=current_row + 3,
                        end_column=3,
                    )
                    output_worksheet.merge_cells(
                        start_row=current_row + 3,
                        start_column=4,
                        end_row=current_row + 3,
                        end_column=5,
                    )
                    output_worksheet.merge_cells(
                        start_row=current_row + 3,
                        start_column=6,
                        end_row=current_row + 3,
                        end_column=7,
                    )
                else:
                    output_worksheet.merge_cells(
                        start_row=current_row + 1,
                        start_column=2,
                        end_row=current_row + 1,
                        end_column=3,
                    )
                    output_worksheet.merge_cells(
                        start_row=current_row + 1,
                        start_column=4,
                        end_row=current_row + 1,
                        end_column=5,
                    )
                    output_worksheet.merge_cells(
                        start_row=current_row + 1,
                        start_column=6,
                        end_row=current_row + 1,
                        end_column=7,
                    )
                    output_worksheet.merge_cells(
                        start_row=current_row + 2,
                        start_column=2,
                        end_row=current_row + 2,
                        end_column=3,
                    )
                    output_worksheet.merge_cells(
                        start_row=current_row + 2,
                        start_column=4,
                        end_row=current_row + 2,
                        end_column=5,
                    )
                    output_worksheet.merge_cells(
                        start_row=current_row + 2,
                        start_column=6,
                        end_row=current_row + 2,
                        end_column=7,
                    )

            # Update the current row with the number of rows used plus one to go to the next row.
            current_row += rows_used + 1
            progress_bar.update(1)

    output_workbook.save(output_path)
