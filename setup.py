import setuptools



setuptools.setup(
    name="Parameter Management",
    use_scm_version={'version_scheme': 'post-release'},
    author="EPC Power Corp.",
    classifiers=[
        ("License :: OSI Approved :: "
         "GNU General Public License v2 or later (GPLv2+)")
    ],
    packages=setuptools.find_packages(),
    entry_points={'gui_scripts': ['pm = pm.__main__:_entry_point']},
    install_requires=[
        'PyQt5==5.9',
        'SIP==4.19.3'
    ],
    setup_requires=[
        'setuptools_scm',
    ],
)
