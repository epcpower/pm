=================
Parameter Manager
=================

|GitHub|

.. image:: screenshot.png
   :alt: Parameter Manager screenshot

.. |GitHub| image:: https://img.shields.io/github/last-commit/altendky/pm/master.svg
   :alt: source on GitHub
   :target: https://github.com/altendky/pm

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
- ``poetry install``
- ``poetry run builduipm``
- ``poetry run builduiepyqlib``

To launch PM run ``poetry run epcpm``.

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
- ``poetry install``
- ``poetry run builduipm``
- ``poetry run builduiepyqlib``

To launch PM run ``poetry run epcpm``

A minimal sample project is available at ``src/epcpm/tests/project/project.pmp``.

.. _pyenv: https://github.com/pyenv/pyenv
