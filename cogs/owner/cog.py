import asyncio
import logging
import textwrap
from contextlib import redirect_stdout
from io import StringIO
from typing import Union

import discord
import discord.app_commands as commands
from discord.ext.commands import Bot, Cog

from core.utils import ExitCodes, io


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
    async def owner_sql(self, interaction: discord.Interaction, sql:str):
        # TODO: Run the SQL query and return the outcome.
        await interaction.response.send_message("This command is not quite ready yet.")

    @owner.command(name="eval", description="Execute code snippets.")
    async def owner_eval(self, interaction: discord.Interaction, code: str):

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
            return await interaction.response.send_message(embed=embed)

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
            return await interaction.response.send_message(embed=embed)

        # Generate results.
        output = stdout.getvalue()
        fields = list()

        if output:
            fields.append(dict(name="Output", value=f"```\n{output}```"))

        if returned:
            fields.append(dict(name="Return Value", value=f"```\n{returned}```"))
        
        embed = io.success("Eval executed successfully.", fields=fields)

        return await interaction.response.send_message(embed=embed)

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
