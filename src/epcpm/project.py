import pathlib

import attr
import graham
import marshmallow

import epyqlib.pm.parametermodel
import epyqlib.utils.qt

import epcpm.canmodel


class ProjectSaveCanceled(Exception):
    pass


# class ProjectLoadCanceled(Exception):
#     pass


def create_blank():
    project = Project()
    _post_load(project)

    return project


def loads(s, project_path=None):
    project = graham.schema(Project).loads(s).data

    if project_path is not None:
        project.filename = pathlib.Path(project_path).absolute()

    _post_load(project)

    return project


def load(f):
    project = loads(f.read(), project_path=f.name)

    return project


def loadp(path):
    with open(path) as f:
        return load(f)


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
            )

    models.parameters.droppable_from.add(models.parameters)

    models.can.droppable_from.add(models.parameters)
    models.can.droppable_from.add(models.can)

    models.sunspec.droppable_from.add(models.parameters)
    models.sunspec.droppable_from.add(models.sunspec)

    enumerations_root = [
        child
        for child in models.parameters.root.children
        if child.name == 'Enumerations'
    ]
    if len(enumerations_root) == 0:
        enumerations_root = None
    else:
        enumerations_root, = enumerations_root
    models.parameters.list_selection_roots['enumerations'] = enumerations_root

    if enumerations_root is None:
        access_level_root = None
    else:
        access_level_root, = (
            child
            for child in enumerations_root.children
            if child.name == 'AccessLevel'
        )
    models.parameters.list_selection_roots['access level'] = access_level_root
    
    if enumerations_root is None:
        visibility_root = None
    else:
        visibility_root, = (
            child
            for child in enumerations_root.children
            if child.name == 'CmmControlsVariant'
       )
    models.parameters.list_selection_roots['visibility'] = visibility_root

    models.parameters.update_nodes()
    models.can.update_nodes()


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

        with open(self.filename, 'w') as f:
            s = graham.dumps(self, indent=4).data
            f.write(s)

            if not s.endswith('\n'):
                f.write('\n')

        for path, model in zip(paths.values(), self.models.values()):
            s = graham.dumps(model.root, indent=4).data

            with open(project_directory / path, 'w') as f:
                f.write(s)

                if not s.endswith('\n'):
                    f.write('\n')


def load_model(project, path, root_type, columns):
    resolved_path = path
    if project.filename is not None:
        resolved_path = project.filename.parents[0] / resolved_path

    with open(resolved_path) as f:
        raw = f.read()

    root_schema = graham.schema(root_type)
    root = root_schema.loads(raw).data

    return epyqlib.attrsmodel.Model(root=root, columns=columns)
