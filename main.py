import discord
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput
import asyncio
import os
from dotenv import load_dotenv
from database import DatabaseManager
from flask import Flask

# ---- Bot Setup ----
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ---- Database ----
db = DatabaseManager()
DEFAULT_POINT_VALUES = {
    "Ultra Speaker Express": 8,
    "Ultra Gramiel Express": 7,
    "4-Man Ultra Daily Express": 4,
    "7-Man Ultra Daily Express": 7,
    "Ultra Weekly Express": 12,
    "Grim Express": 10,
    "Daily Temple Express": 6
}
DEFAULT_HELPER_SLOTS = {
    "7-Man Ultra Daily Express": 6,
    "Grim Express": 6
}
DEFAULT_SLOTS = 3
TICKET_QUESTIONS = [
    ("In-game name?", True),
    ("Server name?", True),
    ("Room number?", True),
    ("Anything else?", False)
]
CUSTOM_COMMANDS = {
    "proof": {"title": "📸 Proof", "desc": "Proof requirements"},
    "hrules": {"title": "📋 Helper Rules", "desc": "Helper guidelines"},
    "rrules": {"title": "📜 Runner Rules", "desc": "Runner guidelines"}
}

# =========================
# ---- HELP COMMAND ----
# =========================
class EmbedHelpCommand(commands.MinimalHelpCommand):
    async def send_bot_help(self, mapping):
        embed = discord.Embed(
            title="🛠️ Bot Commands Overview",
            description="Here’s all the commands you can use! Click a button for more info.",
            color=discord.Color.blurple()
        )
        for cog, commands_list in mapping.items():
            if commands_list:
                name = getattr(cog, "qualified_name", "No Category")
                value = "\n".join(f"**!{cmd.name}** — {cmd.help or 'No description'}" for cmd in commands_list)
                embed.add_field(name=name, value=value, inline=False)
        embed.set_footer(text="Need more help? Contact a server admin!")
        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog):
        embed = discord.Embed(
            title=f"⚡ {cog.qualified_name} Commands",
            color=discord.Color.blurple()
        )
        for cmd in cog.get_commands():
            embed.add_field(name=f"!{cmd.name}", value=cmd.help or "No description", inline=False)
        await self.get_destination().send(embed=embed)

bot.help_command = EmbedHelpCommand()

# =========================
# ---- LEADERBOARD ----
# =========================
@bot.command(name="leaderboard", help="Show the top helpers with points")
async def leaderboard(ctx):
    data = await db.get_leaderboard(ctx.guild.id)  # return list of tuples [(user_id, points)]
    if not data:
        return await ctx.send("No leaderboard data yet!")

    embed = discord.Embed(
        title="🏆 Top Helpers Leaderboard",
        description="The highest ranking helpers in this server!",
        color=discord.Color.gold()
    )
    medals = ["🥇", "🥈", "🥉"]
    for i, (user_id, points) in enumerate(data[:10]):
        member = ctx.guild.get_member(user_id)
        if not member:
            continue
        medal = medals[i] if i < 3 else f"{i+1}."
        embed.add_field(name=f"{medal} {member.display_name}", value=f"Points: **{points}**", inline=False)
    embed.set_footer(text="Keep helping to climb the leaderboard! 💪")
    await ctx.send(embed=embed)

# =========================
# ---- PERMISSIONS ----
# =========================
async def get_config(guild):
    return await db.get_server_config(guild.id) or {}

def has_role(member, role_id):
    return role_id and discord.utils.get(member.roles, id=role_id)

async def is_admin(member):
    cfg = await get_config(member.guild)
    return has_role(member, cfg.get('admin_role_id')) or member.guild_permissions.administrator

async def is_staff(member):
    cfg = await get_config(member.guild)
    return has_role(member, cfg.get('staff_role_id')) or await is_admin(member)

# =========================
# ---- EVENTS ----
# =========================
@bot.event
async def on_ready():
    await db.initialize_database()
    print(f"✅ {bot.user} online!")

