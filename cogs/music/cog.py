import asyncio
import logging
from typing import Optional, TypedDict

import discord
import discord.app_commands as commands
import wavelink
from discord.ext.commands import Bot, Cog

from core.errors import Failure, Warning
from core.utils import io, string

from .player import PlaylistPlayer
from .enums import Repeat, TrackType
from .ui import PlaylistView

class Music(Cog):
    """Cog for music commands."""

    def __init__(self, bot: Bot):
        super().__init__()

        # Internal setup.
        self.log = logging.getLogger(__name__)
        self.bot = bot
        self.node: wavelink.Node = None
        self.node_id = self.bot.config.wavelink_id

        # Create the setup task. Commands that rely on the wavelink node
        # can not be used before this task has been completed.
        self._setup = self.bot.loop.create_task(self.setup())
        self._setup.add_done_callback(self.setup_complete)

    async def setup(self):
        # The initial setup for this cog, which is ran everytime the
        # bot restarts or this module is hot-swapped. Creates the
        # lavalink node used by all music-related commands.
        await self.bot.wait_until_ready()

        # Create the node reference.
        self.log.info("Connecting to lavalink server...")
        try:
            self.node = wavelink.NodePool.get_node(id=self.node_id)
            self.log.info("Reusing existing node.")
        except (wavelink.InvalidNode):
            self.log.info(f"Creating new node with id {self.node_id}.")
            self.node = wavelink.Node(id=self.node_id, **self.bot.config.lavalink_credentials)
            await wavelink.NodePool.connect(client=self.bot, nodes=[self.node])

        # Find stale voice connections without a player and terminate them.
        # These can occur when the bot is improperly restarted and reconnects
        # to Discord before getting automatically kicked from a voice channel.
        for guild in self.bot.guilds:
            for voice in guild.voice_channels:

                # If the bot is in the voice call but we don't have a player,
                # terminate the voice connection to clean up.
                if self.bot.user in voice.members:
                    player = self.get_player(guild)

                    if not player:
                        self.log.info(f"Cleaning up stale connection in {guild!r} {voice!r}")
                        try:
                            client = await voice.connect()
                            await client.disconnect()
                        except:
                            pass

    def setup_complete(self, task: asyncio.Task):
        # Handle errors that might occur while creating the wavelink node.
        if not task.exception():
            self.log.info("Setup completed.")
            return
        
        # Handle errors.
        error = task.exception()
        self.log.error("An error occured while setting up!", exc_info=error)

        cog = self.bot.get_cog("Debug")
        if not cog:
            return

        self.bot.loop.create_task(cog.log_error(error))

    # Event handlers.

    @Cog.listener()
    async def on_wavelink_node_ready(self, node: wavelink.Node):
        self.log.info(f"Wavelink node {node.id!r} is ready.")

    @Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackEventPayload):
        self.log.info(f"Player {payload.player!r} started playing {payload.track.title}.")

        try:
            track = payload.track
            embed = io.message(f"Now playing [`{track.title}`]({track.uri}).")
            await payload.player.text_channel.send(embed=embed)
        except Exception as err:
            self.log.error("Unable to send now playing notification.", exc_info=err)

    @Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEventPayload):
        self.log.info(f"Player {payload.player!r} finished playing {payload.track.title}.")
        
        # Ignore stop events caused by /music stop or /music play.
        if payload.reason in ("STOPPED", "REPLACED"):
            return

        # Try to play the next track in the playlist.
        await payload.player.play_next()

    @Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):

        # Leave the voice channel after the last user leaves.
        if not member.bot and after.channel != before.channel:
            if not [m for m in before.channel.members if not m.bot]:

                # Check if there is a player for this guild / channel.
                player: PlaylistPlayer = self.get_player(member.guild)
                if player and player.channel == before.channel:
                    await self.cleanup_player(player)

        # After this point we don't care if it's not the bot user.
        if member != self.bot.user:
            return

        # Clean up the player after being forcibly removed from a voice channel.
        # This scenario also includes normal disconnects, but in that case the
        # player is already cleaned up, so we don't do any extra work.
        elif after.channel is None:
            
            # Get the player and disconnect it.
            player: PlaylistPlayer = self.get_player(member.guild)
            await self.cleanup_player(player)
        
        # Handle being moved to a different voice channel.
        elif before.channel and after.channel and before.channel != after.channel:

            # Get the player and move or kill it.
            player: PlaylistPlayer = self.get_player(member.guild)

            # If the channel is empty kill the player.
            if player and not [m for m in after.channel.members if not m.bot]:
                self.log.info("Cleaning up player after forced move.")
                await self.cleanup_player(player)
            
            # Otherwise move it.
            elif player:
                self.log.info("Moving player after forced move.")
                await player.move_to(after.channel)
                embed = io.message(f"Moved to {after.channel.mention}.")
                try:
                    await player.text_channel.send(embed=embed)
                except:
                    pass

    # Helper methods.

    def check_wavelink_ready(self):
        """Checks if wavelink is ready."""
        if self.node is None or self.node.status != wavelink.NodeStatus.CONNECTED:
            raise Failure("Just a moment, I'm still getting things ready...")

    def check_can_use_voice_command(self, interaction: discord.Interaction, same_channel: bool=True):
        """Checks whether the interaction author can use voice-related commands.
        
        Parameters
        ----------
        same_channel: bool
            When :obj:`True` also checks whether the user is connected to the
            same voice channel as the bot. Defaults to :obj:`True`."""
        player: wavelink.Player = self.get_player(interaction.guild)

        if not interaction.user.voice or interaction.user.voice.channel is None:
            raise Failure("You are not connected to a voice channel.")

        if same_channel and player != None and interaction.user.voice.channel != player.channel:
            raise Failure(f"You are not connected to {player.channel.mention}.")

    def check_can_connect(self, channel: discord.VoiceChannel):
        """Checks whether a voice channel can be connected to.
        
        Raises
        ------
        Failure
            Exception raised when the bot does not have the connect and / or
            speak permission for the provide voice channel.
        """
        perms: discord.Permissions = channel.permissions_for(channel.guild.me)

        missing = []
        if not perms.connect:
            missing.append("connect")
        
        if not perms.speak:
            missing.append("speak")
        
        if missing:
            formatted = string.human_join(missing, code=True)
            message = f"I am missing the following permissions to access {channel.mention}: {formatted}."
            raise Failure(message)

    # Player and queue methods.

    async def create_player(self, text: discord.TextChannel, voice: discord.VoiceChannel) -> PlaylistPlayer:
        """Create a new player.

        Will raise a :class:`discord.app_commands.BotMissingPermissions` if the bot can not
        connect to the voice channel or is missing any
        of the required permissions.
        
        Parameters
        ----------
        text: discord.TextChannel
            The text channel to output status information to.
        voice: discord.VoiceChannel
            The voice channel to connect the player to.

        Raises
        ------
        discord.app_commands.BotMissingPermissions
            Exception raised when the bot is missing any of the required
            permissions to connect to the voice channel and play audio.
        """
        self.check_can_connect(voice)
        player = await PlaylistPlayer.create(self.bot, text, voice, self.node)
        await voice.connect(cls=player)
        return player

    def get_player(self, guild: discord.Guild) -> Optional[wavelink.Player]:
        """Get the player for a guild.
        
        Returns
        -------
        Optional[wavelink.Player]
            The player or :obj:`None` if no player exists for this guild.
        """
        return self.node.get_player(guild.id) or guild.voice_client

    async def cleanup_player(self, player: Optional[PlaylistPlayer]):
        """Attempt to disconnect and clean up a player.
        
        Disconnetcs and cleans up the player and attempts
        to send a message in its text channel.

        Parameters
        ----------
        player: Optional[PlaylistPlayer]
            The playlist player to clean up. You can pass in :obj:`None` to
            immediately return instead.
        """
        if player is None:
            return
        
        embed = io.message(f"Disconnected from {player.last_voice_channel.mention}.")
        try:
            await player.text_channel.send(embed=embed)
        except:
            pass

        try:
            await player.disconnect()
        except:
            player.cleanup()

    async def resolve_tracks(self, interaction: discord.Interaction, source:str) -> list[wavelink.GenericTrack]:
        """Attempt to find one or more tracks for a given source string.
        
        Parameters
        ----------
        interaction: discord.Interaction
            The interaction during which the tracks are being resolved.
        source: str
            A source string that is used to search for tracks.
        
        Returns
        -------
        list[wavelink.GenericTrack]
            A list of tracks.
        """
        tracks: list[wavelink.GenericTrack] = list()

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
                results = await self.node.get_tracks(query=source, cls=wavelink.GenericTrack)
                if len(results) > 0:
                    tracks.append(results[0])
                else:
                    raise Failure("I could not find any usable music under that URL.")

        # Youtube search.
        else:
            results = await wavelink.YouTubeTrack.search(source)
            if len(results) == 0:
                raise Failure("I could not find any music for the given search term.")

            options = {string.truncate(track.title, 80): track for track in results[:5]}
            view = io.Choice(interaction.user, options=options)
            
            lines = []
            for label, track in options.items():
                lines.append(f"[`{label}`]({track.uri})")

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
            raise Failure("No voice channel provided. Please either join a voice channel or specify a channel for me to join.")

        # Check if the provided channel is empty.
        elif channel and not [m for m in channel.members if not m.bot]:
            raise Failure("There are no listeners in that voice channel.")
        
        # Move existing player.
        channel = channel or interaction.user.voice.channel
        self.check_can_connect(channel)
        player: wavelink.Player = channel.guild.voice_client
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
            channel = player.channel
            await player.disconnect()
            embed = io.success(f"Disconnected from {channel.mention}.")
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

            track = player.playlist.set_position(actual)
            await player.play(track)
            return

        # If a source is specified we look it up and add it to the playlist.
        try:
            tracks: list[wavelink.GenericTrack] = await self.resolve_tracks(interaction, source)
        except wavelink.WavelinkException:
            raise Failure("I could not find any usable music under that URL.")
        
        # Add tracks to playlist.
        play_next = (player.playlist.length != 0)
        position = player.playlist.length + 1
        player.playlist.add_tracks(tracks)
        
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
        if not player:
            raise Failure("I am not playing anything.")
        elif player.is_paused():
            raise Failure("Playback is already paused.")
        elif not player.is_playing():
            raise Failure("I am not playing anything.")
        else:
            await player.pause()
            embed = io.success(f"Paused playback of `{player.current.title}`.")
            await interaction.response.send_message(embed=embed)

    @music.command(name="resume", description="Resume the currently paused track.")
    async def music_resume(self, interaction: discord.Interaction):
        self.check_wavelink_ready()
        self.check_can_use_voice_command(interaction, same_channel=True)

        # Find player.
        player: PlaylistPlayer = self.get_player(interaction.guild)
        if not player:
            raise Failure("I am not playing anything.")
        elif not player.is_paused() or player.is_playing():
            raise Failure("Playback is not paused.")

        await player.resume()
        embed = io.success(f"Resumed playback of `{player.current.title}`.")
        await interaction.response.send_message(embed=embed)

    @music.command(name="stop", description="Stop playback.")
    async def music_stop(self, interaction: discord.Interaction):
        self.check_wavelink_ready()
        self.check_can_use_voice_command(interaction, same_channel=True)

        # Find player.
        player: PlaylistPlayer = self.get_player(interaction.guild)
        if not player or not player.is_playing():
            raise Failure("I am not playing anything.")
        
        track = player.current

        await player.stop()

        embed = io.success(f"Stopped playback of [`{track.title}`]({track.uri}).")
        await interaction.response.send_message(embed=embed)

    @music.command(name="seek", description="Seek to a position in the current track.")
    async def music_seek(
            self, 
            interaction: discord.Interaction, 
            hours: Optional[commands.Range[int, 0, 999]], 
            minutes: Optional[commands.Range[int, 0, 59]], 
            seconds: Optional[commands.Range[int, 0, 59]]
        ):
        self.check_wavelink_ready()
        self.check_can_use_voice_command(interaction, same_channel=True)

        # Find player.
        player: PlaylistPlayer = self.get_player(interaction.guild)
        if not player or not player.is_playing():
            raise Failure("I am not playing anything.")
        
        # Check if any time was provided.
        if hours is None and minutes is None and seconds is None:
            raise Failure("Please provide a time to seek to.")
            
        hours = hours if hours is not None else 0
        minutes = minutes if minutes is not None else 0
        seconds = seconds if seconds is not None else 0

        seconds = seconds + minutes * 60 + hours * 3600
        milliseconds = seconds * 1000
        await player.seek(milliseconds)

        # Send message.
        track = player.current
        position = string.format_milliseconds(milliseconds)
        embed = io.success(f"Skipped [`{track.title}`]({track.uri}) to position `{position}`.")
        await interaction.response.send_message(embed=embed)

    @music.command(name="skip", description="Skip the current track.")
    async def music_skip(self, interaction: discord.Interaction):
        self.check_wavelink_ready()
        self.check_can_use_voice_command(interaction, same_channel=True)

        # Find player.
        player: PlaylistPlayer = self.get_player(interaction.guild)
        if not player or not player.is_playing():
            raise Failure("I am not playing anything.")

        track = player.current
        
        if player.playlist.has_next():
            await player.play_next()
        else:
            await player.stop()

        embed = io.success(f"Skipped playback of [`{track.title}`]({track.uri}).")
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
        
        track = player.playlist.remove_track(position-1)
        
        embed = io.success(f"Removed [`{track.title}`]({track.uri}) from the playlist.")
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
            player.playlist.clear()
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

        track = player.current
        title = track.title
        url = track.uri

        try:
            position = player.playlist.tracks.index(track) + 1
            position = f"#{position:03d}"
        except:
            position = "#???"

        elapsed = string.format_milliseconds(player.position)
        duration = string.format_milliseconds(track.duration)

        description = f"{position} [`{title}`]({url}) ({elapsed} / {duration})"
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
        player.playlist.set_repeat(mode)

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
