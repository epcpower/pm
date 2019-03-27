import pathlib

import attr
import graham
import marshmallow

import epyqlib.pm.parametermodel
import epyqlib.utils.qt

import epcpm.canmodel
import epcpm.sunspecmodel


class ProjectSaveCanceled(Exception):
    pass


# class ProjectLoadCanceled(Exception):
#     pass


def create_blank():
    project = Project()
    _post_load(project)

    return project


def loads(s, project_path=None, post_load=True):
    project = graham.schema(Project).loads(s).data

    if project_path is not None:
        project.filename = pathlib.Path(project_path).absolute()

    if post_load:
        _post_load(project)

    return project


def load(f, post_load=True):
    project = loads(f.read(), project_path=f.name, post_load=post_load)

    return project


def loadp(path, post_load=True):
    with open(path) as f:
        return load(f, post_load=post_load)


def _post_load(project):
    models = project.models

    if models.parameters is None:
        if project.paths.parameters is None:
            models.parameters = epyqlib.attrsmodel.Model(
                root=epyqlib.pm.parametermodel.Root(),
                columns=epyqlib.pm.parametermodel.columns,
            )
        else:
            models.parameters = load_model(
                project=project,
                path=project.paths.parameters,
                root_type=epyqlib.pm.parametermodel.Root,
                columns=epyqlib.pm.parametermodel.columns,
            )

    if models.can is None:
        if project.paths.can is None:
            models.can = epyqlib.attrsmodel.Model(
                root=epcpm.canmodel.Root(),
                columns=epcpm.canmodel.columns,
            )
        else:
            models.can = load_model(
                project=project,
                path=project.paths.can,
                root_type=epcpm.canmodel.Root,
                columns=epcpm.canmodel.columns,
            )

    if models.sunspec is None:
        if project.paths.sunspec is None:
            models.sunspec = epyqlib.attrsmodel.Model(
                root=epcpm.sunspecmodel.Root(),
                columns=epcpm.sunspecmodel.columns,
            )
        else:
            models.sunspec = load_model(
                project=project,
                path=project.paths.sunspec,
                root_type=epcpm.sunspecmodel.Root,
                columns=epcpm.sunspecmodel.columns,
                drop_sources=(models.parameters,),
            )

    models.parameters.droppable_from.add(models.parameters)

    models.can.droppable_from.add(models.parameters)
    models.can.droppable_from.add(models.can)

    models.sunspec.droppable_from.add(models.parameters)
    models.sunspec.droppable_from.add(models.sunspec)

    models.update_enumeration_roots()


@graham.schemify(tag='models')
@attr.s
class Models:
    parameters = attr.ib(
        default=None,
        metadata=graham.create_metadata(
            field=marshmallow.fields.String()
        ),
    )
    can = attr.ib(
        default=None,
        metadata=graham.create_metadata(
            field=marshmallow.fields.String()
        ),
    )
    sunspec = attr.ib(
        default=None,
        metadata=graham.create_metadata(
            field=marshmallow.fields.String()
        ),
    )

    @classmethod
    def __iter__(cls):
        return (field.name for field in attr.fields(cls))

    def set_all(self, value):
        self.parameters = value
        self.can = value
        self.sunspec = value

    def items(self):
        return attr.asdict(self, recurse=False).items()

    def values(self):
        return attr.asdict(self, recurse=False).values()

    def __getitem__(self, item):
        if isinstance(item, str):
            return attr.asdict(self, recurse=False)[item]

        return attr.astuple(self, recurse=False)[item]

    def __setitem__(self, item, value):
        if isinstance(item, str):
            setattr(self, item, value)
            return

        setattr(self, attr.fields(type(self))[item].name, value)

    def update_enumeration_roots(self):
        enumerations_root = [
            child
            for child in self.parameters.root.children
            if child.name == 'Enumerations'
        ]
        if len(enumerations_root) == 0:
            enumerations_root = None
        else:
            enumerations_root, = enumerations_root
        self.parameters.list_selection_roots[
            'enumerations'] = enumerations_root

        if enumerations_root is None:
            access_level_root = None
        else:
            access_level_root, = (
                child
                for child in enumerations_root.children
                if child.name == 'AccessLevel'
            )
        self.parameters.list_selection_roots[
            'access level'] = access_level_root

        if enumerations_root is None:
            visibility_root = None
        else:
            visibility_root, = (
                child
                for child in enumerations_root.children
                if child.name == 'CmmControlsVariant'
            )
        self.parameters.list_selection_roots['visibility'] = visibility_root

        if enumerations_root is None:
            sunspec_types_root = None
        else:
            sunspec_types_root = [
                child
                for child in enumerations_root.children
                if child.name == 'SunSpecTypes'
            ]
            if len(sunspec_types_root) == 1:
                sunspec_types_root, = sunspec_types_root
            else:
                sunspec_types_root = None
        self.parameters.list_selection_roots['sunspec types'] = (
            sunspec_types_root
        )
        self.sunspec.list_selection_roots['sunspec types'] = (
            sunspec_types_root
        )
        self.sunspec.list_selection_roots['enumerations'] = (
            enumerations_root
        )

        self.can.list_selection_roots['enumerations'] = (
            enumerations_root
        )
        self.parameters.update_nodes()
        self.can.update_nodes()
        self.sunspec.update_nodes()


