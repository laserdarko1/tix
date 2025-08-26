import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal, TextInput, View, Button, Select
from discord import Interaction
from database import DatabaseManager

db = DatabaseManager()

class RoleSelectModal(Modal):
    def __init__(self, role_type: str, role_id: int = None):
        super().__init__(title=f"Set {role_type.title()} Role")
        self.role_type = role_type
        
        self.role_input = TextInput(
            label=f"{role_type.title()} Role ID",
            placeholder="Enter the role ID or mention the role",
            default=str(role_id) if role_id else "",
            required=True
        )
        self.add_item(self.role_input)

    async def on_submit(self, interaction: Interaction):
        try:
            role_input = self.role_input.value.strip()
            
            # Extract role ID from mention or use direct ID
            if role_input.startswith('<@&') and role_input.endswith('>'):
                role_id = int(role_input[3:-1])
            else:
                role_id = int(role_input)
            
            # Verify role exists
            role = interaction.guild.get_role(role_id)
            if not role:
                await interaction.response.send_message("❌ Role not found! Please check the ID and try again.", ephemeral=True)
                return
            
            # Update database
            await db.update_server_config(interaction.guild.id, **{f"{self.role_type}_role_id": role_id})
            
            embed = discord.Embed(
                title="✅ Role Updated",
                description=f"{self.role_type.title()} role has been set to {role.mention}",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ Invalid role ID! Please enter a valid number.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error setting role: {str(e)}", ephemeral=True)

class ChannelSelectModal(Modal):
    def __init__(self, channel_type: str, channel_id: int = None):
        super().__init__(title=f"Set {channel_type.title()}")
        self.channel_type = channel_type
        
        self.channel_input = TextInput(
            label=f"{channel_type.title()} ID",
            placeholder="Enter the channel/category ID or mention it",
            default=str(channel_id) if channel_id else "",
            required=True
        )
        self.add_item(self.channel_input)

    async def on_submit(self, interaction: Interaction):
        try:
            channel_input = self.channel_input.value.strip()
            
            # Extract channel ID from mention or use direct ID
            if channel_input.startswith('<#') and channel_input.endswith('>'):
                channel_id = int(channel_input[2:-1])
            else:
                channel_id = int(channel_input)
            
            # Verify channel exists
            channel = interaction.guild.get_channel(channel_id)
            if not channel:
                await interaction.response.send_message("❌ Channel not found! Please check the ID and try again.", ephemeral=True)
                return
            
            # Update database
            field_name = "ticket_category_id" if self.channel_type == "ticket_category" else "transcript_channel_id"
            await db.update_server_config(interaction.guild.id, **{field_name: channel_id})
            
            embed = discord.Embed(
                title="✅ Channel Updated",
                description=f"{self.channel_type.replace('_', ' ').title()} has been set to {channel.mention}",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ Invalid channel ID! Please enter a valid number.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error setting channel: {str(e)}", ephemeral=True)

class OpeningPointsModal(Modal):
    def __init__(self, current_points: int = 0):
        super().__init__(title="Set Opening Points")
        
        self.points_input = TextInput(
            label="Points for Opening Tickets",
            placeholder="Enter points users get for opening tickets (0 to disable)",
            default=str(current_points),
            required=True
        )
        self.add_item(self.points_input)

    async def on_submit(self, interaction: Interaction):
        try:
            points = int(self.points_input.value)
            
            if points < 0:
                await interaction.response.send_message("❌ Points cannot be negative!", ephemeral=True)
                return
            
            # Update database
            await db.update_server_config(interaction.guild.id, opening_points=points)
            
            embed = discord.Embed(
                title="✅ Opening Points Updated",
                description=f"Users will now receive **{points} points** for opening tickets" if points > 0 else "Opening points have been disabled",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ Invalid number! Please enter a valid number.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error setting opening points: {str(e)}", ephemeral=True)

class SetupView(View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="👑 Admin Role", style=discord.ButtonStyle.primary, emoji="👑")
    async def admin_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await db.get_server_config(interaction.guild.id)
        current_id = config.get("admin_role_id")
        await interaction.response.send_modal(RoleSelectModal("admin", current_id))

    @discord.ui.button(label="🛡️ Staff Role", style=discord.ButtonStyle.primary, emoji="🛡️")
    async def staff_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await db.get_server_config(interaction.guild.id)
        current_id = config.get("staff_role_id")
        await interaction.response.send_modal(RoleSelectModal("staff", current_id))

    @discord.ui.button(label="🙋 Helper Role", style=discord.ButtonStyle.primary, emoji="🙋")
    async def helper_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await db.get_server_config(interaction.guild.id)
        current_id = config.get("helper_role_id")
        await interaction.response.send_modal(RoleSelectModal("helper", current_id))

    @discord.ui.button(label="👀 Viewer Role", style=discord.ButtonStyle.primary, emoji="👀")
    async def viewer_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await db.get_server_config(interaction.guild.id)
        current_id = config.get("viewer_role_id")
        await interaction.response.send_modal(RoleSelectModal("viewer", current_id))

    @discord.ui.button(label="🚫 Blocked Role", style=discord.ButtonStyle.danger, emoji="🚫")
    async def blocked_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await db.get_server_config(interaction.guild.id)
        current_id = config.get("blocked_role_id")
        await interaction.response.send_modal(RoleSelectModal("blocked", current_id))

    @discord.ui.button(label="🏆 Reward Role", style=discord.ButtonStyle.secondary, emoji="🏆")
    async def reward_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await db.get_server_config(interaction.guild.id)
        current_id = config.get("reward_role_id")
        await interaction.response.send_modal(RoleSelectModal("reward", current_id))

    @discord.ui.button(label="📁 Ticket Category", style=discord.ButtonStyle.secondary, emoji="📁")
    async def ticket_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await db.get_server_config(interaction.guild.id)
        current_id = config.get("ticket_category_id")
        await interaction.response.send_modal(ChannelSelectModal("ticket_category", current_id))

    @discord.ui.button(label="📄 Transcript Channel", style=discord.ButtonStyle.secondary, emoji="📄")
    async def transcript_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await db.get_server_config(interaction.guild.id)
        current_id = config.get("transcript_channel_id")
        await interaction.response.send_modal(ChannelSelectModal("transcript_channel", current_id))

    @discord.ui.button(label="💰 Opening Points", style=discord.ButtonStyle.success, emoji="💰")
    async def opening_points(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await db.get_server_config(interaction.guild.id)
        current_points = config.get("opening_points", 0)
        await interaction.response.send_modal(OpeningPointsModal(current_points))

    @discord.ui.button(label="📋 View Config", style=discord.ButtonStyle.success, emoji="📋")
    async def view_config(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            config = await db.get_server_config(interaction.guild.id)
            
            embed = discord.Embed(
                title="🛠️ Server Configuration",
                description="Current server settings:",
                color=discord.Color.blue()
            )
            
            # Roles section
            roles_text = ""
            role_fields = [
                ("Admin", "admin_role_id"),
                ("Staff", "staff_role_id"),
                ("Helper", "helper_role_id"),
                ("Viewer", "viewer_role_id"),
                ("Blocked", "blocked_role_id"),
                ("Reward", "reward_role_id")
            ]
            
            for role_name, field_name in role_fields:
                role_id = config.get(field_name)
                if role_id:
                    role = interaction.guild.get_role(role_id)
                    roles_text += f"**{role_name}:** {role.mention if role else '❌ Role not found'}\n"
                else:
                    roles_text += f"**{role_name}:** ❌ Not set\n"
            
            embed.add_field(name="🎭 Roles", value=roles_text, inline=False)
            
            # Channels section
            channels_text = ""
            channel_fields = [
                ("Ticket Category", "ticket_category_id"),
                ("Transcript Channel", "transcript_channel_id")
            ]
            
            for channel_name, field_name in channel_fields:
                channel_id = config.get(field_name)
                if channel_id:
                    channel = interaction.guild.get_channel(channel_id)
                    channels_text += f"**{channel_name}:** {channel.mention if channel else '❌ Channel not found'}\n"
                else:
                    channels_text += f"**{channel_name}:** ❌ Not set\n"
            
            embed.add_field(name="📁 Channels", value=channels_text, inline=False)
            
            # Points section
            opening_points = config.get("opening_points", 0)
            points_text = f"**Opening Points:** {opening_points} points per ticket"
            if opening_points == 0:
                points_text += " (Disabled)"
            
            embed.add_field(name="💰 Points System", value=points_text, inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error viewing configuration: {str(e)}", ephemeral=True)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

class SetupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup", description="Configure server settings (admin only)")
    @app_commands.default_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction):
        """Configure server settings"""
        embed = discord.Embed(
            title="🛠️ Server Setup",
            description="Configure your server settings for the ticket system.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🎭 Roles",
            value="Set up admin, staff, helper, viewer, blocked, and reward roles",
            inline=False
        )
        
        embed.add_field(
            name="📁 Channels",
            value="Configure ticket category and transcript channel",
            inline=False
        )
        
        embed.add_field(
            name="💰 Points System",
            value="Set points users earn for opening tickets",
            inline=False
        )
        
        embed.add_field(
            name="💡 Tips",
            value="• Use role/channel IDs or mentions\n• Reward role is assigned to helpers when they join tickets\n• Opening points are awarded when users create tickets\n• Use 'View Config' to see current settings",
            inline=False
        )
        
        view = SetupView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(SetupCog(bot))
