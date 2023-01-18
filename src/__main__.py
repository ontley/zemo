import discord
import glob
import importlib
import json
import os
from discord.ext import commands
from typing import Any, Sequence

from dotenv import load_dotenv
load_dotenv(f'{os.getcwd()}/.env')


with open('src/bot_info.json', 'r') as bot_info_json:
    guild_ids = json.load(bot_info_json)['guilds']
    GUILD_IDS = list(map(discord.Object, guild_ids))


class Bot(commands.Bot):
    """Inherits from `commands.Bot`."""

    def __init__(
        self,
        command_prefix: str,
        *,
        plugin_dir: str = 'plugins',
        **kwargs: dict[str, Any]
    ) -> None:
        super().__init__(command_prefix, **kwargs)
        self._plugins_dir = plugin_dir

    async def load_plugins(
        self,
        *,
        guilds: Sequence[discord.Object]
    ) -> None:
        plugin_path = f'src/{self._plugins_dir}'

        for filename in glob.iglob('**/*.py', root_dir=plugin_path, recursive=True):
            clean = filename.replace("\\", ".").rstrip('.py')
            ext_path = f'{self._plugins_dir}.{clean}'
            mod = importlib.import_module(ext_path)
            if not hasattr(mod, 'setup'):
                print(f"Plugin {mod.__name__} has no setup function")
                continue
            await mod.setup(self, guilds)
        for guild in guilds:
            await self.tree.sync(guild=guild)

    async def setup_hook(self) -> None:
        await self.load_plugins(guilds=GUILD_IDS)


TOKEN = os.environ.get('DISCORD_TOKEN')
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN token not found in .env file")
APP_ID = os.environ.get('APPLICATION_ID')
if APP_ID is None:
    raise ValueError("APPLICATION_ID token not found in .env file")

intents = discord.Intents.default()
intents.message_content = True
client = Bot(
    '+',
    plugin_dir='plugins',
    application_id=APP_ID,
    intents=intents
)

client.run(TOKEN)
