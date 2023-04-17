from discord.ext import commands

from discord import app_commands
from discord import Interaction

from random import choice


LISTA_MUDRIH = [
    'Svejedno priznajem bodove jer ne želim opet doživjeti neugodno iskustvo u kojem se Davor neprimjereno meni obraća s povišenim tonom.',
    'Kad kurac.',
    'Dakle... ja se jesam drogirao.',
    'Imam neke ljude u glavi.',
    'Bolje miješat alkohol nego beton.',
    'S kim si, s njim si.',
    'Tko umre na jesen, njemu nema zime.',
    'Tko jede, taj sere.',
    'Na mrtvom vuku i zec kurac oštri.',
    'Kad sam trijezan mislim što govorim, kad sam pijan govorim što mislim.',
    'Bolje kurac u ruci nego škola u struci.',
    '42°34\'45.8"N 18°15\'26.6"E',
    'Džabe široka ramena kad su muda malena',
]


class Memes(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client: commands.Bot = client

    @app_commands.command(name='say')
    @app_commands.describe(message='What do you want me to say')
    @app_commands.guild_only()
    async def _say(self, interaction: Interaction, message: str) -> None:
        await interaction.channel.send(message) # type: ignore
        await interaction.response.send_message('Sent message', ephemeral=True)

    @app_commands.command(name='mudra', description='daj mi jednu mudru')
    @app_commands.guild_only()
    async def _mudra(self, interaction: Interaction) -> None:
        await interaction.response.send_message(choice(LISTA_MUDRIH))


async def setup(client: commands.Bot, guilds: list[int]) -> None:
    await client.add_cog(Memes(client), guilds=guilds) # type: ignore
