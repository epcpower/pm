import setuptools

import versioneer


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
        'canmatrix',
        'click',
        'epyqlib>=2019.4.3',
        'graham',
        'lxml',
        'openpyxl',
        'pycparser',
        'pysunspec',
        'pyqt5',
        'xmldiff',
    ],
    extras_require={
        'test': [
            'codecov',
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
