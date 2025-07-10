import os
import discord
from discord.ext import commands
from discord.ui import View, Button
from dotenv import load_dotenv
import asyncio
from keep_alive import keep_alive  # 👈 Important pour Render

# Charger les variables d'environnement
load_dotenv()
token = os.getenv("DISCORD_TOKEN")
if not token:
    raise ValueError("❌ Le token du bot est manquant dans le fichier .env")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

TICKET_CATEGORY_NAME = "🎟️・Tickets"
TICKET_PANEL_CHANNEL_NAME = "📑︱tickets"
RECHERCHE_CHANNEL_NAME = "recherche-produit"
ADMIN_ROLE_NAME = "👑 Admin"
VERIFIED_ROLE_NAME = "🌱 Nouveau"
RULES_CHANNEL_NAME = "regles"
LOG_CHANNEL_NAME = "🧾︱logs-tickets"

created_tickets = {}

# ---------- BOUTON "ACCEPTER LE RÈGLEMENT" ----------
class AcceptRulesButton(Button):
    def __init__(self, member_id):
        super().__init__(label="✅ Accepter le règlement", style=discord.ButtonStyle.success)
        self.member_id = member_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.member_id:
            await interaction.response.send_message("❗ Ce bouton ne t'est pas destiné.", ephemeral=True)
            return

        role = discord.utils.get(interaction.guild.roles, name=VERIFIED_ROLE_NAME)
        if not role:
            role = await interaction.guild.create_role(name=VERIFIED_ROLE_NAME)

        await interaction.user.add_roles(role)
        await open_verification_ticket(interaction.user, interaction.guild)
        await interaction.message.delete()
        await interaction.response.send_message("✅ Merci d’avoir accepté le règlement !", ephemeral=True)

class AcceptRulesView(View):
    def __init__(self, member_id):
        super().__init__(timeout=None)
        self.add_item(AcceptRulesButton(member_id))

# ---------- BOUTON POUR FERMER UN TICKET ----------
class CloseButton(Button):
    def __init__(self):
        super().__init__(label="🗑️ Fermer le ticket", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        for uid, cid in created_tickets.items():
            if cid == interaction.channel.id:
                created_tickets.pop(uid, None)
                break

        await interaction.response.send_message("Fermeture dans 3 secondes...", ephemeral=True)
        await asyncio.sleep(3)
        await interaction.channel.delete()

# ---------- BOUTON POUR RECHERCHE PRODUIT ----------
class RechercheProduitButton(Button):
    def __init__(self):
        super().__init__(label="📸 Faire une demande de recherche produit", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        author = interaction.user
        guild = interaction.guild

        if author.id in created_tickets:
            await interaction.response.send_message("⚠️ Tu as déjà un ticket ouvert.", ephemeral=True)
            return

        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if not category:
            category = await guild.create_category(TICKET_CATEGORY_NAME)

        admin_role = discord.utils.get(guild.roles, name=ADMIN_ROLE_NAME)
        if not admin_role:
            admin_role = await guild.create_role(name=ADMIN_ROLE_NAME)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            author: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            admin_role: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        ticket_name = f"recherche-{author.name.lower()[:20]}"
        channel = await guild.create_text_channel(ticket_name, category=category, overwrites=overwrites)
        created_tickets[author.id] = channel.id

        view = View()
        view.add_item(CloseButton())

        await channel.send(
            f"{admin_role.mention} | {author.mention} a fait une demande de recherche produit. "
            f"Merci d’envoyer une **photo** du produit recherché et de préciser si vous voulez une réplique ou l’original.",
            view=view
        )
        await interaction.response.send_message("✅ Ticket de recherche créé !", ephemeral=True)

class RechercheProduitView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RechercheProduitButton())

# ---------- CRÉATION D'UN TICKET DE VÉRIFICATION ----------
async def open_verification_ticket(user, guild):
    category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
    if not category:
        category = await guild.create_category(TICKET_CATEGORY_NAME)

    admin_role = discord.utils.get(guild.roles, name=ADMIN_ROLE_NAME)
    if not admin_role:
        admin_role = await guild.create_role(name=ADMIN_ROLE_NAME)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        admin_role: discord.PermissionOverwrite(view_channel=True, send_messages=True)
    }

    ticket_name = f"verification-{user.name.lower()[:20]}"
    existing = discord.utils.get(guild.text_channels, name=ticket_name)
    if existing:
        return

    channel = await guild.create_text_channel(ticket_name, category=category, overwrites=overwrites)
    created_tickets[user.id] = channel.id

    view = View()
    view.add_item(CloseButton())

    await channel.send(f"{admin_role.mention} | {user.mention} a accepté le règlement. Merci de vérifier s’il est éligible au rôle premium.", view=view)

