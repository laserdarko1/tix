import discord
from discord.ext import commands
from discord import app_commands, Embed
from database import DatabaseManager

db = DatabaseManager()

class CustomCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rrules", description="Display rules for runners/requesters")
    async def rrules(self, interaction: discord.Interaction):
        """Display custom rules for runners"""
        try:
            command_data = await db.get_custom_command(interaction.guild.id, "rrules")
            if not command_data:
                embed = Embed(
                    title="❌ Not Configured",
                    description="Runner rules have not been configured yet. An administrator needs to use `/setup` to configure custom commands.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            embed = Embed(
                title="📜 Runner Rules",
                description=command_data['content'],
                color=discord.Color.blue()
            )
            embed.set_footer(text="Please follow these rules when creating tickets")
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

    @app_commands.command(name="hrules", description="Display rules for helpers")
    async def hrules(self, interaction: discord.Interaction):
        """Display custom rules for helpers"""
        try:
            command_data = await db.get_custom_command(interaction.guild.id, "hrules")
            if not command_data:
                embed = Embed(
                    title="❌ Not Configured",
                    description="Helper rules have not been configured yet. An administrator needs to use `/setup` to configure custom commands.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            embed = Embed(
                title="📋 Helper Rules",
                description=command_data['content'],
                color=discord.Color.green()
            )
            embed.set_footer(text="Please follow these rules when helping with tickets")
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

    @app_commands.command(name="proof", description="Display proof submission instructions")
    async def proof(self, interaction: discord.Interaction):
        """Display proof submission instructions"""
        try:
            command_data = await db.get_custom_command(interaction.guild.id, "proof")
            if not command_data:
                embed = Embed(
                    title="❌ Not Configured",
                    description="Proof instructions have not been configured yet. An administrator needs to use `/setup` to configure custom commands.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            embed = Embed(
                title="📸 Proof Submission",
                description=command_data['content'],
                color=discord.Color.gold()
            )
            
            if command_data.get('image_url'):
                embed.set_image(url=command_data['image_url'])
            
            embed.set_footer(text="Follow these guidelines for proof submission")
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

# -------------------- LOAD COG --------------------
async def setup(bot):
    await bot.add_cog(CustomCommandsCog(bot))
