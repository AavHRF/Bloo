import discord
from discord.ext import commands
from discord import app_commands
from framework.bot import Bloo
from typing import Union


class Moderator(commands.Cog):
    def __init__(self, bot: Bloo):
        self.bot = bot

    @app_commands.command(
        name="ban_nation", description="Ban a member by nation name"
    )
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
        await self.bot.execute(
            "INSERT INTO nsv_ban_table (nation, reason, guild_id) VALUES ($1, $2, $3)",
            nation.lower().replace(" ", "_"),
            reason,
            interaction.guild.id,
        )
        await interaction.followup.send(
            "Nation banned. On entry/verification, any user with that nation will be removed from the server.",
            ephemeral=True,
        )
        if record:
            await interaction.guild.ban(
                record[0]["discord_id"],
                reason=reason,
                delete_message_days=delete_message_days,
            )

    # @app_commands.command(
    #     name="warn", description="Warn a member in the server"
    # )
    # @app_commands.default_permissions(timeout_members=True)
    # async def warn(
    #     self,
    #     interaction: discord.Interaction,
    #     member: Union[discord.Member, discord.User],
    #     reason: str,
    # ):
    #     await interaction.response.defer(ephemeral=True)
    #     await self.bot.execute(
    #         "INSERT INTO nsv_warn_table (discord_id, reason, guild_id) VALUES ($1, $2, $3)",
    #         member.id,
    #         reason,
    #         interaction.guild.id,
    #     )
    #     await interaction.followup.send(
    #         f"Warned {member.mention}.", ephemeral=True
    #     )


async def setup(bot: Bloo):
    await bot.add_cog(Moderator(bot))
