import os
import io
import sys
import asyncio
import tempfile
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from dotenv import load_dotenv

# ── Config ─────────────────────────────────────────────────────────────────
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    sys.exit("ERROR: DISCORD_TOKEN not set. Create a .env file with DISCORD_TOKEN=your_token")

PASTEFY_API_KEY = os.getenv("PASTEFY_API_KEY")
PASTEFY_URL = "https://pastefy.app/api/v2/paste"

BASE_DIR      = Path(__file__).resolve().parent
OBFUSCATOR_PY = BASE_DIR / "obfuscator.py"
OBF_TIMEOUT   = 90.0

if not OBFUSCATOR_PY.is_file():
    sys.exit(f"ERROR: obfuscator.py not found at {OBFUSCATOR_PY}")

# ── Bot setup ──────────────────────────────────────────────────────────────
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ── Helpers ────────────────────────────────────────────────────────────────
def purple_embed(title: str, description: str) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=discord.Color.purple())

async def get_source(interaction, code, attachment):
    if attachment:
        data = await attachment.read()
        return data.decode("utf-8", errors="replace")
    if code:
        return code
    return None

async def run_obfuscator(source: str, seed: int = 0, min_size: int = 23000) -> str:
    with tempfile.TemporaryDirectory(prefix="obf_") as tmp:
        tmp_path = Path(tmp)
        in_file  = tmp_path / "input.lua"
        out_file = tmp_path / "obfuscated.txt"
        in_file.write_text(source, encoding="utf-8")

        proc = await asyncio.create_subprocess_exec(
            sys.executable, str(OBFUSCATOR_PY),
            str(in_file),
            "-o", str(out_file),
            "--seed", str(seed),
            "--min-size", str(min_size),
            cwd=str(BASE_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=OBF_TIMEOUT)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise RuntimeError(f"Obfuscator timed out after {int(OBF_TIMEOUT)}s.")

        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace").strip() or "(no stderr)"
            raise RuntimeError(f"Obfuscator exited with code {proc.returncode}:\n{err}")

        if not out_file.is_file():
            raise RuntimeError("Obfuscator produced no output file.")

        return out_file.read_text(encoding="utf-8")

async def upload_to_pastefy(source: str, username: str) -> str:
    payload = {
        "title": f"Protected Script by {username}",
        "content": source,
        "visibility": "UNLISTED"
    }
    headers = {"Content-Type": "application/json"}
    if PASTEFY_API_KEY:
        headers["Authorization"] = f"Bearer {PASTEFY_API_KEY}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(PASTEFY_URL, json=payload, headers=headers) as resp:
                text = await resp.text()
                
                # Si falla, imprimimos el error en los logs de Railway para saber por qué
                if resp.status not in (200, 201):
                    print(f"[PASTEFY ERROR] Status {resp.status}: {text}")
                    return None
                
                try:
                    data = await resp.json()
                except Exception as json_err:
                    print(f"[PASTEFY JSON ERROR] {json_err} - Raw: {text}")
                    return None
                    
                paste_id = data.get("id")
                if paste_id:
                    return f"https://pastefy.app/{paste_id}/raw"
                else:
                    print(f"[PASTEFY ERROR] No ID found in response: {data}")
                    return None
    except Exception as e:
        print(f"[PASTEFY EXCEPTION] {e}")
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
        obfuscated = await run_obfuscator(source)
    except Exception as e:
        await interaction.followup.send(
            embed=purple_embed("❌ Obfuscation error", f"```{str(e)[:1800]}```"),
            ephemeral=True
        )
        return

    raw_url = await upload_to_pastefy(obfuscated, interaction.user.name)

    dm_description = "This is your protected code.\n\n"
    if raw_url:
        loadstring_cmd = f'loadstring(game:HttpGet("{raw_url}"))()'
        dm_description += f"**Loadstring:**\n```lua\n{loadstring_cmd}\n```"
    else:
        dm_description += "⚠️ *Could not generate Pastefy URL. Check bot logs on Railway for details.*"

    dm_embed = purple_embed(
        f"👋 Hello {interaction.user.display_name}",
        dm_description
    )
    file_obj = discord.File(
        io.BytesIO(obfuscated.encode("utf-8")),
        filename="obfuscated.txt"
    )

    if interaction.guild is not None:
        try:
            await interaction.user.send(embed=dm_embed, file=file_obj)
            await interaction.followup.send(
                embed=purple_embed("🔒 Script obfuscated", "Your script is obfuscated. Check your DMs."),
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.followup.send(
                embed=purple_embed(
                    "⚠️ DM failed",
                    "I couldn't send you a DM. Please enable direct messages from server members and try again."
                ),
                ephemeral=True
            )
    else:
        await interaction.followup.send(embed=dm_embed, file=file_obj, ephemeral=False)

# Alias /obfuscate
tree.add_command(
    app_commands.Command(
        name="obfuscate",
        description="Alias of /obf: obfuscate your script and receive it via DM.",
        callback=obf.callback
    )
)

# ── Startup ────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    await tree.sync()
    print(f"Bot ready as {bot.user} (ID: {bot.user.id})")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
