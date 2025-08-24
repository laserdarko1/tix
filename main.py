import discord
from discord.ext import commands
from discord.ui import View, Select, Modal, TextInput
import os
from dotenv import load_dotenv
from database import DatabaseManager
from flask import Flask

# ---- Bot Setup ----
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
bot.remove_command("help")  # remove default help

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

# -------------------------
# ---- CUSTOM HELP ----
# -------------------------
@bot.command(name="help", help="Shows all bot commands")
async def help_command(ctx):
    embed = discord.Embed(
        title="🛠️ Bot Commands Overview",
        description="Here’s all the commands you can use! Use them wisely 😉",
        color=discord.Color.blurple()
    )

    # Categorize commands manually if needed
    categories = {
        "🎟️ Tickets": ["panel", "setup"],
        "🏆 Utility": ["leaderboard", "help"]
    }

    emoji = {
        "panel": "🎫",
        "setup": "⚙️",
        "leaderboard": "🏅",
        "help": "❓"
    }

    for category, cmds in categories.items():
        value = ""
        for cmd_name in cmds:
            cmd = bot.get_command(cmd_name)
            if cmd:
                value += f"{emoji.get(cmd_name,'')} `!{cmd.name}` — {cmd.help or 'No description'}\n"
        embed.add_field(name=category, value=value, inline=False)

    embed.set_footer(text="Need more help? Contact a server admin!")
    await ctx.send(embed=embed)

# -------------------------
# ---- LEADERBOARD ----
# -------------------------
@bot.command(name="leaderboard", help="Show the top helpers with points")
async def leaderboard(ctx):
    data = await db.get_leaderboard(ctx.guild.id)  # list of (user_id, points)
    if not data:
        return await ctx.send("No leaderboard data yet!")

    embed = discord.Embed(
        title="🏆 Top Helpers Leaderboard",
        description="Highest ranking helpers on this server!",
        color=discord.Color.gold()
    )

    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, (user_id, points) in enumerate(data[:10]):
        member = ctx.guild.get_member(user_id)
        if not member:
            continue
        medal = medals[i] if i < 3 else f"{i+1}."
        lines.append(f"{medal} {member.mention} — **{points} pts**")

    embed.description = "\n".join(lines)
    embed.set_footer(text="Keep helping to climb the leaderboard! 💪")
    await ctx.send(embed=embed)

# -------------------------
# ---- PERMISSIONS ----
# -------------------------
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

# -------------------------
# ---- EVENTS ----
# -------------------------
@bot.event
async def on_ready():
    await db.initialize_database()
    print(f"✅ {bot.user} online!")

# -------------------------
# ---- SETUP COMMAND ----
# -------------------------
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
        await interaction.response.send_message(f"✅ Set to {ch.mention}", ephemeral=True)

# ---- RUN ----
bot.run(TOKEN)
