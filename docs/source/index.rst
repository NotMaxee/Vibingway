.. _index:

Welcome to Vibingway's documentation!
=====================================

.. note::

   **Hey there!** Please note that this documentation, much like this project,
   is unfinished. While it can help you set up the bot or find an API reference,
   it may be incomplete.

Welcome to the documentation for **Vibingway**, a multipurpose Discord bot for
small communities written in `Python 3.11`_ using `discord.py`_, `Lavalink`_ 
and `wavelink`_.

.. _Python 3.11: https://www.python.org/
.. _discord.py: https://discordpy.readthedocs.io/en/stable/
.. _Lavalink: https://github.com/lavalink-devs/Lavalink
.. _wavelink: https://wavelink.dev/en/latest/

If you want to host an instance of Vibingway yourself, please refer to the
following guides for manual installation or installation using docker.

.. toctree::
   :maxdepth: 1
   :caption: Guides

   guides/installation
   guides/installation_docker

If you are a developer and are looking for an API reference, check out the
core and cogs sections below. The core section concerns itself with the central
bot class, custom exceptions and utilities. For a reference for the various
command modules, check out the cogs section instead.

.. toctree::
   :maxdepth: 1
   :caption: Core

   core/bot
   core/errors
   core/utils

.. toctree::
   :maxdepth: 1
   :caption: Cogs

   cogs/banners
   cogs/debug
   cogs/music
   cogs/owner
   cogs/help

.. toctree::
   :maxdepth: 1
   :caption: Links

   GitHub <https://github.com/NotMaxee/Vibingway>
   Trello <https://trello.com/b/8ErDEEjs/vibingway>

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
