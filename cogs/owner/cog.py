import asyncio
import logging
import textwrap
from contextlib import redirect_stdout
from io import StringIO, BytesIO
from typing import Union

import discord
import discord.app_commands as commands
from discord.ext.commands import Bot, Cog

from core.errors import Failure, Warning
from core.utils import ExitCodes, io, string

from .git import Git, GitError, NoCommits, NoRepository
from .ui import CodeModal, SQLModal
from .utils import create_table_representation

async def autocomplete_module(
    interaction: discord.Interaction,
    current: str
):
    """Autocomplete function for module names."""
    modules = interaction.client.extensions.keys()
    return [
        commands.Choice(name=module, value=module)
        for module in modules if current.lower() in module.lower()
    ]

class Owner(Cog):
    """Cog for owner commands."""

    def __init__(self, bot: Bot):
        super().__init__()

        # Internal setup.
        self.log = logging.getLogger(__name__)
        self.bot = bot
        self.git = Git()
        # Enforce interaction checks.
        self.owner.interaction_check = self.check
        self.module.interaction_check = self.check
        self.sync.interaction_check = self.check

        # Limit available guilds.
        restrict = commands.guilds(*self.bot.config.admin_guilds)
        restrict(self.owner)
        restrict(self.module)
        restrict(self.sync)

        # Need to manually set module as we are creating group objects directly
        # rather than creating a subclass for them. Otherwise reloading any
        # other extension produces an error.
        # See line 1588 in app_commands/commands.py.
        self.owner.module = self.__module__
        self.module.module = self.__module__
        self.sync.module = self.__module__

    async def check(self, interaction: discord.Interaction):
        """Restricts command usage to admin users."""
        return interaction.user.id in self.bot.config.admin_users

    # Command groups.

    owner = commands.Group(name="owner", description="Owner-only commands.", guild_only=True)
    module = commands.Group(name="module", description="Module-related commands.", parent=owner)
    sync = commands.Group(name="sync", description="Command synchronization commands.", parent=owner)

    # Owner commands.

    @owner.command(name="restart", description="Restart the bot.")
    async def owner_restart(self, interaction: discord.Interaction):
        view = io.Confirm(interaction.user)
        embed = io.message("Are you sure you want to restart the bot?")
        await interaction.response.send_message(embed=embed, view=view)
        await view.wait()

        if view.value is None:
            return
        elif not view.value:
            embed = io.success("Restart cancelled.")
            await interaction.followup.send(embed=embed)
        else:
            embed = io.success("Restarting. See you soon!")
            await interaction.followup.send(embed=embed)
            await self.bot.close(exit_code=ExitCodes.RESTART)

    @owner.command(name="shutdown", description="Shut the bot down.")
    async def owner_shutdown(self, interaction: discord.Interaction):
        
        view = io.Confirm(interaction.user)
        embed = io.message("Are you sure you want to shut down the bot?")
        await interaction.response.send_message(embed=embed, view=view)
        await view.wait()

        if view.value is None:
            return
        elif not view.value:
            embed = io.success("Shutdown cancelled.")
            await interaction.followup.send(embed=embed)
        else:
            embed = io.success("Shutting down. See you soon!")
            await interaction.followup.send(embed=embed)
            await self.bot.close(exit_code=ExitCodes.SHUTDOWN)

    @owner.command(name="sql", description="Run an SQL query.")
    async def owner_sql(self, interaction: discord.Interaction):
        
        # Prepare an SQL input modal.
        modal = SQLModal()
        await interaction.response.send_modal(modal)
        
        if await modal.wait():
            raise Failure("You took too long to respond.")
        elif not modal.sql:
            raise Failure("You did not provide a query to run.")
        
        query = modal.sql

        # Extract queries and run them.
        try:
            async with self.bot.db.acquire() as connection:
                if query.count(";") > 1:
                    results = await connection.execute(query)
                else:
                    results = await connection.fetch(query)
        except Exception as err:
            etype = type(err).__name__
            embed = io.failure("An error occured.", fields=[dict(name="Error", value=f"**{etype}**: {err}")])
            await interaction.followup.send(embed=embed)
            return
        
        # Show query results.
        if isinstance(results, str):
            content = results
        else:
            content = create_table_representation(results)
        
        embed = io.success("The SQL query succeeded.")
        file = string.create_text_file("results", content)

        await interaction.followup.send(embed=embed, file=file)

    @owner.command(name="eval", description="Execute code snippets.")
    async def owner_eval(self, interaction: discord.Interaction):

        # Prepare a code input modal.
        modal = CodeModal()
        await interaction.response.send_modal(modal)
        
        if await modal.wait():
            raise Failure("You took too long to respond.")
        elif not modal.code:
            raise Failure("You did not provide any code to run.")
        
        code = modal.code

        # Prepare execution environment.
        env = {
            "bot": self.bot,
            "interaction": interaction,
            "author": interaction.user,
            "channel": interaction.channel,
            "guild": interaction.guild
        }
        env.update(globals())

        # Compile function.
        if code.startswith("```") and code.endswith("```"):
            code = code[3:-3].strip("` \n")

        func = f"async def func():\n{textwrap.indent(code, '    ')}"
        try:
            exec(func, env)
        except Exception as exc:
            self.log.error("Unable to compile eval code!", exc_info=exc)
            embed = io.failure("I could not compile the code!")
            # TODO: Add / attach traceback.
            return await interaction.followup.send(embed=embed)

        # Run function.
        stdout = StringIO()
        func = env["func"]
        returned = None
        output = None
        try:
            with redirect_stdout(stdout):
                returned = await func()
        except Exception as exc:
            self.log.error("Unable to execute eval code!", exc_info=exc)
            embed = io.failure("I could not execute the code!")
            # TODO: Add / attach traceback.
            return await interaction.followup.send(embed=embed)

        # Generate results.
        output = stdout.getvalue()
        fields = list()

        files = []

        if output:
            if len(output) > 1000:
                files.append(string.create_text_file("output", output))
                truncated = string.truncate(output, 1000)
                fields.append(dict(name="Output", value=f"```\n{truncated}```"))
            else:
                fields.append(dict(name="Output", value=f"```\n{output}```"))

        if returned:
            if len(returned) > 1000:
                files.append(string.create_text_file("returned", returned))
                truncated = string.truncate(returned, 1000)
                fields.append(dict(name="Return Value", value=f"```\n{truncated}```"))
            else:
                fields.append(dict(name="Return Value", value=f"```\n{returned}```"))
        
        embed = io.success("Eval executed successfully.", fields=fields)

        return await interaction.followup.send(embed=embed, files=files)

    @owner.command(name="update", description="Check for available updates.")
    async def owner_update(self, interaction: discord.Interaction):
        
        # Check whether we're in a git repository:
        if not await self.git.in_repo():
            raise Failure("I am not running in a git repository.")

        # Check for update.
        await interaction.response.defer(thinking=True)
        behind = await self.git.is_behind()
        
        # No updates available.
        if not behind:
            raise Failure("There are no updates available.")
        
        embed = io.success("An update is available. Would you like to download it?")
        view = io.Confirm(interaction.user)
        await interaction.followup.send(embed=embed, view=view)
        
        if await view.wait():
            raise Failure("You took too long to respond.")

        if not view.value:
            raise Failure("Update cancelled.")

        embed = io.success("Downloading update. This may take a while...")
        await interaction.followup.send(embed=embed)

        # Download the update
        await self.git.pull()
        
        embed = io.success("Update donwloaded. Would you like me to restart now to apply it?")
        view = io.Confirm(interaction.user)
        await interaction.followup.send(embed=embed, view=view)
        
        if await view.wait():
            raise Failure("You took too long to respond.")

        if not view.value:
            raise Failure("Restart cancelled.")

        embed = io.success("Restarting. See you in a moment!")
        await interaction.followup.send(embed=embed)
        await self.bot.close(exit_code=ExitCodes.RESTART)

    # Module commands.

    @module.command(name="list", description="View a list of all loaded modules.")
    async def module_list(self, interaction: discord.Interaction):
        modules = [f"• `{m}`" for m in self.bot.extensions.keys()]
        modules = "\n".join(modules)
        embed = io.message(f"__Modules__\n{modules}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @module.command(name="reload", description="Reload a module.")
    @commands.autocomplete(module=autocomplete_module)
    async def module_reload(self, interaction: discord.Interaction, module: str):
        
        # Attempt to reload module.
        try:
            await self.bot.reload_extension(module)
        except Exception as err:
            self.log.error(f"An error occured while reloading module {module!r}!", exc_info=err)
            embed = io.failure(
                ":zap: An error occured!",
                fields=[dict(name="Details", value=f"```\n{err}```")]
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = io.success(f":white_check_mark: Module `{module}` reloaded.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Synchronization commands.

    @sync.command(name="all", description="Sync all commands.")
    async def sync_all(self, interaction: discord.Interaction):
        global_task = self.bot.global_sync_task
        admin_task = self.bot.admin_sync_task

        global_ok = not global_task or global_task.done()
        admin_ok = not admin_task or admin_task.done()

        if (not (global_ok and admin_ok)):
            # TODO: Ask for confirmation.
            pass

        # Start sync tasks and wait for them to complete.
        self.bot.sync_global_commands()
        self.bot.sync_admin_commands()
        tasks = [self.bot.global_sync_task, self.bot.admin_sync_task]

        embed = io.message(":gear: Syncing commands. This might take a while.")
        await interaction.response.send_message(embed=embed)

        try:
            await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
        except Exception as err:
            pass
        
        embed = io.success(":white_check_mark: All commands synchronized.")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @sync.command(name="global", description="Sync global commands.")
    async def sync_global(self, interaction: discord.Interaction):
        global_task = self.bot.global_sync_task
        global_ok = not global_task or global_task.done()

        if (not global_ok):
            # TODO: Ask for confirmation.
            pass

        # Start sync tasks and wait for them to complete.
        task = self.bot.sync_global_commands()
        embed = io.message(":gear: Syncing global commands. This might take a while.")
        await interaction.response.send_message(embed=embed)

        try:
            await task
        except Exception as err:
            pass
        
        embed = io.success(":white_check_mark: Global commands synchronized.")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @sync.command(name="admin", description="Sync admin commands.")
    async def sync_admin(self, interaction: discord.Interaction):
        admin_task = self.bot.admin_sync_task
        admin_ok = not admin_task or admin_task.done()

        if (not admin_ok):
            # TODO: Ask for confirmation.
            pass

        # Start sync tasks and wait for them to complete.
        task = self.bot.sync_admin_commands()

        embed = io.message(":gear: Syncing admin commands. This might take a while.")
        await interaction.response.send_message(embed=embed)

        try:
            await task
        except Exception as err:
            pass
        
        embed = io.success(":white_check_mark: Admin commands synchronized.")
        await interaction.followup.send(embed=embed, ephemeral=True)
