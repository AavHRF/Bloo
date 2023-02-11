import discord
from discord.ext import commands
from discord import app_commands
from framework.bot import Bloo


class Utility(commands.Cog):
    def __init__(self, bot: Bloo):
        self.bot = bot

    @app_commands.command(name="post", description="Post a message to a channel")
    @app_commands.default_permissions(manage_messages=True)
    async def post(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        *,
        message: str
    ):
        await interaction.response.defer(ephemeral=True)
        await channel.send(message)
        await interaction.followup.send("Message sent!", ephemeral=True)


async def setup(bot: Bloo):
    await bot.add_cog(Utility(bot))
