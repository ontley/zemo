import discord
import importlib
import json
import os

from pathlib import Path

from types import ModuleType
from typing import Sequence

from discord.ext import commands

from dotenv import load_dotenv
load_dotenv('.env')


with open(Path('data/bot_info.json'), 'r') as bot_info_json:
    guild_ids: dict[str, int] = json.load(bot_info_json)['guilds']
    GUILD_IDS: list[discord.Object] = list(map(discord.Object, guild_ids))


class Bot(commands.Bot):
    """Inherits from `commands.Bot`."""

    def __init__(
        self,
        command_prefix: str,
        *,
        plugin_dir: str = 'plugins',
        **kwargs
    ) -> None:
        super().__init__(command_prefix, **kwargs)
        self._plugins_dir_path: Path = Path(plugin_dir)

    async def load_plugins(
        self,
        *,
        guilds: Sequence[discord.Object]
    ) -> None:
        plugin_path = Path('zemo') / self._plugins_dir_path

        for filename in Path(plugin_path).rglob('*.py'):
            ext_path: Path = plugin_path / filename.stem
            print(ext_path)
            mod: ModuleType = importlib.import_module('.'.join(ext_path.parts))
            if not hasattr(mod, 'setup'):
                print(f"Plugin {mod.__name__} has no setup function")
                continue
            await mod.setup(self, guilds)
        for guild in guilds:
            await self.tree.sync(guild=guild)

    async def setup_hook(self) -> None:
        await self.load_plugins(guilds=GUILD_IDS)


def main() -> int:
    TOKEN = os.environ['DISCORD_TOKEN']
    APP_ID = os.environ['APPLICATION_ID']

    intents = discord.Intents.default()
    intents.message_content = True
    client = Bot(
        '+',
        plugin_dir='plugins',
        application_id=APP_ID,
        intents=intents
    )

    client.run(TOKEN)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
