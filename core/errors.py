import discord.app_commands as commands
from .utils import io


class Failure(commands.AppCommandError):
    """Should be raised in an app command to denote a failure.
    
    Handled in :class:`cogs.debug.Debug`.

    Inherits from :class:`~discord.app_commands.AppCommandError`.

    Parameters
    ----------
    message: str
        The message to display to the user.
    """
    def __init__(self, message: str):
        super().__init__(message)


class Warning(commands.AppCommandError):
    """Should be raised in an app command to denote a warning.
    
    Handled in :class:`cogs.debug.Debug`.

    Inherits from :class:`~discord.app_commands.AppCommandError`.

    Parameters
    ----------
    message: str
        The message to display to the user.
    """
    def __init__(self, message: str):
        super().__init__(message)
