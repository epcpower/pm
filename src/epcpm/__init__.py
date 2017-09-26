import pkg_resources

try:
    __version__ = pkg_resources.get_distribution(__name__).version
except pkg_resources.DistributionNotFound:
    # TODO: probably a different exception when pyinstaller'ed
    import epcpm._version
    __version__ = epcpm._version.__version__

__version_tag__ = __version__
__build_tag__ = None
