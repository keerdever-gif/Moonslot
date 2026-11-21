import os
import io
import sys
import re
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
WELCOME_CHANNEL_ID = os.getenv("WELCOME_CHANNEL_ID")

INVITE_URL = os.getenv("INVITE_URL", "https://discord.gg/M5AfTVDxM")
ALLOWED_GUILD_ID = 1572697383693713539

BASE_DIR      = Path(__file__).resolve().parent
OBFUSCATOR_PY = BASE_DIR / "obfuscator.py"
OBF_TIMEOUT   = 90.0

if not OBFUSCATOR_PY.is_file():
    sys.exit(f"ERROR: obfuscator.py not found at {OBFUSCATOR_PY}")

# ── Bot setup ──────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.members = True
intents.message_content = True 

# FIX AQUÍ: help_command=None desactiva el comando help por defecto de discord.py
bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)
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

async def check_dm_restriction(interaction: discord.Interaction) -> bool:
    if interaction.guild is not None:
        return True

    guild = bot.get_guild(ALLOWED_GUILD_ID)
    if not guild:
        try:
            guild = await bot.fetch_guild(ALLOWED_GUILD_ID)
        except Exception:
            pass

    is_member = False
    if guild:
        member = guild.get_member(interaction.user.id)
        if not member:
            try:
                member = await guild.fetch_member(interaction.user.id)
            except Exception:
                pass
        is_member = member is not None

    if not is_member:
        await interaction.followup.send(
            embed=purple_embed(
                "Access Denied", 
                f"Para usar este bot en Mensajes Directos, debes estar en nuestro servidor oficial.\n\n**Únete aquí:** {INVITE_URL}"
            ),
            ephemeral=True
        )
        return False
    return True

def minify_code(code_str):
    code_str = re.sub(r'--\[\[.*?\]\]', '', code_str, flags=re.DOTALL)
    code_str = re.sub(r'--[^\n]*', '', code_str)

    tokens = []
    i, n = 0, len(code_str)
    while i < n:
        c = code_str[i]
        if c in '"\'':
            quote = c
            j = i + 1
            while j < n and code_str[j] != quote:
                if code_str[j] == '\\': j += 1
                j += 1
            tokens.append(code_str[i:j+1])
            i = j + 1
        elif c == '[':
            m = re.match(r'\[(=*)\[', code_str[i:])
            if m:
                eq = m.group(1)
                close = ']' + eq + ']'
                j = code_str.find(close, i)
                if j != -1:
                    tokens.append(code_str[i:j+len(close)])
                    i = j + len(close)
                    continue
            tokens.append(c)
            i += 1
        elif c.isspace():
            i += 1
        elif c.isalnum() or c == '_':
            j = i
            while j < n and (code_str[j].isalnum() or code_str[j] == '_'):
                j += 1
            tokens.append(code_str[i:j])
            i = j
        else:
            tokens.append(c)
            i += 1
            
    out = []
    for idx, tok in enumerate(tokens):
        out.append(tok)
        if idx < len(tokens) - 1:
            nxt = tokens[idx+1]
            if (tok[-1].isalnum() or tok[-1] == '_') and (nxt[0].isalnum() or nxt[0] == '_'):
                out.append(' ')
    return ''.join(out)

