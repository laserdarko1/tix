import discord
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput
import asyncio
import os
from dotenv import load_dotenv
from database import DatabaseManager

# ---- Bot Setup ----
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
intents = discord.Intents.all()

# ---- Custom Embed Help ----
from discord.ext.commands import DefaultHelpCommand

class EmbedHelpCommand(DefaultHelpCommand):
    def get_ending_note(self):
        return "Need more help? Contact an admin!"

    async def send_pages(self):
        destination = self.get_destination()
        for page in self.paginator.pages:
            embed = discord.Embed(description=page, color=discord.Color.blurple())
            await destination.send(embed=embed)

bot = commands.Bot(command_prefix="!", intents=intents, help_command=EmbedHelpCommand())

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
    print(f"✅ {bot.user} online!")

# ---- Setup Command ----
@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    """Start the interactive bot setup."""
    view = SetupView(ctx.guild)
    await ctx.send("🔧 **Bot Setup:** Select what to configure.", view=view)

# ---- Setup UI ----
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

    @discord.ui.button(label="Custom Commands", style=discord.ButtonStyle.secondary, emoji="📝")
    async def custom_btn(self, interaction, _):
        await interaction.response.send_message("Select which custom command to set:", view=CustomCommandView(self.guild), ephemeral=True)

    @discord.ui.button(label="Finish Setup", style=discord.ButtonStyle.success, emoji="✅")
    async def finish_btn(self, interaction, _):
        await interaction.response.send_message("✅ Setup complete! Use `!panel` to create the ticket panel.", ephemeral=True)
        self.stop()

class CustomCommandView(View):
    def __init__(self, guild):
        super().__init__(timeout=60)
        self.guild = guild
        options = [
            discord.SelectOption(label="Proof Command (!proof)", value="proof"),
            discord.SelectOption(label="Helper Rules (!hrules)", value="hrules"),
            discord.SelectOption(label="Runner Rules (!rrules)", value="rrules"),
        ]
        self.add_item(CustomCommandSelect(options, self.guild))

class CustomCommandSelect(Select):
    def __init__(self, options, guild):
        super().__init__(placeholder="Select a command to set", min_values=1, max_values=1, options=options)
        self.guild = guild

    async def callback(self, interaction):
        cmd = self.values[0]
        await interaction.response.send_modal(CustomCommandModal(cmd, self.guild))

class CustomCommandModal(Modal):
    def __init__(self, cmd, guild):
        super().__init__(title=f"Set {cmd} Command")
        self.cmd = cmd
        self.guild = guild
        self.text = TextInput(label="Text Content", style=discord.TextStyle.paragraph, required=True)
        self.add_item(self.text)
        if cmd == "proof":
            self.img = TextInput(label="Image URL (optional)", required=False)
            self.add_item(self.img)

    async def on_submit(self, interaction):
        img = getattr(self, "img", None)
        image_url = img.value if img and img.value else ""
        await db.set_custom_command(self.guild.id, self.cmd, self.text.value, image_url)
        await interaction.response.send_message(f"✅ `{self.cmd}` command set!", ephemeral=True)

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

