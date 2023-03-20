from discord.ext import commands

from discord import app_commands
from discord import Interaction

from random import choice


LISTA_MUDRIH = [
    'Svejedno priznajem bodove jer ne želim opet doživjeti neugodno iskustvo u kojem se Davor neprimjereno meni obraća s povišenim tonom.',
    'Kad kurac.',
    'Dakle... ja se jesam drogirao.',
    'Imam neke ljude u glavi.',
    'Bolje mijesat alkohol nego beton.',
    'S kim si, s njim si.',
    'Tko umre na jesen, njemu nema zime.',
    'Tko jede, taj sere.',
    'Na mrtvom vuku i zec kurac ostri.',
    'Kad sam trijezan mislim sto govorim, kad sam pijan govorim sto mislim.',
    'Bolje kurac u ruci nego skola u struci.',
]


class Memes(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client = client

    @app_commands.command(name='say')
    @app_commands.describe(message='What do you want me to say')
    @app_commands.guild_only()
    async def _say(self, interaction: Interaction, message: str) -> None:
        await interaction.channel.send(message)
        await interaction.response.send_message('Sent message', ephemeral=True)

    @app_commands.command(name='mudra', description='daj mi jednu mudru')
    @app_commands.guild_only()
    async def _mudra(self, interaction: Interaction) -> None:
        await interaction.response.send_message(choice(LISTA_MUDRIH))


async def setup(client: commands.Bot, guilds: list[int]) -> None:
    await client.add_cog(Memes(client), guilds=guilds)
