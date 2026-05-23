import discord
import discord.opus
from discord.ext import commands
import yt_dlp
import asyncio
import logging
import os

logging.basicConfig(level=logging.ERROR)

# 🔥 OPUS FIX (optional)
if not discord.opus.is_loaded():
    try:
        discord.opus.load_opus("libopus.so.0")
    except:
        try:
            discord.opus.load_opus("libopus.so")
        except:
            print("❌ OPUS NICHT GEFUNDEN")

# ✅ WICHTIGER FIX (INTENTS)
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix=".", intents=intents)

queues = {}
current = {}
skip_votes = {}

# ================= READY =================
@bot.event
async def on_ready():
    print(f"Online als {bot.user}")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="/help"
        )
    )

# ================= SONG LOAD =================
async def get_song(search):
    loop = asyncio.get_event_loop()

    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "noplaylist": True,
        "default_search": "ytsearch1",
        "ignoreerrors": True,
    }

    def extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(search, download=False)

    try:
        data = await loop.run_in_executor(None, extract)
    except:
        return None

    if "entries" not in data or not data["entries"]:
        return None

    info = data["entries"][0]

    for f in info["formats"]:
        if f.get("acodec") != "none" and f.get("url"):
            return {
                "title": info["title"],
                "url": f["url"]
            }

    return None

# ================= PLAY NEXT =================
def play_next(ctx):
    vc = ctx.voice_client
    skip_votes[ctx.guild.id] = set()

    if ctx.guild.id not in queues or len(queues[ctx.guild.id]) == 0:
        return

    song = queues[ctx.guild.id].pop(0)
    current[ctx.guild.id] = song["title"]

    source = discord.FFmpegPCMAudio(
        song["url"],
        executable="ffmpeg",
        before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 10 -nostdin",
        options="-vn"
    )

    vc.play(source, after=lambda e: play_next(ctx))

# ================= PLAY =================
@bot.command()
async def play(ctx, *, search):

    if not ctx.author.voice:
        return await ctx.send("❌ Geh in einen Call!")

    channel = ctx.author.voice.channel

    if not ctx.voice_client:
        vc = await channel.connect()
    else:
        vc = ctx.voice_client

    await ctx.send(f"🔍 Suche: {search}")

    if ctx.guild.id not in queues:
        queues[ctx.guild.id] = []

    song = await get_song(search)

    if not song:
        return await ctx.send("❌ Kein Song gefunden")

    if not vc.is_playing():
        current[ctx.guild.id] = song["title"]

        source = discord.FFmpegPCMAudio(
            song["url"],
            executable="ffmpeg",
            before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 10 -nostdin",
            options="-vn"
        )

        vc.play(source, after=lambda e: play_next(ctx))
        await ctx.send(f"🎶 Spiele: {song['title']}")
    else:
        queues[ctx.guild.id].append(song)
        await ctx.send(f"📀 Zur Queue: {song['title']}")

# ================= SKIP =================
@bot.command()
async def skip(ctx):
    vc = ctx.voice_client

    if not vc or not vc.is_playing():
        return await ctx.send("❌ Es läuft nichts")

    vc.stop()
    await ctx.send("⏭️ Übersprungen")

# ================= STOP =================
@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("🛑 Gestoppt")

# ================= /HELP =================
from discord import app_commands

@bot.event
async def setup_hook():
    await bot.tree.sync()

@bot.tree.command(name="help", description="Hilfe")
async def help_slash(interaction: discord.Interaction):
    await interaction.response.send_message("Benutze .play <song>", ephemeral=True)

# ================= START =================
bot.run(os.getenv("TOKEN"))









