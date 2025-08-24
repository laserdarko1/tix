import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, Select
import os
from dotenv import load_dotenv
import asyncio
from database import DatabaseManager  # your existing database manager

# ---- Load environment ----
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ---- Remove default help ----
bot.remove_command("help")

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

# ---- Permission Checks ----
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

# ---- Events ----
@bot.event
async def on_ready():
    await db.initialize_database()
    print(f"✅ {bot.user} is online!")

# ---- HELP COMMAND ----
@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="🛠️ Bot Commands Overview",
        description="Here’s all commands available on this server:",
        color=discord.Color.blurple()
    )

    # General Commands
    embed.add_field(name="📋 General Commands", value=(
        "`!help` - Show this help message\n"
        "`!points [user]` - Check points for yourself or another user\n"
        "`!leaderboard` - Show server points leaderboard\n"
        "`!rrules` - Show runner rules\n"
        "`!hrules` - Show helper rules\n"
        "`!proof` - Show proof submission instructions"
    ), inline=False)

    # Ticket Commands
    embed.add_field(name="🎫 Ticket Commands", value=(
        "Use the ticket panel to create tickets\n"
        "`!removehelper @user` - Remove a helper from current ticket (Admin only)"
    ), inline=False)

    # Admin Commands
    embed.add_field(name="⚙️ Admin Commands", value=(
        "`!setup` - Interactive bot configuration\n"
        "`!create` - Create ticket selection panel\n"
        "`!add @user <points>` - Add points to user\n"
        "`!remove @user <points>` - Remove points from user\n"
        "`!setpoints @user <points>` - Set user's points\n"
        "`!restartleaderboard` - Reset all points\n"
        "`!setupreset` - Reset all bot configuration"
    ), inline=False)

    embed.set_footer(text="Need more help? Contact a server admin!")
    await ctx.send(embed=embed)

# ---- LEADERBOARD ----
@bot.command(name="leaderboard")
async def leaderboard(ctx):
    data = await db.get_leaderboard(ctx.guild.id)
    if not data:
        return await ctx.send("No leaderboard data yet!")

    embed = discord.Embed(
        title="🏆 Server Leaderboard",
        description="Top helpers by points",
        color=discord.Color.gold()
    )
    text = ""
    for i, (user_id, points) in enumerate(data, start=1):
        member = ctx.guild.get_member(user_id)
        if member:
            text += f"{i}. {member.mention} — {points} points\n"
        else:
            text += f"{i}. User ID {user_id} — {points} points\n"

    embed.add_field(name="Leaderboard", value=text, inline=False)
    embed.set_footer(text="Keep helping to earn points!")
    await ctx.send(embed=embed)

# ---- SETUP COMMAND ----
@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup(ctx):
    view = SetupView(ctx.guild)
    await ctx.send("🔧 **Bot Setup:** Select what to configure.", view=view)

# ---- SETUP UI ----
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

# ---- PANEL PLACEHOLDER ----
@bot.command(name="panel")
async def panel(ctx):
    await ctx.send("Ticket panel placeholder — implement your ticket creation here.")

# ---- RUN BOT ----
bot.run(TOKEN

