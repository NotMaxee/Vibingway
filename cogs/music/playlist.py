import logging
import random
from typing import Optional

import discord
import wavelink

from .enums import Repeat


class Playlist:
    """Represents a playlist for a guild.
    
    The playlist keeps track of all requested tracks and syncs
    them with the database. It is used by the :class:`~.PlaylistPlayer`
    to provide music playing functionality.
    
    Parameters
    ----------
    bot: core.Vibingway
        The bot instance.
    guild: discord.Guild
        The guild this playlist is for.
    node: wavelink.Node
        The node to use to resolve track info.
    tracks: list[wavelink.Track]
        A list of tracks in the playlist.
    """
    def __init__(self, bot, guild, node, tracks):
        self.log = logging.getLogger(f"{__name__}[{guild}]")
        self.bot = bot
        self.guild: discord.Guild = guild
        self.node: wavelink.Node = node

        # Track and playlist information.
        self._tracks: list[wavelink.Track] = tracks
        self._position = -1 if len(self._tracks) == 0 else 0
        self._repeat: Repeat = Repeat.OFF

    @classmethod
    async def create(cls, bot, guild, node) -> "Playlist":
        """Initialize a playlist for a guild."""
        # TODO: Load tracks from database.

        tracks = []
        return cls(bot, guild, node, tracks)

    # Playlist properties.

    @property
    def length(self) -> int:
        """int: The length of the playlist."""
        return len(self.tracks)

    @property
    def position(self) -> int:
        """int: The current position of the playlist. ``-1`` if the playlist is empty."""
        if self._position >= len(self._tracks):
            self._position = 0
        return self._position

    @property
    def current(self) -> Optional[wavelink.Track]:
        """Get the track at the current position.
        
        Returns
        -------
        Optional[wavelink.Track]
            The track or :obj:`None` if the playlist is empty.
        """
        try:
            return self._tracks[self._position]
        except IndexError:
            return None

    @property
    def tracks(self) -> list[wavelink.Track]:
        """list[wavelink.Track]: A list of tracks in the playlist."""
        return self._tracks

    @property
    def repeat(self) -> Repeat:
        return self._repeat

    def is_empty(self) -> bool:
        return len(self.tracks) == 0

    # Track management.

    def get_track(self, position: int) -> Optional[wavelink.Track]:
        """Get a track from the playlist.
        
        Parameters
        ----------
        position: int
            The position of the track in the playlist.
        
        Returns
        -------
        Optional[wavelink.Track]
            The track or :obj:`None` if no track exists at the given
            position.
        """
        try:
            return self.tracks.get(position)
        except IndexError:
            return None

    async def add_track(self, track: wavelink.Track):
        """Add a single track to the playlist.
        
        Parameters
        ----------
        track: wavelink.Track
            The track to add.
        """
        self.tracks.append(track)
        if self._position == -1:
            self._position = 0

    async def add_tracks(self, tracks: list[wavelink.Track]):
        """Add multiple tracks to the playlist at once.
        
        Parameters
        ----------
        tracks: list[wavelink.Track]
            The tracks to add.
        """
        self.log.info(f"Adding {len(tracks)} tracks.")
        if tracks:
            for track in tracks:
                self.tracks.append(track)

            if self._position == -1:
                self._position = 0

    async def remove_track(self, position: int):
        """Remove the track at the given position of the playlist.
        
        Returns
        -------
        Optional[wavelink.Track]
            The removed track or :obj:`None` if no track exists at
            the given position.
        """
        try:
            track = self.tracks.pop(position)
            if position <= self._position:
                self._position -= 1
            
            return track
        except IndexError:
            return None

    async def clear(self):
        """Empty the playlist."""
        self.tracks.clear()
        self._position = -1

    async def shuffle(self):
        """Randomize the playlist order."""
        random.shuffle(self.tracks)

    # Settings management.

    async def set_repeat(self, repeat: Repeat):
        """Set the repeat mode of the playlist.
        
        Parameters
        ----------
        repeat: cogs.music.enums.Repeat
            The new repeat mode of the playlist.
        """
        self._repeat = repeat

    # Playlist functionality.

    def has_next(self) -> bool:
        """Check whether the playlist has a track after the current position."""
        if len(self.tracks) == 0:
            return False

        if self.repeat != Repeat.OFF:
            return True
        else:
            return self.position + 1 < self.length

    async def get_next(self) -> Optional[wavelink.Track]:
        """Get the next track from the playlist, based on the position.
        
        Returns
        -------
        wavelink.Track
            The next track in the playlist or :obj:``None` if there is no
            next track.
        """
        if self.length == 0:
            return None

        if self.repeat == Repeat.OFF:
            self._position += 1
        elif self.repeat == Repeat.TRACK:
            # Simply don't advance.
            pass
        elif self.repeat == Repeat.ALL:
            self._position = (self._position + 1) % self.length
        
        return self.current

    async def set_position(self, position: int) -> Optional[wavelink.Track]:
        """Set the position of the playlist and return the track at the given position.
        
        Parameters
        ----------
        position: int
            The playlist position. When set to a value outside the allowed
            range the value is clamped to the nearest valid position.

        Returns
        -------
        wavelink.Track
            The track at the given position or :obj:`None` if the playlist
            is empty.
        """
        if self.length == 0:
            return None

        self._position = max(0, min(self.length - 1, position))
        return self.current
    