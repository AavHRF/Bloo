import discord
from discord.ext import commands
from framework.bot import Bloo
import watchlist


class Listeners(commands.Cog):
    def __init__(self, bot: Bloo):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """
        Handles four things:
        - Alerts on users with watchlisted IDs
        - Bans scambot accounts with watchlisted IDs
        - Bans users with banned nations
        - Welcomes everyone else

        The order of priority is as follows:
        - Ban banned nations
        - Ban scam accounts
        - Alert on watchlisted IDs
        - Fire a welcome message if not banned, else alert admins
        """
        # Read in banned nations and guild settings from the database -- we may not need to fetch
        # welcome settings if they're going to be prebanned anyway, so let's save the call.
        # We sort the nations by the first three letters of their name to let us do a search later
        # on in the code.
        guildbans = await self.bot.fetch(
            "SELECT * FROM nsv_ban_table WHERE guild_id = $1 ORDER BY left(nation, 3)", member.guild.id
        )
        guild_settings = await self.bot.fetch(
            "SELECT * FROM guild_settings WHERE guild_id = $1", member.guild.id
        )
        owned = None
        post_join_message = True
        # If there are no guildbans, we can skip the first check.
        if not guildbans:
            pass
        else:
            # Check to see if the member who joined has any verified nations
            owned = await self.bot.fetch(
                "SELECT * FROM nsv_table WHERE discord_id = $1", member.id
            )
            # If they don't, we can skip the second check.
            if not owned:
                pass
            else:
                # Sort the list of owned nations by the first three letters of their name.
                owned = sorted(owned, key=lambda k: k["nation"][:3])
                # Filter down to the nation names only.
                owned = [x["nation"] for x in owned]
                # The guildbans are sorted by the first three letters of the nation name, so we can
                # do a search to speed up the process of checking if the user has a banned nation.
                for nation in owned:
                    matched = False
                    left = 0
                    right = len(guildbans) - 1
                    mid = 0
                    while left <= right:
                        mid = (left + right) // 2
                        if guildbans[mid]["nation"] == nation:
                            matched = True
                            break
                        elif guildbans[mid]["nation"] < nation:
                            left = mid + 1
                        else:
                            right = mid - 1
                    if matched:
                        # If the nation is banned, ban the user and alert the admins.
                        await member.guild.ban(member, reason=guildbans[mid]["reason"])
                        if guild_settings[0]["admin_channel"] == 0:
                            return  # No admin channel set, so we can't alert the admins. Oh well.
                        embed = discord.Embed(
                            title="Member joined with banned nation.",
                            description=f"User {member.mention} ({member.id}) joined with a nation ({nation['nation']}) that is banned from this server.",
                            color=discord.Color.red(),
                        )
                        await member.guild.get_channel(
                            guild_settings[0]["admin_channel"]
                        ).send(embed=embed)
                        post_join_message = False
                        return  # No need to proceed at this point, they're banned.

        # None of the user's nations are banned -- let's check if they have a watchlisted ID.
        # The watchlist, fortunately, is stored in memory and is updated by the watchlist cog.
        if guild_settings[0]["watchlist_alerts"]:
            ids = self.bot.watchlist["discord_ids"]
            if member.id in ids:
                # Fetch their watchlist record from the database.
                record = await self.bot.fetch(
                    "SELECT * FROM watchlist WHERE known_ids = $1 OR primary_name = $2",
                    f"%{member.id}%",
                    member.id,
                )
                # Check if they're a spam account, this is listed in the reason field.
                if "spammer/scambot" in record[0]["reasoning"].lower().strip():
                    # Auto-ban them.
                    await member.guild.ban(member, reason=record[0]["reasoning"])
                    post_join_message = False
                    # Alert the admins.
                    if guild_settings[0]["admin_channel"] == 0:
                        return
                    embed = discord.Embed(
                        title="Member joined with watchlisted ID.",
                        description=f"User {member.mention} ({member.id}) joined with a watchlisted spam account and was "
                                    f"automatically banned. Use </watchlist:1151581960255328256> to view their watchlist "
                                    f"entry.",
                        color=discord.Color.red(),
                    )
                    await member.guild.get_channel(
                        guild_settings[0]["admin_channel"]
                    ).send(embed=embed)
                    return  # No need to proceed at this point, they're banned.
                else:  # Watchlist ID match, but not a spam account.
                    # Use the watchlist embed generator utility function
                    embed = watchlist.watchlist_embed(record[0])
                    # Alert the admins.
                    if guild_settings[0]["admin_channel"] == 0:
                        return
                    await member.guild.get_channel(
                        guild_settings[0]["admin_channel"]
                    ).send(content="@everyone", embed=embed)

            # Repeat the check, but for nation names.
            names = self.bot.watchlist["nation_names"]
            if owned:
                for nation in owned:
                    if nation in names:
                        # Fetch their watchlist record from the database.
                        record = await self.bot.fetch(
                            "SELECT * FROM watchlist WHERE known_nations = $1 OR primary_name = $1",
                            f"%{nation}%",
                        )
                        embed = watchlist.watchlist_embed(record[0])
                        if guild_settings[0]["admin_channel"] == 0:
                            return
                        await member.guild.get_channel(
                            guild_settings[0]["admin_channel"]
                        ).send(content="@everyone", embed=embed)
                        return

            # Repeat the check, but for known names.
            names = self.bot.watchlist["known_names"]
            if member.global_name in names:
                # Fetch their watchlist record from the database.
                record = await self.bot.fetch(
                    "SELECT * FROM watchlist WHERE known_names = $1 OR primary_name = $1",
                    f"%{member.global_name}%"
                )
                embed = watchlist.watchlist_embed(record[0])
                if guild_settings[0]["admin_channel"] == 0:
                    return
                await member.guild.get_channel(
                    guild_settings[0]["admin_channel"]
                ).send(content="@everyone", embed=embed)
                return

        # Send a welcome message if they're not banned.
        if post_join_message:
            settings = await self.bot.fetch(
                "SELECT * FROM welcome_settings WHERE guild_id = $1", member.guild.id
            )
            if not settings:
                return
            if not settings[0]["welcome_channel"]:
                return

            if settings[0]["welcome_channel"] != 0:
                embed = discord.Embed(
                    title=f"Welcome, {member.display_name}!",
                    color=discord.Color.random(),
                    description=settings[0]["embed_message"]
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.add_field(
                    name="Member count",
                    value=member.guild.member_count,
                )
                embed.set_footer(text=f"ID: {member.id}")
                try:
                    await member.guild.get_channel(settings[0]["welcome_channel"]).send(embed=embed)
                except AttributeError:  # Channel was deleted after being set as the welcome channel.
                    await member.guild.get_channel(
                        guild_settings[0]["admin_channel"]
                    ).send("# WARNING\nYour welcome channel was deleted, please set a new one with "
                           "</settings:1073064073459142688>")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        settings = await self.bot.fetch(
            "SELECT * FROM welcome_settings WHERE guild_id = $1", member.guild.id
        )
        if not settings:
            return
        if not settings[0]["welcome_channel"]:
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
