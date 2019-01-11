import re

import attr
import lxml.etree
import xmldiff.diff
import xmldiff.main


@attr.s(frozen=True)
class ErrorLogEntry:
    line = attr.ib()
    message = attr.ib()
    path = attr.ib()
    original = attr.ib(cmp=False, hash=False, repr=False)

    @classmethod
    def from_lxml(cls, original):
        return cls(
            line=original.line,
            message=original.message,
            path=original.path,
            original=original,
        )


@attr.s
class ValidationResult:
    failed = attr.ib()
    notes = attr.ib(default='')


def validate_against_schema(subject, schema):
    subject_xml = lxml.etree.fromstring(subject.read_bytes())
    success = schema.validate(subject_xml)

    errors = tuple(
        ErrorLogEntry.from_lxml(error)
        for error in schema.error_log
    )

    if len(errors) == 0:
        return ValidationResult(
            failed=False,
            notes='No validation errors for subject',
        )

    return ValidationResult(
        failed=not success,
        notes='\n'.join(f'{error}' for error in errors),
    )


def validate_against_reference(subject, schema, reference):
    failed = False

    schema.validate(reference)
    reference_error_log = schema.error_log
    schema.validate(subject)
    subject_error_log = schema.error_log
    reference_errors, subject_errors = (
        {
            ErrorLogEntry.from_lxml(original=original)
            for original in log
        }
        for log in (reference_error_log, subject_error_log)
    )

    diff = compare_to_reference(subject=subject, reference=reference)

    notes = []

    if len(diff) > 0:
        failed = True

        notes.extend(diff)

    if reference_errors != subject_errors:
        failed = True

    if not failed:
        return ValidationResult(
            failed=False,
            notes='No different errors between subject and reference',
        )

    reference_only = reference_errors - subject_errors
    subject_only = subject_errors - reference_errors
    if len(reference_only) > 0:
        notes.append('')
        notes.append('reference only:')
        notes.extend(f'{error}' for error in sorted(reference_only))
    if len(subject_only) > 0:
        notes.append('')
        notes.append('  subject only:')
        notes.extend(f'{error}' for error in sorted(subject_only))

    return ValidationResult(
        failed=True,
        notes='\n'.join(notes)
    )


def get_change_attribute(change):
    return change.node.rpartition('/')[2].partition('[')[0]


def ignore_read_only_scale_factor_to_writable(change, reference):
    attrib_name = 'access'

    if isinstance(change, xmldiff.diff.UpdateAttrib):
        of_interest = (
            get_change_attribute(change) == 'point'
            and change.name == attrib_name
            and change.value == 'rw'
        )
        if of_interest:
            # TODO: https://github.com/Shoobx/xmldiff/issues/33
            #       This is presently hazardous because if a previous
            #       change would cause things to move around then
            #       this may grab the incorrect element from the
            #       reference.
            left, = reference.xpath(change.node)
            if left.attrib.get('type') == 'sunssf':
                return left.attrib[attrib_name] == 'r'

    return False


def ignore_var_we_do_not_like(change, reference):
    attrib_name = 'units'

    if isinstance(change, xmldiff.diff.UpdateAttrib):
        of_interest = (
            get_change_attribute(change) == 'point'
            and change.name == attrib_name
            and change.value == 'VAr'
        )
        if of_interest:
            left, = reference.xpath(change.node)
            return left.attrib[attrib_name].casefold() == 'var'

    return False


def context_is_vendor_specific(context):
    attributes = context.context_node.attrib

    return re.search(r'Vnd\d*$', attributes['id']) is not None


def vendor_specific_elements(tree):
    function_namespace = lxml.etree.FunctionNamespace(None)
    function_namespace['vendor_specific'] = context_is_vendor_specific

    return tree.xpath(
        "/sunSpecModels/model/block/point[vendor_specific()]/symbol",
    ) + tree.xpath(
        "/sunSpecModels/strings/point[vendor_specific()]/symbol",
    )


def remove_element(element):
    parent = element.getparent()
    parent.remove(element)
    if len(parent) == 0 and len(parent.text.strip()) == 0:
        parent.text = None


def remove_elements_by_name(tree, names):
    xpath = '//*[{}]'.format(
        ' or '.join(f'name() = "{name}"' for name in names),
    )
    points = tree.xpath(xpath)

    for point in points:
        remove_element(element=point)

    return tree


def compare_to_reference(subject, reference):
    trimmed_subject, trimmed_reference = (
        remove_elements_by_name(tree=tree, names=('description', 'notes'))
        for tree in (subject, reference)
    )

    for element in vendor_specific_elements(trimmed_subject):
        remove_element(element=element)

    diff = xmldiff.main.diff_trees(trimmed_reference, trimmed_subject)

    return tuple(
        f'{change}'
        for change in diff
        if not any(
            f(
                change=change,
                reference=trimmed_reference,
            )
            for f in (
                ignore_read_only_scale_factor_to_writable,
                ignore_var_we_do_not_like,
            )
        )
    )


@attr.s
class PairedPaths:
    pairs = attr.ib(factory=dict)
    only_left = attr.ib(factory=list)
    only_right = attr.ib(factory=list)

    @classmethod
    def from_directories(cls, left_path, right_path, file_glob):
        left_paths = left_path.glob(file_glob)
        right_paths = right_path.glob(file_glob)

        left_relative_paths = {
            path.relative_to(left_path)
            for path in left_paths
        }

        right_relative_paths = {
            path.relative_to(right_path)
            for path in right_paths
        }

        only_left = {
            left_path/path
            for path in left_relative_paths - right_relative_paths
        }
        only_right = {
            right_path/path
            for path in right_relative_paths - left_relative_paths
        }
        common = left_relative_paths.intersection(right_relative_paths)

        paired_paths = {
            left_path/path: right_path/path
            for path in common
        }

        return cls(
            pairs=paired_paths,
            only_left=only_left,
            only_right=only_right,
        )
