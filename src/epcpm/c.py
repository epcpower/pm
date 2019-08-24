import os

import jinja2


# TODO: CAMPid 073407143081341008467657184603164130
def format_nested_lists(it, indent=''):
    result = []

    for item in it:
        if isinstance(item, list):
            result.extend(format_nested_lists(item, indent=indent + '    '))
        elif item.strip() == '':
            result.append('')
        else:
            result.append(indent + item)

    if indent == '':
        result.append('')
        return '\n'.join(result)
    else:
        return result


def render(source, destination, context={}, encoding='utf-8', newline='\n'):
    environment = jinja2.Environment(
        undefined=jinja2.StrictUndefined,
        loader=jinja2.FileSystemLoader(os.fspath(source.parent)),
        newline_sequence=newline,
        autoescape=False,
        trim_blocks=True,
    )
    template = environment.get_template(name=source.name)

    rendered = template.render(context)
    rendered = rendered.rstrip() + newline

    destination.write_bytes(rendered.encode(encoding))
