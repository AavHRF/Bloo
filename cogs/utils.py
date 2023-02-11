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

    @commands.guild_only()
    @commands.hybrid_command(with_app_command=True)
    async def info(self, ctx: commands.Context, member: discord.Member = None):
        """
        Gets information about a member
        """
        if not member:
            member = ctx.author
        nation = await self.bot.fetch(
            "SELECT nation FROM nsv_table WHERE discord_id = $1 AND guild_id = $2",
            member.id,
            ctx.guild.id,
        )
        if not nation:
            nation = "None set"
        else:
            nation = nation[0]["nation"]

        embed = discord.Embed(
            title=f"Information for {member.display_name}",
            color=discord.Color.random(),
        )
        embed.add_field(
            name="Nation",
            value=nation.replace("_", " ").title(),
        )
        embed.add_field(
            name="ID",
            value=member.id,
        )
        embed.add_field(
            name="Joined server",
            value=f"<t:{member.joined_at.timestamp().__trunc__()}>",
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    @app_commands.command(name="purge", description="Purge unverified members")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def purge(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        verified = await self.bot.fetch(
            "SELECT discord_id FROM nsv_table WHERE guild_id = $1",
            interaction.guild.id,
        )
        verified = [i["discord_id"] for i in verified]
        await interaction.guild.chunk()
        tally = 0
        for member in interaction.guild.members:
            if member.id not in verified:
                await member.kick(reason="Unverified member purge")
                tally += 1
        await interaction.followup.send(f"Purge complete! Purged {tally} unverified members.", ephemeral=True)


async def setup(bot: Bloo):
    await bot.add_cog(Utility(bot))
