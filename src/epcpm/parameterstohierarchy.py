import json

import attr

import epyqlib.pm.parametermodel
import epyqlib.utils.general

import epcpm.cantosym

builders = epyqlib.utils.general.TypeMap()


dehumanize_name = epcpm.cantosym.dehumanize_name


@builders(epyqlib.pm.parametermodel.Root)
@attr.s
class Root:
    wrapped = attr.ib()
    can_root = attr.ib()

    def gen(self, json_output=True, **kwargs):
        parameters = next(
            node
            for node in self.wrapped.children
            if node.name == 'Parameters'
        )

        d = {
            'children': [
                builders.wrap(
                    wrapped=child,
                    can_root=self.can_root,
                ).gen()
                for child in parameters.children
                if isinstance(
                    child,
                    (
                        epyqlib.pm.parametermodel.Group,
                        epyqlib.pm.parametermodel.Parameter,
                        # epcpm.parametermodel.EnumeratedParameter,
                    ),
                )
            ],
        }

        if not json_output:
            return d

        return json.dumps(d, **kwargs)


@builders(epyqlib.pm.parametermodel.Group)
@attr.s
class Group:
    wrapped = attr.ib()
    can_root = attr.ib()

    def gen(self):
        return {
            'name': self.wrapped.name,
            'children': [
                builders.wrap(
                    wrapped=child,
                    can_root=self.can_root,
                ).gen()
                for child in self.wrapped.children
            ],
        }


@builders(epyqlib.pm.parametermodel.Parameter)
@attr.s
class Parameter:
    wrapped = attr.ib()
    can_root = attr.ib()

    def gen(self):
        signal = self.can_root.nodes_by_attribute(
            attribute_value=self.wrapped.uuid,
            attribute_name='parameter_uuid',
        ).pop()

        message = signal.tree_parent

        return [
            dehumanize_name(message.name),
            dehumanize_name(signal.name),
        ]


@builders(epyqlib.pm.parametermodel.Table)
@attr.s
class Table:
    wrapped = attr.ib()
    can_root = attr.ib()

    def gen(self):
        group, = (
            child
            for child in self.wrapped.children
            if isinstance(child, epyqlib.pm.parametermodel.TableGroupElement)
        )
        return {
            'name': self.wrapped.name,
            'children': builders.wrap(
                wrapped=group,
                can_root=self.can_root,
            ).gen()['children'],
        }


@builders(epyqlib.pm.parametermodel.TableGroupElement)
@attr.s
class TableGroupElement:
    wrapped = attr.ib()
    can_root = attr.ib()

    def gen(self):
        return {
            'name': self.wrapped.name,
            'children': [
                builders.wrap(
                    wrapped=child,
                    can_root=self.can_root,
                ).gen()
                for child in self.wrapped.children
            ],
        }


@builders(epyqlib.pm.parametermodel.TableArrayElement)
@attr.s
class TableArrayElement:
    wrapped = attr.ib()
    can_root = attr.ib()

    def gen(self):
        return self.wrapped.name
