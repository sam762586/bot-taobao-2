import os
import discord
import json
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask

load_dotenv()

# Simple ping endpoint pour Render
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot en ligne sur Render", 200

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

VERIFIED_ROLE_NAME = "🌱 Nouveau"
WELCOME_CHANNEL_NAME = "arrivee"

# Charger la structure du serveur
with open("discord_server_taobao.json", "r", encoding="utf-8") as f:
    server_structure = json.load(f)

@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    guild = ctx.guild

    check_category = discord.utils.get(guild.categories, name="📍・Bienvenue")
    if check_category:
        await ctx.send("⚠️ Le serveur semble déjà configuré.")
        return

    await ctx.send("🔧 Configuration du serveur en cours...")

    for role in server_structure["roles"]:
        if not discord.utils.get(guild.roles, name=role["name"]):
            await guild.create_role(name=role["name"])

    verified_role = discord.utils.get(guild.roles, name=VERIFIED_ROLE_NAME)
    if not verified_role:
        verified_role = await guild.create_role(name=VERIFIED_ROLE_NAME)

    for category in server_structure["categories"]:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            verified_role: discord.PermissionOverwrite(view_channel=True)
        }
        cat = await guild.create_category(category["name"], overwrites=overwrites)
        for channel in category["channels"]:
            if channel["type"] == "text":
                await guild.create_text_channel(channel["name"], category=cat)
            elif channel["type"] == "voice":
                await guild.create_voice_channel(channel["name"], category=cat)

    await ctx.send("✅ Configuration terminée.")

@bot.event
async def on_member_join(member):
    guild = member.guild
    role = discord.utils.get(guild.roles, name=VERIFIED_ROLE_NAME)
    if role:
        try:
            await member.add_roles(role)
            print(f"✅ Rôle '{VERIFIED_ROLE_NAME}' attribué à {member}")
        except Exception as e:
            print(f"Erreur : {e}")

    salon_bienvenue = discord.utils.get(guild.text_channels, name=WELCOME_CHANNEL_NAME)
    if salon_bienvenue:
        try:
            await salon_bienvenue.send(f"👋 Bienvenue {member.mention} sur le serveur !")
        except:
            pass

if __name__ == "__main__":
    import threading

    # Lancer Flask sur un thread secondaire
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()

    # Démarrer le bot
    bot.run(os.getenv("DISCORD_TOKEN"))
