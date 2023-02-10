import discord
from discord.ext import commands
from framework.bot import Bloo


class Listeners(commands.Cog):
    def __init__(self, bot: Bloo):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        settings = await self.bot.fetch(
            "SELECT * FROM welcome_settings WHERE guild_id = $1",
            member.guild.id
        )
        if not settings:
            return
        embed = discord.Embed(
            title=f"Welcome to {member.guild.name}, {member.display_name}!",
            description=settings[0]["embed_message"],
            color=discord.Color.random(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(
            name="Member count",
            value=member.guild.member_count,
        )
        embed.set_footer(text=f"ID: {member.id}")
        await member.guild.get_channel(settings[0]["welcome_channel"]).send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        settings = await self.bot.fetch(
            "SELECT * FROM welcome_settings WHERE guild_id = $1",
            member.guild.id
        )
        if not settings:
            return
        embed = discord.Embed(
            title=f"Goodbye, {member.display_name}!",
            color=discord.Color.random(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(
            name="Member count",
            value=member.guild.member_count,
        )
        embed.set_footer(text=f"ID: {member.id}")
        await member.guild.get_channel(settings[0]["welcome_channel"]).send(embed=embed)


async def setup(bot: Bloo):
    await bot.add_cog(Listeners(bot))
