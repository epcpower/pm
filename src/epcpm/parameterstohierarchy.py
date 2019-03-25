import json

import attr

import epyqlib.pm.parametermodel
import epyqlib.utils.general

import epcpm.cantosym

builders = epyqlib.utils.general.TypeMap()


dehumanize_name = epcpm.cantosym.dehumanize_name


def export(path, can_model, parameters_model):
    builder = epcpm.parameterstohierarchy.builders.wrap(
        wrapped=parameters_model.root,
        can_root=can_model.root,
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='\n') as f:
        f.write(builder.gen(indent=4))


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

        def can_node_wanted(node):
            if getattr(node, 'parameter_uuid', None) is None:
                return False

            parameter_query_parent = node.tree_parent.tree_parent

            is_a_can_table = isinstance(
                node.tree_parent.tree_parent,
                epcpm.canmodel.CanTable,
            )
            if is_a_can_table:
                parameter_query_parent = parameter_query_parent.tree_parent

            is_a_query = (
                getattr(parameter_query_parent, 'name', '')
                == 'ParameterQuery'
            )
            if not is_a_query:
                return False

            return True

        can_nodes_with_parameter_uuid = self.can_root.nodes_by_filter(
            filter=can_node_wanted,
        )

        parameter_uuid_to_can_node = {
            node.parameter_uuid: node
            for node in can_nodes_with_parameter_uuid
        }

        lengths_equal = (
            len(can_nodes_with_parameter_uuid)
            == len(parameter_uuid_to_can_node)
        )
        if not lengths_equal:
            raise Exception()

        d = {
            'children': [
                builders.wrap(
                    wrapped=child,
                    can_root=self.can_root,
                    parameter_uuid_to_can_node=parameter_uuid_to_can_node,
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
    parameter_uuid_to_can_node = attr.ib()

    def gen(self):
        return {
            'name': self.wrapped.name,
            'children': [
                result
                for result in (
                    builders.wrap(
                        wrapped=child,
                        can_root=self.can_root,
                        parameter_uuid_to_can_node=(
                            self.parameter_uuid_to_can_node
                        ),
                    ).gen()
                    for child in self.wrapped.children
                )
                if result is not None
            ],
        }


@builders(epyqlib.pm.parametermodel.Parameter)
@attr.s
class Parameter:
    wrapped = attr.ib()
    can_root = attr.ib()
    parameter_uuid_to_can_node = attr.ib()

    def gen(self):
        signal = self.parameter_uuid_to_can_node.get(self.wrapped.uuid)

        if signal is None:
            return None

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
    parameter_uuid_to_can_node = attr.ib()

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
                parameter_uuid_to_can_node=self.parameter_uuid_to_can_node,
            ).gen()['children'],
        }


@builders(epyqlib.pm.parametermodel.TableGroupElement)
@attr.s
class TableGroupElement:
    wrapped = attr.ib()
    can_root = attr.ib()
    parameter_uuid_to_can_node = attr.ib()

    def gen(self):
        children = []
        for child in self.wrapped.children:
            result = builders.wrap(
                wrapped=child,
                can_root=self.can_root,
                parameter_uuid_to_can_node=self.parameter_uuid_to_can_node,
            ).gen()

            if result is not None:
                children.append(result)

        return {
            'name': self.wrapped.name,
            'children': children,
        }


@builders(epyqlib.pm.parametermodel.TableArrayElement)
@attr.s
class TableArrayElement:
    wrapped = attr.ib()
    can_root = attr.ib()
    parameter_uuid_to_can_node = attr.ib()

    def gen(self):
        signal = self.parameter_uuid_to_can_node.get(self.wrapped.uuid)

        if signal is None:
            return None

        message = signal.tree_parent

        can_table = message.tree_parent

        return [
            dehumanize_name(can_table.name + message.name),
            dehumanize_name(signal.name),
        ]
