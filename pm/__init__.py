import pkg_resources


try:
    __version__ = pkg_resources.get_distribution(__name__).version
except pkg_resources.DistributionNotFound:
    # TODO: probably a different exception when pyinstaller'ed
    import pm._version
    __version__ = pm._version.__version__
