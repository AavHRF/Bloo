import discord
from discord.ext import commands
from discord import app_commands
from framework.bot import Bloo
from typing import Union


class Moderator(commands.Cog):

    def __init__(self, bot: Bloo):
        self.bot = bot

    @app_commands.command(name="ban_nation", description="Ban a member by name, ID, or nation")
    @app_commands.default_permissions(ban_members=True)
    async def ban_nation(
            self,
            interaction: discord.Interaction,
            nation: str,
            reason: str,
            delete_message_days: int = 0,
    ):
        await interaction.response.defer(ephemeral=True)
        record = await self.bot.fetch(
            "SELECT discord_id FROM nsv_table WHERE nation = $1",
            nation.lower().replace(" ", "_"),
        )
        if not nation:
            await self.bot.execute(
                "INSERT INTO nsv_ban_table (nation, reason, guild_id) VALUES ($1, $2, $3)",
                nation.lower().replace(" ", "_"),
                reason,
                interaction.guild.id,
            )
            await interaction.followup.send(
                "Nation banned. On entry/verification, any user with that nation will be removed from the server.",
                ephemeral=True
            )
        await interaction.guild.ban(
            record[0]["discord_id"], reason=reason, delete_message_days=delete_message_days
        )
        await interaction.followup.send("Banned!", ephemeral=True)


async def setup(bot: Bloo):
    await bot.add_cog(Moderator(bot))
