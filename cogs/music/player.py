import asyncio

import asyncpg
import discord
import wavelink

from .queue import DBQueue  # type: ignore


class DBPlayer(wavelink.Player):
    """A :class:`wavelink.Player` implementation with a :class:`~.DBQueue`.

    .. attention::

        You should not manually create objects of this class.
        Use :meth:`~.DBPlayer.create` instead.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._queue = kwargs.pop("queue")

    @property
    def queue(self) -> DBQueue:
        """:class:`~.DBQueue`: The internal queue object for this player."""
        return self._queue

    @classmethod
    async def create(cls, bot: "Vibingway", channel: discord.VoiceChannel, **kwargs):
        """Create a new :class:`~.DBPlayer` for the given voice channel.

        Parameters
        ----------
        bot: :class:`core.Vibingway`
            The bot instance.
        channel: discord.VoiceChannel
            A voice channel.

        Returns
        -------
        DBPlayer
            A new DBPlayer instance.
        """
        queue = await DBQueue.create(bot, channel.guild)
        return cls(client=bot, channel=channel, queue=queue, **kwargs)

    def __repr__(self):
        return f"<Player guild={self.guild.name!r} channel={self.channel.name!r} queue={self.queue.count}>"
