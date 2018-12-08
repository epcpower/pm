import collections

import attr
import openpyxl

import epyqlib.pm.parametermodel
import epyqlib.utils.general

import epcpm.sunspecmodel

builders = epyqlib.utils.general.TypeMap()


@builders(epcpm.sunspecmodel.Root)
@attr.s
class Root:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)
    parameter_model = attr.ib(default=None)

    def gen(self):
        workbook = openpyxl.Workbook()
        workbook.remove(workbook.active)

        for model in self.wrapped.children:
            worksheet = workbook.create_sheet()

            builders.wrap(
                wrapped=model,
                worksheet=worksheet,
                parameter_uuid_finder=self.parameter_uuid_finder,
            ).gen()

        return workbook


@builders(epcpm.sunspecmodel.Model)
@attr.s
class Model:
    wrapped = attr.ib()
    worksheet = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

    def gen(self):
        self.worksheet.title = str(self.wrapped.id)
