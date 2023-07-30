import logging
from typing import Optional, Union

import discord
import wavelink

from .playlist import Playlist


class PlaylistPlayer(wavelink.Player):
    """A :class:`wavelink.Player` implementation with an internal :class:`Playlist`.

    Parameters
    ----------
    bot: Vibingway
        The discord client to use. Usually this will be the bot.
    text_channel: discord.TextChannel
        The text channel the player is associated with.
    voice_channel: Union[discord.VoiceChannel, discord.StageChannel]
        The voice channel this player is connected to.
    node: wavelink.Node
        The node this player is associated with.
    """

    def __init__(
        self,
        bot: "Vibingway",
        text_channel: discord.TextChannel,
        voice_channel: Union[discord.VoiceChannel, discord.StageChannel],
        node: Optional[wavelink.Node] = None,
        playlist: Optional[Playlist] = None,
    ):
        # Internal variables
        self.log = logging.getLogger(f"{__name__}[{text_channel.guild}]")
        self._text_channel = text_channel
        self._voice_channel = None
        self._last_voice_channel = None
        self._playlist = playlist or Playlist(
            bot=bot,
            guild=voice_channel.guild,
            node=node)
        
        # Constructor
        super().__init__(client=bot, channel=voice_channel, nodes=[node] if node else list())

    def __repr__(self) -> str:
        channel_name = self.channel.name if self.channel is not None else None
        return f"<PlaylistPlayer guild={self.guild.name!r} channel={channel_name!r}>"

    @property
    def text_channel(self) -> discord.TextChannel:
        """discord.TextChannel: The text channel the player is associated with."""
        return self._text_channel
    
    @property
    def channel(self) -> Union[discord.VoiceChannel, discord.StageChannel]:
        return self._voice_channel
    
    @channel.setter
    def channel(self, value:Union[discord.VoiceChannel, discord.StageChannel]):
        self._voice_channel = value
        if value is not None:
            self._last_voice_channel = value

    @property
    def last_voice_channel(self) -> discord.VoiceChannel:
        """discord.VoiceChannel: The last valid voice channel the player was conencted to."""
        return self._last_voice_channel

    @property
    def playlist(self) -> Playlist:
        """Playlist: The playlist associated with this player."""
        return self._playlist
    
    @classmethod
    async def create(cls, client, text_channel, voice_channel, nodes):
        # TODO: Implement loading saved guild playlists from DB.
        return cls(client, text_channel, voice_channel, nodes)

    async def play(self, source, *args, **kwargs):
        source = await super().play(source, *args, **kwargs)
        self.log.info(f"Playing {source}.")

    async def play_next(self) -> Optional[wavelink.GenericTrack]:
        """Play the next track from the playlist, if possible.
        
        Returns
        -------
        Optional[wavelink.GenericTrack]
            The new track being played or :obj:`None`.
        """
        self.log.info(f"Requesting next track.")
        
        if self.playlist.has_next():
            track = self.playlist.get_next()
            self.log.info(f"Playing {track}.")
            await self.play(track)
            return track
        else:
            return None
