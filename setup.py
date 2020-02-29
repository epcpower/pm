import pathlib

import alqtendpy.compileui
import setuptools
import versioneer


alqtendpy.compileui.compile_ui(
    directory_paths=[pathlib.Path(__file__).parent  / 'src' / 'epcpm'],
)


setuptools.setup(
    name='epcpm',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    author="EPC Power Corp.",
    classifiers=[
        ("License :: OSI Approved :: "
         "GNU General Public License v2 or later (GPLv2+)")
    ],
    packages=setuptools.find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    entry_points={
        'gui_scripts': [
            'epcpm = epcpm.__main__:_entry_point',
        ],
        'console_scripts': [
            'epcpmcli = epcpm.cli.main:main',
            'epcparameterstoc = epcpm.cli.parameterstoc:cli',
            'epcimportsym = epcpm.cli.importsym:cli',
            'epcexportsym = epcpm.cli.exportsym:cli',
            'epcexportdocx = epcpm.cli.exportdocx:cli',
            'epcconvertparameters = epcpm.cli.convertepp:cli',
        ],
    },
    install_requires=[
        'canmatrix>=0.9.1',
        'click',
        'epyqlib>=2020.2.7',
        'graham',
        'jinja2',
        'lxml',
        'openpyxl',
        'pycparser',
        'pysunspec',
        'pyqt5',
        'toolz',
        'xmldiff',
    ],
    extras_require={
        'test': [
            'codecov',
            'gitignoreio',
            'pytest',
            'pytest-cov',
            'pytest-qt',
            'tox',
        ],
        'build': [
            'pyinstaller',
        ]
    },
)
