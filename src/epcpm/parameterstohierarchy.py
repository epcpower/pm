import json

import attr

import epyqlib.utils.general

import epcpm.parametermodel
import epcpm.symbolstosym

builders = epyqlib.utils.general.TypeMap()


dehumanize_name = epcpm.symbolstosym.dehumanize_name


@builders(epcpm.parametermodel.Root)
@attr.s
class Root:
    wrapped = attr.ib()
    symbol_root = attr.ib()

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
                    symbol_root=self.symbol_root,
                ).gen()
                for child in parameters.children
                if isinstance(
                    child,
                    (
                        epcpm.parametermodel.Group,
                        epcpm.parametermodel.Parameter,
                        # epcpm.parametermodel.EnumeratedParameter,
                    ),
                )
            ],
        }

        if not json_output:
            return d

        return json.dumps(d, **kwargs)


@builders(epcpm.parametermodel.Group)
@attr.s
class Group:
    wrapped = attr.ib()
    symbol_root = attr.ib()

    def gen(self):
        return {
            'name': self.wrapped.name,
            'children': [
                builders.wrap(
                    wrapped=child,
                    symbol_root=self.symbol_root,
                ).gen()
                for child in self.wrapped.children
            ],
        }


@builders(epcpm.parametermodel.Parameter)
@attr.s
class Parameter:
    wrapped = attr.ib()
    symbol_root = attr.ib()

    def gen(self):
        signal = self.symbol_root.node_from_uuid(
            target_uuid=self.wrapped.uuid,
            attribute_name='parameter_uuid',
        )

        message = signal.tree_parent

        return [
            dehumanize_name(message.name),
            dehumanize_name(signal.name),
        ]
