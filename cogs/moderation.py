import discord
from discord.ext import commands
from discord import app_commands
from framework.bot import Bloo
from typing import Union


class Moderator(commands.Cog):

    def __init__(self, bot: Bloo):
        self.bot = bot

    @app_commands.command(name="ban", description="Ban a member by name, ID, or nation")
    @app_commands.default_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        member: Union[discord.Member, discord.User, str],
        reason: str,
        delete_message_days: int = 0,
    ):
        await interaction.response.defer(ephemeral=True)
        if isinstance(member, str):
            record = await self.bot.fetch(
                "SELECT discord_id FROM nsv_table WHERE nation = $1",
                member.lower().replace(" ", "_"),
            )
            if not member:
                await self.bot.execute(
                    "INSERT INTO nsv_ban_table (nation, reason, guild_id) VALUES ($1, $2, $3)",
                    member.lower().replace(" ", "_"),
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
        else:
            await interaction.guild.ban(
                member, reason=reason, delete_message_days=delete_message_days
            )
            await interaction.followup.send("Banned!", ephemeral=True)
