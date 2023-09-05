import asyncpg
import discord
import datetime
from discord.ext import commands
from discord import app_commands
from framework.bot import Bloo
from typing import List


# Fuzzy string matching is powered by pg_trgm
# Was attempting to use fuzzymatching for the IDs, but it's not working
# so now we're iterating over the list of IDs and checking if the query is in the list
# Slow? Yes. But with very limited data, it's not a big deal.

# TODO:
# - Add staff commands for editing the watchlist
# - Implement member search for the watchlist /done
#   - Fuzzy matching? /done
# - Watchlist alerts
#  - When a member joins, check if they're on the watchlist
#  - If they are, send a message to the staff channel
#  - Requires me to finish settings rewrite first

def natify(item: str) -> str:
    return f"[{item}](https://nationstates.net/nation={item.lower().replace(' ', '_')})"


def watchlist_embed(record: asyncpg.Record) -> discord.Embed:
    embed = discord.Embed(
        title=f"WATCHLIST — {record['primary_name']}",
        description=f"**Reason for Watchlist Addition:**\n {record['reasoning']}\n"
    )
    known_ids = record['known_ids'].split(",")
    known_names = record['known_names'].split(",")
    known_nations = [natify(nation) for nation in record['known_nations'].split(",")]
    evidence = record['evidence'].split(",")
    embed.add_field(
        name="Known IDs",
        value="\n".join(known_ids),
    )
    embed.add_field(
        name="Known Names",
        value="\n".join(known_names),
    )
    embed.add_field(
        name="Known Nations",
        value="\n".join(known_nations),
    )
    embed.add_field(
        name="Evidence",
        value="\n".join(evidence),
    )
    embed.set_footer(text=f"Added on {record['date_added']}")
    return embed


def error_embed() -> discord.Embed:
    embed = discord.Embed(
        title="No Results",
        description="Your search returned no results.",
        color=discord.Color.red(),
    )
    return embed


class FlexibleWLModal(discord.ui.Modal, title="Update Watchlist Entry"):

    def __init__(self, bot: Bloo, edit_mode: str, name: str):
        super().__init__(timeout=None)
        self.bot = bot
        self.edit_mode = edit_mode
        self.name = name
        if self.edit_mode == "reasoning":
            reasoning = discord.ui.TextInput(
                label="Reasoning",
                placeholder="Enter the reason for adding this member to the watchlist",
                required=True,
                style=discord.TextStyle.long,
                max_length=1000,
            )
            self.add_item(reasoning)
        elif self.edit_mode == "ids":
            ids = discord.ui.TextInput(
                label="Known IDs",
                placeholder="Enter comma-separated Discord IDs",
                required=True,
                max_length=1000,
            )
            self.add_item(ids)
        elif self.edit_mode == "names":
            names = discord.ui.TextInput(
                label="Known Names",
                placeholder="Enter comma-separated Discord names",
                required=True,
                max_length=1000,
            )
            self.add_item(names)
        elif self.edit_mode == "nations":
            nations = discord.ui.TextInput(
                label="Known Nations",
                placeholder="Enter comma-separated NationStates nations",
                required=True,
                max_length=1000,
            )
            self.add_item(nations)
        elif self.edit_mode == "evidence":
            evidence = discord.ui.TextInput(
                label="Evidence",
                placeholder="Enter evidence with a brief description before each item. Place each item on a new line.",
                required=True,
                max_length=1000,
                style=discord.TextStyle.long,
            )
            self.add_item(evidence)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if self.edit_mode == "reasoning":
            await self.bot.execute(
                "UPDATE watchlist SET reasoning = $1 WHERE primary_name = $2",
                self.children[0].value,
                self.name,
            )
        elif self.edit_mode == "ids":
            discord_ids = self.children[0].value.split(",")
            discord_ids = [discord_id.strip() for discord_id in discord_ids]
            discord_ids = ",".join(discord_ids)
            await self.bot.execute(
                "UPDATE watchlist SET known_ids = $1 WHERE primary_name = $2",
                discord_ids,
                self.name,
            )
        elif self.edit_mode == "names":
            discord_names = self.children[0].value.split(",")
            discord_names = [discord_name.strip() for discord_name in discord_names]
            discord_names = ",".join(discord_names)
            await self.bot.execute(
                "UPDATE watchlist SET known_names = $1 WHERE primary_name = $2",
                discord_names,
                self.name,
            )
        elif self.edit_mode == "nations":
            nations = self.children[0].value.split(",")
            nations = [nation.strip() for nation in nations]
            nations = ",".join(nations)
            await self.bot.execute(
                "UPDATE watchlist SET known_nations = $1 WHERE primary_name = $2",
                nations,
                self.name,
            )
        elif self.edit_mode == "evidence":
            evidence = self.children[0].value.split("\n")
            evidence = [evidence_item.strip() for evidence_item in evidence]
            evidence = [evidence_item for evidence_item in evidence if
                        evidence_item != ""]  # I said a little trickier, not a lot trickier
            evidence = ",".join(evidence)
            await self.bot.execute(
                "UPDATE watchlist SET evidence = $1 WHERE primary_name = $2",
                evidence,
                self.name,
            )
        await interaction.response.send_message(
            f"Updated the watchlist entry for `{self.name}`.",
        )