async def run_obfuscator(source: str, seed: int = 0, min_size: int = 23000) -> str:
    with tempfile.TemporaryDirectory(prefix="obf_") as tmp:
        tmp_path = Path(tmp)
        in_file  = tmp_path / "input.lua"
        out_file = tmp_path / "obfuscated.txt"
        in_file.write_text(source, encoding="utf-8")

        proc = await asyncio.create_subprocess_exec(
            sys.executable, str(OBFUSCATOR_PY), str(in_file), "-o", str(out_file),
            "--seed", str(seed), "--min-size", str(min_size), cwd=str(BASE_DIR),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
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

        return out_file.read_text(encoding="utf-8")

async def upload_to_pastefy(source: str, username: str) -> str:
    form = aiohttp.FormData()
    form.add_field('title', f"Protected Script by {username}")
    form.add_field('content', source)
    form.add_field('visibility', 'UNLISTED')

    headers = {}
    if PASTEFY_API_KEY:
        headers["Authorization"] = f"Bearer {PASTEFY_API_KEY.strip()}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(PASTEFY_URL, data=form, headers=headers) as resp:
                if resp.status not in (200, 201): return None
                data = await resp.json()
                paste_info = data.get("paste", {})
                return paste_info.get("raw_url") or (f"https://pastefy.app/{paste_info.get('id')}/raw" if paste_info.get("id") else None)
    except Exception:
        return None

# ── EVENTO DE BIENVENIDA ───────────────────────────────────────────────────
@bot.event
async def on_member_join(member: discord.Member):
    if not WELCOME_CHANNEL_ID: return
    try:
        channel = bot.get_channel(int(WELCOME_CHANNEL_ID))
        if channel:
            embed = discord.Embed(
                title="Welcome!",
                description=f"Welcome {member.mention} to the server! Protect your code from skidders. Go to #protect-your-code to get started.",
                color=discord.Color.purple()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await channel.send(embed=embed)
    except Exception as e:
        print(f"[WELCOME ERROR] {e}")

# ── COMANDOS DE AYUDA ──────────────────────────────────────────────────────
def get_help_embed():
    embed = discord.Embed(
        title="Moonslot Bot - Quick Guide",
        description="Protect and optimize your Lua scripts with our advanced tools.",
        color=discord.Color.purple()
    )
    embed.add_field(name="/obf or /obfuscate", value="Usage: Provide `code` or upload a file.\nAction: Obfuscates your script and DMs you the file + a ready-to-use `loadstring`.", inline=False)
    embed.add_field(name="/minify", value="Usage: Provide `code` or upload a file.\nAction: Compresses your code into a single line and sends it to your DMs.", inline=False)
    embed.add_field(name="/help or .help", value="Usage: Displays this guide.", inline=False)
    embed.set_footer(text="Keep your DMs open if you use commands inside a server.")
    return embed

@tree.command(name="help", description="Show all available commands.")
async def help_slash(interaction: discord.Interaction):
    await interaction.response.send_message(embed=get_help_embed(), ephemeral=True)

@bot.command(name="help")
async def help_prefix(ctx):
    await ctx.send(embed=get_help_embed())

# ── COMANDO /MINIFY ────────────────────────────────────────────────────────
@tree.command(name="minify", description="Minify your Lua script (sent via DM).")
@app_commands.describe(code="Paste your Lua code here.", file="Upload a .lua or .txt file.")
async def minify_cmd(interaction: discord.Interaction, code: str = None, file: discord.Attachment = None):
    await interaction.response.defer(ephemeral=True)

    if not await check_dm_restriction(interaction):
        return

    source = await get_source(interaction, code, file)
    if not source:
        return await interaction.followup.send(embed=purple_embed("❌ Missing input", "Provide `code` or a `file`."), ephemeral=True)

    try:
        minified = minify_code(source)
        file_obj = discord.File(io.BytesIO(minified.encode("utf-8")), filename="minified.lua")
        
        dm_embed = purple_embed("📦 Minified Code", "Here is your minified script.")
        
        if interaction.guild is not None:
            await interaction.user.send(embed=dm_embed, file=file_obj)
            await interaction.followup.send(embed=purple_embed("✅ Success", "Check your DMs."), ephemeral=True)
        else:
            await interaction.followup.send(embed=dm_embed, file=file_obj, ephemeral=False)
            
    except Exception as e:
        await interaction.followup.send(embed=purple_embed("❌ Error", str(e)), ephemeral=True)

# ── COMANDO /OBF ───────────────────────────────────────────────────────────
@tree.command(name="obf", description="Obfuscate a Lua script (sent via DM).")
@app_commands.describe(code="Paste your Lua code here.", file="Upload a .lua or .txt file.")
async def obf(interaction: discord.Interaction, code: str = None, file: discord.Attachment = None):
    await interaction.response.defer(ephemeral=True)

    if not await check_dm_restriction(interaction):
        return

    source = await get_source(interaction, code, file)
    if not source:
        return await interaction.followup.send(embed=purple_embed("❌ Missing input", "Provide `code` or a `file`."), ephemeral=True)

    try:
        obfuscated = await run_obfuscator(source)
        raw_url = await upload_to_pastefy(obfuscated, interaction.user.name)

        dm_description = "This is your protected code.\n\n"
        if raw_url:
            dm_description += f"**Loadstring:**\n```lua\nlocal s = game:HttpGet(\"{raw_url}\")\nlocal f, e = loadstring(s)\nif f then f() else warn(\"Error: \" .. tostring(e)) end\n```"
        else:
            dm_description += "⚠️ *Could not generate Pastefy URL.*"

        dm_embed = purple_embed(f"👋 Hello {interaction.user.display_name}", dm_description)
        file_obj = discord.File(io.BytesIO(obfuscated.encode("utf-8")), filename="obfuscated.txt")

        if interaction.guild is not None:
            await interaction.user.send(embed=dm_embed, file=file_obj)
            await interaction.followup.send(embed=purple_embed("🔒 Script obfuscated", "Check your DMs."), ephemeral=True)
        else:
            await interaction.followup.send(embed=dm_embed, file=file_obj, ephemeral=False)
            
    except Exception as e:
        await interaction.followup.send(embed=purple_embed("❌ Obfuscation error", f"```{str(e)[:1800]}```"), ephemeral=True)

# Alias /obfuscate
tree.add_command(app_commands.Command(name="obfuscate", description="Alias of /obf.", callback=obf.callback))

# ── Startup ────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    await tree.sync()
    print(f"Bot ready as {bot.user} (ID: {bot.user.id})")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
