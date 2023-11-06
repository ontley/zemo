from discord import app_commands
from discord import Interaction

from discord.ext import commands

from zemo.utils.muse import Song
from zemo.utils.muse import VideoNotFoundError

from zemo.utils.data import MusicData
from zemo.utils.data import music_data


@app_commands.guild_only()
class Theme(app_commands.Group, name='theme'):
    def __init__(self, client: commands.Bot, data: MusicData) -> None:
        self.client: commands.Bot = client
        self.data: MusicData = data
        super().__init__()

    @app_commands.command(name='set')
    @app_commands.describe(url='The url of your theme')
    @app_commands.guild_only()
    async def _set(self, interaction: Interaction, url: str) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            song: Song = Song.find_by_query(url)
        except VideoNotFoundError:
            await interaction.edit_original_response(content=f'Could not find a video from url `{url}`')
            return
        try:
            self.data.set_theme(interaction.user.id, song.url)
            await interaction.edit_original_response(content=f'Set your theme to {song.title}', embed=song.embed)
            return
        except OSError as e:
            print(e)
            await interaction.edit_original_response(content='Failed to set your theme')

    @app_commands.command(name='clear')
    async def _clear(self, interaction: Interaction) -> None:
        try:
            self.data.clear_theme(interaction.user.id)
            await interaction.response.send_message(content=f'Cleared your theme', ephemeral=True)
            return
        except OSError as e:
            print(e)
            await interaction.response.send_message(content='Failed to set your theme', ephemeral=True)


async def setup(client: commands.Bot, guilds: list[int]) -> None:
    client.tree.add_command(Theme(client, music_data), guilds=guilds) # type: ignore
