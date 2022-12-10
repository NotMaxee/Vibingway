import logging
from typing import Optional

import discord
import wavelink

from .playlist import Playlist
from .enums import Repeat

class PlaylistPlayer(wavelink.Player):

    def __init__(self, client, text, voice, node, playlist):
        super().__init__(client, voice, node=node)
        self.log = logging.getLogger(f"{__name__}[{text.guild}]")
        self.text: discord.TextChannel = text
        # Get rid of the built-in queue and add playlist.
        del self.queue
        self._playlist = playlist

    def __repr__(self) -> str:
        return f"<PlaylistPlayer guild={self.guild.name!r} channel={self.channel.name!r}>"

    @classmethod
    async def create(cls, bot: "Vibingway", text: discord.TextChannel, voice: discord.VoiceChannel, node: wavelink.Node):
        """Initialize a playlist player and link it to a channel.

        Parameters
        ----------
        bot: core.Vibingway
            The bot instance.
        text: discord.TextChannel
            The text channel to output status updates to.
        channel: discord.VoiceChannel
            The voice channel to link to.
        node: wavelink.Node
            The wavelink node to use.
        
        Returns
        -------
        PlaylistPlayer
            A new playlist player instance.
        """
        # TODO: Load player settings from database and apply them here.

        playlist = await Playlist.create(bot, text.guild, node)
        # playlist._position 
        # playlist._order
        # playlist._repeat

        player = cls(bot, text, voice, node, playlist)
        # player._volume = 

        return player

    # Player properties.

    @property
    def playlist(self) -> Playlist:
        """Playlist: The playlist associated with this player."""
        return self._playlist

    # Player methods.

    async def play(self, source, *args, **kwargs):
        source = await super().play(source, *args, **kwargs)
        self.log.info(f"Playing {source}.")
        self._source = source

    async def play_next(self) -> Optional[wavelink.Track]:
        """Play the next track from the playlist, if possible.
        
        Returns
        -------
        Optional[wavelink.Track]
            The new track being played or :obj:`None`.
        """
        self.log.info(f"Requesting next track.")
        
        if self.playlist.has_next():
            track = await self.playlist.get_next()
            self.log.info(f"Playing {track}.")
            await self.play(track)
            return track
        else:
            return None
