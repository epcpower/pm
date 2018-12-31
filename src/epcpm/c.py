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
