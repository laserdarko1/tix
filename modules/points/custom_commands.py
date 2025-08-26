import discord
from discord.ext import commands
from discord import app_commands
from database import DatabaseManager

db = DatabaseManager()

class CustomCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rrules", description="Show rules for ticket requesters")
    async def rrules(self, interaction: discord.Interaction):
        """Show runner/requester rules"""
        try:
            command_data = await db.get_custom_command(interaction.guild.id, "rrules")
            
            if not command_data:
                embed = discord.Embed(
                    title="📜 Runner Rules",
                    description="This command has not been configured yet. An administrator needs to use `/setupcommands` to set up this command.",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📜 Runner Rules",
                description=command_data['content'],
                color=discord.Color.blue()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error displaying rules: {str(e)}", ephemeral=True)

    @app_commands.command(name="hrules", description="Show rules for helpers")
    async def hrules(self, interaction: discord.Interaction):
        """Show helper rules"""
        try:
            command_data = await db.get_custom_command(interaction.guild.id, "hrules")
            
            if not command_data:
                embed = discord.Embed(
                    title="📋 Helper Rules",
                    description="This command has not been configured yet. An administrator needs to use `/setupcommands` to set up this command.",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📋 Helper Rules",
                description=command_data['content'],
                color=discord.Color.green()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error displaying rules: {str(e)}", ephemeral=True)

    @app_commands.command(name="proof", description="Show proof submission guidelines")
    async def proof(self, interaction: discord.Interaction):
        """Show proof submission guidelines"""
        try:
            command_data = await db.get_custom_command(interaction.guild.id, "proof")
            
            if not command_data:
                embed = discord.Embed(
                    title="📸 Proof Instructions",
                    description="This command has not been configured yet. An administrator needs to use `/setupcommands` to set up this command.",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📸 Proof Instructions",
                description=command_data['content'],
                color=discord.Color.purple()
            )
            
            # Add image if provided
            if command_data['image_url']:
                embed.set_image(url=command_data['image_url'])
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error displaying proof instructions: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(CustomCommandsCog(bot))
