import discord

from discord import app_commands
from discord import Interaction

from discord.ext import commands

from utils.checks import user_connected
from utils.checks import user_and_bot_connected
from utils.checks import bot_connected

from utils.data import MusicData
from utils.data import music_data

from utils.muse import Player
from utils.muse import DisconnectReason
from utils.muse import Song
from utils.muse import VideoNotFoundError
from utils.menu import ListMenu

from utils.queue import RepeatMode


class Music(commands.Cog):
    def __init__(self, client: commands.Bot, data: MusicData) -> None:
        self.client = client
        self.data = data

    async def join_vc(self, vc: discord.VoiceChannel | discord.StageChannel) -> Player:
        """Join a voice channel."""
        id = vc.guild.id
        voice_client: discord.VoiceClient = await vc.connect(self_deaf=True)
        if voice_client.guild.id not in self.data.players:
            self.data.players[id] = player = Player(voice_client)
            player.queue.repeat = RepeatMode.All
        else:
            self.data.players[id].voice_client = voice_client
        return self.data.players[id]

    @app_commands.command(name='join')
    @app_commands.guild_only()
    @user_connected()
    async def _join(self, interaction: Interaction) -> None:
        """Join your channel"""
        user = interaction.user
        player = self.data.players.get(user.voice.channel.id, None)
        if player is None:
            await self.join_vc(user.voice.channel)
            await interaction.response.send_message(
                'Joining your voice channel',
                ephemeral=True
            )
            return
        if player.voice_client.channel == interaction.user.voice.channel:
            await interaction.response.send_message(
                'Already in your channel',
                ephemeral=True
            )
        else:
            # TODO: Swap channels menu, also don't lol and shid
            pass

    @app_commands.command(name='leave')
    @app_commands.describe(clear='Should I clear this channel\'s queue?')
    @app_commands.guild_only()
    async def _leave(self, interaction: Interaction, clear: bool | None) -> None:
        """Leave the channel and remove the queue"""
        player = self.data.players[interaction.guild_id]
        await player.leave()
        await interaction.response.send_message('Leaving')
        player = self.data.players[interaction.guild_id]
        if clear:
            del self.data.players[interaction.guild_id]

    @app_commands.command(name='add')
    @app_commands.describe(query='What to search for')
    @app_commands.guild_only()
    @user_connected()
    async def _add(self, interaction: Interaction, query: str) -> None:
        """Add a song to the queue and start playing if not already started"""
        await interaction.response.defer()
        player = self.data.players.get(interaction.guild_id, None)
        if player is None:
            player = await self.join_vc(interaction.user.voice.channel)
        try:
            song = Song.find_by_query(query)
        except VideoNotFoundError:
            await interaction.edit_original_response(
                content=f'Couldn\'t find any videos from query `{query}`'
            )
            return
        player.queue.items.append(song)
        if not player.is_playing():
            player.play()
        await interaction.edit_original_response(
            content=f'Added `{song.title}` to the queue',
            embed=song.embed
        )

    @app_commands.command(name='insert')
    @app_commands.describe(query='What to search for')
    @app_commands.describe(position='Where to place song')
    @app_commands.guild_only()
    @user_connected()
    async def _insert(self, interaction: Interaction, query: str, position: int) -> None:
        """Insert a song into some position in the queue and start playing if not already started"""
        await interaction.response.defer()
        player = self.data.players.get(interaction.guild_id, None)
        if player is None:
            player = await self.join_vc(interaction.user.voice.channel)
        try:
            song = Song.find_by_query(query)
        except VideoNotFoundError:
            await interaction.edit_original_response(
                content=f'Could not find any song matching query {query}'
            )
            return
        position = min(len(player.queue), position)
        player.queue.items.insert(position, song)
        if not player.is_playing():
            player.play()
        await interaction.edit_original_response(content=f'Inserted `{song.title}` into positition {position} of the queue')

    @app_commands.command(name='loop')
    @app_commands.describe(mode='Looping mode')
    @app_commands.guild_only()
    @user_and_bot_connected()
    async def _loop(self, interaction: Interaction, mode: RepeatMode | None) -> None:
        """Set the looping mode"""
        player = self.data.players[interaction.guild_id]
        if mode is not None:
            player.queue.repeat = mode
        await interaction.response.send_message(f'Looping mode set to `{player.queue.repeat.value}`')
        if player.queue and not player.voice_client.is_playing():
            player.play()

    @app_commands.command(name='shuffle')
    @app_commands.guild_only()
    @user_and_bot_connected()
    async def _shuffle(self, interaction: Interaction) -> None:
        """Shuffle the queue"""
        player = self.data.players[interaction.guild_id]
        player.queue.shuffle()
        await interaction.response.send_message('Shuffled the queue')

    @app_commands.command(name='queue')
    @app_commands.guild_only()
    @bot_connected()
    async def _queue(self, interaction: Interaction) -> None:
        """Sends an embed with the queue list"""
        player = self.data.players[interaction.guild_id]
        if not player.queue:
            await interaction.response.send_message('Nothing in queue')
            return
        songs = [
            f'**{index}. **{song} by {song.channel_name}'
            for index, song in enumerate(player.queue.items, start=1)
        ]
        m = ListMenu(
            items=songs,
            title='Queue',
            description='Current queue',
            owner=interaction.user
        )
        await m.start(interaction)

    @app_commands.command(name='current')
    @app_commands.guild_only()
    @bot_connected()
    async def _current(self, interaction: Interaction):
        """Currently playing song"""
        player = self.data.players[interaction.guild_id]
        if not player.queue:
            await interaction.response.send_message('Nothing in queue')
            return
        q = player.queue
        song = q.current
        await interaction.response.send_message(embed=song.embed)

    @app_commands.command(name='skip')
    @app_commands.describe(offset='How far to skip')
    @app_commands.guild_only()
    @user_and_bot_connected()
    async def _skip(self, interaction: Interaction, offset: int = 1) -> None:
        """Skip a certain number of songs, negative values allowed"""
        player = self.data.players[interaction.guild_id]
        player.queue.index += offset
        player.stop()
        song = player.queue.current
        await interaction.response.send_message(f'Skipped to `{song.title}`!')

    @app_commands.command(name='jump')
    @app_commands.describe(position='The position in queue to jump to')
    @app_commands.guild_only()
    @user_and_bot_connected()
    async def _jump(self, interaction: Interaction, position: int) -> None:
        """Jump to a certain position in the queue"""
        player = self.data.players[interaction.guild_id]
        queue = player.queue
        if position < 1:
            await interaction.response.send_message(
                'Position can\'t be less than 1',
                ephemeral=True
            )
            return
        elif position > len(queue):
            await interaction.response.send_message(
                f'Position {position} is out of range of the queue',
                ephemeral=True
            )
            return
        queue.index = position - 1
        player.stop()
        song = player.queue.current
        await interaction.response.send_message(f'Jumped to `{song.title}`')

    @app_commands.command(name='pause')
    @app_commands.guild_only()
    @user_and_bot_connected()
    async def _pause(self, interaction: Interaction):
        """Pause playback"""
        player = self.data.players[interaction.guild_id]
        player.pause()
        await interaction.response.send_message('Paused')

    @app_commands.command(name='resume')
    @app_commands.guild_only()
    @user_and_bot_connected()
    async def _resume(self, interaction: Interaction):
        """Resume playback"""
        player = self.data.players[interaction.guild_id]
        player.resume()
        await interaction.response.send_message('Resumed')

    @app_commands.command(name='remove')
    @app_commands.describe(position='Position of the song to remove, removes the current song if not given')
    @app_commands.guild_only()
    @user_and_bot_connected()
    async def _remove(self, interaction: Interaction, position: int | None = None):
        """Removes a song from the queue, removes the current song if called without argument"""
        player = self.data.players[interaction.guild_id]
        if position is None:
            position = player.queue.index + 1
        if position not in range(len(player.queue) + 1):
            await interaction.response.send_message(
                f'Position {position} is outside the range of the queue'
            )
            return
        removed = player.queue.items.pop(position - 1)
        await interaction.response.send_message(f'Removed `{removed.title}`')

    @app_commands.command(name='clear')
    @app_commands.guild_only()
    @user_and_bot_connected()
    async def _clear(self, interaction: Interaction):
        """Clear the queue"""
        player = self.data.players[interaction.guild_id]
        player.queue.clear()
        await interaction.response.send_message('Cleared the queue')

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ):
        if member.bot:
            if member.id == self.client.user.id and after.channel is None:
                # del self.data.players[member.guild.id, None]
                pass
            return
        player = self.data.players.get(member.guild.id, None)
        if player is None:
            return
        if after.channel == player.voice_client.channel != before.channel:
            player.cancel_timeout(DisconnectReason.ALONE_IN_CHANNEL)
            themes = self.data.user_themes
            if str(member.id) in themes:
                user_theme_url = themes[str(member.id)]
                player.queue.alt_queue.append(Song.find_by_url(user_theme_url))
                if not player.is_playing():
                    player.play()
        else:
            members = player.voice_client.channel.members
            if all(user.bot for user in members):
                player.add_timeout(DisconnectReason.ALONE_IN_CHANNEL)


async def setup(client: commands.Bot, guilds: list[int]) -> None:
    await client.add_cog(Music(client, music_data), guilds=guilds)
