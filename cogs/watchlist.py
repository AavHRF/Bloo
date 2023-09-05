import discord
import datetime
from discord.ext import commands
from discord import app_commands
from framework.bot import Bloo
from typing import List


class SearchBox(discord.ui.Modal, title="Search"):

    def __init__(self, bot: Bloo, message: discord.Message):
        super().__init__(timeout=None)
        self.bot = bot
        self.message = message

    name = discord.ui.TextInput(
        label="Name",
        placeholder="Enter a name",
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        pass


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

    @staticmethod
    def natify(item: str) -> str:
        return f"[{item}](https://nationstates.net/nation={item.lower().replace(' ', '_')})"

    @app_commands.command()
    @app_commands.guilds(414822188273762306)
    @app_commands.default_permissions(administrator=True)
    async def watchlist(self, interaction: discord.Interaction):
        watchlist = await self.bot.fetch("SELECT * FROM watchlist")
        watchlistitems = []
        for item in watchlist:
            embed = discord.Embed(
                title=f"WATCHLIST — {item['primary_name']}",
                description=f"**Reason for Watchlist Addition:**\n {item['reasoning']}\n"
            )
            known_ids = item['known_ids'].split(",")
            known_names = item['known_names'].split(",")
            known_nations = [self.natify(nation) for nation in item['known_nations'].split(",")]
            evidence = item['evidence'].split(",")

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
            embed.set_footer(text=f"Added on {item['date_added']}")
            watchlistitems.append(embed)

        await interaction.response.send_message(
            embed=watchlistitems[0],
            view=PaginateWL(self.bot, watchlistitems)
        )


async def setup(bot: Bloo):
    await bot.add_cog(Watchlist(bot))