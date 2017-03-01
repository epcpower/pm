import platform

from setuptools import setup, find_packages

setup(
    name="Parameter Management",
    version="0.1",
    author="EPC Power Corp.",
    classifiers=[
        ("License :: OSI Approved :: "
         "GNU General Public License v2 or later (GPLv2+)")
    ],
    packages=find_packages(),
    entry_points={'gui_scripts': ['pm = pm.__main__:_entry_point']},
    install_requires=[
        'PyQt5==5.8.0',
        'SIP==4.19.1'
    ]
)
