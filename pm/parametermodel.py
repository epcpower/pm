import epyqlib.abstractcolumns
import epyqlib.pyqabstractitemmodel
import epyqlib.treenode

import pm.parameters

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


class Columns(epyqlib.abstractcolumns.AbstractColumns):
    _members = ['name']

Columns.indexes = Columns.indexes()


class Parameter(epyqlib.treenode.TreeNode):
    def __init__(self, parameter, parent=None):
        super().__init__(parent=parent)

        self.fields = Columns()

        self._parameter = None
        self.parameter = parameter

    @property
    def parameter(self):
        return self._parameter

    @parameter.setter
    def parameter(self, parameter):
        self._parameter = parameter

        self.fields.name = self.parameter.name


class Group(epyqlib.treenode.TreeNode):
    def __init__(self, group, parent=None):
        super().__init__(parent=parent)

        self.fields = Columns()

        self._group = None
        self.group = group

    @property
    def group(self):
        return self._group

    @group.setter
    def group(self, group):
        self._group = group

        self.fields.name = self.group.name


class ParameterModel(epyqlib.pyqabstractitemmodel.PyQAbstractItemModel):
    def __init__(self, parent=None):
        root_group = pm.parameters.Group(name='root')

        super().__init__(root=Group(root_group), parent=parent)

        self.headers = Columns(
            name='Name'
        )
