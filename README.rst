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
- ``git clone https://github.com/altendky/pm``
- ``cd pm``
- ``git submodule update --init``
- ``poetry install``

- wait
- wait some more...
- ...

To launch PM run ``.venv\Scripts\epcpm.exe or poetry run epcpm``.

.. _`Git`: https://git-scm.com/download