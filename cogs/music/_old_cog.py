import asyncio
import logging
from typing import Optional, TypedDict

import discord
import discord.app_commands as commands
import wavelink
from discord.ext.commands import Bot, Cog

from core.errors import Failure, Warning
from core.utils import io, string

from .enums import LoopModes
from .player import DBPlayer
from .queue import DBQueue  # type: ignore


class Music(Cog):
    """Cog for music commands."""

    def __init__(self, bot: Bot):
        super().__init__()

        # Internal setup.
        self.log = logging.getLogger(__name__)
        self.bot = bot
        self.node: wavelink.Node = None
        self.timeout = 300 # 5 minute timeout
        self.node_region = None
        self.node_id = self.bot.wavelink_id

        # Create the connection task.
        self.bot.loop.create_task(self.setup())

    # Setup and teardown functionality.

    async def setup(self):
        # The initial setup for when the bot is restarting or the module
        # is being reloaded. As we can't really differentiate, we assume
        # we need to replace everything.
        await self.bot.wait_until_ready()

        # Connect to lavalink.
        self.log.info("Connecting to lavalink server...")
        try:
            self.node = wavelink.NodePool.get_node(
                identifier=self.node_id,
                region=self.node_region)
            
            self.log.info("Reusing existing node.")
        except:
            self.log.info("Creating new node.")

            self.node = await wavelink.NodePool.create_node(
                bot=self.bot,
                identifier=self.node_id,
                region=self.node_region,
                **self.bot.config.lavalink_credentials
            )

        self.log.info(f"self.node.players = {self.node.players}")

        # Find voice connections without players and terminate them.
        players = self.bot.voice_clients
        self.log.info(f"Existing clients: {players}")
        # TODO: Terminate stale connections.

        # Find stale player instances and recreate them. This allows us to
        # hot-swap the player object when reloading the module.
        # TODO: Hot-swap player.
        self.log.info("Updating existing player instances.")
        
    # Wavelink event handlers.

    @Cog.listener()
    async def on_wavelink_node_ready(self, node: wavelink.Node):
        self.log.info(f"Node {node.identifier} is ready.")

    @Cog.listener()
    async def on_wavelink_track_start(self, player: Player, track: wavelink.Track):
        self.log.debug(f"Player {player!r} started playing {track!r}.")
        self.log.info(f"track_start: {player}, {track}")

    @Cog.listener()
    async def on_wavelink_track_end(self, player: Player, track: wavelink.Track, reason: str):
        self.log.debug(f"Player {player!r} finished playing {track!r} ({reason}).")
        # Wait for the next track or disconnect after 3 minutes of inactivity.
        try:
            async with asyncio.timeout(self.timeout):
                track = await player.queue.get_wait()
                await player.play(track)
        except asyncio.TimeoutError:
            await player.disconnect()

    @Cog.listener()
    async def on_wavelink_track_exception(self, player: Player, track: wavelink.Track, error):
        self.log.debug(f"Player {player!r} encounted an error playing {track!r}: {error}")

    @Cog.listener()
    async def on_wavelink_track_stuck(self, player: Player, track: wavelink.Track, threshold):
        self.log.debug(f"Player {player!r} is stuck playing {track!r} (threshold: {threshold}).")

    # Audio event handlers.

    @Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        self.log.info(f"on_voice_state_update: {member}, {before}, {after}")
        # TODO: Handle the following cases.
        # - Only bot left in voice channel. Terminate player.
        # - Bot is disconnected from a voice channel. Terminate player.

    # Helper methods.

    def get_player(self, guild: discord.Guild) -> Optional[Player]:
        return self.node.get_player(guild) or guild.voice_client

    def ensure_voice(self, interaction: discord.Interaction, same_channel: bool=True):
        """Checks whether the user is connected to a voice channel.
        
        Parameters
        ----------
        same_channel: bool
            When :obj:`True` also checks whether the user is connected to the
            same voice channel as the bot. Defaults to :obj:`True`."""
        player: Player = self.get_player(interaction.guild)

        if not interaction.user.voice or interaction.user.voice.channel is None:
            raise Failure("You are not connected to a voice channel.")

        if same_channel and player != None and interaction.user.voice.channel != player.channel:
            raise Failure(f"You are not connected to {player.channel.mention}.")

    def check_can_connect(self, channel: discord.VoiceChannel) -> bool:
        """Checks whether a voice channel can be connected to.
        
        Raises
        ------
        discord.app_commands.BotMissingPermissions
            Exception raised when the bot does not have the connect and speak
            permission. This is handled by the debug module.
        """
        perms: discord.Permissions = channel.permissions_for(channel.guild.me)

        missing = []
        if not perms.connect:
            missing.append("connect")
        
        if not perms.speak:
            missing.append("speak")
        
        if missing:
            raise commands.BotMissingPermissions(missing)

    # Player logic.


    # Command groups.

    music = commands.Group(name="music", description="Music-related commands.", guild_only=True)
    queue = commands.Group(name="queue", description="Queue-related commands.", parent=music)

    # Music commands.

    @music.command(name="join", description="Add or move me to a voice channel.")
    @commands.describe(channel="The channel to join or move me to. If not specified I will join the channel you are currently in.")
    async def music_join(self, interaction: discord.Interaction, channel: Optional[discord.VoiceChannel]):
        self.ensure_voice(interaction, same_channel=False)

        # Check if a channel has been provided.
        if not channel and not interaction.user.voice:
            embed = io.failure("You are not in a voice channel. Please either join a voice channel or specify a channel for me to join.")
            await interaction.response.send_message(embed=embed)
            return

        # Move or create a player.
        channel = channel or interaction.user.voice.channel
        player: Player = channel.guild.voice_client
        if player:
            if player.channel == channel:
                embed = io.success(f"I'm already connected to {channel.mention}.")
                await interaction.response.send_message(embed=embed)
            else:
                await player.move_to(channel)
                embed = io.success(f"Moved to {channel.mention}.")
                await interaction.response.send_message(embed=embed)#
        else:
            player = Player(self.bot)
            await channel.connect(cls=player)
            embed = io.success(f"Connected to {channel.mention}.")
            await interaction.response.send_message(embed=embed)

    @music.command(name="leave", description="Remove me from a voice channel.")
    async def music_leave(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild)

        if player:
            await player.disconnect()
            embed = io.success(f"Disconnected from {player.channel.mention}.")
            await interaction.response.send_message(embed=embed)
        else:
            embed = io.failure(f"I am not connected to any voice channels.")
            await interaction.response.send_message(embed=embed)

    @music.command(name="play", description="Play music from a source.")
    @commands.describe(source="A URL or the name of a video to play.")
    async def music_play(self, interaction: discord.Interaction, source: str):
        self.ensure_voice(interaction)

        await interaction.response.defer(thinking=True)

        # Find or create a player.
        player: Player = self.get_player(interaction.guild)
        if not player:
            channel = interaction.user.voice.channel
            player = Player(self.bot)
            await channel.connect(cls=player)
        
        # Resolve the track.
        track: wavelink.Track = None
        playlist: wavelink.YouTubePlaylist = None

        if source.startswith("https://"):
            if "playlist?" in source:
                playlist = await wavelink.YouTubePlaylist.search(query=source)
                # TODO: Handle adding playlist or just song.
                for track in playlist.tracks:
                    await player.queue.put_wait(track)
                if not player.is_playing():
                    track = await player.queue.get_wait()
                    return await player.play(track)
            else:
                track = await player.node.get_tracks(query=source, cls=wavelink.Track)
        else:
            track = await wavelink.YouTubeTrack.search(source)

        self.log.info("Tracks:")
        for t in track:
            self.log.info(f"- {t.title} {t.uri}")       

        # Play the song or add it to the queue.
        if player.queue.is_empty and not player.is_playing():
            await player.play(track[0])
            embed = io.success(f"Playing {track[0].title}.")
            await interaction.followup.send(embed=embed)
        else:
            await player.queue.put_wait(track[0])
            embed = io.success(f"Added {track[0].title} to the queue (#{player.queue.count}).")
            await interaction.followup.send(embed=embed)

    @music.command(name="playing", description="View the current track.")
    async def music_playing(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild)

        if not player or not player.is_playing():
            embed = io.success(f"Nothing is playing at the moment.")
            await interaction.response.send_message(embed=embed)
            return
        
        track: wavelink.Track = player.track

        title    = track.title
        url      = track.uri
        elapsed  = string.format_seconds(player.position)
        duration = string.format_seconds(track.duration)

        # TODO: Fetch requester info.
        requester = "TBD"

        embed = io.success(f"Playing [{title}]({url}) `[{elapsed} / {duration}]` requested by {requester}.")
        await interaction.response.send_message(embed=embed)

    @music.command(name="skip", description="Skip the current track.")
    async def music_skip(self, interaction: discord.Interaction):
        self.ensure_voice(interaction)

        player: Player = self.get_player(interaction.guild)
        if player and player.is_playing():
            player.stop()

            embed = io.success("Skipped current song. Now playing: {player.queue[0]}")
            await interaction.response.send_message(embed=embed)
        else:
            embed = io.success("There is nothing to skip.")
            await interaction.response.send_message(embed=embed)
        
    @music.command(name="stop", description="Stop playback.")
    async def music_stop(self, interaction: discord.Interaction):
        self.ensure_voice(interaction)
        # TODO: Check if there is a voice client. If so, stop the currently playing song and stop playback.
        await interaction.response.send_message("This command is not quite ready yet.")
        
    # Queue commands.

    @queue.command(name="view", description="View the current queue.")
    async def queue_view(self, interaction: discord.Interaction):
        # TODO: Show a paginated view of the current queue.
        await interaction.response.send_message("This command is not quite ready yet.")

    @queue.command(name="jump", description="Jump to a given track in the queue.")
    async def queue_jump(self, interaction: discord.Interaction, position: int):
        self.ensure_voice(interaction)
        # TODO: Show a paginated view of the current queue.
        await interaction.response.send_message("This command is not quite ready yet.")

    @queue.command(name="clear", description="Empty the queue.")
    async def queue_clear(self, interaction: discord.Interaction):
        self.ensure_voice(interaction)
        # TODO: Remove all tracks except the currently playing one from the queue.
        await interaction.response.send_message("This command is not quite ready yet.")
