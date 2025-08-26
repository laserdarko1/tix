import discord
from discord.ext import commands
from discord import app_commands, Embed
from database import DatabaseManager

# Initialize database
db = DatabaseManager()

# Points for each ticket category
CATEGORY_POINTS = {
    "Ultra Speaker Express": 8,
    "Ultra Gramiel Express": 7,
    "4-Man Ultra Daily Express": 4,
    "7-Man Ultra Daily Express": 7,
    "Ultra Weekly Express": 12,
    "Grim Express": 10,
    "Daily Temple Express": 6
}

# Number of helper slots for each ticket category
CATEGORY_SLOTS = {
    "Ultra Speaker Express": 3,
    "Ultra Gramiel Express": 3,
    "4-Man Ultra Daily Express": 3,
    "7-Man Ultra Daily Express": 6,
    "Ultra Weekly Express": 3,
    "Grim Express": 6,
    "Daily Temple Express": 3
}

# Channel name prefix for each category
CATEGORY_CHANNEL_NAMES = {
    "Ultra Speaker Express": "ultra-speaker",
    "Ultra Gramiel Express": "ultra-gramiel",
    "4-Man Ultra Daily Express": "4-man-daily",
    "7-Man Ultra Daily Express": "7-man-daily",
    "Ultra Weekly Express": "weekly-ultra",
    "Grim Express": "grimchallenge",
    "Daily Temple Express": "templeshrine"
}

class TicketSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
        options = [
            discord.SelectOption(
                label=category, 
                value=category, 
                emoji="🎫",
                description=f"{CATEGORY_POINTS[category]} points • {CATEGORY_SLOTS[category]} helpers"
            ) 
            for category in CATEGORY_POINTS.keys()
        ]
        
        self.add_item(TicketSelect(options))

