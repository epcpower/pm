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

- Download artifact from the `latest ci run on github actions`_
- Extract contents of the ``.zip`` file
- Run ``epcpm.exe``

A minimal sample project is available at ``src/epcpm/tests/project/project.pmp``.

.. _`pm github actions`: https://github.com/epcpower/pm/actions

-------------------
Running From Source
-------------------

Windows & Linux
=======

- Install `Poetry`_
- Install `Git`_
- ``git clone https://github.com/epcpower/pm``
- ``cd pm``
- ``git submodule update --init``
- ``poetry install``

To launch PM run ``poetry run epcpm or .venv\Scripts\epcpm.exe``.

.. _`Poetry`: https://python-poetry.org/
.. _`Git`: https://git-scm.com/download
