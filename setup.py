import setuptools



setuptools.setup(
    name='epcpm',
    use_scm_version={'version_scheme': 'post-release'},
    author="EPC Power Corp.",
    classifiers=[
        ("License :: OSI Approved :: "
         "GNU General Public License v2 or later (GPLv2+)")
    ],
    packages=setuptools.find_packages('src'),
    package_dir={'': 'src'},
    entry_points={
        'gui_scripts': [
            'epcpm = epcpm.__main__:_entry_point',
        ],
        'console_scripts': [
            'epcparameterstoc = epcpm.cli.parameterstoc:cli',
            'epcimportsym = epcpm.cli.importsym:cli',
            'epcexportsym = epcpm.cli.exportsym:cli',
            'epcexportdocx = epcpm.cli.exportdocx:cli',
        ],
    },
    install_requires=[
        'canmatrix',
        'click',
        'graham',
        'pycparser',
        'pyqt5',
        'sip',
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
    setup_requires=[
        'setuptools_scm',
    ],
)
