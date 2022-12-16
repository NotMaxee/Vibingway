import asyncio
import logging
from typing import Optional, TypedDict

import discord
import discord.app_commands as commands
import wavelink

from discord.ext.commands import Bot, Cog

from core.errors import Failure, Warning
from core.utils import io, string

from .enums import Repeat
from .player import PlaylistPlayer
from .playlist import Playlist
from .ui import PlaylistView

class Music(Cog):
    """Cog for music commands."""

    def __init__(self, bot: Bot):
        super().__init__()

        # Internal setup.
        self.log = logging.getLogger(__name__)
        self.bot = bot
        self.timeout: int = 300
        self.node: wavelink.Node = None
        self.node_region = None
        self.node_id = self.bot.config.wavelink_id

        # Create the setup task. Commands can not be used before this
        # task has been completed.
        self._setup = self.bot.loop.create_task(self.setup())
        self._setup.add_done_callback(self.setup_complete)

    async def setup(self):
        # The initial setup for this cog. This is ran when the bot is
        # restarting ot the module is being hot-swapped.
        await self.bot.wait_until_ready()

        # Connect to lavalink.
        self.log.info("Connecting to lavalink server...")
        try:
            self.node = wavelink.NodePool.get_node(
                identifier=self.node_id,
                region=self.node_region)
            
            self.log.info("Reusing existing node.")
        except (wavelink.ZeroConnectedNodes, wavelink.NoMatchingNode):
            self.log.info("Creating new node.")

            self.node = await wavelink.NodePool.create_node(
                bot=self.bot,
                identifier=self.node_id,
                region=self.node_region,
                **self.bot.config.lavalink_credentials
            )

        # TODO: Find and terminate stale voice connections without players.
        # Players: self.node.players / self.bot.voice_clients

    def setup_complete(self, task: asyncio.Task):
        # Handle errors that might occur while connecting to wavelink.
        if not task.exception():
            self.log.info("Setup completed.")
            return

        error = task.exception()
        self.log.error("An error occured while setting up!", exc_info=error)

        cog = self.bot.get_cog("Debug")
        if not cog:
            return

        self.bot.loop.create_task(cog.log_error(error))

    # Event handlers.

    @Cog.listener()
    async def on_wavelink_node_ready(self, node: wavelink.Node):
        self.log.info(f"Node {node.identifier} is ready.")

    @Cog.listener()
    async def on_wavelink_track_start(self, player: PlaylistPlayer, track: wavelink.Track):
        self.log.info(f"PlaylistPlayer {player!r} started playing {track.title!r}.")

        # NOTE: When removing the monkey patches in __init__.py the following
        # line may be required, unless the following bug in wavelink has been fixed.
        # https://github.com/PythonistaGuild/Wavelink/issues/156.
        # 
        # player._source = track

        try:
            embed = io.message(f"Now playing [{track.title}]({track.uri}).")
            await player.text.send(embed=embed)
        except Exception as err:
            self.log.error("Unable to send notification.", exc_info=err)

    @Cog.listener()
    async def on_wavelink_track_end(self, player: PlaylistPlayer, track: wavelink.Track, reason: str):
        self.log.info(f"PlaylistPlayer {player!r} finished playing {track.title!r} ({reason}).")

        # When playback is stopped don't continue playing.
        if reason in ("STOPPED", "REPLACED"):
            return

        # Try to play the next track in the playlist.
        await player.play_next()

    @Cog.listener()
    async def on_wavelink_track_exception(self, player: PlaylistPlayer, track: wavelink.Track, error):
        self.log.info(f"PlaylistPlayer {player!r} encounted an error playing {track.title!r}: {error}")
        await player.play_next()

    @Cog.listener()
    async def on_wavelink_track_stuck(self, player: PlaylistPlayer, track: wavelink.Track, threshold):
        self.log.info(f"PlaylistPlayer {player!r} is stuck playing {track.title!r} (threshold: {threshold}).")
        await player.play_next()

    @Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        
        # Leave the voice channel when the last user leaves.
        if not member.bot and after.channel is None:
            if not [m for m in before.channel.members if not m.bot]:
                player: PlaylistPlayer = self.get_player(member.guild)
                if player and player.channel == before.channel:
                    embed = io.message(f"Disconnected from {player.channel.mention}.")
                    try:
                        await player.text.send(embed=embed)
                    except:
                        pass
                    await player.disconnect()
        
        # Clean up after getting forcibly removed from a voice channel.
        if member == self.bot.user and after.channel is None:
            player = self.get_player(member.guild)

            if player is not None:
                try:
                    await player.disconnect()
                except:
                    player.cleanup()

    # Helper methods.

    def check_wavelink_ready(self):
        """Checks if wavelink is ready."""
        if self.node is None:
            raise Failure("Just a moment, I'm still getting things ready...")

    def check_can_use_voice_command(self, interaction: discord.Interaction, same_channel: bool=True):
        """Checks whether the interaction author can use voice-related commands.
        
        Parameters
        ----------
        same_channel: bool
            When :obj:`True` also checks whether the user is connected to the
            same voice channel as the bot. Defaults to :obj:`True`."""
        player: PlaylistPlayer = self.get_player(interaction.guild)

        if not interaction.user.voice or interaction.user.voice.channel is None:
            raise Failure("You are not connected to a voice channel.")

        if same_channel and player != None and interaction.user.voice.channel != player.channel:
            raise Failure(f"You are not connected to {player.channel.mention}.")

    def check_can_connect(self, channel: discord.VoiceChannel):
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

    # Player and queue methods.

    async def create_player(self, text: discord.TextChannel, voice: discord.VoiceChannel) -> PlaylistPlayer:
        """Create a new player.
        
        Parameters
        ----------
        text: discord.TextChannel
            The text channel to output status information to.
        voice: discord.VoiceChannel
            The voice channel to connect the player to.
        """
        player = await PlaylistPlayer.create(self.bot, text, voice, self.node)
        await voice.connect(cls=player)
        return player

    def get_player(self, guild: discord.Guild) -> Optional[PlaylistPlayer]:
        """Get the player for a guild.
        
        Returns
        -------
        Optional[PlaylistPlayer]
            The player or :obj:`None` if no player exists for this guild.
        """
        return self.node.get_player(guild) or guild.voice_client

    async def resolve_tracks(self, interaction: discord.Interaction, source:str) -> list[wavelink.Track]:
        """Attempt to find one or more tracks for a given source string.
        
        Parameters
        ----------
        interaction: discord.Interaction
            The interaction during which the tracks are being resolved.
        source: str
            A source string that is used to search for tracks.
        
        Returns
        -------
        list[wavelink.Track]
            A list of tracks.
        """
        tracks: list[wavelink.Track] = list()

        if source.startswith("https://"):

            # Youtube playlist.
            if ("playlist?" in source) or ("&list=" in source) or ("?list" in source):
                playlist = await wavelink.YouTubePlaylist.search(query=source)

                if len(playlist.tracks) > 1:
                    view = io.Choice(interaction.user, options={"Add all tracks":True, "Add first track":False})
                    embed = io.message(f"You seem to have requested a playlist containing `{len(playlist.tracks):,}` tracks. Would you like to add them all?")
                    await interaction.response.send_message(embed=embed, view=view)
                    if await view.wait():
                        raise Failure("The interaction timed out.")

                    if view.cancelled:
                        raise Failure("You cancelled the request.")
                    
                    if view.value:
                        tracks = playlist.tracks
                    else:
                        tracks = [playlist.tracks[0]]

            # Other URL.
            else:
                results = await self.node.get_tracks(query=source, cls=wavelink.Track)
                tracks.append(results[0])

        # Youtube search.
        else:
            results = await wavelink.YouTubeTrack.search(source)
            options = {string.truncate(track.title, 80): track for track in results[:5]}
            view = io.Choice(interaction.user, options=options)
            
            lines = []
            for label, track in options.items():
                lines.append(f"[{label}]({track.uri})")

            fields = [dict(name="Search Results", value="\n".join(lines))]
            embed = io.message(f"Please choose one of the search results to add to the playlist.", fields=fields)

            await interaction.response.send_message(embed=embed, view=view)
            if await view.wait():
                raise Failure("The interaction timed out.")

            if view.cancelled:
                raise Failure("You cancelled the request.")

            tracks.append(view.value)

        # Return.
        return tracks

    # Command groups.

    music = commands.Group(name="music", description="Music commands.", guild_only=True)

    # Music commands.

    @music.command(name="join", description="Add or move me to a voice channel.")
    @commands.describe(channel="The channel to join or move me to. If not specified I will join the channel you are currently in.")
    async def music_join(self, interaction: discord.Interaction, channel: Optional[discord.VoiceChannel]):
        self.check_wavelink_ready()
        self.check_can_use_voice_command(interaction, same_channel=False)

        # Check if a channel has been provided.
        if not channel and not interaction.user.voice:
            embed = io.failure("No voice channel provided. Please either join a voice channel or specify a channel for me to join.")
            await interaction.response.send_message(embed=embed)
            return

        # Move existing player.
        channel = channel or interaction.user.voice.channel
        player: PlaylistPlayer = channel.guild.voice_client
        if player:
            if player.channel == channel:
                embed = io.success(f"I'm already connected to {channel.mention}.")
                await interaction.response.send_message(embed=embed)
            else:
                await player.move_to(channel)
                embed = io.success(f"Moved to {channel.mention}.")
                await interaction.response.send_message(embed=embed)
        
        # Create a new player.
        else:
            await self.create_player(interaction.channel, channel)
            embed = io.success(f"Connected to {channel.mention}.")
            await interaction.response.send_message(embed=embed)

    @music.command(name="leave", description="Remove me from a voice channel.")
    async def music_leave(self, interaction: discord.Interaction):
        self.check_wavelink_ready()
        player = self.get_player(interaction.guild)

        if player:
            await player.disconnect()
            embed = io.success(f"Disconnected from {player.channel.mention}.")
            await interaction.response.send_message(embed=embed)
        else:
            embed = io.failure(f"I am not connected to any voice channels.")
            await interaction.response.send_message(embed=embed)

    @music.command(name="play", description="Play music from a source.")
    @commands.describe(source="A URL or the name of a video to play.", position="The position in the playlist to play from.")
    async def music_play(self, interaction: discord.Interaction, source: Optional[str], position: Optional[commands.Range[int, 1, None]]):
        self.check_wavelink_ready()
        self.check_can_use_voice_command(interaction, same_channel=True)

        # Find or create a player.
        player: PlaylistPlayer = self.get_player(interaction.guild)
        if not player:
            channel = interaction.user.voice.channel
            player = await self.create_player(interaction.channel, channel)
        
        # If no parameter is provided we try to play the current track.
        if (source is None) and (position is None):
            track = player.playlist.current
            
            if track:
                embed = io.success(f"Starting playback from position {player.playlist.position+1}.")
                await interaction.response.send_message(embed=embed)
                await player.play(track)
                return
            elif player.playlist.is_empty():
                raise Failure("The playlist is empty.")
            else:
                raise Failure("The playlist is exhausted. Use `/play position:1` to play from start.")

        if (source is not None) and (position is not None):
            raise Failure("The `source` and `position` options are mutually exclusive.")

        # If a position is specified we try to play it from the playlist.
        if position is not None:
            if player.playlist.is_empty():
                raise Failure("The playlist is empty.")

            actual = position - 1
            if actual >= player.playlist.length:
                actual = player.playlist.length - 1

            embed = io.success(f"Playing playlist from position {position}.")
            await interaction.response.send_message(embed=embed)

            track = await player.playlist.set_position(actual)
            await player.play(track)
            return

        # If a source is specified we look it up and add it to the playlist.
        try:
            tracks: list[wavelink.Track] = await self.resolve_tracks(interaction, source)
        except wavelink.LoadTrackError:
            raise Failure("I could not find any usable music under that URL.")
        
        # Add tracks to playlist.
        play_next = (player.playlist.length != 0)
        position = player.playlist.length + 1
        await player.playlist.add_tracks(tracks)
        
        if not player.is_playing():
            if play_next:
                await player.play_next()
            else:
                await player.play(player.playlist.current)

        # Send confirmation.
        if len(tracks) == 1:
            embed = io.success(f"{interaction.user.mention} added [`{tracks[0].title}`]({tracks[0].uri}) to the playlist at position #{position}.")
        else:
            embed = io.success(f"{interaction.user.mention} added {len(tracks)} tracks to the playlist #{position}.")

        if interaction.response.is_done():
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message(embed=embed)

    @music.command(name="pause", description="Pause the currently playing track.")
    async def music_pause(self, interaction: discord.Interaction):
        self.check_wavelink_ready()
        self.check_can_use_voice_command(interaction, same_channel=True)

        # Find player.
        player: PlaylistPlayer = self.get_player(interaction.guild)
        if not player or not player.is_playing():
            raise Failure("I am not playing anything.")

        if player.is_paused():
            raise Failure("Playback is already paused.")
        else:
            await player.pause()
            embed = io.success(f"Paused playback of `{player.source.title}`.")
            await interaction.response.send_message(embed=embed)

    @music.command(name="resume", description="Resume the currently paused track.")
    async def music_resume(self, interaction: discord.Interaction):
        self.check_wavelink_ready()
        self.check_can_use_voice_command(interaction, same_channel=True)

        # Find player.
        player: PlaylistPlayer = self.get_player(interaction.guild)
        if not player or not player.is_playing():
            raise Failure("I am not playing anything.")

        if not player.is_paused():
            raise Failure("Playback is not paused.")
        else:
            await player.resume()
            embed = io.success(f"Resumed playback of `{player.source.title}`.")
            await interaction.response.send_message(embed=embed)

    @music.command(name="stop", description="Stop playback.")
    async def music_stop(self, interaction: discord.Interaction):
        self.check_wavelink_ready()
        self.check_can_use_voice_command(interaction, same_channel=True)

        # Find player.
        player: PlaylistPlayer = self.get_player(interaction.guild)
        if not player or not player.is_playing():
            raise Failure("I am not playing anything.")
        
        track = player.source

        await player.stop()

        embed = io.success(f"Stopped playback of `{track.title}`.")
        await interaction.response.send_message(embed=embed)

    @music.command(name="skip", description="Skip the current track.")
    async def music_skip(self, interaction: discord.Interaction):
        self.check_wavelink_ready()
        self.check_can_use_voice_command(interaction, same_channel=True)

        # Find player.
        player: PlaylistPlayer = self.get_player(interaction.guild)
        if not player or not player.is_playing():
            raise Failure("I am not playing anything.")

        track = player.source
        
        if player.playlist.has_next():
            await player.play_next()
        else:
            await player.stop()

        embed = io.success(f"Skipped playback of `{track.title}`.")
        await interaction.response.send_message(embed=embed)
        
    @music.command(name="playlist", description="View the playlist.")
    async def music_playlist(self, interaction: discord.Interaction):
        self.check_wavelink_ready()

        # Find player.
        player: PlaylistPlayer = self.get_player(interaction.guild)
        if not player:
            raise Failure("I can't show you the playlist without first joining a voice channel.")

        view = PlaylistView(interaction.user, player)
        embed = view.get_page(0)
        await interaction.response.send_message(embed=embed, view=view)
        await view.wait()

    @music.command(name="remove", description="Remove a track from the playlist.")
    async def music_remove(self, interaction: discord.Interaction, position: commands.Range[int, 1, None]):
        self.check_wavelink_ready()

        # Find player.
        player: PlaylistPlayer = self.get_player(interaction.guild)
        if not player:
            raise Failure("I can't remove a track from the playlist without first joining a voice channel.")

        if player.playlist.is_empty():
            raise Failure("The playlist is empty.")

        # Get the track.
        if position > player.playlist.length:
            raise Failure(f"You must specify a position within the playlist range (max: {player.playlist.length}).")
        
        track = await player.playlist.remove_track(position-1)
        
        embed = io.success(f"Removed `[{track.title}]({track.uri})` from the playlist.")
        await interaction.response.send_message(embed=embed)

    @music.command(name="clear", description="Clear the playlist.")
    async def music_clear(self, interaction: discord.Interaction):
        self.check_wavelink_ready()

        # Find player.
        player: PlaylistPlayer = self.get_player(interaction.guild)
        if not player:
            raise Failure("I can't empty the playlist without first joining a voice channel.")

        if player.playlist.is_empty():
            raise Failure("The playlist is empty.")
    
        view = io.Confirm(interaction.user)
        count = player.playlist.length
        embed = io.message(f"Are you sure you want to remove {count} track(s) from the playlist?")
        await interaction.response.send_message(embed=embed, view=view)

        if await view.wait():
            raise Failure("The interaction timed out.")
        
        if view.value:
            await player.playlist.clear()
            embed = io.success(f"Removed {count} track(s) from the playlist.")
            await interaction.followup.send(embed=embed)
        else:
            embed = io.success("The playlist was not cleared.")
            await interaction.followup.send(embed=embed)
    
    @music.command(name="nowplaying", description="View information about the currently playing track.")
    async def music_nowplaying(self, interaction: discord.Interaction):
        self.check_wavelink_ready()

        # Find player.
        player: PlaylistPlayer = self.get_player(interaction.guild)
        if not player:
            raise Failure("I can't show you track information without first joining a voice channel.")

        if not player.is_playing():
            raise Failure("I am not playing anything at the moment.")

        track = player.track
        title = track.title
        url = track.uri

        try:
            position = player.playlist.tracks.index(track) + 1
            position = f"#{position:03d}"
        except:
            position = "#???"

        elapsed = string.format_seconds(player.position)
        duration = string.format_seconds(track.duration)

        description = f"{position} [{title}]({url}) ({elapsed} / {duration})"
        embed: discord.Embed = io.message(description)
        if isinstance(track, wavelink.YouTubeTrack):
            embed.set_thumbnail(url=track.thumbnail)
        
        await interaction.response.send_message(embed=embed)

    @music.command(name="repeat", description="Enable track or playlist repeating.")
    @commands.choices(mode=[
        commands.Choice(name="off", value=Repeat.OFF),
        commands.Choice(name="all", value=Repeat.ALL),
        commands.Choice(name="track", value=Repeat.TRACK)
    ])
    async def music_repeat(self, interaction: discord.Interaction, mode: Optional[commands.Choice[str]]):
        self.check_wavelink_ready()

        # Find player.
        player: PlaylistPlayer = self.get_player(interaction.guild)
        if not player:
            raise Failure("I can't change the repeat mode without first joining a voice channel.")

        # Show current mode if no mode is given.
        if mode is None:
            mode = player.playlist.repeat
            embed = io.success(f"Repeat mode is currently set to `{mode}`")
            await interaction.response.send_message(embed=embed)
            return

        # Change repeat mode.
        mode = Repeat(mode.value)
        self.log.info(f"Setting repeat for {player} to {mode}.")
        await player.playlist.set_repeat(mode)

        if mode == Repeat.OFF:
            embed = io.success("Repeating is now disabled.")
        elif mode == Repeat.ALL:
            embed = io.success("Playlist repeating enabled.")
        elif mode == Repeat.TRACK:
            embed = io.success("Single track repeating enabled.")
        
        await interaction.response.send_message(embed=embed)

    @music.command(name="volume", description="Check or change the playlist volume.")
    @commands.describe(volume="Volume in percent from 0% to 150%.")
    async def music_volume(self, interaction: discord.Interaction, volume: Optional[commands.Range[int, 0, 150]]):
        self.check_wavelink_ready()

        # Find player.
        player: PlaylistPlayer = self.get_player(interaction.guild)
        if not player:
            raise Failure("I can't change the volume without first joining a voice channel.")

        # If the volume is provided, set it.
        if volume is not None:
            await player.set_volume(volume)

            embed = io.success(f"Volume set to `{volume}%`.")
            await interaction.response.send_message(embed=embed)
            return
        
        # Otherwise show the current volume.
        volume = player.volume

        embed = io.success(f"The volume is set to `{volume}%`.")
        await interaction.response.send_message(embed=embed)
