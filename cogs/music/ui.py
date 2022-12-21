import discord
from .player import PlaylistPlayer
from .playlist import Playlist
from core.utils import io, string

class PlaylistView(discord.ui.View):
    """Creates a paginated view of a playlist."""
    def __init__(self, owner: discord.User, player: PlaylistPlayer):
        super().__init__(timeout=180)

        self.owner = owner
        self.player = player

        self._per = 10
        self._page = 0
        
    @property
    def page(self) -> int:
        return self._page

    @property
    def max_pages(self) -> int:
        """int: Returns the maximum amount of pages."""
        pages, remainder = divmod(self.player.playlist.length, self._per)
        if remainder > 0:
            pages += 1
        
        return max(1, pages)

    def get_page(self, page: int) -> discord.Embed:
        """Get the embed for page ``page``.
        
        Uses a zero index. To show page 1 pass ``0`` and so on.
        """
        page = max(0, min(page, self.max_pages-1))

        # Calculate track range
        start = self._per * page
        end = start + self._per
        tracks = self.player.playlist.tracks[start:end]

        # Generate track list
        format = "`{position:03d}` [{title}]({url})"
        lines = []

        position = self._per * page
        for track in tracks:
            position += 1
            title = string.truncate(track.title, 80)
            url = track.uri
            
            if self.player.track == track:
                lines.append("__" + format.format(position=position, title=title, url=url) + "__")
            else:
                lines.append(format.format(position=position, title=title, url=url))

        lines = "\n".join(lines)

        # Build the embed
        text = f"Playlist Tracks `{start+1:03d}` - `{end:03d}`\n\n{lines}"
        footer = f"Page {page+1} / {self.max_pages}"
        return io.message(text, title="Playlist Browser", footer=dict(text=footer))

    def stop(self):
        super().stop()
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user == self.owner

    async def update(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.get_page(self.page), view=self)
        
    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.blurple)
    async def button_skip_backwards(self, interaction: discord.Interaction, button: discord.ui.Button):
        self._page -= 5
        await self.update(interaction)

    @discord.ui.button(emoji="⬅️")
    async def show_previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self._page = max(self._page - 1, 0)
        await self.update(interaction)

    @discord.ui.button(emoji="➡️")
    async def show_next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self._page = min(self._page + 1, self.max_pages - 1)
        await self.update(interaction)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.blurple)
    async def button_skip_forward(self, interaction: discord.Interaction, button: discord.ui.Button):
        self._page += 5
        await self.update(interaction)

    @discord.ui.button(emoji="⏹️")
    async def stop_view(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.edit_message(view=self)