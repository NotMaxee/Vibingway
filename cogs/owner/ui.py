import discord


class CodeModal(discord.ui.Modal, title="Code Evaluation"):
    code_input = discord.ui.TextInput(
        label="Code",
        style=discord.TextStyle.long,
        placeholder="...",
        required=True,
        max_length=512,
    )

    def __init__(self):
        self.code: str = None
        super().__init__()

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.code = self.code_input.value

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await interaction.response.defer()


class SQLModal(discord.ui.Modal, title="SQL Evaluation"):
    sql_input = discord.ui.TextInput(
        label="SQL",
        style=discord.TextStyle.long,
        placeholder="...",
        required=True,
        max_length=512,
    )

    def __init__(self):
        self.sql: str = None
        super().__init__()

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.sql = self.sql_input.value

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await interaction.response.defer()
