import inspect
import logging
import traceback
from io import BytesIO

import discord
import discord.app_commands as commands
from discord.ext.commands import Bot, Cog

from core.utils import io, string
from core.errors import Failure, Warning
from .handlers import *


class Debug(Cog):
    """Cog for debugging functionality."""

    def __init__(self, bot: Bot):
        super().__init__()

        # Internal setup.
        self.log = logging.getLogger(__name__)
        self.bot = bot

        # Default exception handlers.
        self.handlers = {

            # Built-in errors.
            commands.BotMissingPermissions: handle_bot_missing_permissions,
            

            # Custom errors.
            Failure: handle_failure,
            Warning: handle_warning,
        }

        # Logging webhook.
        self.webhook: discord.Webhook = None
        self.bot.loop.create_task(self.setup())

    async def setup(self):
        # Internal webhook setup.
        if not self.bot.config.logging_webhook:
            self.log.info("No logging webhook configured.")
            return

        self.webhook = discord.Webhook.from_url(
            self.bot.config.logging_webhook,
            session=self.bot.session)
        
    # Handler registration.

    def add_handler(self, exception, func):
        """Register a handler for an exception type.
        
        The handler function must accept the same arguments as
        :func:`discord.on_app_command_error` and return an embed
        that will be sent through the interaction.
        """
        if not issubclass(exception, Exception):
            raise TypeError("exception must be an Exception subclass")

        if not inspect.iscoroutinefunction(func):
            raise TypeError("func must be a coroutine")

        self.handlers[exception] = func

    def remove_handler(self, exception):
        """Remove the exception handler for an exception type."""
        if not issubclass(exception, Exception):
            raise TypeError("exception must be an Exception subclass")
        
        try:
            del self.handlers[exception]
        except KeyError:
            pass

    async def handle_unhandled_app_command_error(self, interaction: discord.Interaction, error: commands.AppCommandError) -> discord.Embed:
        # Default error handler for app commands.
        command = interaction.command.qualified_name
        self.log.error(f"An error occured in command {command!r}!", exc_info=error)

        self.bot.loop.create_task(self.log_app_command_error(interaction, error))

        embed = io.failure("An unhandled error has occured while running this command and has been reported to the developer.")
        return embed

    # Helper methods.

    async def log_error(self, error):
        """Log arbitrary exceptions through the logging webhook."""
        now = discord.utils.utcnow()

        name = type(error).__name__
        trace = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        file, line, func, text = traceback.extract_tb(error.__traceback__)[-1]
        details = f"{name} raised in file {file}, line {line} in {func}."

        fields = list()
        fields.append(dict(name="Error", value=details, inline=False))
        fields.append(dict(name="Traceback", value=f"```\n{string.truncate(trace, 990)}```", inline=False))
        
        embed = io.failure(
            f"Error report for `{name}`.",
            fields=fields,
            timestamp=now
        )

        params = dict(embed=embed, username=self.bot.user.name, avatar_url=self.bot.user.avatar.url)
        if len(trace) > 1000:
            stamp = now.strftime("%d-%m-%Y_%H-%M-%S_%f")
            buffer = BytesIO(trace.encode("utf-8"))
            params["file"] = discord.File(buffer, f"error_{stamp}.txt")

        try:
            await self.webhook.send(**params)
        except Exception as err:
            self.log.error("Failed to send error through webhook.", exc_info=err)

    async def log_app_command_error(self, interaction: discord.Interaction, error: commands.AppCommandError):
        """Log app command exceptions through the logging webhook."""
        if self.webhook is None:
            return

        # Unpack nested errors.
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
        
        # Collect error information.
        user = interaction.user
        command = interaction.command

        name = type(error).__name__
        trace = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        file, line, func, text = traceback.extract_tb(error.__traceback__)[-1]
        details = f"{name} raised in file {file}, line {line} in {func}."

        # Generate embed
        fields = []
        fields.append(dict(name="Author", value=f"{user}", inline=False))
        fields.append(dict(name="Channel", value=interaction.channel.mention))
        fields.append(dict(name="Error", value=details, inline=False))
        fields.append(dict(name="Traceback", value=f"```\n{string.truncate(trace, 990)}```", inline=False))

        embed = io.failure(
            f"Error report for command `/{command.qualified_name}`.",
            author=dict(name=user, icon=user.avatar.url),
            fields=fields,
            timestamp=interaction.created_at
        )

        params = dict(embed=embed, username=self.bot.user.name, avatar_url=self.bot.user.avatar.url)
        if len(trace) > 1000:
            stamp = interaction.created_at.strftime("%d-%m-%Y_%H-%M-%S_%f")
            buffer = BytesIO(trace.encode("utf-8"))
            params["file"] = discord.File(buffer, f"error_{stamp}.txt")

        try:
            await self.webhook.send(**params)
        except Exception as err:
            self.log.error("Failed to send app command error through webhook.", exc_info=err)

    # Event handlers.

    @Cog.listener(name="on_interaction")
    async def handle_interaction(self, interaction: discord.Interaction):
        # Logs used app commands to console.
        if isinstance(interaction.command, commands.Command):
            command = interaction.command.qualified_name
            self.log.info(f"{interaction.user} used /{command}.")

    @Cog.listener("on_app_command_error")
    async def handle_app_command_error(self, interaction: discord.Interaction, error: commands.AppCommandError):
        # Find a suitable error handler for the exception and process it.
        if not interaction.response.is_done():
            await interaction.response.defer()

        handler = self.handlers.get(type(error), self.handle_unhandled_app_command_error)
        
        try:
            embed = await handler(interaction, error)
        except Exception as err:
            self.log.error(f"An error occured in the error handler for {type(error)}!", exc_info=err)
            return

        if embed:
            await interaction.followup.send(embed=embed)

