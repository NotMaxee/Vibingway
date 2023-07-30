.. _core_bot:

``core.bot``
############

Vibingway
*********

The central :class:`discord.ext.commands.Bot` subclass used by this project.
It provides a central reference to the configuration module, the database
connection and a client session for modules to use.

Further, it provides helper methods for command synchronization.

.. autoclass:: core.Vibingway
    :members: