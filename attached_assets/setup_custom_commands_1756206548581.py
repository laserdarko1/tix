import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal, TextInput, View, Button
from discord import Interaction
from database import DatabaseManager

db = DatabaseManager()

class CustomCommandModal(Modal):
    def __init__(self, command_name: str, existing_content: str = "", existing_image: str = ""):
        super().__init__(title=f"Setup {command_name.title()} Command")
        self.command_name = command_name

        self.content_input = TextInput(
            label="Command Content", 
            placeholder="Enter the command content...", 
            default=existing_content, 
            style=discord.TextStyle.long, 
            max_length=2000,
            required=True
        )
        self.add_item(self.content_input)

        if command_name == "proof":
            self.image_input = TextInput(
                label="Image URL (Optional)", 
                placeholder="https://example.com/image.png", 
                default=existing_image, 
                required=False,
                max_length=500
            )
            self.add_item(self.image_input)

    async def on_submit(self, interaction: Interaction):
        try:
            content = self.content_input.value
            image_url = getattr(self, 'image_input', None)
            image_url = image_url.value if image_url else ""
            
            await db.set_custom_command(interaction.guild.id, self.command_name, content, image_url)
            
            embed = discord.Embed(
                title="✅ Command Configured",
                description=f"Custom command `/{self.command_name}` has been successfully configured!",
                color=discord.Color.green()
            )
            embed.add_field(name="Command", value=f"/{self.command_name}", inline=True)
            embed.add_field(name="Content Length", value=f"{len(content)} characters", inline=True)
            
            if image_url:
                embed.add_field(name="Image URL", value="✅ Included", inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error configuring command: {str(e)}", ephemeral=True)

class CustomCommandView(View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="📜 Runner Rules", style=discord.ButtonStyle.primary, emoji="📜")
    async def setup_rrules(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            existing = await db.get_custom_command(interaction.guild.id, "rrules")
            content = existing['content'] if existing else ""
            await interaction.response.send_modal(CustomCommandModal("rrules", content))
        except Exception as e:
            await interaction.response.send_message(f"❌ Error opening modal: {str(e)}", ephemeral=True)

    @discord.ui.button(label="📋 Helper Rules", style=discord.ButtonStyle.primary, emoji="📋")
    async def setup_hrules(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            existing = await db.get_custom_command(interaction.guild.id, "hrules")
            content = existing['content'] if existing else ""
            await interaction.response.send_modal(CustomCommandModal("hrules", content))
        except Exception as e:
            await interaction.response.send_message(f"❌ Error opening modal: {str(e)}", ephemeral=True)

    @discord.ui.button(label="📸 Proof Instructions", style=discord.ButtonStyle.primary, emoji="📸")
    async def setup_proof(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            existing = await db.get_custom_command(interaction.guild.id, "proof")
            content = existing['content'] if existing else ""
            image = existing['image_url'] if existing else ""
            await interaction.response.send_modal(CustomCommandModal("proof", content, image))
        except Exception as e:
            await interaction.response.send_message(f"❌ Error opening modal: {str(e)}", ephemeral=True)

    @discord.ui.button(label="👁️ View Commands", style=discord.ButtonStyle.secondary, emoji="👁️")
    async def view_commands(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            embed = discord.Embed(
                title="📋 Current Custom Commands",
                description="Here are the current custom command configurations:",
                color=discord.Color.blue()
            )
            
            commands = ["rrules", "hrules", "proof"]
            for cmd in commands:
                data = await db.get_custom_command(interaction.guild.id, cmd)
                if data:
                    content_preview = data['content'][:100] + "..." if len(data['content']) > 100 else data['content']
                    status = f"✅ Configured\n*{content_preview}*"
                    if cmd == "proof" and data.get('image_url'):
                        status += "\n🖼️ Has image"
                else:
                    status = "❌ Not configured"
                
                embed.add_field(
                    name=f"/{cmd}",
                    value=status,
                    inline=False
                )
            
            embed.set_footer(text="Use the buttons above to configure these commands")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error viewing commands: {str(e)}", ephemeral=True)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

class SetupCustomCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setupcommands", description="Configure custom commands (admin only)")
    @app_commands.default_permissions(administrator=True)
    async def setupcommands(self, interaction: discord.Interaction):
        """Configure custom commands"""
        embed = discord.Embed(
            title="🛠️ Setup Custom Commands",
            description="Configure the custom information commands for your server.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📜 Runner Rules (/rrules)", 
            value="Rules and guidelines for users requesting help", 
            inline=True
        )
        embed.add_field(
            name="📋 Helper Rules (/hrules)", 
            value="Rules and guidelines for users providing help", 
            inline=True
        )
        embed.add_field(
            name="📸 Proof Instructions (/proof)", 
            value="Instructions for submitting proof (supports images)", 
            inline=True
        )
        
        embed.add_field(
            name="💡 Tips",
            value="• Use markdown formatting for better appearance\n• Keep content concise but informative\n• Use the View Commands button to see current configs",
            inline=False
        )
        
        view = CustomCommandView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(SetupCustomCommandsCog(bot))
