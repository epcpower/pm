import epcpm._build

from ._version import get_versions
__version__ = get_versions()['version']
__sha__ = get_versions()['full-revisionid']
del get_versions

__version_tag__ = 'v{}'.format(__version__)
__build_tag__ = epcpm._build.job_id
