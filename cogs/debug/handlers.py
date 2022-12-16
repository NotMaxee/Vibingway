import discord
import discord.app_commands as commands

from core.utils import io
from core.utils import string

# Built-in error handlers.

async def handle_bot_missing_permissions(interaction: discord.Interaction, error: commands.BotMissingPermissions):
    def _format(string):
        return string.replace("_", " ").replace("guild", "server").lower()


    perms = [_format(perm) for perm in error.missing_permissions]
    perms = string.human_join(perms, code=True)
    message =f"I require the {perms} permission(s) to do that."
    return io.failure(message)

# Custom error handlers.

async def handle_warning(interaction: discord.Interaction, error: commands.BotMissingPermissions):
    return io.warning(str(error))

async def handle_failure(interaction: discord.Interaction, error: commands.BotMissingPermissions):
    return io.failure(str(error))
