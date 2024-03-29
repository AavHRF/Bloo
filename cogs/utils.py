import discord
import datetime
import uuid
from discord.ext import commands
from discord import app_commands
from framework.bot import Bloo
from typing import Literal, Optional, Union
from xml.etree import ElementTree


class ReasonModal(discord.ui.Modal, title="Reason for ban"):
    def __init__(self, nation: str):
        super().__init__()
        self.nation = nation

    reason = discord.ui.TextInput(
        label="Reason",
        placeholder="Why is this nation banned?",
        min_length=1,
        max_length=1000,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        # noinspection PyTypeChecker
        bot: Bloo = interaction.client
        await bot.execute(
            "INSERT INTO nsv_ban_table (nation, reason, guild_id) VALUES ($1, $2, $3)",
            self.nation,
            self.reason.value,
            interaction.guild.id,
        )
        await interaction.response.send_message("Nation banned!", ephemeral=True)


class ModView(discord.ui.View):
    def __init__(
        self, bot: Bloo, nation: str, member: discord.Member, banned: bool = False
    ):
        super().__init__()
        self.bot = bot
        self.nation = nation
        self.member = member
        self.banned = banned
        self.add_item(
            discord.ui.Button(
                label="Show on nationstates.net",
                style=discord.ButtonStyle.link,
                url=f"https://www.nationstates.net/nation={self.nation}",
            )
        )

    @discord.ui.button(label="Unban", style=discord.ButtonStyle.green, row=0)
    async def unban(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.banned:
            return await interaction.response.send_message(
                "This nation is not banned!", ephemeral=True
            )
        else:
            await self.bot.execute(
                "DELETE FROM nsv_ban_table WHERE nation = $1 AND guild_id = $2",
                self.nation,
                interaction.guild.id,
            )
            await interaction.response.send_message("Nation unbanned!", ephemeral=True)
            self.banned = False

    @discord.ui.button(label="Ban", style=discord.ButtonStyle.red, row=0)
    async def ban(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.banned:
            return await interaction.response.send_message(
                "This nation is already banned!", ephemeral=True
            )
        else:
            await interaction.response.send_modal(ReasonModal(self.nation))


class Utility(commands.Cog):
    def __init__(self, bot: Bloo):
        self.bot = bot

    async def cog_app_command_error(
            self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"This command is on cooldown. Please try again in {error.retry_after:.2f} seconds.",
                ephemeral=True,
            )
        else:
            raise error

    @app_commands.command(name="post", description="Post a message to a channel")
    @app_commands.default_permissions(manage_messages=True)
    async def post(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: str,
        edit: Optional[str] = None,
    ):
        await interaction.response.defer(ephemeral=True)
        if not edit:
            await channel.send(message)
        else:
            msg = await channel.fetch_message(int(edit))
            await msg.edit(content=message)
        await interaction.followup.send("Message sent!", ephemeral=True)

    @app_commands.command(name="dm", description="Directly message a member from the bot.")
    @app_commands.default_permissions(kick_members=True)
    async def dm(self, interaction: discord.Interaction, member: discord.Member, sign: bool, message: str):
        await interaction.response.defer(ephemeral=True)
        if not sign:
            await member.send(message)
        else:
            await member.send(f"{message}\n*Sent by {interaction.user.name}#{interaction.user.discriminator}*")

        await interaction.followup.send("Message sent!", ephemeral=True)

    @commands.guild_only()
    @commands.hybrid_command(with_app_command=True)
    async def info(self, ctx: commands.Context, member: discord.Member = None):
        """
        Gets information about a member
        """
        if not member:
            member = ctx.author

        if ctx.guild.id != 414822188273762306:
            nations = await self.bot.fetch(
                "SELECT nation FROM nsv_table WHERE discord_id = $1 AND guild_id = $2",
                member.id,
                ctx.guild.id,
            )
            if not nations:
                nation = "None set"
            else:
                nation = ", ".join(
                    [i["nation"].replace("_", " ").title() for i in nations]
                )
        else:
            nations = await self.bot.fetch(
                "SELECT nation FROM nsl_table WHERE discord_id = $1",
                member.id,
            )
            if not nations:
                nation = "None set"
            else:
                nation = ", ".join(
                    [i["nation"].replace("_", " ").title() for i in nations]
                )

        embed = discord.Embed(
            title=f"Information for {member.display_name}",
            color=discord.Color.random(),
        )
        embed.add_field(
            name="Nation(s)",
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
        if response.status == 404:
            if which == "nation":
                await interaction.followup.send(
                    f"Could not find that nation. Try [checking the boneyard.]("
                    f"https://www.nationstates.net/page=boneyard?nation={name.lower().replace(' ', '_')})",
                    ephemeral=True,
                )
                return
            else:
                await interaction.followup.send(
                    f"That region does not appear to exist.", ephemeral=True
                )
                return
        elif response.status != 200:
            await interaction.followup.send(
                "NationStates experienced an error.", ephemeral=True
            )
            return
        tree = ElementTree.fromstring(await response.text())
        if which == "nation":
            embed = discord.Embed(
                title=tree.find("FULLNAME").text,
                url=f"https://www.nationstates.net/nation={name.lower().replace(' ', '_')}",
                description=f"*{tree.find('MOTTO').text}*",
            )
            if not tree.find("FLAG").text.endswith(".svg"):
                embed.set_thumbnail(url=tree.find("FLAG").text)
            embed.add_field(
                name="Region",
                value=f"[{tree.find('REGION').text}](https://nationstates.net/region={tree.find('REGION').text.lower().replace(' ', '_')})",
            )
            embed.add_field(name="World Assembly", value=tree.find("UNSTATUS").text)
            embed.add_field(
                name="Founded", value=f"<t:{int(tree.find('FIRSTLOGIN').text)}>"
            )
            embed.set_footer(text=f"Last activity was {tree.find('LASTACTIVITY').text}")
            if interaction.user.guild_permissions.ban_members:
                if show == "me":
                    modcheck = await self.bot.fetch(
                        "SELECT * FROM nsv_ban_table WHERE nation = $1 AND guild_id = $2",
                        name.lower().replace(" ", "_"),
                        interaction.guild.id,
                    )
                    if modcheck:
                        reason = modcheck[0]["reason"]
                        embed.description += "```ansi\n\u001b[1;31m**BANNED**\u001b[0m"
                        embed.description += (
                            f"\n\u001b[1;31mReason:\u001b[0m\n{reason}```"
                        )
                    await interaction.followup.send(
                        embed=embed,
                        ephemeral=True,
                        view=ModView(
                            self.bot,
                            name.lower().replace(" ", "_"),
                            interaction.user,
                            bool(modcheck),
                        ),
                    )
                else:
                    await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)

        else:
            embed = discord.Embed(
                title=tree.find("NAME").text,
                url=f"https://www.nationstates.net/region={name.lower().replace(' ', '_')}",
            )
            embed.add_field(name="Population", value=tree.find("NUMNATIONS").text)
            f = tree.find("FOUNDER").text
            embed.add_field(
                name="Founder",
                value=f"[{f.title().replace('_', ' ')}](https://nationstates.net/nation={f})"
                if f != "0"
                else "None",
            )
            w = tree.find("DELEGATE").text
            embed.add_field(
                name="WA Delegate",
                value=f"[{w.title().replace('_', ' ')}](https://nationstates.net/nation={w})"
                if w != "0"
                else "None",
            )
            embed.add_field(
                name="Founder Authority",
                value="Executive"
                if "X" in tree.find("FOUNDERAUTH").text
                else "Non-Executive",
            )
            embed.add_field(
                name="Delegate Authority",
                value="Executive"
                if "X" in tree.find("DELEGATEAUTH").text
                else "Non-Executive",
            )
            embed.add_field(
                name="Delegate Votes", value=tree.find("DELEGATEVOTES").text
            )
            embed.set_thumbnail(url=tree.find("FLAG").text)
            embed.set_image(
                url=f"https://nationstates.net{tree.find('BANNERURL').text}"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="ticket",
        description="Creates a ticket for support.",
    )
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def ticket(
        self,
        interaction: discord.Interaction,
        category: Literal["bug", "feature request", "other"],
        title: str,
        description: str,
        image: Optional[discord.Attachment],
    ):
        ticketchannel: discord.ForumChannel = self.bot.get_channel(1086813742823637062)
        tags = ticketchannel.available_tags
        tickettag = None
        for tag in tags:
            if tag.name.lower() == category:
                tickettag = tag
                break
        if image:
            ticket = await ticketchannel.create_thread(
                name=title,
                auto_archive_duration=10080,
                allowed_mentions=discord.AllowedMentions.none(),
                reason=f"Ticket created by {interaction.user} ({interaction.user.id})",
                file=await image.to_file(),
                applied_tags=[tickettag],
                content=description,
            )
        else:
            ticket = await ticketchannel.create_thread(
                name=title,
                auto_archive_duration=10080,
                allowed_mentions=discord.AllowedMentions.none(),
                reason=f"Ticket created by {interaction.user} ({interaction.user.id})",
                applied_tags=[tickettag],
                content=description,
            )
        ticket_id = str(uuid.uuid4())
        await self.bot.execute(
            "INSERT INTO tickets (user_id, response_id, filed_at) VALUES ($1, $2, $3)",
            interaction.user.id,
            ticket_id,
            datetime.datetime.utcnow(),
        )
        await interaction.response.send_message(
            f"Your ticket has been filed. Your ticket ID is `{ticket_id}`. Please provide this as a reference to the "
            f"developer if they ask for follow-up information.",
            ephemeral=True,
        )
        await ticket.thread.send(
            f"**Ticket filed by {interaction.user} ({interaction.user.id})**\n Ticket ID: `{ticket_id}`"
        )

    @commands.command()
    @commands.is_owner()
    async def respond(self, ctx: commands.Context, ticket_id: str, *, response: str):
        ticket = await self.bot.fetch(
            "SELECT * FROM tickets WHERE response_id = $1", ticket_id
        )
        if not ticket:
            return await ctx.send("That ticket does not exist.")
        user = self.bot.get_user(ticket[0]["user_id"])
        if not user:
            return await ctx.send("That user does not exist.")
        embed = discord.Embed(
            title="Ticket Response",
            description=response,
            color=discord.Color.green(),
        )
        embed.set_footer(text=f"Ticket ID: {ticket_id}")
        await user.send(embed=embed)
        await ctx.send("Response sent.")

    @commands.hybrid_command()
    async def whois(self, ctx: commands.Context, nation: str):
        mem_id = await self.bot.fetch(
            "SELECT discord_id FROM nsv_table WHERE nation = $1 AND guild_id = $2",
            nation.lower().replace(" ", "_"),
            ctx.guild.id,
        )
        if not mem_id:
            return await ctx.send("That nation is not verified.")
        target = ctx.guild.get_member(mem_id[0]["discord_id"])
        return await ctx.send(f"The nation {nation} is owned by {target.mention}.")


async def setup(bot: Bloo):
    await bot.add_cog(Utility(bot))
