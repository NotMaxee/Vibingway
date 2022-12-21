import asyncio
import logging
import functools
import discord

from core.utils import io

from .api import BannerAPI


class BannerView(discord.ui.View):
    def __init__(self, api: BannerAPI, guild: discord.Guild, owner: discord.Member, banners: list[tuple[str, int]]):
        super().__init__(timeout=300)

        # Setup
        self.log = logging.getLogger(f"{__name__}[{guild.name}]")
        self.api: BannerAPI = api
        self.guild: discord.Guild = guild
        self.owner: discord.Member = owner
        self.banners: list[tuple[str, int]] = banners

        # Internals
        self._page = 0
        self._task = None
        self.update_buttons()

    # Constructor and overrides

    @classmethod
    async def create(cls, interaction: discord.Interaction, api: BannerAPI):
        """Create a new banner view."""
        guild = interaction.guild
        user = interaction.user
        banners = await api.get_banners(guild)
        return cls(api, guild, user, banners)

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user == self.owner

    def stop(self):
        super().stop()
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    # Helpers

    def get_embed(self) -> discord.Embed:
        """Get the embed for the current page."""

        if not self.banners:
            embed = io.message("There are no banners. Use `/banner add <url>` to add one!", footer="Page 1 / 1")
            return embed
        
        url, user_id = self.banners[self._page]
        pages = max(1, len(self.banners))

        embed = io.message(f"Banner added by <@{user_id}>", title="Banner Browser", image=url)
        embed.set_footer(text=f"Page {self._page+1} / {pages}")
        return embed

    def update_buttons(self):
        """Update the button states."""
        if not self.banners:
            self.button_previous.disabled = True
            self.button_next.disabled = True
            self.button_show.disabled = True
            self.button_delete.disabled = True
        else:
            self.button_previous.disabled = (self._page == 0)
            self.button_next.disabled = len(self.banners) == 1 or self._page == (len(self.banners) - 1)
            self.button_show.disabled = False
            self.button_delete.disabled = False

    async def update(self, interaction: discord.Interaction):

        # When updating we have to regenerate our internal set of pages.
        self.banners = await self.api.get_banners(self.guild)
        self._page = max(0, min(self._page, len(self.banners) - 1))

        # Show a custom page if there are no banners.
        embed = self.get_embed()
        self.update_buttons()

        await interaction.response.edit_message(embed=embed, view=self)

    async def _update_banner(self, interaction: discord.Interaction, url:str):
        """Attempt to update the server banner."""
        try:
            await self.api.set_banner(self.guild, url)
        except Exception as error:
            # TODO: Add exception handling.
            embed = io.failure(f"I could not update the banner!", fields=dict(name="Reason", value=str(error)))
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            embed = io.success(f"I have updated the banner.", thumbnail=url)
            await interaction.followup.send(embed=embed)

    # Buttons

    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.blurple)
    async def button_previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self._page -= 1
        await self.update(interaction)

    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.blurple)
    async def button_next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self._page += 1
        await self.update(interaction)

    @discord.ui.button(emoji="🖼️", style=discord.ButtonStyle.green)
    async def button_show(self, interaction: discord.Interaction, button: discord.ui.Button):

        # Check if an update task is running.
        if self._task is not None and not self._task.done():
            embed = io.failure("I am still working on your last change request.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Create the update task.
        url = self.banners[self._page][0]

        embed = io.success(f"I am updating the banner. This may take a moment.", thumbnail=url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

        self._task = asyncio.create_task(self._update_banner(interaction, url))

    @discord.ui.button(emoji="🗑️", style=discord.ButtonStyle.red)
    async def button_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        url = self.banners[self._page][0]
        await self.api.remove_banner(self.guild, url)
        await self.update(interaction)

        if len(self.banners) == 0:
            await self.api.set_enabled(self.guild, False)
            embed = io.success(
                "I have deleted the banner. As there are no banners left I "
                "have also disabled the automatic banner rotation.", 
                thumbnail=url
            )
        else:
            embed = io.success(f"I have deleted the banner.", thumbnail=url)
        
        await interaction.followup.send(embed=embed)

    @discord.ui.button(emoji="⏹️")
    async def stop_view(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.edit_message(view=self)