class SearchBox(discord.ui.Modal, title="Search"):

    def __init__(self, bot: Bloo, message: discord.Message):
        super().__init__(timeout=None)
        self.bot = bot
        self.message = message

    query = discord.ui.TextInput(
        label="Query",
        placeholder="Enter a name, ID, or nation.",
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        # Determine what the user is searching for
        await interaction.response.defer(thinking=True)
        query = self.query.value
        try:
            int(query)
            # If the query is an integer, it's a discord ID
            watchlist = await self.bot.fetch(
                "SELECT * FROM watchlist",
            )
            if not watchlist:
                await interaction.followup.send(
                    embed=error_embed(),
                )
                return

            found = False
            record = None
            for item in watchlist:
                ids = item['known_ids'].split(",")
                if query in ids:
                    found = True
                    record = item
                    break

            # You can only have one record per Discord ID, so we can just grab the first
            # record in the list and return the embed.
            if found:
                embed = watchlist_embed(record)
                await interaction.followup.send(
                    f"Your search for `{query}` returned the following result:",
                    embed=embed
                )
            else:
                await interaction.followup.send(
                    embed=error_embed(),
                )

        except ValueError:
            # You can't coerce a string to an integer, so it's not a discord ID
            # It's either a name or a nation
            # We can use the fuzzy string matching provided by pg_trgm to search for
            # similar names and nations
            query = f"%{query}%"
            record = await self.bot.fetch(
                "SELECT * FROM watchlist WHERE primary_name % $1 OR known_names % $1 OR known_nations % $1",
                query,
            )
            if not record:
                await interaction.followup.send(
                    embed=error_embed(),
                )
                return
            else:
                count = len(record)
                if count == 1:
                    embed = watchlist_embed(record[0])
                    await interaction.followup.send(
                        f"Your search for `{query.strip('%')}` returned the following result:",
                        embed=embed
                    )
                else:
                    watchlistitems = []
                    for item in record:
                        watchlistitems.append(watchlist_embed(item))

                    await interaction.followup.send(
                        f"Your search for `{query.strip('%')}` returned {count} results:",
                        embed=watchlistitems[0],
                        view=PaginateWL(self.bot, watchlistitems)
                    )


class WatchlistAddModal(discord.ui.Modal, title="Add to Watchlist"):

    def __init__(self, bot: Bloo, name: str):
        super().__init__(timeout=None)
        self.bot = bot
        self.name = name

    reasoning = discord.ui.TextInput(
        label="Reasoning",
        placeholder="Enter the reason for adding this member to the watchlist",
        required=True,
        style=discord.TextStyle.long,
        max_length=1000,
    )

    known_ids = discord.ui.TextInput(
        label="Known IDs",
        placeholder="Enter comma-separated Discord IDs",
        required=True,
        max_length=1000,
    )

    known_names = discord.ui.TextInput(
        label="Known Names",
        placeholder="Enter comma-separated Discord names",
        required=True,
        max_length=1000,
    )

    known_nations = discord.ui.TextInput(
        label="Known Nations",
        placeholder="Enter comma-separated NationStates nations",
        required=True,
        max_length=1000,
    )

    evidence = discord.ui.TextInput(
        label="Evidence",
        placeholder="Enter evidence with a brief description before each item. Place each item on a new line.",
        required=True,
        max_length=1000,
        style=discord.TextStyle.long,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        # Parse the discord IDs and clean them up
        discord_ids = self.known_ids.value.split(",")
        discord_ids = [discord_id.strip() for discord_id in discord_ids]
        discord_ids = ",".join(discord_ids)

        # Do the same for the discord names
        discord_names = self.known_names.value.split(",")
        discord_names = [discord_name.strip() for discord_name in discord_names]
        discord_names = ",".join(discord_names)

        # ...andddd the nations
        nations = self.known_nations.value.split(",")
        nations = [nation.strip() for nation in nations]
        nations = ",".join(nations)

        # Evidence is a little trickier to parse because it's newline separated
        # We want to clean up each line and make sure that it's not empty etc before
        # we join them all into a comma separated list.
        evidence = self.evidence.value.split("\n")
        evidence = [evidence_item.strip() for evidence_item in evidence]
        evidence = [evidence_item for evidence_item in evidence if
                    evidence_item != ""]  # I said a little trickier, not a lot trickier
        evidence = ",".join(evidence)

        # Insert the record into the database
        await self.bot.execute(
            "INSERT INTO watchlist (primary_name, reasoning, known_ids, known_names, known_nations, evidence, date_added) VALUES ($1, $2, $3, $4, $5, $6, $7)",
            self.name,
            self.reasoning.value,
            discord_ids,
            discord_names,
            nations,
            evidence,
            datetime.datetime.now(),
        )

        # Send a confirmation message
        await interaction.followup.send(
            f"Added the member to the watchlist. Use </watchlist:1148519844304650280> to view the watchlist.",
            ephemeral=True,
        )


class PaginateWL(discord.ui.View):

    def __init__(self, bot: Bloo, watchlistitems: List[discord.Embed]):
        super().__init__()
        self.current_page = 0
        self.bot = bot
        self.watchlistitems = watchlistitems

    @discord.ui.button(
        label="Previous",
        style=discord.ButtonStyle.secondary,
        custom_id="previous_page",
        emoji="⬅️",
    )
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page != 0:
            self.current_page = len(self.watchlistitems) - 1
        else:
            self.current_page = 0

        embed = self.watchlistitems[self.current_page]
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="Next",
        style=discord.ButtonStyle.secondary,
        custom_id="next_page",
        emoji="➡️",
    )
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page != len(self.watchlistitems) - 1:
            self.current_page += 1
        else:
            self.current_page = 0

        embed = self.watchlistitems[self.current_page]
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="Search",
        style=discord.ButtonStyle.primary,
        custom_id="search",
        emoji="🔍",
    )
    async def search(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SearchBox(self.bot, interaction.message))

    @discord.ui.button(
        label="Close",
        style=discord.ButtonStyle.danger,
        custom_id="close",
        emoji="🔒",
    )
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(
        label="Staff Options",
        style=discord.ButtonStyle.blurple,
        custom_id="staff_options",
        emoji="🛠️",
    )
    async def staff_options(self, interaction: discord.Interaction, button: discord.ui.Button):
        nsl_staff = interaction.guild.get_role(414822801397121035)
        if nsl_staff not in interaction.user.roles:
            self.staff_options.disabled = True
            await interaction.response.edit_message(
                view=self
            )
            await interaction.followup.send(
                "You do not have permission to use this button.",
                ephemeral=True,
            )
        else:
            await interaction.response.edit_message(
                view=NSLStaffWLButtons(self.bot)
            )