@graham.schemify(tag='project')
@attr.s
class Project:
    paths = attr.ib(
        default=attr.Factory(Models),
        metadata=graham.create_metadata(
            field=marshmallow.fields.Nested(graham.schema(Models)),
        )
    )
    filename = attr.ib(default=None)
    models = attr.ib(default=attr.Factory(Models))
    filters = attr.ib(
        default=(
            ('Parameter Project', ['pmp']),
            ('All Files', ['*'])
        )
    )
    data_filters = attr.ib(
        default=(
            ('Dataset', ['json']),
            ('All Files', ['*'])
        )
    )

    def save(self, parent=None):
        if self.filename is None:
            project_path = epyqlib.utils.qt.file_dialog(
                filters=self.filters,
                parent=parent,
                save=True,
                caption='Save Project As',
            )

            if project_path is None:
                raise ProjectSaveCanceled()

            self.filename = pathlib.Path(project_path)

        project_directory = self.filename.parents[0]

        paths = Models()

        for name, path in self.paths.items():
            if path is not None:
                paths[name] = path
            else:
                new_path = epyqlib.utils.qt.file_dialog(
                    filters=self.data_filters,
                    parent=parent,
                    save=True,
                    caption='Save {} As'.format(name.title()),
                )

                if new_path is None:
                    raise ProjectSaveCanceled()

                paths[name] = (
                    pathlib.Path(new_path).relative_to(project_directory)
                )

        self.paths = paths

        with open(self.filename, 'w', newline='\n') as f:
            s = graham.dumps(self, indent=4).data
            f.write(s)

            if not s.endswith('\n'):
                f.write('\n')

        for path, model in zip(paths.values(), self.models.values()):
            s = graham.dumps(model.root, indent=4).data

            with open(project_directory / path, 'w', newline='\n') as f:
                f.write(s)

                if not s.endswith('\n'):
                    f.write('\n')


def load_model(project, path, root_type, columns, drop_sources=()):
    resolved_path = path
    if project.filename is not None:
        resolved_path = project.filename.parents[0] / resolved_path

    with open(resolved_path) as f:
        raw = f.read()

    root_schema = graham.schema(root_type)
    root = root_schema.loads(raw).data

    def collect(node, payload):
        payload[node.uuid] = node

    uuid_to_node = {}
    root.traverse(call_this=collect, payload=uuid_to_node, internal_nodes=True)

    def update(node, payload):
        for field in attr.fields(type(node)):
            if (
                field.metadata.get(graham.core.metadata_key) is None
                or not isinstance(
                    field.metadata.get(graham.core.metadata_key).field,
                    epyqlib.attrsmodel.Reference,
                )
            ):
                continue

            value = getattr(node, field.name)
            original = payload.get(value)
            if original is not None:
                setattr(node, field.name, original)

    root.traverse(call_this=update, payload=uuid_to_node, internal_nodes=True)

    return epyqlib.attrsmodel.Model(
        root=root,
        columns=columns,
        drop_sources=drop_sources,
    )