# =========================
# ---- SETUP COMMAND ----
# =========================
@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    view = SetupView(ctx.guild)
    await ctx.send("🔧 **Bot Setup:** Select what to configure.", view=view)

class SetupView(View):
    def __init__(self, guild):
        super().__init__(timeout=240)
        self.guild = guild

    @discord.ui.button(label="Admin Role", style=discord.ButtonStyle.danger, emoji="🛡️")
    async def admin_btn(self, interaction, _):
        await interaction.response.send_modal(RoleModal("Admin", "admin_role_id", self.guild))

    @discord.ui.button(label="Staff Role", style=discord.ButtonStyle.primary, emoji="👔")
    async def staff_btn(self, interaction, _):
        await interaction.response.send_modal(RoleModal("Staff", "staff_role_id", self.guild))

    @discord.ui.button(label="Helper Role", style=discord.ButtonStyle.success, emoji="🧑‍💼")
    async def helper_btn(self, interaction, _):
        await interaction.response.send_modal(RoleModal("Helper", "helper_role_id", self.guild))

    @discord.ui.button(label="Reward Role", style=discord.ButtonStyle.success, emoji="🏅")
    async def reward_btn(self, interaction, _):
        await interaction.response.send_modal(RoleModal("Reward", "reward_role_id", self.guild))

    @discord.ui.button(label="Ticket Category", style=discord.ButtonStyle.secondary, emoji="📁")
    async def cat_btn(self, interaction, _):
        await interaction.response.send_modal(ChannelModal("Ticket Category", "ticket_category_id", self.guild, cat=True))

    @discord.ui.button(label="Transcript Channel", style=discord.ButtonStyle.secondary, emoji="📝")
    async def log_btn(self, interaction, _):
        await interaction.response.send_modal(ChannelModal("Transcript Channel", "transcript_channel_id", self.guild))

    @discord.ui.button(label="Finish Setup", style=discord.ButtonStyle.success, emoji="✅")
    async def finish_btn(self, interaction, _):
        await interaction.response.send_message("✅ Setup complete! Use `!panel` to create the ticket panel.", ephemeral=True)
        self.stop()

# ---- Role & Channel Modals ----
class RoleModal(Modal):
    def __init__(self, rolename, key, guild):
        super().__init__(title=f"Set {rolename} Role")
        self.roletype = rolename
        self.key = key
        self.guild = guild
        self.input = TextInput(label="Role ID or name", required=True)
        self.add_item(self.input)

    async def on_submit(self, interaction):
        val = self.input.value.strip()
        role = self.guild.get_role(int(val)) if val.isdigit() else discord.utils.find(lambda r: r.name.lower() == val.lower(), self.guild.roles)
        if not role:
            await interaction.response.send_message("❌ Role not found.", ephemeral=True)
            return
        await db.update_server_config(self.guild.id, **{self.key: role.id})
        await interaction.response.send_message(f"✅ {self.roletype} role set to {role.mention}.", ephemeral=True)

class ChannelModal(Modal):
    def __init__(self, title, key, guild, cat=False):
        super().__init__(title=f"Set {title}")
        self.key = key
        self.guild = guild
        self.cat = cat
        self.input = TextInput(label="Channel/Category ID or name", required=True)
        self.add_item(self.input)

    async def on_submit(self, interaction):
        val = self.input.value.strip()
        ch = None
        if val.isdigit():
            ch = self.guild.get_channel(int(val))
        else:
            if self.cat:
                ch = discord.utils.find(lambda c: c.name.lower() == val.lower(), self.guild.categories)
            else:
                ch = discord.utils.find(lambda c: c.name.lower() == val.lower(), self.guild.text_channels)
        if not ch:
            await interaction.response.send_message("❌ Not found.", ephemeral=True)
            return
        await db.update_server_config(self.guild.id, **{self.key: ch.id})
        await interaction.response.send_message(f"✅ Set to {ch.mention}.", ephemeral=True)