# ---------- BOUTONS MULTI-TICKETS ----------
class TicketButton(Button):
    def __init__(self, label, ticket_type):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.ticket_type = ticket_type

    async def callback(self, interaction: discord.Interaction):
        author = interaction.user
        guild = interaction.guild

        if author.id in created_tickets:
            await interaction.response.send_message("⚠️ Tu as déjà un ticket ouvert.", ephemeral=True)
            return

        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if not category:
            category = await guild.create_category(TICKET_CATEGORY_NAME)

        admin_role = discord.utils.get(guild.roles, name=ADMIN_ROLE_NAME)
        if not admin_role:
            admin_role = await guild.create_role(name=ADMIN_ROLE_NAME)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            author: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            admin_role: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        ticket_name = f"ticket-{author.name.lower()[:20]}"
        channel = await guild.create_text_channel(ticket_name, category=category, overwrites=overwrites)
        created_tickets[author.id] = channel.id

        view = View()
        view.add_item(CloseButton())

        await channel.send(f"{author.mention} a ouvert un ticket : **{self.ticket_type}**", view=view)
        await interaction.response.send_message("✅ Ticket créé en DM avec succès !", ephemeral=True)

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketButton("📦 Commande", "commande"))
        self.add_item(TicketButton("🤝 Partenariat", "partenariat"))
        self.add_item(TicketButton("❓ Autre", "autre"))

# ---------- EVENTS ----------
@bot.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {bot.user}")

    for guild in bot.guilds:
        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if not category:
            category = await guild.create_category(TICKET_CATEGORY_NAME)

        panel_channel = discord.utils.get(guild.text_channels, name=TICKET_PANEL_CHANNEL_NAME)
        if not panel_channel:
            panel_channel = await guild.create_text_channel(TICKET_PANEL_CHANNEL_NAME, category=category)

        async for msg in panel_channel.history(limit=20):
            if msg.author == bot.user:
                await msg.delete()

        embed = discord.Embed(
            title="📩 Ouvre un ticket",
            description="Clique sur un des boutons ci-dessous pour recevoir un ticket en message privé",
            color=0x2ecc71
        )
        await panel_channel.send(embed=embed, view=TicketView())

        recherche_channel = discord.utils.get(guild.text_channels, name=RECHERCHE_CHANNEL_NAME)
        if not recherche_channel:
            recherche_channel = await guild.create_text_channel(RECHERCHE_CHANNEL_NAME)

        async for msg in recherche_channel.history(limit=20):
            if msg.author == bot.user:
                await msg.delete()

        recherche_embed = discord.Embed(
            title="🔍 Recherche de produit",
            description="Tu cherches un article ? Clique sur le bouton ci-dessous, envoie une photo et précise si tu veux une réplique ou l’original.",
            color=0x3498db
        )
        await recherche_channel.send(embed=recherche_embed, view=RechercheProduitView())

        regles_channel = discord.utils.get(guild.text_channels, name=RULES_CHANNEL_NAME)
        if regles_channel:
            await regles_channel.edit(overwrites={
                guild.default_role: discord.PermissionOverwrite(send_messages=False),
                guild.me: discord.PermissionOverwrite(send_messages=True)
            })

@bot.event
async def on_member_join(member):
    guild = member.guild
    regles_channel = discord.utils.get(guild.text_channels, name=RULES_CHANNEL_NAME)
    if not regles_channel:
        regles_channel = await guild.create_text_channel(RULES_CHANNEL_NAME)

    async for msg in regles_channel.history(limit=100):
        if msg.author == bot.user:
            await msg.delete()

    embed = discord.Embed(
        title="📜 Règlement",
        description=f"Bienvenue {member.mention} ! Merci de lire et accepter le règlement ci-dessous.",
        color=0xf1c40f
    )
    message = await regles_channel.send(embed=embed)
    await message.pin()
    view = AcceptRulesView(member.id)
    await message.edit(view=view)

# ---------- COMMANDE ADMIN POUR PANEL RECHERCHE ----------
@bot.command()
@commands.has_permissions(administrator=True)
async def recherche_panel(ctx):
    recherche_embed = discord.Embed(
        title="🔍 Recherche de produit",
        description="Tu cherches un article ? Clique sur le bouton ci-dessous, envoie une photo et précise si tu veux une réplique ou l’original.",
        color=0x3498db
    )
    await ctx.send(embed=recherche_embed, view=RechercheProduitView())

# ---------- LANCEMENT ----------
keep_alive()  # 👈 Nécessaire pour Render
bot.run(token)
