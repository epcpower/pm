try:
    from epcpm.__version import __version__, __sha__, __revision__
except ImportError:
    __version__ = None
    __sha__ = None
    __revision__ = None
