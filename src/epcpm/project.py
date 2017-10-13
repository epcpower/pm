import pathlib

import attr
import graham
import marshmallow

import epyqlib.utils.qt


class ProjectSaveCanceled(Exception):
    pass


# class ProjectLoadCanceled(Exception):
#     pass


@graham.schemify(tag='models')
@attr.s
class Models:
    parameters = attr.ib(
        default=None,
        metadata=graham.create_metadata(
            field=marshmallow.fields.String()
        ),
    )
    symbols = attr.ib(
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
        self.symbols = value

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
            s = model.model.to_json_string()

            with open(project_directory / path, 'w') as f:
                f.write(s)

                if not s.endswith('\n'):
                    f.write('\n')


graham.register(Project)