# ---- Panel Command ----
@bot.command()
async def panel(ctx):
    """Create a ticket panel."""
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
        + "\n".join(f"- **{k}** — **{v}** points" for k, v in pts.items()) +
        "\n\n### ℹ️ How it works\n"
        "1. Select a service\n"
        "2. Fill out the form\n"
        "3. Wait for helpers to join\n"
        "4. Get help in your private ticket!\n"
    )
    embed = discord.Embed(
        title="🎟️ Ticket Panel",
        description=desc,
        color=discord.Color.blurple()
    )
    options = [
        discord.SelectOption(label=k, value=k, description=f"{pts[k]} pts | {slots.get(k, DEFAULT_SLOTS)} helpers")
        for k in pts
    ]
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
        self.inputs = []
        for q, req in TICKET_QUESTIONS:
            inp = TextInput(label=q, required=req)
            self.add_item(inp)
            self.inputs.append(inp)

    async def on_submit(self, interaction):
        cfg = await get_config(self.guild)
        cat = self.guild.get_channel(cfg.get('ticket_category_id'))
        overwrites = {
            self.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        # Helper role can view/send
        if cfg.get('helper_role_id'):
            helper_role = self.guild.get_role(cfg['helper_role_id'])
            if helper_role: overwrites[helper_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        # Staff/admin can view/send
        if cfg.get('staff_role_id'):
            staff_role = self.guild.get_role(cfg['staff_role_id'])
            if staff_role: overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        if cfg.get('admin_role_id'):
            admin_role = self.guild.get_role(cfg['admin_role_id'])
            if admin_role: overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        pts = await db.get_point_values(self.guild.id) or DEFAULT_POINT_VALUES
        slots = await db.get_helper_slots(self.guild.id) or DEFAULT_HELPER_SLOTS
        slot_count = slots.get(self.ticket_type, DEFAULT_SLOTS)
        # Create channel
        try:
            channel = await self.guild.create_text_channel(
                name=f"{self.ticket_type.lower().replace(' ', '-')}-{interaction.user.name}",
                category=cat,
                overwrites=overwrites
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Could not create ticket: {e}", ephemeral=True)
            return
        embed = discord.Embed(
            title=f"🆕 {self.ticket_type} Ticket",
            color=discord.Color.green()
        )
        embed.add_field(name="Requester", value=interaction.user.mention, inline=True)
        for i, inp in enumerate(self.inputs):
            embed.add_field(name=TICKET_QUESTIONS[i][0], value=inp.value or "None", inline=False)
        embed.add_field(name="Helpers", value="\n".join([f"{i+1}. [Empty]" for i in range(slot_count)]), inline=False)
        embed.add_field(name="Reward", value=f"{pts[self.ticket_type]} points per helper", inline=False)
        embed.set_footer(text="Only staff/admin can close this ticket. Helpers: use the button below to join!")
        view = TicketView(interaction.user, self.ticket_type, slot_count, pts[self.ticket_type], db)
        msg = await channel.send(embed=embed, view=view)
        await channel.purge(limit=1)  # Remove bot-created initial channel message
        await channel.send(f"{interaction.user.mention} Your ticket is ready! Helpers will join soon.")
        await interaction.response.send_message(
            f"✅ Ticket created: {channel.mention}", ephemeral=True
        )

# ---- Ticket View ----
class TicketView(View):
    def __init__(self, owner, ttype, slots, reward, db):
        super().__init__(timeout=None)
        self.owner = owner
        self.ttype = ttype
        self.slots = slots
        self.helpers = []
        self.reward = reward
        self.db = db

    @discord.ui.button(label="Join as Helper", style=discord.ButtonStyle.green, emoji="🙋")
    async def join_btn(self, interaction, btn):
        cfg = await get_config(interaction.guild)
        if cfg.get('helper_role_id'):
            if not has_role(interaction.user, cfg['helper_role_id']) and not await is_staff(interaction.user):
                return await interaction.response.send_message("❌ Only helpers or staff can join.", ephemeral=True)
        if interaction.user in self.helpers:
            return await interaction.response.send_message("❌ Already joined.", ephemeral=True)
        if len(self.helpers) >= self.slots:
            return await interaction.response.send_message("❌ Helper slots full!", ephemeral=True)
        self.helpers.append(interaction.user)
        await interaction.channel.set_permissions(interaction.user, view_channel=True, send_messages=True)
        await self._refresh_embed(interaction)
        await interaction.response.send_message("✅ Joined as helper!", ephemeral=True)

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.grey, emoji="🚪")
    async def leave_btn(self, interaction, btn):
        if interaction.user not in self.helpers:
            return await interaction.response.send_message("❌ You are not a helper in this ticket.", ephemeral=True)
        self.helpers.remove(interaction.user)
        await interaction.channel.set_permissions(interaction.user, overwrite=None)
        await self._refresh_embed(interaction)
        await interaction.response.send_message("👋 You left the ticket.", ephemeral=True)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, emoji="🔒")
    async def close_btn(self, interaction, btn):
        if not await is_staff(interaction.user):
            return await interaction.response.send_message("❌ Only staff or admin can close this ticket.", ephemeral=True)
        # transcript
        messages = []
        async for m in interaction.channel.history(limit=None, oldest_first=True):
            messages.append(f"[{m.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {m.author}: {m.content}")
        transcript = "\n".join(messages)
        cfg = await get_config(interaction.guild)
        logch = interaction.guild.get_channel(cfg.get('transcript_channel_id')) if cfg.get('transcript_channel_id') else None
        if logch:
            if len(transcript) < 1900:
                await logch.send(f"📄 **Transcript for {interaction.channel.name}**\n```{transcript}```")
            else:
                import io
                f = discord.File(fp=io.BytesIO(transcript.encode()), filename=f"transcript-{interaction.channel.name}.txt")
                await logch.send(f"📄 **Transcript for {interaction.channel.name}**", file=f)
        # award points
        for h in self.helpers:
            await db.add_user_points(interaction.guild.id, h.id, self.reward)
        await interaction.response.send_message("🔒 Ticket will be closed & deleted in 5s.")
        await asyncio.sleep(5)
        await interaction.channel.delete()

    async def _refresh_embed(self, interaction):
        embed = interaction.message.embeds[0]
        lines = []
        for i in range(self.slots):
            if i < len(self.helpers):
                lines.append(f"{i+1}. {self.helpers[i].mention}")
            else:
                lines.append(f"{i+1}. [Empty]")
        for idx, field in enumerate(embed.fields):
            if field.name == "Helpers":
                embed.set_field_at(idx, name="Helpers", value="\n".join(lines), inline=False)
        await interaction.message.edit(embed=embed, view=self)

# ---- Points & Leaderboard ----
@bot.command()
async def leaderboard(ctx, page: int = 1):
    """Show leaderboard (10 per page)."""
    pts = await db.get_all_user_points(ctx.guild.id)
    users = sorted(pts.items(), key=lambda x: x[1], reverse=True)
    start = (page - 1) * 10
    end = start + 10
    embed = discord.Embed(
        title="🏆 Helper Leaderboard",
        description="Top helpers based on points awarded for assistance.",
        color=discord.Color.gold()
    )
    if not users:
        embed.add_field(name="No helpers yet!", value="Be the first to help!", inline=False)
    else:
        for idx, (uid, score) in enumerate(users[start:end], start=start+1):
            member = ctx.guild.get_member(uid)
            name = member.name if member else f"User ID {uid}"
            embed.add_field(name=f"{idx}. {name}", value=f"Points: **{score}**", inline=False)
    embed.set_footer(text=f"Page {page}")
    await ctx.send(embed=embed)

# ---- Run Bot ----
bot.run(TOKEN)
