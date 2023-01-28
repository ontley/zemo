import os
import json
from discord import app_commands, Interaction
from discord.ext import commands
from utils.muse import Song, VideoNotFoundError
from utils.data import MusicData, music_data


@app_commands.guild_only()
class Theme(app_commands.Group, name='theme'):
    def __init__(self, client: commands.Bot, data: MusicData) -> None:
        self.client = client
        self.data = data
        super().__init__()

    @app_commands.command(name='set')
    @app_commands.describe(url='The url of your theme')
    @app_commands.guild_only()
    async def _set(self, interaction: Interaction, url: str) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            song: Song = Song.find_by_url(url)
        except VideoNotFoundError:
            await interaction.edit_original_response(content=f'Could not find a video from url `{url}`')
            return
        try:
            with open(f'{os.getcwd()}/data/user_themes.json', 'r') as f:
                data = json.load(f)
            with open(f'{os.getcwd()}/data/user_themes.json', 'w') as f:
                data['user_themes'][interaction.user.id] = url
                json.dump(data, f)
                await interaction.edit_original_response(content=f'Set your theme to {song.title}', embed=song.embed)
                return
        except OSError as e:
            print(e)
            await interaction.edit_original_response(content='Failed to set your theme')

    @app_commands.command(name='clear')
    async def _clear(self, interaction: Interaction) -> None:
        try:
            with open(f'{os.getcwd()}/data/user_themes.json', 'r') as f:
                data = json.load(f)
            with open(f'{os.getcwd()}/data/user_themes.json', 'w') as f:
                del data['user_themes'][interaction.user.id]
                json.dump(data, f)
                await interaction.response.send_message(content=f'Cleared your theme', ephemeral=True)
                return
        except OSError as e:
            print(e)
            await interaction.response.send_message(content='Failed to set your theme', ephemeral=True)


async def setup(client: commands.Bot, guilds: list[int]) -> None:
    client.tree.add_command(Theme(client, music_data), guilds=guilds)
