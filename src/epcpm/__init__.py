import pkg_resources

import epcpm._build

try:
    __version__ = pkg_resources.get_distribution(__name__).version
    __sha__ = None
except pkg_resources.DistributionNotFound:
    # TODO: probably a different exception when pyinstaller'ed
    from epcpm._version import __version__, __sha__

__version_tag__ = 'v{}'.format(__version__)
__build_tag__ = epcpm._build.job_id
