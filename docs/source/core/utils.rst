.. _core_utils:

``core.utilities``
##################

The utilities package provides various helpers and utilities that are
used by the command modules of the bot.

Database Helpers
****************

.. autofunction:: core.utils.db.init_db

Exit Codes
**********

.. autoclass:: core.utils.exitcodes.ExitCodes
    :members:

Embed and Message Helpers
*************************

.. autofunction:: core.utils.io.build_embed
.. autofunction:: core.utils.io.success
.. autofunction:: core.utils.io.warning
.. autofunction:: core.utils.io.failure

Views
=====

.. autoclass:: core.utils.io.Confirm

Logging Helper
**************

.. autofunction:: core.utils.log.setup_logging

String Helpers
**************

.. autofunction:: core.utils.string.truncate
.. autofunction:: core.utils.string.human_join
.. autofunction:: core.utils.string.format_milliseconds