class NSLStaffWLButtons(discord.ui.View):

    def __init__(self, bot: Bloo):
        super().__init__()
        self.bot = bot

    @discord.ui.button(
        label="Edit Watchlist Reasoning",
        style=discord.ButtonStyle.blurple,
        custom_id="edit_reasoning",
    )
    async def edit_reasoning(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            FlexibleWLModal(self.bot, "reasoning", interaction.message.embeds[0].title.split("—")[1].strip())
        )

    @discord.ui.button(
        label="Edit Known IDs",
        style=discord.ButtonStyle.blurple,
        custom_id="edit_ids",
    )
    async def edit_ids(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            FlexibleWLModal(self.bot, "ids", interaction.message.embeds[0].title.split("—")[1].strip())
        )

    @discord.ui.button(
        label="Edit Known Names",
        style=discord.ButtonStyle.blurple,
        custom_id="edit_names",
    )
    async def edit_names(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            FlexibleWLModal(self.bot, "names", interaction.message.embeds[0].title.split("—")[1].strip())
        )

    @discord.ui.button(
        label="Edit Known Nations",
        style=discord.ButtonStyle.blurple,
        custom_id="edit_nations",
    )
    async def edit_nations(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            FlexibleWLModal(self.bot, "nations", interaction.message.embeds[0].title.split("—")[1].strip())
        )

    @discord.ui.button(
        label="Edit Evidence",
        style=discord.ButtonStyle.blurple,
        custom_id="edit_evidence",
    )
    async def edit_evidence(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            FlexibleWLModal(self.bot, "evidence", interaction.message.embeds[0].title.split("—")[1].strip())
        )

    @discord.ui.button(
        label="Close",
        style=discord.ButtonStyle.danger,
        custom_id="close",
        emoji="🔒",
    )
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()


