import discord
from discord.ext import commands
from discord import app_commands, Embed
from discord.ui import View, Button, Modal, TextInput
from database import DatabaseManager

db = DatabaseManager()

class RoleChannelModal(Modal):
    def __init__(self):
        super().__init__(title="Configure Role or Channel")

        self.role_type = TextInput(
            label="Type",
            placeholder="admin, staff, helper, viewer, blocked, reward, ticket_category, transcript_channel",
            required=True, 
            max_length=50
        )
        self.add_item(self.role_type)

        self.id_input = TextInput(
            label="Role/Channel ID", 
            placeholder="Right-click role/channel → Copy ID", 
            required=True,
            max_length=20
        )
        self.add_item(self.id_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            field_type = self.role_type.value.lower().strip()
            
            try:
                field_id = int(self.id_input.value)
            except ValueError:
                await interaction.response.send_message("❌ Invalid ID! Please enter a valid Discord ID.", ephemeral=True)
                return

            role_fields = {
                "admin": "admin_role_id",
                "staff": "staff_role_id", 
                "helper": "helper_role_id",
                "viewer": "viewer_role_id",
                "blocked": "blocked_role_id",
                "reward": "reward_role_id"
            }

            channel_fields = {
                "ticket_category": "ticket_category_id",
                "transcript_channel": "transcript_channel_id"
            }

            if field_type in role_fields:
                # Verify role exists
                role = interaction.guild.get_role(field_id)
                if not role:
                    await interaction.response.send_message("❌ Role not found! Please check the ID.", ephemeral=True)
                    return
                    
                await db.update_server_config(interaction.guild.id, **{role_fields[field_type]: field_id})
                await interaction.response.send_message(f"✅ **{field_type.title()} Role** set to `{role.name}`", ephemeral=True)
                
            elif field_type in channel_fields:
                # Verify channel exists
                channel = interaction.guild.get_channel(field_id)
                if not channel:
                    await interaction.response.send_message("❌ Channel not found! Please check the ID.", ephemeral=True)
                    return
                    
                await db.update_server_config(interaction.guild.id, **{channel_fields[field_type]: field_id})
                await interaction.response.send_message(f"✅ **{field_type.replace('_', ' ').title()}** set to `{channel.name}`", ephemeral=True)
                
            else:
                valid_types = list(role_fields.keys()) + list(channel_fields.keys())
                await interaction.response.send_message(f"❌ Invalid type! Valid types: {', '.join(valid_types)}", ephemeral=True)
                
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

class ViewConfigModal(Modal):
    def __init__(self, config):
        super().__init__(title="Current Server Configuration")
        self.config = config
        
        # Create a text display of current config
        config_text = "Current Configuration:\n\n"
        
        role_mappings = {
            "admin_role_id": "Admin Role",
            "staff_role_id": "Staff Role", 
            "helper_role_id": "Helper Role",
            "viewer_role_id": "Viewer Role",
            "blocked_role_id": "Blocked Role",
            "reward_role_id": "Reward Role"
        }
        
        channel_mappings = {
            "ticket_category_id": "Ticket Category",
            "transcript_channel_id": "Transcript Channel"
        }
        
        for key, label in {**role_mappings, **channel_mappings}.items():
            value = config.get(key)
            if value:
                config_text += f"{label}: {value}\n"
            else:
                config_text += f"{label}: Not set\n"
                
        self.config_display = TextInput(
            label="Configuration",
            default=config_text,
            style=discord.TextStyle.long,
            required=False
        )
        self.add_item(self.config_display)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("Configuration viewed!", ephemeral=True)

class SetupView(View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="🔧 Set Roles/Channels", style=discord.ButtonStyle.primary)
    async def set_roles_channels(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RoleChannelModal())

    @discord.ui.button(label="👁️ View Current Config", style=discord.ButtonStyle.secondary)
    async def view_config(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            config = await db.get_server_config(interaction.guild.id)
            
            embed = discord.Embed(
                title="⚙️ Current Server Configuration",
                color=discord.Color.blue()
            )
            
            # Role configurations
            role_fields = {
                "admin_role_id": "👑 Admin Role",
                "staff_role_id": "🛡️ Staff Role",
                "helper_role_id": "🙋 Helper Role", 
                "viewer_role_id": "👀 Viewer Role",
                "blocked_role_id": "🚫 Blocked Role",
                "reward_role_id": "🏆 Reward Role"
            }
            
            role_text = ""
            for key, label in role_fields.items():
                role_id = config.get(key)
                if role_id:
                    role = interaction.guild.get_role(role_id)
                    role_text += f"{label}: {role.mention if role else 'Role not found'}\n"
                else:
                    role_text += f"{label}: Not set\n"
                    
            embed.add_field(name="🎭 Role Configuration", value=role_text, inline=False)
            
            # Channel configurations
            channel_fields = {
                "ticket_category_id": "🎫 Ticket Category",
                "transcript_channel_id": "📄 Transcript Channel"
            }
            
            channel_text = ""
            for key, label in channel_fields.items():
                channel_id = config.get(key)
                if channel_id:
                    channel = interaction.guild.get_channel(channel_id)
                    channel_text += f"{label}: {channel.mention if channel else 'Channel not found'}\n"
                else:
                    channel_text += f"{label}: Not set\n"
                    
            embed.add_field(name="📺 Channel Configuration", value=channel_text, inline=False)
            
            embed.set_footer(text="Use the 'Set Roles/Channels' button to modify these settings")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error viewing config: {str(e)}", ephemeral=True)

    @discord.ui.button(label="🗑️ Reset Setup", style=discord.ButtonStyle.danger)
    async def reset_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await db.update_server_config(interaction.guild.id,
                                          admin_role_id=None,
                                          staff_role_id=None,
                                          helper_role_id=None,
                                          viewer_role_id=None,
                                          blocked_role_id=None,
                                          reward_role_id=None,
                                          ticket_category_id=None,
                                          transcript_channel_id=None)
            
            embed = discord.Embed(
                title="✅ Setup Reset Complete",
                description="All server configuration has been reset!",
                color=discord.Color.green()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error resetting setup: {str(e)}", ephemeral=True)

    async def on_timeout(self):
        # Disable all buttons when view times out
        for item in self.children:
            item.disabled = True

class SetupCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup", description="Configure server settings (admin only)")
    @app_commands.default_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction):
        """Configure server settings"""
        embed = Embed(
            title="🛠️ Server Setup",
            description="Configure roles and channels for the ticket bot system.",
            color=discord.Color.blurple()
        )
        
        embed.add_field(
            name="🔧 Available Options",
            value="• **Set Roles/Channels** - Configure role and channel IDs\n• **View Current Config** - See current settings\n• **Reset Setup** - Clear all configuration",
            inline=False
        )
        
        embed.add_field(
            name="📝 How to Get IDs",
            value="1. Enable Developer Mode in Discord settings\n2. Right-click on role/channel\n3. Select 'Copy ID'",
            inline=False
        )
        
        view = SetupView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(SetupCommandsCog(bot))
