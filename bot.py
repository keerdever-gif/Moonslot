# bot.py
import os
import io
import sys
import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from dotenv import load_dotenv

from obfuscator import build_bundle

# ── Config ─────────────────────────────────────────────────────────────────
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    sys.exit("ERROR: DISCORD_TOKEN environment variable is not set. Create a .env file with DISCORD_TOKEN=your_token")

PASTEFY_URL = "https://pastefy.app/api/v2/paste"

# ── Bot setup ──────────────────────────────────────────────────────────────
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ── Helpers ────────────────────────────────────────────────────────────────
def purple_embed(title: str, description: str) -> discord.Embed:
    return discord.Embed(
        title=title,
        description=description,
        color=discord.Color.purple()
    )

async def get_source(
    interaction: discord.Interaction,
    code: str | None,
    attachment: discord.Attachment | None
) -> str | None:
    if attachment:
        data = await attachment.read()
        return data.decode("utf-8", errors="replace")
    if code:
        return code
    return None

# ── /obf and /obfuscate ────────────────────────────────────────────────────
@tree.command(name="obf", description="Obfuscate a Lua script and receive it via DM (Delta-ready).")
@app_commands.describe(
    code="Paste your Lua code here (optional if you upload a file).",
    file="Upload a .lua or .txt file with your code (optional)."
)
async def obf(interaction: discord.Interaction, code: str = None, file: discord.Attachment = None):
    await interaction.response.defer(ephemeral=True)

    source = await get_source(interaction, code, file)
    if not source:
        await interaction.followup.send(
            embed=purple_embed("❌ Missing input", "You must provide `code` or upload a `file`."),
            ephemeral=True
        )
        return

    try:
        obfuscated = build_bundle(source, seed=0, min_size=23000)
    except Exception as e:
        await interaction.followup.send(
            embed=purple_embed("❌ Obfuscation error", f"```{e}```"),
            ephemeral=True
        )
        return

    confirm_embed = purple_embed(
        "🔒 Script obfuscated",
        "Your script is obfuscated. Check your DMs."
    )
    await interaction.followup.send(embed=confirm_embed, ephemeral=True)

    try:
        dm_embed = purple_embed(
            f"👋 Hello {interaction.user.display_name}",
            "This is your protected code."
        )
        file_obj = discord.File(
            io.BytesIO(obfuscated.encode("utf-8")),
            filename="obfuscated.txt"
        )
        await interaction.user.send(embed=dm_embed, file=file_obj)
    except discord.Forbidden:
        await interaction.followup.send(
            embed=purple_embed(
                "⚠️ DM failed",
                "I couldn't send you a DM. Please enable direct messages from server members and try again."
            ),
            ephemeral=True
        )

# Alias /obfuscate
tree.add_command(
    app_commands.Command(
        name="obfuscate",
        description="Alias of /obf: obfuscate your script and receive it via DM.",
        callback=obf.callback
    )
)

# ── /pastefy ───────────────────────────────────────────────────────────────
@tree.command(name="pastefy", description="Upload your Lua code to Pastefy and get a URL.")
@app_commands.describe(
    code="Paste your Lua code here (optional if you upload a file).",
    file="Upload a .lua or .txt file with your code (optional)."
)
async def pastefy(interaction: discord.Interaction, code: str = None, file: discord.Attachment = None):
    await interaction.response.defer(ephemeral=True)

    source = await get_source(interaction, code, file)
    if not source:
        await interaction.followup.send(
            embed=purple_embed("❌ Missing input", "You must provide `code` or upload a `file`."),
            ephemeral=True
        )
        return

    payload = {
        "title": f"Script by {interaction.user.name}",
        "content": source,
        "visibility": "UNLISTED"
    }
    headers = {"Content-Type": "application/json"}

    async with aiohttp.ClientSession() as session:
        async with session.post(PASTEFY_URL, json=payload, headers=headers) as resp:
            if resp.status not in (200, 201):
                text = await resp.text()
                await interaction.followup.send(
                    embed=purple_embed("❌ Pastefy error", f"```{text[:1000]}```"),
                    ephemeral=True
                )
                return
            data = await resp.json()

    paste_id = data.get("id")
    if not paste_id:
        await interaction.followup.send(
            embed=purple_embed("❌ Pastefy error", "The response did not contain a paste `id`."),
            ephemeral=True
        )
        return

    paste_url = f"https://pastefy.app/{paste_id}"

    embed = purple_embed(
        "🔗 Pastefy link",
        f"Your code is available on Pastefy:\n{paste_url}"
    )
    view = discord.ui.View()
    view.add_item(
        discord.ui.Button(
            style=discord.ButtonStyle.link,
            label="Open on Pastefy",
            url=paste_url
        )
    )
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)

# ── Startup ────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    await tree.sync()
    print(f"Bot ready as {bot.user} (ID: {bot.user.id})")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
