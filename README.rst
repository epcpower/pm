=================
Parameter Manager
=================

.. image:: https://img.shields.io/github/workflow/status/epcpower/pm/CI/master?color=seagreen&logo=GitHub-Actions&logoColor=whitesmoke
   :alt: tests on GitHub Actions
   :target: https://github.com/epcpower/pm/actions?query=branch%3Amaster

.. image:: https://img.shields.io/github/last-commit/epcpower/pm/master.svg
   :alt: source on GitHub
   :target: https://github.com/epcpower/pm

.. image:: screenshot.png
   :alt: Parameter Manager screenshot

-------------------
Running From Binary
-------------------

Windows
=======

- Download artifact from the `build history on Github`_
- Extract contents of the ``.zip`` file
- Run ``epcpm.exe``

A minimal sample project is available at ``src/epcpm/tests/project/project.pmp``.

.. _`build history on Github`: https://github.com/epcpower/pm/actions

-------------------
Running From Source
-------------------

Windows
=======

- Install `Python 3.7`_
- Install `Poetry`_
- Install `Git`_
- ``git clone https://github.com/epcpower/pm``
- ``cd pm``
- ``git submodule update --init``
- ``poetry@1.5.1 install``
- ``poetry@1.5.1 run builduipm``
- ``poetry@1.5.1 run builduiepyqlib``

To launch PM run ``poetry@1.5.1 run epcpm``.

.. _`Python 3.7`: https://www.python.org/downloads/
.. _`Poetry`: https://python-poetry.org/docs/
.. _`Git`: https://git-scm.com/download

Linux
=====

- Install Python 3.7

  - pyenv_ to get Python versions

- Install git
- ``git clone https://github.com/epcpower/pm``
- ``cd pm``
- ``git submodule update --init``
- ``poetry@1.5.1 install``
- ``poetry@1.5.1 run builduipm``
- ``poetry@1.5.1 run builduiepyqlib``

To launch PM run ``poetry@1.5.1 run epcpm``

A minimal sample project is available at ``src/epcpm/tests/project/project.pmp``.

.. _pyenv: https://github.com/pyenv/pyenv
