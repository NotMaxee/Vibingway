import asyncio
import logging

import discord
import wavelink
from discord.ext.commands import Bot

from .enums import LoopModes, QueueOrder, TrackType
from .tracks import RequestedYoutubeTrack, RequestedSoundcloudTrack


class DBQueue:
    """A persistable track queue.

    .. attention::

        This object should not be manually created.
        Use :meth:`.Queue.create` instead.
    """

    def __init__(
        self,
        bot: "Vibingway",
        guild: discord.Guild,
        tracks: list[wavelink.abc.Playable],
        position: int = -1,
        volume: int = 0,
        order: QueueOrder = QueueOrder.NORMAL,
        loop: LoopModes = LoopModes.OFF,
    ):
        self._bot = bot
        self._guild = guild

        self.log = logging.getLogger(f"{__name__}[{guild.id}]")

        # Persistable properties
        self._tracks: list[wavelink.abc.Playable] = tracks
        self._position: int = position
        self._volume: int = volume
        self._order: QueueOrder = order
        self._loop: LoopModes = loop

    @property
    def guild(self) -> discord.Guild:
        """:class:`discord.Guild`: The guild this queue belongs to."""
        return self._guild

    @property
    def length(self) -> int:
        """int: The current length of the queue."""
        return len(self._tracks)

    @property
    def tracks(self) -> list[wavelink.Track]:
        """list[wavelink.Track]: The tracks currently in the queue."""
        return self._tracks

    @property
    def position(self) -> int:
        """int: The position of the current track in the queue."""
        pass

    @property
    def volume(self) -> int:
        """int: The current volume for this order."""
        return self._volume

    @property
    def order(self) -> QueueOrder:
        """QueueOrder: The playback order for this queue."""
        return self._order

    @property
    def loop(self) -> LoopModes:
        """LoopModes: The loop mode for this queue."""
        return self._loop

    def has_next(self) -> bool:
        """bool: Checks whether there are more tracks to play after the current one.

        Always returns false for loop modes other than off."""
        pass

    async def get_next(self):
        """Advances the queue and returns the next track. Returns :obj:`None` if there is no next track."""

    @classmethod
    async def create(cls, bot: "Vibingway", guild: discord.Guild):
        """Create a new :class:`~.DBQueue`.

        Parameters
        ----------
        bot: :class:`~core.Vibingway`
            The bot instance.
        guild: discord.Guild
            The guild this queue is for.
        """
        # Fetch existing record or create a default one.
        query = """
        WITH
            present AS (SELECT * FROM queue_settings WHERE guild_id=$1),
            inserted AS (
                INSERT INTO queue_settings (guild_id, "position", "order", "loop", "volume")
                SELECT $1, -1, $2, $3, $4
                WHERE NOT EXISTS (SELECT 1 FROM present)
                RETURNING *
            )
            SELECT * FROM inserted UNION ALL
            SELECT * FROM present;
        """
        row = await bot.db.fetchrow(
            query, guild.id, QueueOrder.NORMAL, LoopModes.OFF, 100
        )

        order: QueueOrder = QueueOrder(row["order"])
        loop: LoopModes = LoopModes(row["loop"])
        position: int = row["position"]
        volume: int = row["volume"]

        # Fetch tracks from the database and initialize them.
        query = """SELECT * FROM queue_entries WHERE guild_id=$1;"""
        rows = await bot.db.fetch(query, guild.id)

        tracks = []
        node: wavelink.Node = wavelink.NodePool.get_node(
            identifier=bot.config.wavelink_id
        )
        for row in rows:
            user_id: int = row["user_id"]
            position: int = row["position"]
            type: TrackType = TrackType(row["type"])
            identifier: str = row["identifier"]

            cls = None
            if type is TrackType.YOUTUBE:
                cls = RequestedYoutubeTrack
            elif type is TrackType.YOUTUBE_MUSIC:
                cls = RequestedYoutubeTrack
            elif type is TrackType.SOUNDCLOUD:
                cls = RequestedSoundcloudTrack

            track = await node.build_track(cls=cls, identifier=identifier)
            track.requester_id = user_id

            tracks.append(track)

        # TODO: Get tracks, position and settings from database.
        return cls(bot, guild, tracks)

    async def save(self):
        """Save the queue to the database."""
        pass

    async def clear(self):
        """Clear the queue."""
        pass

    async def insert_track(self, track, position: int = None):
        pass

    async def remove_track(self, position: int):
        pass

    async def remove_tracks(self, start: int, end: int):
        pass

    async def set_volume(self, volume: int):
        """Set the volume for this queue.

        Parameters
        ----------
        volume: int
            The volume in percent as a value from 0 to 100.
        """
        volume = min(100, max(0, int(volume)))

    async def set_order(self, mode: QueueOrder):
        """Set the playback order for this queue.

        Parameters
        ----------
        mode: ~cogs.music.enums.QueueOrder
            The new queue order.
        """
        pass

    async def set_loop(self, mode: LoopModes):
        """Set the loop mode for this queue.

        Parameters
        ----------
        mode: ~cogs.music.enums.LoopModes
            The new loop mode.
        """
        pass