class TicketSelect(discord.ui.Select):
    def __init__(self, options):
        super().__init__(
            placeholder="🎯 Choose a ticket type to get started...", 
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            # Import here to avoid circular imports
            from modules.tickets.ticket_modal import TicketModal
            
            selected_category = self.values[0]
            modal = TicketModal(selected_category, interaction.guild.id)
            await interaction.response.send_modal(modal)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error opening ticket form: {str(e)}", ephemeral=True)

class TicketCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.CATEGORY_POINTS = CATEGORY_POINTS
        self.CATEGORY_SLOTS = CATEGORY_SLOTS
        self.CATEGORY_CHANNEL_NAMES = CATEGORY_CHANNEL_NAMES

    @app_commands.command(name="createpanel", description="Create the ticket selection panel (admin only)")
    @app_commands.default_permissions(administrator=True)
    async def create_ticket_panel(self, interaction: discord.Interaction):
        """Create the ticket selection panel"""
        try:
            embed = Embed(
                title="🎮 In-game Assistance",
                description="Select a service below to create a help ticket. Our helpers will assist you!",
                color=discord.Color.blue()
            )
            
            # Guidelines & Rules section
            embed.add_field(
                name="📜 Guidelines & Rules",
                value="Use /hrules, /rrules, and /proof commands",
                inline=False
            )
            
            # Available Services section
            services_text = (
                "- Ultra Speaker Express — 8 points\n"
                "- Ultra Gramiel Express — 7 points\n"
                "- 4-Man Ultra Daily Express — 4 points\n"
                "- 7-Man Ultra Daily Express — 7 points\n"
                "- Ultra Weekly Express — 12 points\n"
                "- Grim Express — 10 points\n"
                "- Daily Temple Express — 6 points"
            )
            embed.add_field(
                name="📋 Available Services",
                value=services_text,
                inline=False
            )
            
            # How it works section
            how_it_works = (
                "1. Select a service\n"
                "2. Fill out the form\n"
                "3. Wait for helpers to join\n"
                "4. Get help in your private ticket!"
            )
            embed.add_field(
                name="ℹ️ How it works",
                value=how_it_works,
                inline=False
            )
            
            view = TicketSelectView()
            await interaction.response.send_message(embed=embed, view=view)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error creating ticket panel: {str(e)}", ephemeral=True)

    async def create_ticket(self, interaction, category, answers):
        """Create a ticket with the given category and answers"""
        try:
            guild_id = interaction.guild.id

            # Get next ticket number
            ticket_number = await db.get_next_ticket_number(guild_id, category)

            # Channel name
            channel_name = f"{CATEGORY_CHANNEL_NAMES[category]}-{ticket_number}"

            # Get server configuration
            server_config = await db.get_server_config(guild_id)
            if not server_config or not server_config.get("ticket_category_id"):
                await interaction.followup.send("❌ Ticket category not configured! An administrator needs to use `/setup` first.", ephemeral=True)
                return

            # Permissions
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True, read_message_history=True)
            }

            # Add staff/admin permissions
            if server_config.get("admin_role_id"):
                admin_role = interaction.guild.get_role(server_config["admin_role_id"])
                if admin_role:
                    overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True, read_message_history=True)
            
            if server_config.get("staff_role_id"):
                staff_role = interaction.guild.get_role(server_config["staff_role_id"])
                if staff_role:
                    overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            
            # Add helper role permissions (can see and join tickets)
            if server_config.get("helper_role_id"):
                helper_role = interaction.guild.get_role(server_config["helper_role_id"])
                if helper_role:
                    overwrites[helper_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            
            # Add viewer role permissions (read-only access)
            if server_config.get("viewer_role_id"):
                viewer_role = interaction.guild.get_role(server_config["viewer_role_id"])
                if viewer_role:
                    overwrites[viewer_role] = discord.PermissionOverwrite(view_channel=True, send_messages=False, read_message_history=True, add_reactions=False)

            # Create channel
            category_channel = interaction.guild.get_channel(server_config["ticket_category_id"])
            ticket_channel = await interaction.guild.create_text_channel(
                name=channel_name,
                category=category_channel,
                overwrites=overwrites,
                reason=f"{category} ticket created by {interaction.user.display_name}"
            )

            # Import TicketView here to avoid circular imports
            from modules.tickets.ticket_views import TicketView
            
            # Create ticket view
            slots = CATEGORY_SLOTS[category]
            ticket_view = TicketView(interaction.user, category, slots, guild_id, ticket_channel)

            # Create embed
            embed = Embed(
                title=f"🎫 {category} Ticket #{ticket_number}", 
                description=f"Ticket created by {interaction.user.mention}",
                color=discord.Color.green()
            )
            
            embed.add_field(name="👤 Requester", value=interaction.user.mention, inline=True)
            embed.add_field(name="🏆 Points Value", value=f"{CATEGORY_POINTS[category]} points", inline=True)
            embed.add_field(name="👥 Helper Slots", value=f"0/{slots} filled", inline=True)
            
            # Add ticket details
            details_text = ""
            for k, v in answers.items():
                if v and k != "Additional Info":
                    details_text += f"**{k}:** {v}\n"
            
            if details_text:
                embed.add_field(name="📋 Ticket Details", value=details_text, inline=False)
            
            if answers.get("Additional Info"):
                embed.add_field(name="📝 Additional Information", value=answers["Additional Info"], inline=False)
            
            helper_list = [f"{i+1}. [Empty]" for i in range(slots)]
            embed.add_field(name="👥 Helpers", value="\n".join(helper_list), inline=False)
            
            embed.add_field(
                name="💡 Instructions",
                value="• Click **Join as Helper** to assist with this ticket\n• Helpers will earn points when the ticket is completed\n• Use **Close Ticket** when assistance is complete",
                inline=False
            )

            embed.set_footer(text=f"Ticket ID: {ticket_number} | Created")
            embed.timestamp = discord.utils.utcnow()

            # Get helper role for mention
            helper_mention = ""
            if server_config.get("helper_role_id"):
                helper_role = interaction.guild.get_role(server_config["helper_role_id"])
                if helper_role:
                    helper_mention = f" {helper_role.mention}"

            await ticket_channel.send(
                f"🎫 **New {category} Ticket**\n\n"
                f"Hello {interaction.user.mention}! Your ticket has been created.\n"
                f"📢 Calling all helpers!{helper_mention}\n\n"
                f"📋 Helpers can join below to assist you with **{category}**.\n"
                f"🏆 This ticket is worth **{CATEGORY_POINTS[category]} points** per helper.",
                embed=embed,
                view=ticket_view
            )

            # Save ticket in database
            await db.save_active_ticket(guild_id, ticket_channel.id, interaction.user.id, category, ticket_number)

            # Notify user
            success_embed = Embed(
                title="✅ Ticket Created Successfully",
                description=f"Your **{category}** ticket has been created!",
                color=discord.Color.green()
            )
            success_embed.add_field(name="📍 Location", value=ticket_channel.mention, inline=True)
            success_embed.add_field(name="🎫 Ticket Number", value=f"#{ticket_number}", inline=True)
            success_embed.add_field(name="🏆 Point Value", value=f"{CATEGORY_POINTS[category]} points", inline=True)
            
            await interaction.followup.send(embed=success_embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ Error creating ticket: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TicketCommandsCog(bot))
