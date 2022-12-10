import asyncio
import logging

import aiohttp
import asyncpg
import discord
from discord.ext import commands

from .utils.db import init_db


class Vibingway(commands.Bot):
    """The central :class:`~discord.ext.commands.Bot` subclass."""

    def __init__(self):
        super().__init__(
            intents=discord.Intents.default(),
            command_prefix="?",
            help_command=None
        )

        # Internal setup.
        self.log = logging.getLogger(__name__)
        self.tree.on_error = self._dispatch_command_tree_error

        self._session: aiohttp.ClientSession = None
        self._db: asyncpg.Pool = None
        self._global_sync_task: asyncio.Task = None
        self._admin_sync_task: asyncio.Task = None
        self._exit_code: int = 0

    @property
    def db(self):
        """asyncpg.Pool: The bot's database connection."""
        return self._db

    @property
    def session(self):
        """aiohttp.ClientSession: The bot's client session."""
        return self._session

    @property
    def config(self):
        """Returns the configuration module."""
        return __import__("config")

    @property
    def exit_code(self) -> int:
        """int: Returns the exit code."""
        return self._exit_code

    @property
    def global_sync_task(self):
        return self._global_sync_task

    @property
    def admin_sync_task(self):
        return self._admin_sync_task

    async def _dispatch_command_tree_error(self, *args, **kwargs):
        self.dispatch("app_command_error", *args, **kwargs)

    async def on_ready(self):
        self.log.info(f"Logged in as {self.user} (id: {self.user.id}).")

        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Game("good vibes.")
        )

    async def setup_hook(self):
        """Performs the initial setup of loading extensions and syncing commands."""
        self.log.info("Performing initial setup.")

        # Connect to database.
        self.log.info("Step 1/4: Connecting to database...")
        self._db = await init_db(**self.config.database_credentials)

        # Create client session.
        self.log.info("Step 2/4: Creating client session...")
        self._session = aiohttp.ClientSession()

        # Load extensions.
        self.log.info("Step 3/4: Loading extensions...")
        for ext in self.config.extensions:
            try:
                await self.load_extension(ext)
            except Exception as err:
                self.log.error(f"Unable to load {ext!r}!", exc_info=err)
                await self.close()
                return

        # Sync commands to admin guilds.
        self.log.info("Step 4/4: Syncing all commands...")
        self.sync_global_commands()
        self.sync_admin_commands()

        self.log.info("Initial setup complete.")

    def sync_global_commands(self):
        """asyncio.Task: Create a task to sync global application commands."""
        if self._global_sync_task and not self._global_sync_task.done():
            self.log.info("Cancelling outstanding global sync task.")
            self._global_sync_task.cancel()

        self._global_sync_task = self.loop.create_task(self._sync_global_commands())
        return self._global_sync_task
        
    async def _sync_global_commands(self):
        """Sync the command tree with discord."""
        self.log.info("Syncing global commands.")
        await self.tree.sync()
        self.log.info("Finished syncing global commands.")

    def sync_admin_commands(self):
        """asyncio.Task: Create a task to sync all commands to admin guilds."""
        if self._admin_sync_task and not self._admin_sync_task.done():
            self.log.info("Cancelling outstanding admin sync task.")
            self._admin_sync_task.cancel()
        
        self._admin_sync_task = self.loop.create_task(self._sync_admin_commands())
        return self._admin_sync_task
    
    async def _sync_admin_commands(self):
        """Sync all commands to admin guilds."""
        self.log.info("Syncing all commands to admin guilds.")

        for guild_id in self.config.admin_guilds:
            guild = self.get_guild(guild_id) or discord.Object(id=guild_id)
            self.log.info(f"Syncing commands for guild {guild}.")
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            self.log.info(f"Finished syncing commands for guild {guild}.")
        
        self.log.info("Finished syncing commands to admin guilds.")
            
    async def add_cog(self, cog, *args, **kwargs):
        await super().add_cog(cog, *args, **kwargs)
        self.dispatch("cog_add", cog)

    async def remove_cog(self, cog, *args, **kwargs):
        await super().remove_cog(cog, *args, **kwargs)
        self.dispatch("cog_remove", cog)

    async def close(self, exit_code:int=0) -> None:
        """Closes the connection to Discord.
        
        Parameters
        ----------
        exit_code: int
            Optional exit code to return when the bot has closed.
            Defaults to ``0``.
        """
        self._exit_code = exit_code
        await super().close()
        
        try:
            await self._session.close()
            await self._db.close()
        except Exception as err:
            self.log.error("An error occured during cleanup.", exc_info=err)
    
    def run(self, *args, **kwargs):
        super().run(*args, token=self.config.token, log_handler=None, **kwargs)
        return self._exit_code