# =========================
# ---- PANEL + TICKETS ----
# =========================
@bot.command()
async def panel(ctx):
    if not await is_staff(ctx.author):
        return await ctx.send("❌ Only staff or admin can create a panel.")
    cfg = await get_config(ctx.guild)
    pts = await db.get_point_values(ctx.guild.id) or DEFAULT_POINT_VALUES
    slots = await db.get_helper_slots(ctx.guild.id) or DEFAULT_HELPER_SLOTS
    desc = (
        "### 🎮 In-game Assistance\n"
        "Select a service below to create a help ticket. Our helpers will assist you!\n\n"
        "### 📜 Guidelines & Rules: Use `!hrules`, `!rrules`, and `!proof` commands\n"
        "📋 **Available Services**\n"
        + "\n".join(f"- **{k}** — **{v} points**" for k, v in pts.items()) +
        "\n\n### ℹ️ How it works\n"
        "1. Select a service\n"
        "2. Fill out the form\n"
        "3. Wait for helpers to join\n"
        "4. Get help in your private ticket!\n"
    )
    embed = discord.Embed(title="🎟️ Ticket Panel", description=desc, color=discord.Color.blurple())
    options = [discord.SelectOption(label=k, value=k, description=f"{pts[k]} pts | {slots.get(k, DEFAULT_SLOTS)} helpers") for k in pts]

    class TicketSelect(Select):
        def __init__(self):
            super().__init__(placeholder="Choose service", min_values=1, max_values=1, options=options)
        async def callback(self, interaction):
            await interaction.response.send_modal(TicketModal(self.values[0], interaction.guild, interaction.user))

    view = View()
    view.add_item(TicketSelect())
    await ctx.send(embed=embed, view=view)

# ---- Ticket Modal ----
class TicketModal(Modal):
    def __init__(self, ticket_type, guild, requester):
        super().__init__(title=f"{ticket_type} Ticket")
        self.ticket_type = ticket_type
        self.guild = guild
        self.requester = requester
        for q, req in TICKET_QUESTIONS:
            self.add_item(TextInput(label=q, required=req))

    async def on_submit(self, interaction):
        cfg = await get_config(self.guild)
        cat = self.guild.get_channel(cfg.get('ticket_category_id'))
        overwrites = {
            self.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        for role_key in ['helper_role_id', 'staff_role_id', 'admin_role_id']:
            role_id = cfg.get(role_key)
            if role_id:
                role = self.guild.get_role(role_id)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        pts = await db.get_point_values(self.guild.id) or DEFAULT_POINT_VALUES
        slots = await db.get_helper_slots(self.guild.id) or DEFAULT_HELPER_SLOTS
        slot_count = slots.get(self.ticket_type, DEFAULT_SLOTS)

        try:
            channel = await self.guild.create_text_channel(
                name=f"{self.ticket_type.lower().replace(' ', '-')}-{interaction.user.name}",
                category=cat,
                overwrites=overwrites
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Could not create ticket: {e}", ephemeral=True)
            return

        embed = discord.Embed(title=f"🆕 {self.ticket_type} Ticket", color=discord.Color.green())
        embed.add_field(name="Requester", value=interaction.user.mention, inline=True)
        for i, inp in enumerate(self.children):
            embed.add_field(name=TICKET_QUESTIONS[i][0], value=inp.value or "None", inline=False)
        embed.add_field(name="Helpers", value="\n".join([f"{i+1}. [Empty]" for i in range(slot_count)]), inline=False)
        embed.add_field(name="Reward", value=f"{pts[self.ticket_type]} points per helper", inline=False)
        embed.set_footer(text="Only staff/admin can close this ticket. Helpers: use the button below to join!")
        await channel.send(embed=embed)
        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)

# =========================
# ---- RUN BOT ----
# =========================
bot.run(TOKEN)