class Watchlist(commands.Cog):
    """
    Defines commands used for viewing, adding, and removing from the Watchlist.

    The Watchlist is managed by staff from the NS Leaders server. You can reach them here: https://discord.gg/7bSCkyp

    The watchlist is stored in a PostgreSQL database. The table is defined as follows:

    CREATE TABLE IF NOT EXISTS watchlist (
        primary_name VARCHAR(50) NOT NULL,
        reasoning TEXT NOT NULL,
        known_ids TEXT NOT NULL,
        known_names TEXT NOT NULL,
        known_nations TEXT NOT NULL,
        evidence TEXT NOT NULL,
        date_added TIMESTAMP NOT NULL
    );
    """

    def __init__(self, bot: Bloo):
        self.bot = bot

    @app_commands.command(
        description="View the Watchlist"
    )
    @app_commands.guilds(414822188273762306)
    @app_commands.default_permissions(administrator=True)
    async def watchlist(self, interaction: discord.Interaction):
        watchlist = await self.bot.fetch("SELECT * FROM watchlist")
        watchlistitems = []
        for item in watchlist:
            watchlistitems.append(watchlist_embed(item))

        await interaction.response.send_message(
            embed=watchlistitems[0],
            view=PaginateWL(self.bot, watchlistitems)
        )

    @app_commands.command(
        description="Add a member to the Watchlist"
    )
    @app_commands.guilds(414822188273762306)
    @app_commands.default_permissions(administrator=True)
    async def wl_add(self, interaction: discord.Interaction, name: str):
        await interaction.response.send_modal(WatchlistAddModal(self.bot, name))

    @app_commands.command(
        description="Add a spammer to the Watchlist"
    )
    @app_commands.guilds(414822188273762306)
    @app_commands.default_permissions(administrator=True)
    async def wl_spammer(self, interaction: discord.Interaction, id: int):
        await self.bot.execute(
            "INSERT INTO watchlist (primary_name, reasoning, known_ids, known_names, known_nations, evidence, date_added) VALUES ($1, $2, $3, $4, $5, $6, $7)",
            id,
            "Spammer/Scambot",
            id,
            "Spammer/Scambot",
            "Spammer/Scambot",
            "Spammer/Scambot",
            datetime.datetime.now(),
        )
        await interaction.response.send_message(
            f"Added the member to the watchlist. Use </watchlist:1148519844304650280> to view the watchlist.",
            ephemeral=True,
        )


async def setup(bot: Bloo):
    await bot.add_cog(Watchlist(bot))
