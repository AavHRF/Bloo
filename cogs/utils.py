import discord
from discord.ext import commands
from discord import app_commands
from framework.bot import Bloo
from typing import Literal
from xml.etree import ElementTree


class ModView(discord.ui.View):

    def __init__(self, bot: Bloo, nation: str, member: discord.Member):
        super().__init__()
        self.value = None


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
            message: str,
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
        await interaction.followup.send(
            f"Purge complete! Purged {tally} unverified members.", ephemeral=True
        )

    @app_commands.command(
        name="lookup", description="Looks up a nation or region on nationstates.net."
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def lookup(
            self,
            interaction: discord.Interaction,
            which: Literal["nation", "region"],
            name: str,
            show: Literal["me", "channel"],
    ):
        if show == "me":
            await interaction.response.defer(ephemeral=True)
        else:
            await interaction.response.defer()
        if which == "nation":
            response = await self.bot.ns_request(
                payload={"nation": name.lower().replace(" ", "_")},
                mode="GET",
            )
        else:
            response = await self.bot.ns_request(
                payload={"region": name.lower().replace(" ", "_")},
                mode="GET",
            )
        if response.status != 200:
            await interaction.followup.send(
                "NationStates experienced an error.", ephemeral=True
            )
            return
        tree = ElementTree.fromstring(await response.text())
        if which == "nation":
            embed = discord.Embed(
                title=tree.find("FULLNAME").text,
                url=f"https://www.nationstates.net/nation={name.lower().replace(' ', '_')}",
                description=f"*{tree.find('MOTTO').text}*"
            )
            if not tree.find("FLAG").text.endswith(".svg"):
                embed.set_thumbnail(url=tree.find("FLAG").text)
            embed.add_field(
                name="Region",
                value=f"[{tree.find('REGION').text}](https://nationstates.net/region={tree.find('REGION').text.lower().replace(' ', '_')})"
            )
            embed.add_field(
                name="World Assembly",
                value=tree.find("UNSTATUS").text
            )
            embed.add_field(
                name="Founded",
                value=f"<t:{int(tree.find('FIRSTLOGIN').text)}>"
            )
            embed.set_footer(
                text=f"Last activity was {tree.find('LASTACTIVITY').text}"
            )
            if interaction.user.guild_permissions.ban_members:
                if show == "me":
                    modcheck = await self.bot.fetch(
                        "SELECT * FROM nsv_ban_table WHERE nation = $1 AND guild_id = $2",
                        name.lower().replace(' ', '_'),
                        interaction.guild.id,
                    )
                    if modcheck:
                        reason = modcheck[0]["reason"]
                        embed.description += "```ansi\n\u001b[14;31m**BANNED**\u001b[0m"
                        embed.description += f"\n\u001b[14;31mReason:\u001b[0m\n{reason}```"
            await interaction.followup.send(embed=embed, ephemeral=True)

        else:
            embed = discord.Embed(
                title=tree.find("NAME").text,
                url=f"https://www.nationstates.net/region={name.lower().replace(' ', '_')}",
                description=f"*{tree.find('MOTTO').text}*"
            )
            embed.add_field(
                name="Delegates",
                value=tree.find("DELEGATES").text
            )
            embed.add_field(
                name="Founded",
                value=f"<t:{int(tree.find('CREATED').text)}>"
            )
            embed.set_footer(
                text=f"Last activity was {tree.find('LASTACTIVITY').text}"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: Bloo):
    await bot.add_cog(Utility(bot))
